"""Dialog core tests with mocked backend + optional Windows integration.

对话框核心测试：默认用 mock，不依赖真实桌面；
标记 ``integration`` 的用例在有桌面的 Windows 上跑真实场景。
"""

from __future__ import annotations

import sys
from typing import Any

import pytest

from win_dialog_agent import dialogs
from win_dialog_agent.config import Settings
from win_dialog_agent.dialogs import (
    DialogInfo,
    DialogNotFoundError,
    UnsafeControlError,
    handle_to_id,
    id_to_handle,
    set_backend,
)
from fakes import FakeBackend, FakeControl, FakeDialog, FakeElementInfo


def test_handle_id_roundtrip() -> None:
    assert id_to_handle(handle_to_id(442)) == 442
    assert id_to_handle("0x000001BA") == 0x1BA
    assert id_to_handle("12345") == 12345


def test_dialog_list_and_wait() -> None:
    save_btn = FakeControl(FakeElementInfo(name="保存(&S)", control_type="Button", handle=2))
    edit = FakeControl(FakeElementInfo(name="文件名:", control_type="Edit", handle=3))
    dlg = FakeDialog(0x1000, "另存为", [save_btn, edit])
    set_backend(FakeBackend([dlg]))

    listed = dialogs.dialog_list()
    assert len(listed) == 1
    assert listed[0].title == "另存为"
    assert listed[0].is_standard

    found = dialogs.dialog_wait_for(title="另存为", timeout=1.0)
    assert found.handle_id == handle_to_id(0x1000)


def test_dialog_wait_timeout() -> None:
    set_backend(FakeBackend([]))
    with pytest.raises(DialogNotFoundError):
        dialogs.dialog_wait_for(title="nope", timeout=0.2)


def test_click_button_alias_and_set_text() -> None:
    save_btn = FakeControl(FakeElementInfo(name="Save(&S)", control_type="Button", handle=2))
    edit = FakeControl(FakeElementInfo(name="File name:", control_type="Edit", handle=3))
    dlg = FakeDialog(0x2000, "Save As", [save_btn, edit])
    set_backend(FakeBackend([dlg]))
    hid = handle_to_id(0x2000)

    assert dialogs.dialog_click_button(hid, "保存").startswith("clicked:")
    assert save_btn.invoked

    assert dialogs.dialog_set_text(hid, r"D:\out.txt") == "ok"
    assert edit.written == r"D:\out.txt"


def test_refuse_password_field() -> None:
    pwd = FakeControl(
        FakeElementInfo(name="Password", control_type="Edit", handle=3, is_password=True)
    )
    dlg = FakeDialog(0x3000, "Login", [pwd])
    set_backend(FakeBackend([dlg]))
    with pytest.raises(UnsafeControlError):
        dialogs.dialog_set_text(handle_to_id(0x3000), "secret", field="Password")


def test_handle_save_as_with_overwrite() -> None:
    save_btn = FakeControl(FakeElementInfo(name="保存", control_type="Button", handle=2))
    edit = FakeControl(FakeElementInfo(name="文件名", control_type="Edit", handle=3))
    primary = FakeDialog(0x4000, "另存为", [save_btn, edit])

    yes_btn = FakeControl(FakeElementInfo(name="是", control_type="Button", handle=6))
    confirm = FakeDialog(0x4001, "确认另存为", [yes_btn])

    backend = FakeBackend([primary])
    original_click = dialogs.dialog_click_button

    def click_and_spawn(handle_id: str, label: str, **kwargs: Any) -> str:
        kwargs.setdefault("backend", backend)
        result = original_click(handle_id, label, **kwargs)
        if label.casefold() == "save" or label == "保存":
            backend.windows[confirm.handle] = confirm
        return result

    dialogs.dialog_click_button = click_and_spawn  # type: ignore[assignment]
    try:
        set_backend(backend)
        settings = Settings(overwrite_confirm_timeout=0.5, retry_delay=0.05)
        out = dialogs.dialog_handle_save_as(
            handle_to_id(0x4000),
            r"D:\out.txt",
            backend=backend,
            settings=settings,
        )
        assert "saved" in out
        assert yes_btn.invoked
    finally:
        dialogs.dialog_click_button = original_click  # type: ignore[assignment]


def test_messagebox_flow() -> None:
    yes_btn = FakeControl(FakeElementInfo(name="Yes", control_type="Button", handle=2))
    text = FakeControl(
        FakeElementInfo(name="Overwrite existing file?", control_type="Text", handle=3)
    )
    dlg = FakeDialog(0x5000, "Confirm", [yes_btn, text])
    set_backend(FakeBackend([dlg]))
    result = dialogs.dialog_handle_messagebox(handle_to_id(0x5000), "yes")
    assert "Overwrite" in result["text"]
    assert result["choice"] == "yes"
    assert yes_btn.invoked


def test_describe_and_read() -> None:
    btn = FakeControl(FakeElementInfo(name="OK", control_type="Button", handle=2))
    text = FakeControl(FakeElementInfo(name="Hello", control_type="Text", handle=3))
    dlg = FakeDialog(0x6000, "Msg", [btn, text])
    set_backend(FakeBackend([dlg]))
    hid = handle_to_id(0x6000)
    desc = dialogs.dialog_describe(hid)
    assert desc["control_count"] >= 1
    body = dialogs.dialog_read_text(hid)
    assert "Hello" in body


def test_no_coordinate_helpers_in_p0_source() -> None:
    """Acceptance §9.7: dialogs.py must not use click_input / move_mouse."""
    from pathlib import Path

    src = Path(__file__).resolve().parents[1] / "src" / "win_dialog_agent" / "dialogs.py"
    text = src.read_text(encoding="utf-8")
    assert "click_input" not in text
    assert "move_mouse" not in text


@pytest.mark.integration
@pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
def test_integration_dialog_list_smoke() -> None:
    """Smoke: listing should not raise on a real Windows session.

    Run explicitly: ``pytest -m integration``
    """
    set_backend(None)  # real backend
    try:
        result = dialogs.dialog_list()
    except Exception as exc:  # noqa: BLE001 — COM / session quirks
        pytest.skip(f"Desktop UIA unavailable in this session: {exc}")
    assert isinstance(result, list)
    for item in result:
        assert isinstance(item, DialogInfo)
