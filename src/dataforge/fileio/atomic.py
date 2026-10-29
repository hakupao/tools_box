"""Atomic file writes via a same-directory temp file and ``os.replace``."""
from __future__ import annotations

import logging
import os
import secrets
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

logger = logging.getLogger(__name__)


@contextmanager
def atomic_path(target: Path) -> Iterator[Path]:
    """Yield a temp path next to ``target``; replace ``target`` on success.

    On any exception (including BaseException such as Cancelled) the temp file is removed
    and the exception re-raised. The target directory must already exist.
    """
    tmp = target.parent / f".{target.stem}.{os.getpid()}.{secrets.token_hex(4)}.tmp{target.suffix}"
    try:
        yield tmp
        os.replace(tmp, target)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
