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

    def test_fluent_translator_installed_and_kept_alive(self) -> None:
        with mock.patch.object(app, "setup_logging"), \
                mock.patch.object(app, "QApplication") as qapp, \
                mock.patch.object(app, "FluentTranslator") as translator_cls, \
                mock.patch.object(app, "MainThreadGarbageCollector"), \
                mock.patch.object(app, "ConfigStore"), \
                mock.patch.object(app, "apply_theme_mode"), \
                mock.patch.object(app, "start_system_theme_listener"), \
                mock.patch.object(app, "JobRunner"), \
                mock.patch.object(app, "RecentStore"), \
                mock.patch.object(app, "MainWindow"), \
                mock.patch.object(app, "wait_for_orphans", return_value=True):
            qapp.return_value.exec.return_value = 0
            app.main(["x"])
        locale = translator_cls.call_args.args[0]
        self.assertEqual(locale.name(), "zh_CN")
        qapp.return_value.installTranslator.assert_called_once_with(translator_cls.return_value)


if __name__ == "__main__":
    unittest.main()
