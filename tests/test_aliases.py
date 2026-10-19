"""Unit tests for bilingual button aliases / 中英文别名单测."""

from __future__ import annotations

from win_dialog_agent.aliases import (
    expand_label_candidates,
    labels_match,
    looks_like_password_field,
    normalize_label,
    strip_accelerator,
)


def test_strip_accelerator_en_and_zh() -> None:
    assert strip_accelerator("Save(&S)") == "Save"
    assert strip_accelerator("保存(&S)") == "保存"
    assert strip_accelerator("文件名:") == "文件名"
    assert strip_accelerator("File name：") == "File name"


def test_normalize_ascii_casefold() -> None:
    assert normalize_label("SAVE") == normalize_label("save")
    assert normalize_label("保存") == "保存"


def test_expand_semantic_key() -> None:
    cands = expand_label_candidates("save")
    assert "保存" in cands
    assert "Save" in cands


def test_labels_match_zh_en() -> None:
    assert labels_match("保存(&S)", "save")
    assert labels_match("Save", "保存")
    assert labels_match("确定", "ok")
    assert labels_match("Yes", "是")
    assert not labels_match("取消", "yes")


def test_password_hints() -> None:
    assert looks_like_password_field("密码")
    assert looks_like_password_field("Password")
    assert looks_like_password_field(None, "LoginPasswordBox")
    assert not looks_like_password_field("文件名")
