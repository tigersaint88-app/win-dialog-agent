"""Shared fakes for dialog / UIA tests."""

from __future__ import annotations

from typing import Any


class FakeElementInfo:
    def __init__(
        self,
        *,
        name: str = "",
        control_type: str = "Button",
        class_name: str = "#32770",
        handle: int = 0,
        process_id: int = 1,
        automation_id: str = "",
        enabled: bool = True,
        is_password: bool = False,
    ) -> None:
        self.name = name
        self.control_type = control_type
        self.class_name = class_name
        self.handle = handle
        self.process_id = process_id
        self.automation_id = automation_id
        self.enabled = enabled
        self.is_password = is_password


class FakeControl:
    def __init__(self, info: FakeElementInfo) -> None:
        self.element_info = info
        self.handle = info.handle
        self._text = info.name
        self.invoked = False
        self.written: str | None = None

    def window_text(self) -> str:
        return self._text

    def class_name(self) -> str:
        return self.element_info.class_name

    def invoke(self) -> None:
        self.invoked = True

    def click(self) -> None:
        self.invoked = True

    def set_edit_text(self, text: str) -> None:
        self.written = text
        self._text = text

    def descendants(self) -> list[FakeControl]:
        return []


class FakeDialog(FakeControl):
    def __init__(self, hwnd: int, title: str, children: list[FakeControl] | None = None) -> None:
        super().__init__(
            FakeElementInfo(
                name=title,
                control_type="Window",
                class_name="#32770",
                handle=hwnd,
            )
        )
        self._children = children or []

    def descendants(self) -> list[FakeControl]:
        return list(self._children)


class FakeBackend:
    def __init__(self, windows: list[FakeDialog]) -> None:
        self.windows = {w.handle: w for w in windows}

    def list_top_level(self, class_name: str | None = None) -> list[Any]:
        items = list(self.windows.values())
        if class_name:
            return [w for w in items if w.element_info.class_name == class_name]
        return items

    def from_handle(self, hwnd: int) -> Any:
        if hwnd not in self.windows:
            raise RuntimeError("not found")
        return self.windows[hwnd]
