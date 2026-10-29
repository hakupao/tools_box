from __future__ import annotations

import gc
import time
import unittest
import weakref

from PySide6.QtCore import QCoreApplication

from dataforge.ui.gc_guard import MainThreadGarbageCollector

from .qt_helpers import qapp


class _Node:
    pass


class GcGuardTests(unittest.TestCase):
    def test_collects_cycles_on_timer_and_restores_gc(self) -> None:
        qapp()
        was_enabled = gc.isenabled()
        guard = MainThreadGarbageCollector(interval_ms=50)
        self.addCleanup(guard.stop if was_enabled else guard._timer.stop)
        guard.start()
        self.assertFalse(gc.isenabled())
        a, b = _Node(), _Node()
        a.other, b.other = b, a
        ref = weakref.ref(a)
        del a, b
        self.assertIsNotNone(ref())
        # Make the young-generation count exceed its threshold, as real allocation would.
        junk = [[] for _ in range(gc.get_threshold()[0] + 50)]
        deadline = time.monotonic() + 3
        while ref() is not None and time.monotonic() < deadline:
            QCoreApplication.processEvents()
            time.sleep(0.01)
        del junk
        self.assertIsNone(ref())
        guard.stop()
        self.assertTrue(gc.isenabled())


if __name__ == "__main__":
    unittest.main()
