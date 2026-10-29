"""Date conversion tool backend: line-by-line ISO 8601 normalisation."""
from __future__ import annotations

from dataforge.dates import to_iso8601


def convert_text(text: str) -> str:
    return "\n".join(to_iso8601(line) for line in text.splitlines())
