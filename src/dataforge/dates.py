"""Date normalisation helpers (backend, no UI dependencies)."""
from __future__ import annotations

import calendar


def to_iso8601(value: str) -> str:
    """Convert ``YYYY/M/D``-style text to ISO 8601, degrading to a valid prefix.

    Unparseable input is returned unchanged (after stripping surrounding spaces).
    """
    text = value.strip()
    if not text or "/" not in text:
        return text
    pieces = text.split("/")
    try:
        year = int(pieces[0])
        if not 1000 <= year <= 9999:
            return text
        month = int(pieces[1])
        if not 1 <= month <= 12:
            return f"{year:04d}"
        if len(pieces) == 2:
            return f"{year:04d}-{month:02d}"
        day = int(pieces[2])
    except ValueError:
        return text
    if len(pieces) > 3:
        return text
    if 1 <= day <= calendar.monthrange(year, month)[1]:
        return f"{year:04d}-{month:02d}-{day:02d}"
    return f"{year:04d}-{month:02d}"
