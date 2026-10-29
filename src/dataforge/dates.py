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
        numbers = [int(p) for p in pieces]
    except ValueError:
        return text
    if len(numbers) > 3:
        return text
    year = numbers[0]
    if not 1000 <= year <= 9999:
        return text
    if len(numbers) == 1:
        return f"{year:04d}"
    month = numbers[1]
    if not 1 <= month <= 12:
        return f"{year:04d}"
    if len(numbers) == 2:
        return f"{year:04d}-{month:02d}"
    day = numbers[2]
    if 1 <= day <= calendar.monthrange(year, month)[1]:
        return f"{year:04d}-{month:02d}-{day:02d}"
    return f"{year:04d}-{month:02d}"
