"""Progress callback and cooperative cancellation."""
from __future__ import annotations

import threading
from collections.abc import Callable

from .errors import Cancelled

ProgressFn = Callable[[int, int, str], None]


def no_progress(current: int, total: int, label: str) -> None:
    """Default progress callback that does nothing."""


class CancelToken:
    """Thread-safe cancellation flag."""

    def __init__(self) -> None:
        self._event = threading.Event()

    def cancel(self) -> None:
        self._event.set()

    @property
    def cancelled(self) -> bool:
        return self._event.is_set()

    def raise_if_cancelled(self) -> None:
        if self._event.is_set():
            raise Cancelled()
