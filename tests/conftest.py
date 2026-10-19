"""Pytest fixtures."""

from __future__ import annotations

from typing import Any

import pytest

from win_dialog_agent.config import reset_settings_cache
from win_dialog_agent.dialogs import set_backend


@pytest.fixture(autouse=True)
def _clean_backend() -> Any:
    set_backend(None)
    reset_settings_cache()
    yield
    set_backend(None)
    reset_settings_cache()
