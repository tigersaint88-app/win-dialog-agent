"""Button / field label aliases (zh + en) / 按钮与字段中英文别名表.

Community contributions welcome: add labels you see in real dialogs.
社区欢迎 PR：把你在真实对话框里见到的文案补进来，覆盖面会越来越广。

Matching rules (applied in dialogs.py):
1. Exact match (case-sensitive for CJK, case-insensitive for ASCII)
2. Strip accelerator markers: ``Save(&S)`` → ``Save``, ``保存(&S)`` → ``保存``
3. Alias-group match: any label in the same semantic group counts as a hit
"""

from __future__ import annotations

import re
from typing import Final

# Semantic group → accepted visible texts (order = preference for programmatic clicks)
BUTTON_ALIASES: Final[dict[str, list[str]]] = {
    "save": [
        "保存",
        "另存为",
        "Save",
        "Save As",
        "Save(&S)",
        "保存(&S)",
        "另存为(&A)",
        "Save As(&A)",
    ],
    "open": [
        "打开",
        "Open",
        "打开(&O)",
        "Open(&O)",
    ],
    "ok": [
        "确定",
        "OK",
        "确定(&O)",
        "OK(&O)",
    ],
    "cancel": [
        "取消",
        "Cancel",
        "取消(&C)",
        "Cancel(&C)",
    ],
    "yes": [
        "是",
        "Yes",
        "是(&Y)",
        "Yes(&Y)",
    ],
    "no": [
        "否",
        "No",
        "否(&N)",
        "No(&N)",
    ],
    "close": [
        "关闭",
        "Close",
        "关闭(&C)",
        "Close(&C)",
    ],
    "apply": [
        "应用",
        "Apply",
        "应用(&A)",
        "Apply(&A)",
    ],
    "retry": [
        "重试",
        "Retry",
        "重试(&R)",
        "Retry(&R)",
    ],
    "ignore": [
        "忽略",
        "Ignore",
        "忽略(&I)",
        "Ignore(&I)",
    ],
    "abort": [
        "中止",
        "Abort",
        "中止(&A)",
        "Abort(&A)",
    ],
}

# MessageBox choice → semantic button group
MESSAGEBOX_CHOICE_MAP: Final[dict[str, str]] = {
    "ok": "ok",
    "cancel": "cancel",
    "yes": "yes",
    "no": "no",
}

# Filename / path edit field labels commonly seen in Open / Save As dialogs
FILENAME_FIELD_ALIASES: Final[list[str]] = [
    "文件名",
    "文件名:",
    "文件名：",
    "File name",
    "File name:",
    "文件名称",
    "Name",
]

# Texts that strongly suggest a password control — refuse set_text
PASSWORD_HINTS: Final[list[str]] = [
    "密码",
    "口令",
    "Password",
    "Passphrase",
    "PIN",
]

_ACCEL_RE = re.compile(r"\s*\(&.\)\s*")
_TRAILING_COLON_RE = re.compile(r"[:：]\s*$")


def strip_accelerator(label: str) -> str:
    """Remove Win32 accelerator markers like ``(&S)`` and trailing colons."""
    text = _ACCEL_RE.sub("", label or "").strip()
    return _TRAILING_COLON_RE.sub("", text).strip()


def normalize_label(label: str) -> str:
    """Normalize for comparison."""
    cleaned = strip_accelerator(label)
    # ASCII-only labels compare case-insensitively
    if cleaned.isascii():
        return cleaned.casefold()
    return cleaned


def expand_label_candidates(label: str) -> list[str]:
    """Expand a user-provided label into concrete candidates (self + alias group).

    Args:
        label: Visible text, English keyword (``save``), or zh/en button caption.
    """
    raw = (label or "").strip()
    if not raw:
        return []

    candidates: list[str] = [raw, strip_accelerator(raw)]
    key = normalize_label(raw)

    # Direct semantic key: "save", "yes", ...
    if raw.casefold() in BUTTON_ALIASES:
        candidates.extend(BUTTON_ALIASES[raw.casefold()])

    # Find which group contains this label, then add the whole group
    for group, aliases in BUTTON_ALIASES.items():
        normalized_aliases = {normalize_label(a) for a in aliases}
        if key in normalized_aliases or key == group:
            candidates.extend(aliases)
            candidates.append(group)

    # Deduplicate while preserving order
    seen: set[str] = set()
    ordered: list[str] = []
    for item in candidates:
        if item and item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def labels_match(visible: str, wanted: str) -> bool:
    """Return True if *visible* matches *wanted* under alias rules."""
    if not visible or not wanted:
        return False
    v = normalize_label(visible)
    for candidate in expand_label_candidates(wanted):
        if v == normalize_label(candidate):
            return True
        # Soft contains for captions like "Save file" vs "Save"
        c = normalize_label(candidate)
        if c and (c in v or v in c):
            # Avoid ultra-short false positives (e.g. "是" is OK; single ASCII letter not)
            if not c.isascii() or len(c) >= 2:
                return True
    return False


def looks_like_password_field(name: str | None, automation_id: str | None = None) -> bool:
    """Heuristic: refuse writing into password-like controls."""
    haystack = f"{name or ''} {automation_id or ''}"
    for hint in PASSWORD_HINTS:
        if hint.casefold() in haystack.casefold():
            return True
    return False
