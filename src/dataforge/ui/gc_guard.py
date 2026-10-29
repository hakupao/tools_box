"""Run Python's cyclic garbage collector on the GUI thread only.

Why: CPython runs the automatic collector on whichever thread crosses the allocation
threshold. With a background job thread that can be the worker, which then destroys Python-owned
Qt garbage (QTimer, QPropertyAnimation, smooth-scroll engines of qfluentwidgets pages that went
out of scope) off the GUI thread while the GUI thread drives animations -> heap corruption /
access violation. So automatic GC is disabled and a main-thread timer collects instead.

Rule: every QObject needs a Qt parent or explicit deletion (``deleteLater()``), and modal
dialogs created per use must be ``deleteLater()``'d after ``exec()`` returns.
"""
from __future__ import annotations

import gc

from PySide6.QtCore import QObject, QTimer


class MainThreadGarbageCollector(QObject):
    def __init__(self, parent: QObject | None = None, interval_ms: int = 1000) -> None:
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.setInterval(interval_ms)
        self._timer.timeout.connect(self.check)

    def start(self) -> None:
        gc.disable()
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()
        gc.enable()

    def check(self) -> None:
        """Generation-aware collection, mirroring the interpreter's own thresholds."""
        counts = gc.get_count()
        thresholds = gc.get_threshold()
        for generation in (2, 1, 0):
            if generation < len(thresholds) and counts[generation] > thresholds[generation]:
                gc.collect(generation)
                return
