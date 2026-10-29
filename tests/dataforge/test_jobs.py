from __future__ import annotations

import logging
import threading
import time
import unittest

from dataforge.core.errors import DataForgeError
from dataforge.core.progress import CancelToken, ProgressFn
from dataforge.core.result import Result
from dataforge.ui.jobs import JobRunner, wait_for_orphans
from tests.dataforge.qt_helpers import qapp, wait_until


class JobRunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        qapp()
        self.gates: list[threading.Event] = []
        self.runner = JobRunner()
        self.events: list[tuple] = []
        r = self.runner
        r.started.connect(lambda t: self.events.append(("started", t)))
        r.progress.connect(lambda c, n, s: self.events.append(("progress", c, n, s)))
        r.log.connect(lambda s: self.events.append(("log", s)))
        r.finished.connect(lambda t, res: self.events.append(("finished", t, res)))
        r.failed.connect(lambda t, m: self.events.append(("failed", t, m)))
        r.cancelled.connect(lambda t: self.events.append(("cancelled", t)))
        r.busy_changed.connect(lambda b: self.events.append(("busy", b)))

    def tearDown(self) -> None:
        for g in self.gates:
            g.set()
        wait_for_orphans(3000)
        self.runner.shutdown()
        self.runner.dispose()

    def _names(self) -> list[str]:
        return [e[0] for e in self.events]

    def _idle(self) -> None:
        wait_until(lambda: not self.runner.is_busy() and ("busy", False) in self.events)

    def test_finished_delivers_result(self):
        res = Result(stats={"n": 1})
        self.assertTrue(self.runner.submit("t", lambda p, c: res))
        self._idle()
        self.assertIn(("finished", "t", res), self.events)
        busy = [e[1] for e in self.events if e[0] == "busy"]
        self.assertEqual(busy, [True, False])
        self.assertIsNone(self.runner.current_tool())

    def test_second_submit_rejected_while_busy(self):
        gate = threading.Event()

        def fn(p: ProgressFn, c: CancelToken) -> Result:
            gate.wait(5)
            return Result()

        self.assertTrue(self.runner.submit("t", fn))
        self.assertTrue(self.runner.is_busy())
        self.assertEqual(self.runner.current_tool(), "t")
        self.assertFalse(self.runner.submit("u", lambda p, c: Result()))
        gate.set()
        self._idle()
        self.assertEqual(self._names().count("started"), 1)
        self.assertTrue(self.runner.submit("u", lambda p, c: Result()))
        self._idle()

    def test_cancel_emits_cancelled(self):
        def fn(p: ProgressFn, c: CancelToken) -> Result:
            while True:
                c.raise_if_cancelled()
                time.sleep(0.01)

        self.runner.submit("t", fn)
        self.runner.cancel()
        self._idle()
        self.assertIn(("cancelled", "t"), self.events)
        self.assertNotIn("failed", self._names())

    def test_cancel_inside_except_exception_still_cancelled(self):
        def job(progress, token):
            token.cancel()
            try:
                token.raise_if_cancelled()
            except Exception:  # per-file guard must not swallow cancellation
                pass
            return Result()

        self.assertTrue(self.runner.submit("t", job))
        self._idle()
        self.assertIn(("cancelled", "t"), self.events)
        self.assertNotIn("finished", self._names())

    def test_dataforge_error_maps_to_failed(self):
        def fn(p, c):
            raise DataForgeError("缺少 DM.csv")

        self.runner.submit("t", fn)
        self._idle()
        self.assertIn(("failed", "t", "缺少 DM.csv"), self.events)

    def test_unexpected_error_maps_to_failed(self):
        def fn(p, c):
            raise RuntimeError("boom")

        with self.assertLogs("dataforge", level="ERROR"):
            self.runner.submit("t", fn)
            self._idle()
        failed = [e for e in self.events if e[0] == "failed"]
        self.assertEqual(len(failed), 1)
        self.assertTrue(failed[0][2].startswith("内部错误："))
        self.assertIn("boom", failed[0][2])

    def test_progress_forwarded(self):
        def fn(p, c):
            p(1, 2, "a.xlsx")
            return Result()

        self.runner.submit("t", fn)
        self._idle()
        self.assertIn(("progress", 1, 2, "a.xlsx"), self.events)

    def test_log_forwarded_while_busy(self):
        def fn(p, c):
            logging.getLogger("dataforge.tools.t").info("处理中")
            return Result()

        self.runner.submit("t", fn)
        self._idle()
        logs = [e[1] for e in self.events if e[0] == "log"]
        self.assertTrue(any("处理中" in s for s in logs), logs)
        self.assertTrue(any(s.startswith("INFO ") for s in logs))

    def test_log_not_forwarded_when_idle(self):
        logging.getLogger("dataforge.tools.t").info("空闲日志")
        qapp().processEvents()
        self.assertEqual([e for e in self.events if e[0] == "log"], [])

    def test_shutdown_cancels_and_waits(self):
        started = threading.Event()

        def fn(p, c):
            started.set()
            while True:
                c.raise_if_cancelled()
                time.sleep(0.01)

        self.runner.submit("t", fn)
        self.assertTrue(started.wait(5))
        self.runner.shutdown()
        self.assertFalse(self.runner.is_busy())

    def test_submit_rejected_after_shutdown(self):
        self.runner.shutdown()
        self.assertFalse(self.runner.submit("t", lambda p, c: Result()))
        self.assertFalse(self.runner.is_busy())
        self.assertNotIn("started", self._names())

    def test_pending_follow_up_cannot_start_during_shutdown(self):
        started = threading.Event()
        follow_ups: list[bool] = []

        def fn(p, c):
            started.set()
            while True:
                c.raise_if_cancelled()
                time.sleep(0.01)

        def on_busy(busy: bool) -> None:
            if not busy:
                follow_ups.append(self.runner.submit("t2", lambda p, c: Result()))

        self.runner.submit("t", fn)
        self.assertTrue(started.wait(5))
        self.runner.busy_changed.connect(on_busy)
        self.runner.shutdown()
        self.assertEqual(follow_ups, [False])
        self.assertFalse(self.runner.is_busy())
        self.assertIsNone(self.runner.current_tool())

    def test_finished_delivered_before_busy_false(self):
        self.runner.submit("t", lambda p, c: Result())
        self._idle()
        names = [(e[0], e[1] if e[0] == "busy" else None) for e in self.events]
        self.assertLess(names.index(("finished", None)), names.index(("busy", False)))

    def test_shutdown_timeout_orphans_job_and_ignores_late_signals(self):
        gate = threading.Event()
        self.gates.append(gate)
        started = threading.Event()

        def stuck(p, c):
            started.set()
            gate.wait(10)  # ignores the cancel token
            return Result()

        self.runner.submit("t", stuck)
        self.assertTrue(started.wait(5))
        with self.assertLogs("dataforge", level="WARNING"):
            self.runner.shutdown(timeout_ms=50)
        self.assertFalse(self.runner.is_busy())
        self.assertIn(("busy", False), self.events)

        # A shut-down runner accepts no new job.
        self.assertFalse(self.runner.submit("t2", lambda p, c: Result(stats={"n": 2})))

        gate.set()
        self.assertTrue(wait_for_orphans(2000))
        for _ in range(20):
            qapp().processEvents()
            time.sleep(0.01)
        # The orphan's late outcome is ignored.
        self.assertNotIn("finished", self._names())
        self.assertNotIn("failed", self._names())
        self.assertEqual(self._names().count("started"), 1)
        self.assertNotIn("cancelled", self._names())
        self.assertFalse(self.runner.is_busy())

    def test_dispose_removes_handler(self):
        before = len(logging.getLogger("dataforge").handlers)
        other = JobRunner()
        self.assertEqual(len(logging.getLogger("dataforge").handlers), before + 1)
        other.dispose()
        self.assertEqual(len(logging.getLogger("dataforge").handlers), before)


if __name__ == "__main__":
    unittest.main()
