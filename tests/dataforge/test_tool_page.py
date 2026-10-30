from __future__ import annotations

import logging
import threading
import time
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

import shiboken6
from PySide6.QtWidgets import QVBoxLayout, QWidget
from qfluentwidgets import PushButton

from dataforge.core.errors import DataForgeError
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

    def test_keep_log_for_next_start(self) -> None:
        def fn(progress, token) -> Result:
            logging.getLogger("dataforge.test").info("旧行")
            return Result()

        page = self._page(fn=fn)
        page.run_bar.start_requested.emit()
        wait_until(lambda: "旧行" in page.result_panel.page_text("log"))
        wait_until(lambda: not self.runner.is_busy())
        page.keep_log_for_next_start("—— 继续 ——")
        page.run_bar.start_requested.emit()
        wait_until(lambda: "—— 继续 ——" in page.result_panel.page_text("log"))
        wait_until(lambda: not self.runner.is_busy())
        text = page.result_panel.page_text("log")
        self.assertIn("旧行", text)
        self.assertIn("—— 继续 ——", text)
        page.run_bar.start_requested.emit()
        wait_until(lambda: "—— 继续 ——" not in page.result_panel.page_text("log"))
        wait_until(lambda: not self.runner.is_busy())
        self.assertEqual(page.result_panel.page_text("log").count("旧行"), 1)

    def test_recent_snapshot_taken_at_start(self) -> None:
        gate = threading.Event()
        self.gates.append(gate)

        def fn(progress, token) -> Result:
            gate.wait(5)
            r = Result()
            r.add_output(Path("out.csv"))
            return r

        page = self._page(fn=fn)
        got: list[tuple] = []
        page.run_succeeded.connect(lambda s, d: got.append((s, d)))
        page.run_bar.start_requested.emit()
        page.summary = lambda: "changed"
        page.capture_state = lambda: {"k": 2}
        gate.set()
        wait_until(lambda: bool(got))
        self.assertEqual(got[0], ("dummy", {"k": 1}))

    def _finish_with(self, result: Result):
        page = self._page(fn=lambda p, c: result)
        with mock.patch("dataforge.ui.components.tool_page.InfoBar") as bar:
            page.run_bar.start_requested.emit()
            wait_until(lambda: bar.method_calls != [])
        wait_until(lambda: not self.runner.is_busy())
        return bar

    def test_infobar_error_when_nothing_converted_with_errors(self) -> None:
        r = Result()
        r.fail("a.xlsx", "坏文件")
        bar = self._finish_with(r)
        bar.error.assert_called_once()
        self.assertEqual(bar.error.call_args.args[1], "坏文件")
        bar.success.assert_not_called()

    def test_infobar_warning_when_nothing_generated(self) -> None:
        r = Result()
        r.warn("a.xlsx", "没有需要转换的内容")
        bar = self._finish_with(r)
        bar.warning.assert_called_once()
        self.assertEqual(bar.warning.call_args.args[:2], ("未生成文件", "没有需要转换的内容"))
        bar.success.assert_not_called()

    def test_infobar_partial_failure_warning(self) -> None:
        r = Result()
        r.add_output(Path("o.csv"))
        r.fail("a.xlsx", "坏文件")
        bar = self._finish_with(r)
        self.assertEqual(bar.warning.call_args.args[0], "部分文件失败")

    def test_infobar_success(self) -> None:
        r = Result()
        r.add_output(Path("o.csv"))
        bar = self._finish_with(r)
        bar.success.assert_called_once()

    def test_snapshot_cleared_after_run(self) -> None:
        page = self._page()
        page.run_bar.start_requested.emit()
        wait_until(lambda: not self.runner.is_busy() and page.locked == [True, False])
        self.assertIsNone(page._snapshot)

    def test_zero_output_without_issues_shows_info(self) -> None:
        bar = self._finish_with(Result())
        bar.info.assert_called_once()
        self.assertEqual(bar.info.call_args.args[:2], ("未生成文件", "本次运行没有生成任何文件"))
        bar.success.assert_not_called()

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


class _Quiet(ToolPage):
    """Minimal page whose first job returns one output and one encoding question."""

    def __init__(self, spec, runner, parent=None) -> None:
        super().__init__(spec, runner, parent)
        self.state = {"k": 1}
        self.retry_args: list[dict[str, str]] = []
        self.carried_seen: list = []

    def build_job(self) -> JobFn | None:
        def job(progress, token) -> Result:
            r = Result()
            r.add_output(Path("first.csv"))
            r.ask_encoding("amb.csv", {"cp932": "a", "gbk": "b"})
            return r

        return job

    def capture_state(self) -> dict[str, Any]:
        return dict(self.state)

    def restore_state(self, state: dict[str, Any]) -> list[str]:
        return []

    def summary(self) -> str:
        return "quiet"

    def set_inputs_locked(self, locked: bool) -> None:
        pass


class _Retrying(_Quiet):
    def build_retry_job(self, encodings: dict[str, str]) -> JobFn | None:
        self.retry_args.append(encodings)
        self.carried_seen.append(len(self.carried_result().outputs))

        def job(progress, token) -> Result:
            r = Result()
            r.add_output(Path("second.csv"))
            return r

        return job


class _CancellingRetry(_Retrying):
    def build_retry_job(self, encodings: dict[str, str]) -> JobFn | None:
        def job(progress, token) -> Result:
            token.cancel()
            token.raise_if_cancelled()
            return Result()

        return job


class _FailingRetry(_Retrying):
    def build_retry_job(self, encodings: dict[str, str]) -> JobFn | None:
        def job(progress, token) -> Result:
            raise RuntimeError("boom")

        return job


class _ReplacingRetry(_Retrying):
    RETRY_MERGES = False

    def build_retry_job(self, encodings: dict[str, str]) -> JobFn | None:
        carried = self.carried_result()
        carried.outputs.clear()
        return super().build_retry_job(encodings)


class _TwoAmbiguous(_Retrying):
    def build_job(self) -> JobFn | None:
        def job(progress, token) -> Result:
            logging.getLogger("dataforge.test").info("first-run-line")
            r = Result()
            r.add_output(Path("first.csv"))
            r.count("skipped", 1)
            r.ask_encoding("amb1.csv", {"cp932": "a", "gbk": "b"})
            r.ask_encoding("amb2.csv", {"cp932": "a", "gbk": "b"})
            return r

        return job


class _DataForgeErrorRetry(_TwoAmbiguous):
    def build_retry_job(self, encodings: dict[str, str]) -> JobFn | None:
        def job(progress, token) -> Result:
            raise DataForgeError("bad retry")

        return job


class _CancellingTwo(_TwoAmbiguous):
    def build_retry_job(self, encodings: dict[str, str]) -> JobFn | None:
        def job(progress, token) -> Result:
            token.cancel()
            token.raise_if_cancelled()
            return Result()

        return job


class _AuxPage(_Quiet):
    """Page whose job is a 'scan' auxiliary job returning data."""

    def __init__(self, spec, runner, parent=None, fn: JobFn | None = None) -> None:
        super().__init__(spec, runner, parent)
        self.fn = fn
        self.aux_calls: list[tuple] = []
        self.locked: list[bool] = []

    def current_job_kind(self) -> str:
        return "scan"

    def build_job(self) -> JobFn | None:
        if self.fn is not None:
            return self.fn

        def job(progress, token) -> Result:
            r = Result()
            r.data = {"columns": ["a"]}
            return r

        return job

    def on_aux_finished(self, kind: str, result: Result) -> None:
        self.aux_calls.append((kind, result))

    def set_inputs_locked(self, locked: bool) -> None:
        self.locked.append(locked)


class AuxJobTests(unittest.TestCase):
    def setUp(self) -> None:
        qapp()
        self.runner = JobRunner()
        self.gates: list[threading.Event] = []

    def tearDown(self) -> None:
        for g in self.gates:
            g.set()
        self.runner.shutdown()
        self.runner.dispose()

    def _run_aux(self, page, settle) -> mock.MagicMock:
        with mock.patch("dataforge.ui.components.tool_page.InfoBar") as bar:
            page.run_bar.start_requested.emit()
            wait_until(settle)
            wait_until(lambda: not self.runner.is_busy())
        return bar

    def test_aux_finish_calls_hook_without_recent_or_infobar(self) -> None:
        page = _AuxPage(get_tool("date_convert"), self.runner)
        got: list[tuple] = []
        page.run_succeeded.connect(lambda s, d: got.append((s, d)))
        bar = self._run_aux(page, lambda: page.aux_calls != [])
        kind, result = page.aux_calls[0]
        self.assertEqual(kind, "scan")
        self.assertEqual(result.data, {"columns": ["a"]})
        self.assertEqual(got, [])
        self.assertEqual(bar.method_calls, [])
        self.assertIs(page.locked[-1], False)
        self.assertEqual(page._job_kind, "run")

    def test_aux_with_encoding_questions_skips_retry(self) -> None:
        def fn(progress, token) -> Result:
            r = Result()
            r.ask_encoding("amb.csv", {"cp932": "a", "gbk": "b"})
            return r

        page = _AuxPage(get_tool("date_convert"), self.runner, fn=fn)
        with mock.patch("dataforge.ui.components.tool_page.ask_encodings") as ask:
            self._run_aux(page, lambda: page.aux_calls != [])
        ask.assert_not_called()
        self.assertEqual(len(page.aux_calls[0][1].encoding_questions), 1)

    def test_aux_failure_shows_error_no_recent(self) -> None:
        def fn(progress, token) -> Result:
            raise DataForgeError("boom")

        page = _AuxPage(get_tool("date_convert"), self.runner, fn=fn)
        got: list[tuple] = []
        page.run_succeeded.connect(lambda s, d: got.append((s, d)))
        with mock.patch("dataforge.ui.components.tool_page.InfoBar") as bar:
            page.run_bar.start_requested.emit()
            wait_until(lambda: bar.error.called)
            wait_until(lambda: not self.runner.is_busy())
        self.assertEqual(got, [])
        self.assertEqual(page.aux_calls, [])
        self.assertEqual(page._job_kind, "run")
        self.assertIs(page.locked[-1], False)

    def test_aux_cancel_shows_info_no_recent(self) -> None:
        started = threading.Event()

        def fn(progress, token) -> Result:
            started.set()
            for _ in range(500):
                token.raise_if_cancelled()
                threading.Event().wait(0.01)
            return Result()

        page = _AuxPage(get_tool("date_convert"), self.runner, fn=fn)
        page._carry = Result()  # stale carry must not be shown
        page._carry.add_output(Path("stale.csv"))
        got: list[tuple] = []
        page.run_succeeded.connect(lambda s, d: got.append((s, d)))
        with mock.patch("dataforge.ui.components.tool_page.InfoBar") as bar:
            page.run_bar.start_requested.emit()
            wait_until(started.is_set)
            page.run_bar.cancel_requested.emit()
            wait_until(lambda: bar.info.called)
        self.assertEqual(got, [])
        self.assertEqual(page._job_kind, "run")

    def test_submit_job_busy_warns(self) -> None:
        gate = threading.Event()
        self.gates.append(gate)

        def blocker(progress, token) -> Result:
            gate.wait(5)
            return Result()

        self.assertTrue(self.runner.submit("width_convert", blocker))
        page = _AuxPage(get_tool("date_convert"), self.runner)
        with mock.patch("dataforge.ui.components.tool_page.InfoBar") as bar:
            self.assertFalse(page.submit_job(blocker, "scan"))
        bar.warning.assert_called_once()
        self.assertEqual(bar.warning.call_args.args[:2], ("无法开始", "已有任务正在运行"))
        self.assertEqual(page._job_kind, "run")

    def test_refused_submit_drops_keep_log_separator(self) -> None:
        gate = threading.Event()
        self.gates.append(gate)

        def blocker(progress, token) -> Result:
            gate.wait(5)
            return Result()

        page = _AuxPage(get_tool("date_convert"), self.runner)
        page.keep_log_for_next_start("—— 继续 ——")
        self.assertTrue(self.runner.submit("width_convert", blocker))
        with mock.patch("dataforge.ui.components.tool_page.InfoBar"):
            self.assertFalse(page.submit_job(blocker, "scan"))
        self.assertIsNone(page._keep_log_separator)
        gate.set()
        wait_until(lambda: not self.runner.is_busy())
        page.result_panel.append_log("旧行")
        with mock.patch("dataforge.ui.components.tool_page.InfoBar"):
            page.run_bar.start_requested.emit()
            wait_until(lambda: len(page.aux_calls) == 1)
            wait_until(lambda: not self.runner.is_busy())
        log = page.result_panel.page_text("log")
        self.assertNotIn("—— 继续 ——", log)
        self.assertNotIn("旧行", log)
        shiboken6.delete(page)

    def test_hook_can_queue_next_job_when_idle(self) -> None:
        for _ in range(10):
            page = _AuxPage(get_tool("date_convert"), self.runner)
            page.runs = 0

            def again(progress, token) -> Result:
                return Result()

            def hook(kind, result, page=page, again=again):
                page.aux_calls.append((kind, result))
                if len(page.aux_calls) == 1:
                    page.submit_job_when_idle(again, "scan")

            page.on_aux_finished = hook
            with mock.patch("dataforge.ui.components.tool_page.InfoBar") as bar:
                page.run_bar.start_requested.emit()
                wait_until(lambda: len(page.aux_calls) == 2)
                wait_until(lambda: not self.runner.is_busy())
            self.assertEqual(bar.method_calls, [])
            self.assertEqual(page.locked[-1], False)
            shiboken6.delete(page)  # stale pages would also hear the next runs

    def test_when_idle_follow_up_dropped_on_shutdown(self) -> None:
        page = _AuxPage(get_tool("date_convert"), self.runner)
        started = threading.Event()
        follow_ups: list[int] = []

        def blocker(progress, token) -> Result:
            started.set()
            while True:
                token.raise_if_cancelled()
                time.sleep(0.01)

        def follow(progress, token) -> Result:
            follow_ups.append(1)
            return Result()

        with mock.patch("dataforge.ui.components.tool_page.InfoBar") as bar:
            self.assertTrue(self.runner.submit("date_convert", blocker))
            self.assertTrue(started.wait(5))
            page.submit_job_when_idle(follow, "scan")
            self.runner.shutdown()
            wait_until(lambda: not self.runner.is_busy())
        self.assertEqual(bar.method_calls, [])
        self.assertEqual(follow_ups, [])
        self.assertFalse(self.runner.is_busy())
        shiboken6.delete(page)

    def test_aux_then_run_emits_run_succeeded_once(self) -> None:
        page = _AuxPage(get_tool("date_convert"), self.runner)
        got: list[tuple] = []
        page.run_succeeded.connect(lambda s, d: got.append((s, d)))
        with mock.patch("dataforge.ui.components.tool_page.InfoBar"):
            page.run_bar.start_requested.emit()
            wait_until(lambda: page.aux_calls != [])
            wait_until(lambda: not self.runner.is_busy())

            def run_job(progress, token) -> Result:
                r = Result()
                r.add_output(Path("out.csv"))
                return r

            self.assertTrue(page.submit_job(run_job))
            wait_until(lambda: got != [])
            wait_until(lambda: not self.runner.is_busy())
        self.assertEqual(got, [("quiet", {"k": 1})])
        self.assertEqual(len(page.aux_calls), 1)

    def test_default_hook_raises(self) -> None:
        page = _Quiet(get_tool("date_convert"), self.runner)
        with self.assertRaises(NotImplementedError):
            page.on_aux_finished("scan", Result())
        self.assertEqual(page.current_job_kind(), "run")


class RetryFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        qapp()
        self.runner = JobRunner()

    def tearDown(self) -> None:
        self.runner.shutdown()
        self.runner.dispose()

    def _run(self, cls, answers):
        page = cls(get_tool("date_convert"), self.runner)
        got: list[tuple] = []
        done: list[bool] = []
        page.run_succeeded.connect(lambda s, d: got.append((s, d)))
        with mock.patch("dataforge.ui.components.tool_page.ask_encodings",
                        return_value=answers) as ask, \
                mock.patch("dataforge.ui.components.tool_page.InfoBar") as bar:
            page.run_bar.start_requested.emit()
            page.state = {"k": 2}  # edited after submit: snapshot must stay {"k": 1}
            wait_until(lambda: bar.method_calls != [])
            wait_until(lambda: not self.runner.is_busy())
        return page, got, ask

    def test_retry_flow_merges_results(self) -> None:
        page, got, ask = self._run(_Retrying, {"amb.csv": "gbk"})
        ask.assert_called_once()
        self.assertEqual(page.retry_args, [{"amb.csv": "gbk"}])
        self.assertEqual(page.carried_seen, [1])
        self.assertIsNone(page.carried_result())
        self.assertEqual(page.result_panel.tab_text("result"), "结果 (2)")
        self.assertIn("first.csv", page.result_panel.page_text("result"))
        self.assertIn("second.csv", page.result_panel.page_text("result"))
        self.assertEqual(got, [("quiet", {"k": 1})])

    def test_retry_replaces_when_not_merging(self) -> None:
        page, got, _ = self._run(_ReplacingRetry, {"amb.csv": "gbk"})
        self.assertEqual(page.result_panel.tab_text("result"), "结果 (1)")
        self.assertNotIn("first.csv", page.result_panel.page_text("result"))
        self.assertIn("second.csv", page.result_panel.page_text("result"))
        self.assertEqual(got, [("quiet", {"k": 1})])

    def test_cancelled_dialog_warns_and_skips(self) -> None:
        page, got, _ = self._run(_Retrying, {})
        self.assertEqual(page.retry_args, [])
        self.assertEqual(page.result_panel.tab_text("result"), "结果 (1)")
        self.assertIn("amb.csv: 未选择编码，已跳过", page.result_panel.page_text("warnings"))
        self.assertNotIn("需要选择编码", page.result_panel.page_text("warnings"))
        self.assertEqual(len(got), 1)

    def test_cancelled_retry_still_emits_run_succeeded_once(self) -> None:
        page, got, _ = self._run(_CancellingRetry, {"amb.csv": "gbk"})
        self.assertEqual(got, [("quiet", {"k": 1})])
        self.assertIn("first.csv", page.result_panel.page_text("result"))

    def test_failed_retry_still_emits_run_succeeded_once(self) -> None:
        page, got, _ = self._run(_FailingRetry, {"amb.csv": "gbk"})
        self.assertEqual(got, [("quiet", {"k": 1})])
        self.assertIn("first.csv", page.result_panel.page_text("result"))

    def test_retry_not_offered_without_hook(self) -> None:
        page, got, ask = self._run(_Quiet, {"amb.csv": "gbk"})
        ask.assert_not_called()
        self.assertEqual(page.result_panel.tab_text("warnings"), "警告 (1)")
        self.assertIn("amb.csv: 需要选择编码", page.result_panel.page_text("warnings"))
        self.assertEqual(len(got), 1)

    def test_declined_encoding_counts_as_skipped(self) -> None:
        page, _, _ = self._run(_TwoAmbiguous, {"amb1.csv": "gbk"})
        self.assertIn("skipped: 2", page.result_panel.page_text("result"))
        self.assertIn("amb2.csv: 未选择编码，已跳过", page.result_panel.page_text("warnings"))

    def test_retry_keeps_first_run_log(self) -> None:
        page, _, _ = self._run(_TwoAmbiguous, {"amb1.csv": "gbk"})
        log = page.result_panel.page_text("log")
        self.assertIn("first-run-line", log)
        self.assertIn("—— 重新处理编码有歧义的文件 ——", log)

    def test_retry_failure_keeps_first_outputs(self) -> None:
        page = _DataForgeErrorRetry(get_tool("date_convert"), self.runner)
        got: list[tuple] = []
        page.run_succeeded.connect(lambda s, d: got.append((s, d)))
        with mock.patch("dataforge.ui.components.tool_page.ask_encodings",
                        return_value={"amb1.csv": "gbk"}), \
                mock.patch("dataforge.ui.components.tool_page.InfoBar") as bar:
            page.run_bar.start_requested.emit()
            page.state = {"k": 2}
            wait_until(lambda: bar.error.called)
            wait_until(lambda: not self.runner.is_busy())
        self.assertEqual(got, [("quiet", {"k": 1})])
        self.assertIn("first.csv", page.result_panel.page_text("result"))
        bar.error.assert_called_once()

    def test_retry_cancel_keeps_first_outputs(self) -> None:
        page = _CancellingTwo(get_tool("date_convert"), self.runner)
        got: list[tuple] = []
        page.run_succeeded.connect(lambda s, d: got.append((s, d)))
        with mock.patch("dataforge.ui.components.tool_page.ask_encodings",
                        return_value={"amb1.csv": "gbk"}), \
                mock.patch("dataforge.ui.components.tool_page.InfoBar") as bar:
            page.run_bar.start_requested.emit()
            page.state = {"k": 2}
            wait_until(lambda: bar.info.called)
            wait_until(lambda: not self.runner.is_busy())
        self.assertEqual(got, [("quiet", {"k": 1})])
        self.assertIn("first.csv", page.result_panel.page_text("result"))
        bar.info.assert_called_once()


if __name__ == "__main__":
    unittest.main()
