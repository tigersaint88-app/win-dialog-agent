"""Standard Windows dialog discovery and semantic actions / 标准对话框发现与语义操作.

P0 layer: no coordinate clicks. Uses pywinauto UIA backend.
P0 层禁止坐标点击；使用 pywinauto UIA 后端。

Architecture: find-window vs do-action are separated so unit tests can mock the finder.
找窗口与做动作分离，便于无副作用单测。
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Protocol

from win_dialog_agent.aliases import (
    FILENAME_FIELD_ALIASES,
    MESSAGEBOX_CHOICE_MAP,
    expand_label_candidates,
    labels_match,
    looks_like_password_field,
    normalize_label,
)
from win_dialog_agent.config import Settings, get_settings
from win_dialog_agent.logging_utils import get_logger, path_digest, text_digest

logger = get_logger(__name__)

STANDARD_DIALOG_CLASS = "#32770"


class DialogError(Exception):
    """Base error for dialog operations."""


class DialogNotFoundError(DialogError):
    """No matching dialog within timeout."""


class DialogAccessError(DialogError):
    """Dialog exists but is not reachable (elevation / secure desktop)."""


class UnsafeControlError(DialogError):
    """Refused because the target looks like a password field."""


@dataclass(frozen=True)
class DialogInfo:
    """Lightweight dialog identity returned to callers / agents."""

    handle_id: str
    title: str
    class_name: str
    is_standard: bool
    pid: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ControlSummary:
    control_type: str
    name: str
    automation_id: str = ""
    is_enabled: bool = True
    is_password: bool = False
    actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class WindowBackend(Protocol):
    """Abstraction over pywinauto Desktop for testability."""

    def list_top_level(self, class_name: str | None = None) -> list[Any]: ...

    def from_handle(self, hwnd: int) -> Any: ...


class PywinautoBackend:
    """Default UIA backend wrapper."""

    def __init__(self) -> None:
        from pywinauto import Desktop

        self._desktop = Desktop(backend="uia")

    def list_top_level(self, class_name: str | None = None) -> list[Any]:
        try:
            if class_name:
                return list(self._desktop.windows(class_name=class_name, visible_only=True))
            return list(self._desktop.windows(visible_only=True))
        except BaseException as exc:  # noqa: BLE001 — COM / RPC can raise BaseException subclasses
            # Includes pywinauto COM failures; never crash the agent process.
            logger.warning("list_top_level failed: %s", exc)
            return []

    def from_handle(self, hwnd: int) -> Any:
        from pywinauto import Application

        app = Application(backend="uia").connect(handle=hwnd)
        return app.window(handle=hwnd)


_backend: WindowBackend | None = None


def get_backend() -> WindowBackend:
    global _backend
    if _backend is None:
        _backend = PywinautoBackend()
    return _backend


def set_backend(backend: WindowBackend | None) -> None:
    """Inject a mock backend for tests."""
    global _backend
    _backend = backend


def handle_to_id(hwnd: int) -> str:
    return f"0x{int(hwnd):08X}"


def id_to_handle(handle_id: str) -> int:
    text = (handle_id or "").strip()
    if text.lower().startswith("0x"):
        return int(text, 16)
    return int(text)


def _safe_elem_text(elem: Any) -> str:
    for attr in ("window_text", "element_info"):
        try:
            if attr == "window_text":
                return (elem.window_text() or "").strip()
            info = elem.element_info
            return (getattr(info, "name", None) or "").strip()
        except Exception:  # noqa: BLE001
            continue
    return ""


def _safe_class_name(elem: Any) -> str:
    try:
        return (elem.element_info.class_name or "").strip()
    except Exception:  # noqa: BLE001
        try:
            return (elem.class_name() or "").strip()
        except Exception:  # noqa: BLE001
            return ""


def _safe_pid(elem: Any) -> int | None:
    try:
        return int(elem.element_info.process_id)
    except Exception:  # noqa: BLE001
        return None


def _safe_hwnd(elem: Any) -> int | None:
    try:
        handle = elem.handle
        return int(handle) if handle else None
    except Exception:  # noqa: BLE001
        try:
            return int(elem.element_info.handle)
        except Exception:  # noqa: BLE001
            return None


def _is_standard_class(class_name: str, settings: Settings | None = None) -> bool:
    cfg = settings or get_settings()
    return (class_name or "") == cfg.standard_class_name


def _with_retries(fn: Callable[[], Any], *, settings: Settings | None = None) -> Any:
    cfg = settings or get_settings()
    last_exc: Exception | None = None
    attempts = max(1, cfg.retry_count)
    for i in range(attempts):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if i + 1 < attempts:
                time.sleep(cfg.retry_delay)
    assert last_exc is not None
    raise last_exc


def _wrap_access_errors(exc: Exception) -> DialogError:
    msg = str(exc).lower()
    if any(k in msg for k in ("access is denied", "access denied", "elevated", "privilege")):
        return DialogAccessError(
            "Target dialog is not accessible. If it runs elevated (Administrator), "
            "this process must also run elevated. "
            "目标对话框不可访问；若其以管理员运行，本进程也需要管理员权限。"
        )
    if any(k in msg for k in ("secure desktop", "uac", "consent ui")):
        return DialogAccessError(
            "Dialog is on the secure desktop (UAC) and cannot be automated via UIA. "
            "对话框位于安全桌面（UAC），UIA 不可达。"
        )
    return DialogError(str(exc))


def dialog_info_from_element(elem: Any, settings: Settings | None = None) -> DialogInfo | None:
    hwnd = _safe_hwnd(elem)
    if hwnd is None:
        return None
    class_name = _safe_class_name(elem)
    return DialogInfo(
        handle_id=handle_to_id(hwnd),
        title=_safe_elem_text(elem),
        class_name=class_name,
        is_standard=_is_standard_class(class_name, settings),
        pid=_safe_pid(elem),
    )


def resolve_window(handle_id: str, backend: WindowBackend | None = None) -> Any:
    """Resolve handle_id → pywinauto window wrapper."""
    be = backend or get_backend()
    try:
        hwnd = id_to_handle(handle_id)
    except ValueError as exc:
        raise DialogError(f"Invalid handle_id: {handle_id!r}") from exc
    try:
        return _with_retries(lambda: be.from_handle(hwnd))
    except Exception as exc:  # noqa: BLE001
        raise _wrap_access_errors(exc) from exc


# ---------------------------------------------------------------------------
# §4.1 Discovery
# ---------------------------------------------------------------------------


def dialog_list(
    *,
    class_name: str | None = None,
    backend: WindowBackend | None = None,
    settings: Settings | None = None,
) -> list[DialogInfo]:
    """List top-level dialogs (default: standard ``#32770``).

    列出当前顶层对话框（默认标准 ``#32770``）。
    """
    cfg = settings or get_settings()
    be = backend or get_backend()
    target_class = cfg.standard_class_name if class_name is None else class_name
    # Empty string means "all top-level windows"
    windows = be.list_top_level(None if target_class == "" else target_class)
    results: list[DialogInfo] = []
    for win in windows:
        info = dialog_info_from_element(win, cfg)
        if info is not None:
            results.append(info)
    logger.info("dialog_list count=%s class=%s", len(results), target_class or "*")
    return results


def dialog_wait_for(
    title: str | None = None,
    class_name: str | None = None,
    timeout: float | None = None,
    *,
    backend: WindowBackend | None = None,
    settings: Settings | None = None,
) -> DialogInfo:
    """Wait until a matching dialog appears; return its handle_id info.

    等待对话框出现并返回句柄信息。
    """
    cfg = settings or get_settings()
    be = backend or get_backend()
    wait_s = cfg.default_timeout if timeout is None else float(timeout)
    want_class = cfg.standard_class_name if class_name is None else class_name
    deadline = time.monotonic() + wait_s
    title_key = normalize_label(title) if title else None

    while True:
        candidates = dialog_list(class_name=want_class, backend=be, settings=cfg)
        for info in candidates:
            if title_key is None or normalize_label(info.title) == title_key or (
                title_key in normalize_label(info.title)
            ):
                logger.info(
                    "dialog_wait_for hit handle=%s title_digest=%s standard=%s",
                    info.handle_id,
                    text_digest(info.title),
                    info.is_standard,
                )
                return info
        if time.monotonic() >= deadline:
            raise DialogNotFoundError(
                f"No dialog matched title={title!r} class_name={want_class!r} "
                f"within {wait_s}s / 超时未找到匹配对话框"
            )
        time.sleep(cfg.retry_delay)


def _control_actions(control_type: str) -> list[str]:
    ct = (control_type or "").casefold()
    actions: list[str] = []
    if ct in {"button", "menuitem", "hyperlink", "tabitem", "listitem", "treeitem"}:
        actions.append("click")
    if ct in {"edit", "document", "combobox"}:
        actions.extend(["set_text", "read"])
    if ct in {"text", "textblock", "statusbar"}:
        actions.append("read")
    if ct in {"checkbox", "radiobutton"}:
        actions.append("toggle")
    return actions


def dialog_describe(
    handle_id: str,
    *,
    backend: WindowBackend | None = None,
    max_controls: int = 80,
) -> dict[str, Any]:
    """Return a control-tree summary for LLM decision-making.

    返回控件树摘要，供模型决策。
    """
    win = resolve_window(handle_id, backend)
    info = dialog_info_from_element(win)
    controls: list[ControlSummary] = []
    try:
        descendants = win.descendants()
    except Exception as exc:  # noqa: BLE001
        raise _wrap_access_errors(exc) from exc

    for elem in descendants:
        if len(controls) >= max_controls:
            break
        try:
            ei = elem.element_info
            control_type = str(getattr(ei, "control_type", "") or "")
            name = (getattr(ei, "name", None) or "")[:200]
            automation_id = str(getattr(ei, "automation_id", "") or "")
            is_enabled = bool(getattr(ei, "enabled", True))
            is_password = bool(getattr(ei, "is_password", False)) or looks_like_password_field(
                name, automation_id
            )
            # Skip empty nameless panes to keep summary small
            if not name and control_type.casefold() in {"pane", "group", "thumb", "separator"}:
                continue
            controls.append(
                ControlSummary(
                    control_type=control_type,
                    name=name,
                    automation_id=automation_id,
                    is_enabled=is_enabled,
                    is_password=is_password,
                    actions=_control_actions(control_type),
                )
            )
        except Exception:  # noqa: BLE001
            continue

    payload = {
        "dialog": info.to_dict() if info else {"handle_id": handle_id},
        "controls": [c.to_dict() for c in controls],
        "control_count": len(controls),
        "truncated": len(controls) >= max_controls,
    }
    logger.info(
        "dialog_describe handle=%s controls=%s digest=%s",
        handle_id,
        len(controls),
        text_digest(json.dumps(payload["dialog"], ensure_ascii=False)),
    )
    return payload


# ---------------------------------------------------------------------------
# §4.2 Semantic actions
# ---------------------------------------------------------------------------


def dialog_read_text(
    handle_id: str,
    *,
    backend: WindowBackend | None = None,
) -> str:
    """Read static / document text from the dialog (message body included).

    读取对话框静态文本（含消息框正文）。
    """
    win = resolve_window(handle_id, backend)
    chunks: list[str] = []
    title = _safe_elem_text(win)
    if title:
        chunks.append(title)

    try:
        for elem in win.descendants():
            try:
                ei = elem.element_info
                ct = str(getattr(ei, "control_type", "") or "").casefold()
                if ct not in {"text", "textblock", "document", "statusbar", "titlebar"}:
                    continue
                name = (getattr(ei, "name", None) or "").strip()
                if name and name not in chunks:
                    chunks.append(name)
            except Exception:  # noqa: BLE001
                continue
    except Exception as exc:  # noqa: BLE001
        raise _wrap_access_errors(exc) from exc

    text = "\n".join(chunks).strip()
    logger.info("dialog_read_text handle=%s %s", handle_id, text_digest(text))
    return text


def _iter_buttons(win: Any) -> list[Any]:
    buttons: list[Any] = []
    try:
        for elem in win.descendants():
            try:
                ct = str(elem.element_info.control_type or "").casefold()
                if ct == "button":
                    buttons.append(elem)
            except Exception:  # noqa: BLE001
                continue
    except Exception as exc:  # noqa: BLE001
        raise _wrap_access_errors(exc) from exc
    return buttons


def dialog_click_button(
    handle_id: str,
    label: str,
    *,
    backend: WindowBackend | None = None,
) -> str:
    """Click a button by visible label (zh/en aliases supported).

    按按钮文本点击，支持中英文别名。不使用坐标点击。
    """
    win = resolve_window(handle_id, backend)
    candidates = expand_label_candidates(label)
    buttons = _iter_buttons(win)

    # Pass 1: exact / alias match
    for btn in buttons:
        name = _safe_elem_text(btn)
        for wanted in candidates:
            if labels_match(name, wanted):
                try:
                    if hasattr(btn, "invoke"):
                        btn.invoke()
                    else:
                        btn.click()
                except Exception as exc:  # noqa: BLE001
                    raise _wrap_access_errors(exc) from exc
                logger.info(
                    "dialog_click_button handle=%s label=%s matched=%s",
                    handle_id,
                    label,
                    text_digest(name),
                )
                return f"clicked:{name}"

    available = [_safe_elem_text(b) for b in buttons if _safe_elem_text(b)]
    raise DialogError(
        f"Button not found for label={label!r}. Available={available!r} / 未找到按钮"
    )


def _is_password_elem(elem: Any) -> bool:
    try:
        ei = elem.element_info
        if bool(getattr(ei, "is_password", False)):
            return True
        return looks_like_password_field(
            getattr(ei, "name", None), getattr(ei, "automation_id", None)
        )
    except Exception:  # noqa: BLE001
        return False


def _set_edit_value(edit: Any, text: str) -> None:
    """Set edit text via UIA value pattern / set_edit_text — never coordinates."""
    if _is_password_elem(edit):
        raise UnsafeControlError(
            "Refusing to write into a password control. / 拒绝向密码框写入。"
        )
    # Prefer set_edit_text / set_value over type_keys to avoid focus races
    errors: list[str] = []
    for method_name in ("set_edit_text", "set_value", "iface_value"):
        try:
            if method_name == "iface_value":
                iface = getattr(edit, "iface_value", None)
                if iface is not None:
                    iface.SetValue(text)
                    return
                continue
            method = getattr(edit, method_name, None)
            if callable(method):
                method(text)
                return
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{method_name}:{exc}")
    # Last resort: legacy set_text if present (still not coordinates)
    try:
        if hasattr(edit, "set_text"):
            edit.set_text(text)
            return
    except Exception as exc:  # noqa: BLE001
        errors.append(f"set_text:{exc}")
    raise DialogError(f"Failed to set edit text ({'; '.join(errors)})")


def _find_edits(win: Any) -> list[Any]:
    edits: list[Any] = []
    for elem in win.descendants():
        try:
            ct = str(elem.element_info.control_type or "").casefold()
            if ct in {"edit", "document"}:
                edits.append(elem)
        except Exception:  # noqa: BLE001
            continue
    return edits


def dialog_set_text(
    handle_id: str,
    text: str,
    field: str | None = None,
    *,
    backend: WindowBackend | None = None,
) -> str:
    """Fill an edit box (filename field for Open / Save As when *field* omitted).

    向编辑框填入文本；另存为/打开对话框默认定位文件名栏。
    """
    win = resolve_window(handle_id, backend)
    edits = _find_edits(win)
    if not edits:
        raise DialogError("No editable field found / 未找到可编辑控件")

    target = None
    if field:
        field_keys = [normalize_label(x) for x in expand_label_candidates(field)]
        field_keys.append(normalize_label(field))
        # Match by nearby name / automation id
        for edit in edits:
            try:
                ei = edit.element_info
                name = normalize_label(getattr(ei, "name", None) or "")
                auto_id = normalize_label(str(getattr(ei, "automation_id", "") or ""))
                if any(k and (k == name or k in name or k == auto_id) for k in field_keys):
                    target = edit
                    break
            except Exception:  # noqa: BLE001
                continue
        if target is None:
            raise DialogError(f"Edit field not found for field={field!r} / 未找到指定编辑框")
    else:
        # Prefer filename-labeled edit; else last edit (common for Save As)
        for edit in edits:
            try:
                name = getattr(edit.element_info, "name", None) or ""
                if any(labels_match(name, alias) for alias in FILENAME_FIELD_ALIASES):
                    target = edit
                    break
            except Exception:  # noqa: BLE001
                continue
        if target is None:
            target = edits[-1]

    _set_edit_value(target, text)
    logger.info(
        "dialog_set_text handle=%s field=%s %s",
        handle_id,
        field,
        path_digest(text) if ("\\" in text or "/" in text) else text_digest(text),
    )
    return "ok"


def _wait_child_or_top_dialog(
    *,
    exclude_handle: str | None,
    timeout: float,
    backend: WindowBackend | None,
    settings: Settings,
) -> DialogInfo | None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        for info in dialog_list(class_name=settings.standard_class_name, backend=backend, settings=settings):
            if exclude_handle and info.handle_id == exclude_handle:
                continue
            return info
        time.sleep(settings.retry_delay)
    return None


def dialog_handle_save_as(
    handle_id: str,
    path: str,
    *,
    backend: WindowBackend | None = None,
    settings: Settings | None = None,
) -> str:
    """Composite: fill path → click Save → auto-confirm overwrite if prompted.

    组合工具：填路径 → 点保存 → 如有覆盖确认自动点“是”。
    """
    cfg = settings or get_settings()
    dialog_set_text(handle_id, path, backend=backend)
    dialog_click_button(handle_id, "save", backend=backend)

    confirm = _wait_child_or_top_dialog(
        exclude_handle=handle_id,
        timeout=cfg.overwrite_confirm_timeout,
        backend=backend,
        settings=cfg,
    )
    if confirm is not None:
        # Overwrite / replace prompts usually offer Yes / OK
        try:
            dialog_click_button(confirm.handle_id, "yes", backend=backend)
            logger.info(
                "dialog_handle_save_as overwrite confirmed handle=%s %s",
                confirm.handle_id,
                path_digest(path),
            )
            return f"saved_with_overwrite_confirm:{path}"
        except DialogError:
            try:
                dialog_click_button(confirm.handle_id, "ok", backend=backend)
                return f"saved_with_ok_confirm:{path}"
            except DialogError:
                logger.warning(
                    "Secondary dialog appeared but Yes/OK not found handle=%s",
                    confirm.handle_id,
                )
    logger.info("dialog_handle_save_as done handle=%s %s", handle_id, path_digest(path))
    return f"saved:{path}"


def dialog_handle_open_file(
    handle_id: str,
    path: str,
    *,
    backend: WindowBackend | None = None,
) -> str:
    """Composite: fill path → click Open.

    组合工具：填路径 → 点打开。
    """
    dialog_set_text(handle_id, path, backend=backend)
    dialog_click_button(handle_id, "open", backend=backend)
    logger.info("dialog_handle_open_file handle=%s %s", handle_id, path_digest(path))
    return f"opened:{path}"


def dialog_handle_messagebox(
    handle_id: str,
    choice: str,
    *,
    backend: WindowBackend | None = None,
) -> dict[str, str]:
    """Handle a message box: read text first, then click ok/cancel/yes/no.

    处理消息确认框；先读文本返回给调用方备查。
    """
    key = (choice or "").strip().casefold()
    if key not in MESSAGEBOX_CHOICE_MAP:
        raise DialogError(
            f"choice must be one of {sorted(MESSAGEBOX_CHOICE_MAP)} / 非法 choice"
        )
    body = dialog_read_text(handle_id, backend=backend)
    clicked = dialog_click_button(handle_id, MESSAGEBOX_CHOICE_MAP[key], backend=backend)
    return {"text": body, "clicked": clicked, "choice": key}
