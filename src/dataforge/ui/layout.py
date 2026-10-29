from __future__ import annotations

from enum import Enum

MIN_WINDOW_WIDTH = 640
WIDE_MIN_WIDTH = 1100
MEDIUM_MIN_WIDTH = 750


class LayoutMode(Enum):
    WIDE = "wide"
    MEDIUM = "medium"
    NARROW = "narrow"


def layout_mode_for_width(window_width: int) -> LayoutMode:
    if window_width >= WIDE_MIN_WIDTH:
        return LayoutMode.WIDE
    if window_width >= MEDIUM_MIN_WIDTH:
        return LayoutMode.MEDIUM
    return LayoutMode.NARROW
