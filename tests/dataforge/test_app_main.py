from __future__ import annotations

import unittest
from unittest import mock

from dataforge import app


class AppMainTests(unittest.TestCase):
    def test_runner_shut_down_before_dispose(self) -> None:
        order = mock.Mock()
        runner = order.runner
        with mock.patch.object(app, "setup_logging"), \
                mock.patch.object(app, "QApplication") as qapp, \
                mock.patch.object(app, "MainThreadGarbageCollector") as guard_cls, \
                mock.patch.object(app, "ConfigStore"), \
                mock.patch.object(app, "apply_theme_mode"), \
                mock.patch.object(app, "start_system_theme_listener"), \
                mock.patch.object(app, "JobRunner", return_value=runner), \
                mock.patch.object(app, "RecentStore"), \
                mock.patch.object(app, "MainWindow"), \
                mock.patch.object(app, "wait_for_orphans", return_value=True) as wait:
            order.attach_mock(guard_cls.return_value, "guard")
            order.attach_mock(wait, "wait")
            qapp.return_value.exec.return_value = 0
            self.assertEqual(app.main(["x"]), 0)
        names = [c[0] for c in runner.method_calls]
        self.assertLess(names.index("shutdown"), names.index("dispose"))
        flow = [c[0] for c in order.mock_calls if c[0] in ("guard.start", "guard.stop", "wait")]
        self.assertEqual(flow, ["guard.start", "wait"])  # started, and never re-enabled gc


if __name__ == "__main__":
    unittest.main()
