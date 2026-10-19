"""Generic UIA fallback for non-standard dialogs / 非标准对话框通用 UIA 兜底 (P1).

These tools are the only place where low-level control targeting is allowed.
When a dialog is not ``#32770``, callers should prefer this layer and expect
warning logs. P1 是唯一允许按 control_id 操作的层；非标准对话框会打告警日志。
"""

from __future__ import annotations

import json
import warnings
from typing import Any

from win_dialog_agent.config import get_settings
from win_dialog_agent.dialogs import (
    DialogError,
    _safe_class_name,
    _safe_elem_text,
    _set_edit_value,
    _wrap_access_errors,
    dialog_info_from_element,
    resolve_window,
)
from win_dialog_agent.logging_utils import get_logger, text_digest

logger = get_logger(__name__)


def _warn_nonstandard(handle_id: str, class_name: str) -> None:
    cfg = get_settings()
    if class_name != cfg.standard_class_name:
        msg = (
            f"Non-standard dialog hit UIA fallback: handle={handle_id} "
            f"class_name={class_name!r}. Prefer semantic tools for #32770. "
            f"非标准对话框走 UIA 兜底，已记录告警。"
        )
        logger.warning(msg)
        warnings.warn(msg, UserWarning, stacklevel=3)


def _control_id_of(elem: Any, index: int) -> str:
    """Stable-enough id: automation_id if present, else type:index:namehash."""
    try:
        ei = elem.element_info
        auto = str(getattr(ei, "automation_id", "") or "").strip()
        if auto:
            return f"auto:{auto}"
        ct = str(getattr(ei, "control_type", "") or "Unknown")
        name = (getattr(ei, "name", None) or "")[:40]
        return f"idx:{index}:{ct}:{text_digest(name).split()[0]}"
    except Exception:  # noqa: BLE001
        return f"idx:{index}"


def _enumerate_controls(win: Any) -> list[tuple[str, Any]]:
    items: list[tuple[str, Any]] = []
    try:
        for i, elem in enumerate(win.descendants()):
            items.append((_control_id_of(elem, i), elem))
    except Exception as exc:  # noqa: BLE001
        raise _wrap_access_errors(exc) from exc
    return items


def _match_control(
    elem: Any,
    *,
    control_type: str | None,
    text: str | None,
) -> bool:
    try:
        ei = elem.element_info
        if control_type:
            ct = str(getattr(ei, "control_type", "") or "")
            if ct.casefold() != control_type.casefold():
                return False
        if text:
            name = (getattr(ei, "name", None) or "").strip()
            if text not in name and name.casefold() != text.casefold():
                return False
        return True
    except Exception:  # noqa: BLE001
        return False


def uia_find(
    handle_id: str,
    control_type: str | None = None,
    text: str | None = None,
    *,
    backend: Any | None = None,
) -> list[dict[str, Any]]:
    """Find controls inside a dialog by optional control_type / text.

    在对话框内按条件查找控件。
    """
    win = resolve_window(handle_id, backend)
    class_name = _safe_class_name(win)
    _warn_nonstandard(handle_id, class_name)

    hits: list[dict[str, Any]] = []
    for cid, elem in _enumerate_controls(win):
        if not _match_control(elem, control_type=control_type, text=text):
            continue
        try:
            ei = elem.element_info
            hits.append(
                {
                    "control_id": cid,
                    "control_type": str(getattr(ei, "control_type", "") or ""),
                    "name": (getattr(ei, "name", None) or "")[:200],
                    "automation_id": str(getattr(ei, "automation_id", "") or ""),
                    "is_enabled": bool(getattr(ei, "enabled", True)),
                }
            )
        except Exception:  # noqa: BLE001
            continue
    logger.info("uia_find handle=%s hits=%s", handle_id, len(hits))
    return hits


def _resolve_control(handle_id: str, control_id: str, *, backend: Any | None = None) -> Any:
    win = resolve_window(handle_id, backend)
    class_name = _safe_class_name(win)
    _warn_nonstandard(handle_id, class_name)
    for cid, elem in _enumerate_controls(win):
        if cid == control_id:
            return elem
    raise DialogError(f"control_id not found: {control_id!r} / 未找到控件")


def uia_click(
    handle_id: str,
    control_id: str,
    *,
    backend: Any | None = None,
) -> str:
    """Click a control by control_id from ``uia_find`` / ``uia_snapshot``.

    按 control_id 点击控件。优先 invoke/click，避免坐标。
    """
    elem = _resolve_control(handle_id, control_id, backend=backend)
    try:
        if hasattr(elem, "invoke"):
            elem.invoke()
        elif hasattr(elem, "click"):
            elem.click()
        else:
            # Absolute last resort for odd custom controls — still logged as fallback
            logger.warning(
                "uia_click using click_input fallback control_id=%s (non-semantic)",
                control_id,
            )
            elem.click_input()
    except Exception as exc:  # noqa: BLE001
        raise _wrap_access_errors(exc) from exc
    logger.info(
        "uia_click handle=%s control_id=%s name=%s",
        handle_id,
        control_id,
        text_digest(_safe_elem_text(elem)),
    )
    return f"clicked:{control_id}"


def uia_set_text(
    handle_id: str,
    control_id: str,
    text: str,
    *,
    backend: Any | None = None,
) -> str:
    """Set text on a control identified by control_id."""
    elem = _resolve_control(handle_id, control_id, backend=backend)
    try:
        _set_edit_value(elem, text)
    except DialogError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise _wrap_access_errors(exc) from exc
    logger.info("uia_set_text handle=%s control_id=%s", handle_id, control_id)
    return "ok"


def uia_snapshot(
    handle_id: str,
    *,
    backend: Any | None = None,
    max_nodes: int = 120,
) -> dict[str, Any]:
    """Return a compact control tree JSON for LLM reasoning on unknown dialogs.

    返回精简控件树 JSON，供未知对话框推理。
    """
    win = resolve_window(handle_id, backend)
    info = dialog_info_from_element(win)
    class_name = info.class_name if info else _safe_class_name(win)
    _warn_nonstandard(handle_id, class_name)

    nodes: list[dict[str, Any]] = []
    for cid, elem in _enumerate_controls(win):
        if len(nodes) >= max_nodes:
            break
        try:
            ei = elem.element_info
            name = (getattr(ei, "name", None) or "")[:200]
            ct = str(getattr(ei, "control_type", "") or "")
            if not name and ct.casefold() in {"pane", "group", "thumb", "separator"}:
                continue
            nodes.append(
                {
                    "control_id": cid,
                    "control_type": ct,
                    "name": name,
                    "automation_id": str(getattr(ei, "automation_id", "") or ""),
                    "is_enabled": bool(getattr(ei, "enabled", True)),
                    "is_password": bool(getattr(ei, "is_password", False)),
                }
            )
        except Exception:  # noqa: BLE001
            continue

    payload = {
        "dialog": info.to_dict() if info else {"handle_id": handle_id},
        "nodes": nodes,
        "node_count": len(nodes),
        "truncated": len(nodes) >= max_nodes,
        "path": "uia_fallback",
    }
    logger.info(
        "uia_snapshot handle=%s nodes=%s digest=%s",
        handle_id,
        len(nodes),
        text_digest(json.dumps(payload["dialog"], ensure_ascii=False)),
    )
    return payload
