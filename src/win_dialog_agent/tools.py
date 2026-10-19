"""OpenAI Agents SDK function tools / Agents SDK 工具封装.

English docstrings are the model-facing descriptions; Chinese comments aid maintainers.
英文 docstring 供模型理解；中文注释给维护者。
"""

from __future__ import annotations

import json
from typing import Any

from agents import function_tool

from win_dialog_agent import dialogs, uia_fallback


def _json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


@function_tool
def dialog_wait_for(
    title: str | None = None,
    class_name: str | None = None,
    timeout: float | None = None,
) -> str:
    """Wait for a Windows dialog to appear and return its handle info as JSON.

    Args:
        title: Optional window title to match (substring / exact after normalize).
        class_name: Optional class name; defaults to standard ``#32770``.
        timeout: Seconds to wait; defaults to configured timeout.
    """
    # 等待对话框出现，返回 handle_id 等信息
    info = dialogs.dialog_wait_for(title=title, class_name=class_name, timeout=timeout)
    return _json(info.to_dict())


@function_tool
def dialog_list() -> str:
    """List currently visible top-level standard ``#32770`` dialogs (title + handle_id)."""
    # 列出当前所有顶层标准对话框
    return _json([d.to_dict() for d in dialogs.dialog_list()])


@function_tool
def dialog_describe(handle_id: str) -> str:
    """Describe a dialog's control tree summary for LLM decision-making.

    Args:
        handle_id: Handle id from dialog_wait_for / dialog_list (e.g. ``0x000A0B0C``).
    """
    # 返回控件树摘要
    return _json(dialogs.dialog_describe(handle_id))


@function_tool
def dialog_read_text(handle_id: str) -> str:
    """Read all static / document text from a dialog, including message box body.

    Args:
        handle_id: Dialog handle id.
    """
    # 读取对话框静态文本
    return dialogs.dialog_read_text(handle_id)


@function_tool
def dialog_click_button(handle_id: str, label: str) -> str:
    """Click a dialog button by label. Supports Chinese and English aliases.

    Args:
        handle_id: Dialog handle id.
        label: Button text or semantic key such as ``save`` / ``保存`` / ``OK`` / ``确定``.
    """
    # 按按钮文本点击（中英文别名）
    return dialogs.dialog_click_button(handle_id, label)


@function_tool
def dialog_set_text(handle_id: str, text: str, field: str | None = None) -> str:
    """Set text on an edit field (filename box for Open / Save As when field omitted).

    Args:
        handle_id: Dialog handle id.
        text: Text to write.
        field: Optional field label such as ``文件名`` / ``File name``.
    """
    # 往编辑框填文本；拒绝密码框
    return dialogs.dialog_set_text(handle_id, text, field=field)


@function_tool
def dialog_handle_save_as(handle_id: str, path: str) -> str:
    """Handle a standard Save As dialog: fill filename and click Save,
    auto-confirm overwrite if prompted. handle_id from dialog_wait_for.

    Args:
        handle_id: Dialog handle id.
        path: Full destination path to save.
    """
    # 组合：填路径 → 保存 → 自动确认覆盖
    return dialogs.dialog_handle_save_as(handle_id, path)


@function_tool
def dialog_handle_open_file(handle_id: str, path: str) -> str:
    """Handle a standard Open File dialog: fill path and click Open.

    Args:
        handle_id: Dialog handle id.
        path: Full file path to open.
    """
    # 组合：填路径 → 打开
    return dialogs.dialog_handle_open_file(handle_id, path)


@function_tool
def dialog_handle_messagebox(handle_id: str, choice: str) -> str:
    """Handle a message confirmation box. Reads text first, then clicks the choice.

    Args:
        handle_id: Dialog handle id.
        choice: One of ``ok``, ``cancel``, ``yes``, ``no``.
    """
    # 消息框：先读文本再按 choice 点击
    return _json(dialogs.dialog_handle_messagebox(handle_id, choice))


@function_tool
def uia_find(
    handle_id: str,
    control_type: str | None = None,
    text: str | None = None,
) -> str:
    """Find controls inside a dialog (UIA fallback for non-standard dialogs).

    Args:
        handle_id: Dialog handle id.
        control_type: Optional UIA control type filter (e.g. ``Button``, ``Edit``).
        text: Optional visible text filter.
    """
    # 通用 UIA 查找（非标准对话框）
    return _json(
        uia_fallback.uia_find(handle_id, control_type=control_type, text=text)
    )


@function_tool
def uia_click(handle_id: str, control_id: str) -> str:
    """Click a control by control_id from uia_find / uia_snapshot (UIA fallback).

    Args:
        handle_id: Dialog handle id.
        control_id: Control id returned by uia_find or uia_snapshot.
    """
    return uia_fallback.uia_click(handle_id, control_id)


@function_tool
def uia_set_text(handle_id: str, control_id: str, text: str) -> str:
    """Set text on a control by control_id (UIA fallback).

    Args:
        handle_id: Dialog handle id.
        control_id: Control id returned by uia_find or uia_snapshot.
        text: Text to write.
    """
    return uia_fallback.uia_set_text(handle_id, control_id, text)


@function_tool
def uia_snapshot(handle_id: str) -> str:
    """Return a compact control-tree JSON for unknown / non-standard dialogs.

    Args:
        handle_id: Dialog handle id.
    """
    return _json(uia_fallback.uia_snapshot(handle_id))


# Export list for Agent(tools=[...])
ALL_TOOLS = [
    dialog_wait_for,
    dialog_list,
    dialog_describe,
    dialog_read_text,
    dialog_click_button,
    dialog_set_text,
    dialog_handle_save_as,
    dialog_handle_open_file,
    dialog_handle_messagebox,
    uia_find,
    uia_click,
    uia_set_text,
    uia_snapshot,
]

__all__ = [
    "ALL_TOOLS",
    "dialog_wait_for",
    "dialog_list",
    "dialog_describe",
    "dialog_read_text",
    "dialog_click_button",
    "dialog_set_text",
    "dialog_handle_save_as",
    "dialog_handle_open_file",
    "dialog_handle_messagebox",
    "uia_find",
    "uia_click",
    "uia_set_text",
    "uia_snapshot",
]
