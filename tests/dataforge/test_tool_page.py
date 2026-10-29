from __future__ import annotations

import threading
import unittest
from pathlib import Path
from typing import Any

from PySide6.QtWidgets import QVBoxLayout, QWidget
from qfluentwidgets import PushButton

from dataforge.core.result import Result
from dataforge.ui.components.responsive_form import ResponsiveForm
from dataforge.ui.components.tool_page import ToolPage
from dataforge.ui.jobs import JobFn, JobRunner
from dataforge.ui.layout import LayoutMode
from dataforge.ui.registry import get_tool
from tests.dataforge.qt_helpers import qapp, wait_until


class _DummyPage(ToolPage):
    def __init__(self, spec, runner, parent=None, fn: JobFn | None = None) -> None:
        super().__init__(spec, runner, parent)
        self.form = ResponsiveForm(self)
        self.form.add_row("名称", PushButton("x", self))
        self.add_section("设置", self.form)
        self.fn = fn
        self.locked: list[bool] = []

    def build_job(self) -> JobFn | None:
        if self.fn is not None:
            return self.fn

        def job(progress, token) -> Result:
            r = Result()
            r.add_output(Path("out.csv"))
            return r

        return job

    def capture_state(self) -> dict[str, Any]:
        return {"k": 1}

    def restore_state(self, state: dict[str, Any]) -> list[str]:
        return []

    def summary(self) -> str:
        return "dummy"

    def set_inputs_locked(self, locked: bool) -> None:
        self.locked.append(locked)


class ToolPageTests(unittest.TestCase):
    def setUp(self) -> None:
        qapp()
        self.runner = JobRunner()
        self.gates: list[threading.Event] = []

    def tearDown(self) -> None:
        for g in self.gates:
            g.set()
        self.runner.shutdown()
        self.runner.dispose()

    def _page(self, tool: str = "date_convert", **kw) -> _DummyPage:
        return _DummyPage(get_tool(tool), self.runner, **kw)

    def _blocking_fn(self) -> JobFn:
        gate = threading.Event()
        self.gates.append(gate)

        def fn(progress, token) -> Result:
            gate.wait(5)
            return Result()

        return fn

    def test_layout_mode_switches(self) -> None:
        page = self._page()
        page.apply_layout_mode(LayoutMode.NARROW)
        self.assertTrue(page.result_panel.is_collapsed())
        self.assertTrue(page.form.is_compact())
        self.assertEqual(page.layout_mode(), LayoutMode.NARROW)
        page.apply_layout_mode(LayoutMode.WIDE)
        self.assertFalse(page.result_panel.is_collapsed())
        self.assertFalse(page.form.is_compact())
        page.apply_layout_mode(LayoutMode.MEDIUM)
        self.assertFalse(page.result_panel.is_collapsed())
        self.assertEqual(page.layout_mode(), LayoutMode.MEDIUM)

    def test_resize_picks_mode_from_window_width(self) -> None:
        host = QWidget()
        lay = QVBoxLayout(host)
        page = self._page(parent=host)
        lay.addWidget(page)
        host.resize(700, 500)
        host.show()
        qapp().sendPostedEvents()
        page.update_layout_mode()
        self.assertEqual(page.layout_mode(), LayoutMode.NARROW)
        host.resize(1200, 500)
        page.update_layout_mode()
        self.assertEqual(page.layout_mode(), LayoutMode.WIDE)
        host.close()

    def test_run_emits_run_succeeded(self) -> None:
        page = self._page()
        got: list[tuple] = []
        page.run_succeeded.connect(lambda s, d: got.append((s, d)))
        page.run_bar.start_requested.emit()
        wait_until(lambda: bool(got))
        self.assertEqual(got[0], (page.summary(), page.capture_state()))
        wait_until(lambda: not self.runner.is_busy())
        self.assertEqual(page.locked, [True, False])
        self.assertTrue(page.run_bar.primary_button().isEnabled())

    def test_other_tool_running_blocks(self) -> None:
        page = self._page("date_convert")
        self.assertTrue(self.runner.submit("width_convert", self._blocking_fn()))
        wait_until(lambda: not page.run_bar.primary_button().isEnabled())
        self.assertIn("全角转半角 正在运行", page.run_bar.reason_text())
        for g in self.gates:
            g.set()
        wait_until(lambda: page.run_bar.primary_button().isEnabled())
        self.assertEqual(page.run_bar.reason_text(), "")

    def test_cancel_only_for_own_tool(self) -> None:
        page = self._page("date_convert")
        self.runner.submit("width_convert", self._blocking_fn())
        page.run_bar.cancel_requested.emit()
        self.assertFalse(self.runner._worker.token.cancelled)
        for g in self.gates:
            g.set()
        wait_until(lambda: not self.runner.is_busy())

    def test_cancel_own_tool(self) -> None:
        def fn(progress, token) -> Result:
            while True:
                token.raise_if_cancelled()
                threading.Event().wait(0.01)

        page = self._page("date_convert", fn=fn)
        page.run_bar.start_requested.emit()
        wait_until(lambda: self.runner.is_busy())
        page.run_bar.cancel_requested.emit()
        wait_until(lambda: not self.runner.is_busy())
        self.assertEqual(page.locked, [True, False])
        self.assertFalse(page.run_bar.cancel_button().isEnabled())

    def test_build_job_none_does_not_submit(self) -> None:
        page = self._page()
        page.build_job = lambda: None  # type: ignore[method-assign]
        page.run_bar.start_requested.emit()
        self.assertFalse(self.runner.is_busy())


if __name__ == "__main__":
    unittest.main()
