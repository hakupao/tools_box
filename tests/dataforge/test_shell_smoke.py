from __future__ import annotations

import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from qfluentwidgets import MessageBox, Theme, setTheme

from dataforge.config.recent import RecentStore
from dataforge.config.store import ConfigStore
from dataforge.core.result import Result
from dataforge.ui.jobs import JobRunner, wait_for_orphans
from dataforge.ui.registry import TOOLS
from dataforge.ui.shell import MainWindow
from tests.dataforge.qt_helpers import qapp, wait_until


class ShellSmokeTests(unittest.TestCase):
    def setUp(self) -> None:
        qapp()
        self._tmp = tempfile.TemporaryDirectory()
        self.cfg_path = Path(self._tmp.name) / "config.json"
        self.config = ConfigStore(self.cfg_path)
        self.runner = JobRunner()
        self.recent = RecentStore(self.config)
        self.gates: list[threading.Event] = []
        self.windows: list[MainWindow] = []
        self.finished: list[tuple] = []
        self.runner.finished.connect(lambda t, _r: self.finished.append(("finished", t)))

    def tearDown(self) -> None:
        for g in self.gates:
            g.set()
        wait_for_orphans(3000)
        self.runner.shutdown()
        self.runner.dispose()
        for w in self.windows:
            w.close()
            w.deleteLater()
        setTheme(Theme.AUTO)
        self._tmp.cleanup()

    def _window(self) -> MainWindow:
        w = MainWindow(self.config, self.runner, self.recent)
        self.windows.append(w)
        w.show()
        return w

    def _blocking_job(self):
        gate = threading.Event()
        self.gates.append(gate)

        def job(progress, token):
            gate.wait(5)
            return Result()

        return gate, job

    def test_window_builds_in_both_themes(self):
        for theme in (Theme.LIGHT, Theme.DARK):
            setTheme(theme)
            w = self._window()
            for spec in TOOLS:
                w.open_tool(spec.id)
                self.assertIsNotNone(w.page_for(spec.id), spec.id)

    def test_theme_switch_while_running(self):
        w = self._window()
        gate, job = self._blocking_job()
        self.assertTrue(self.runner.submit("date_convert", job))
        setTheme(Theme.DARK)
        for spec in TOOLS:
            w.open_tool(spec.id)
            self.assertIsNotNone(w.page_for(spec.id), spec.id)
        self.assertTrue(self.runner.is_busy())
        self.assertEqual(self.runner.current_tool(), "date_convert")
        gate.set()
        wait_until(lambda: not self.runner.is_busy())
        self.assertIn(("finished", "date_convert"), self.finished)

    def test_open_running_tool_keeps_inputs(self):
        w = self._window()
        w.open_tool("width_convert")
        page = w.page_for("width_convert")
        gate, job = self._blocking_job()
        self.assertTrue(self.runner.submit("width_convert", job))
        with mock.patch("dataforge.ui.shell.InfoBar") as bar,                 mock.patch.object(page, "restore_state") as restore:
            w.open_tool("width_convert", {"files": ["x.xlsx"]})
        restore.assert_not_called()
        bar.info.assert_called_once()
        gate.set()
        wait_until(lambda: not self.runner.is_busy())

    def test_open_idle_tool_restores(self):
        w = self._window()
        w.open_tool("width_convert")
        page = w.page_for("width_convert")
        with mock.patch.object(page, "restore_state", return_value=[]) as restore:
            w.open_tool("width_convert", {"files": []})
        restore.assert_called_once()

    def test_nav_collapse_breakpoint(self):
        from dataforge.ui.layout import WIDE_MIN_WIDTH

        w = self._window()
        self.assertEqual(w.navigationInterface.panel.minimumExpandWidth, WIDE_MIN_WIDTH)

    def test_settings_persists_theme(self):
        w = self._window()
        w.settings.theme_combo.setCurrentIndex(2)
        self.assertEqual(ConfigStore(self.cfg_path).section("app")["theme"], "dark")

    def test_close_while_running_shuts_down(self):
        w = self._window()
        _, job = self._blocking_job()
        self.assertTrue(self.runner.submit("date_convert", job))
        with mock.patch.object(MessageBox, "exec", return_value=True):
            w.close()
        self.assertFalse(self.runner.is_busy())

    def test_close_cancelled_keeps_running(self):
        w = self._window()
        gate, job = self._blocking_job()
        self.assertTrue(self.runner.submit("date_convert", job))
        with mock.patch.object(MessageBox, "exec", return_value=False):
            w.close()
        self.assertTrue(self.runner.is_busy())
        self.assertTrue(w.isVisible())
        gate.set()
        wait_until(lambda: not self.runner.is_busy())

    def test_page_load_failure_does_not_crash(self):
        w = self._window()
        with mock.patch("dataforge.ui.shell.load_page_class", side_effect=ImportError("boom")):
            w.open_tool("date_convert")
        self.assertIsNone(w.page_for("date_convert"))

    def test_shell_injects_config(self):
        from dataforge.ui.components.tool_page import ToolPage

        seen: dict = {}

        class _CfgPage(ToolPage):
            USES_CONFIG = True

            def __init__(self, spec, runner, parent=None, config=None):
                super().__init__(spec, runner, parent)
                seen["config"] = config

        w = self._window()
        with mock.patch("dataforge.ui.shell.load_page_class", return_value=_CfgPage):
            w.open_tool("date_convert")
        self.assertIs(seen["config"], self.config)

    def test_run_succeeded_records_recent(self):
        w = self._window()
        w.open_tool("width_convert")
        page = w.page_for("width_convert")
        page.run_succeeded.emit("摘要", {"k": 1})
        entries = self.recent.entries()
        self.assertEqual((entries[0].tool_id, entries[0].summary), ("width_convert", "摘要"))


if __name__ == "__main__":
    unittest.main()
