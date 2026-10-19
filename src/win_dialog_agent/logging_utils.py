"""Privacy-aware logging helpers / 隐私友好日志。

Never log full user file paths or dialog body text — only hashes / short digests.
不把用户文件内容或完整正文写入日志，只记 hash 或脱敏摘要。
"""

from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path


def get_logger(name: str = "win_dialog_agent") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
        )
        logger.addHandler(handler)
        logger.propagate = False
    return logger


def text_digest(text: str, *, preview: int = 24) -> str:
    """Return ``sha256[:12] + short preview`` for logging."""
    raw = text or ""
    digest = hashlib.sha256(raw.encode("utf-8", errors="replace")).hexdigest()[:12]
    flat = re.sub(r"\s+", " ", raw).strip()
    snippet = flat[:preview] + ("…" if len(flat) > preview else "")
    return f"sha256={digest} preview={snippet!r}"


def path_digest(path: str) -> str:
    """Log-safe path summary: drive + basename + hash of full path."""
    try:
        p = Path(path)
        digest = hashlib.sha256(str(p).encode("utf-8", errors="replace")).hexdigest()[:12]
        return f"drive={p.drive or '-'} name={p.name!r} sha256={digest}"
    except Exception:
        digest = hashlib.sha256((path or "").encode("utf-8", errors="replace")).hexdigest()[:12]
        return f"sha256={digest}"
