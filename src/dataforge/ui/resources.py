"""Bundled resource lookup (dev tree and PyInstaller onedir)."""
from __future__ import annotations

import sys
from pathlib import Path


def app_icon_path() -> Path | None:
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS"))
    else:
        base = Path(__file__).resolve().parents[3]
    path = base / "assets" / "icons" / "favicon.ico"
    return path if path.is_file() else None
