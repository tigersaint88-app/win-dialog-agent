"""UIA fallback unit tests with mocked dialog tree."""

from __future__ import annotations

import warnings

from win_dialog_agent.dialogs import handle_to_id, set_backend
from win_dialog_agent.uia_fallback import uia_find, uia_snapshot

from fakes import FakeBackend, FakeControl, FakeDialog, FakeElementInfo


def test_uia_snapshot_warns_for_nonstandard() -> None:
    btn = FakeControl(FakeElementInfo(name="CustomOK", control_type="Button", handle=2))
    dlg = FakeDialog(0x7000, "WpfDialog", [btn])
    dlg.element_info.class_name = "HwndWrapper[Wpf]"
    set_backend(FakeBackend([dlg]))

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        snap = uia_snapshot(handle_to_id(0x7000))
        hits = uia_find(handle_to_id(0x7000), control_type="Button", text="CustomOK")
    assert snap["path"] == "uia_fallback"
    assert any("Non-standard" in str(w.message) for w in caught)
    assert len(hits) == 1
    assert hits[0]["name"] == "CustomOK"
