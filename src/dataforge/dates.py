"""Date normalisation helpers (backend, no UI dependencies)."""
from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from datetime import date
from enum import Enum


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


class SlashOrder(Enum):
    DAY_FIRST = "dmy"
    MONTH_FIRST = "mdy"


class SlashKind(Enum):
    NOT_SLASH = "not_slash"
    DAY_FIRST_ONLY = "day_first_only"
    MONTH_FIRST_ONLY = "month_first_only"
    SAME = "same"
    AMBIGUOUS = "ambiguous"
    INVALID = "invalid"


class DateOutcome(Enum):
    BLANK = "blank"
    SHIFTED = "shifted"
    FILLED = "filled"
    UNPARSED = "unparsed"


@dataclass(frozen=True)
class ParsedDate:
    value: date
    partial: bool
    suffix: str


_SLASH_RE = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")
_FULL_RE = re.compile(r"^(\d{4})[-/](\d{1,2})[-/](\d{1,2})")
_SUFFIX_RE = re.compile(
    r"^([T ]\d{1,2}:\d{1,2}(:\d{1,2}(\.\d+)?)?)?(Z|[+-]\d{2}:?\d{2})?$"
)
_YEAR_MONTH_RE = re.compile(r"^(\d{4})[-/](\d{1,2})$")
_YEAR_RE = re.compile(r"^\d{4}$")


def _make_date(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _slash_readings(text: str) -> tuple[date | None, date | None] | None:
    """Return (day-first, month-first) readings, or None if not a/b/yyyy."""
    match = _SLASH_RE.match(text.strip())
    if not match:
        return None
    a, b, year = (int(g) for g in match.groups())
    return _make_date(year, b, a), _make_date(year, a, b)


def slash_kind(text: str) -> SlashKind:
    readings = _slash_readings(text)
    if readings is None:
        return SlashKind.NOT_SLASH
    day_first, month_first = readings
    if day_first and month_first:
        return SlashKind.SAME if day_first == month_first else SlashKind.AMBIGUOUS
    if day_first:
        return SlashKind.DAY_FIRST_ONLY
    if month_first:
        return SlashKind.MONTH_FIRST_ONLY
    return SlashKind.INVALID


def parse_mask_date(text: str, order: SlashOrder | None = None) -> ParsedDate | None:
    t = text.strip()
    match = _FULL_RE.match(t)
    if match:
        rest = t[match.end():]
        if _SUFFIX_RE.match(rest):
            parsed = _make_date(*(int(g) for g in match.groups()))
            return ParsedDate(parsed, False, rest) if parsed else None
        return None
    match = _YEAR_MONTH_RE.match(t)
    if match:
        parsed = _make_date(int(match.group(1)), int(match.group(2)), 1)
        return ParsedDate(parsed, True, "") if parsed else None
    if _YEAR_RE.match(t):
        parsed = _make_date(int(t), 1, 1)
        return ParsedDate(parsed, True, "") if parsed else None
    readings = _slash_readings(t)
    if readings is None:
        return None
    day_first, month_first = readings
    if day_first and month_first and day_first != month_first:  # ambiguous
        if order is None:
            return None
        chosen = day_first if order is SlashOrder.DAY_FIRST else month_first
    else:
        chosen = day_first or month_first
    return ParsedDate(chosen, False, "") if chosen else None


def is_date_like(text: str) -> bool:
    if parse_mask_date(text, None) is not None:
        return True
    return slash_kind(text) is SlashKind.AMBIGUOUS


def shift_years(value: date, years: int) -> date | None:
    year = value.year + years
    if not 1 <= year <= 9999:
        return None
    day = min(value.day, calendar.monthrange(year, value.month)[1])
    return date(year, value.month, day)


def mask_date(text: str, years: int, order: SlashOrder | None) -> tuple[str, DateOutcome]:
    stripped = text.strip()
    if not stripped or stripped.lower() == "nan":
        return text, DateOutcome.BLANK
    parsed = parse_mask_date(text, order)
    if parsed is None:
        return text, DateOutcome.UNPARSED
    shifted = shift_years(parsed.value, years)
    if shifted is None:
        return text, DateOutcome.UNPARSED
    outcome = DateOutcome.FILLED if parsed.partial else DateOutcome.SHIFTED
    return f"{shifted.year:04d}-{shifted.month:02d}-{shifted.day:02d}{parsed.suffix}", outcome
