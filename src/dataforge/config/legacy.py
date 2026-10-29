"""Migration helpers for v2 config layouts (whole-file configs and standalone JSON files)."""
from __future__ import annotations

import json
import logging
import sys
from collections.abc import Collection, Sequence
from pathlib import Path
from typing import Any

from .store import ConfigStore

logger = logging.getLogger(__name__)


def load_section_with_legacy(
    store: ConfigStore,
    section: str,
    legacy_keys: Collection[str],
    legacy_files: Sequence[Path] = (),
) -> dict[str, Any]:
    """Return the section, falling back to v2 layouts (never modifies legacy files)."""
    current = store.section(section)
    if current:
        return current

    root = store.root()
    if any(key in root for key in legacy_keys):
        return root

    for path in legacy_files:
        try:
            if not path.exists():
                continue
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            logger.warning("Skipping unreadable legacy config %s", path)
            continue
        if isinstance(data, dict) and any(key in data for key in legacy_keys):
            store.update_section(section, data)
            return data
    return {}


def legacy_file_candidates(file_name: str, *extra_dirs: Path) -> list[Path]:
    """Places where v2 kept a standalone config file, in priority order."""
    candidates: list[Path] = []
    if getattr(sys, "frozen", False):
        candidates.append(Path(sys.executable).resolve().parent / file_name)
    candidates.append(Path(__file__).resolve().parents[2] / "utils" / file_name)
    candidates.extend(Path(d) / file_name for d in extra_dirs)

    seen: set[Path] = set()
    result: list[Path] = []
    for path in candidates:
        if path not in seen:
            seen.add(path)
            result.append(path)
    return result
