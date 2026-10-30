from __future__ import annotations

import contextlib
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from PySide6.QtCore import QObject, Signal

from dataforge.core.errors import DataForgeError
from dataforge.tools.edc.config import DEFAULT_POSITIONS, STEP_KEYS
from dataforge.tools.edc.loop import StopChoice
from dataforge.tools.edc.windows import WindowInfo
from dataforge.ui.pages.edc.hooks import EscHook, MouseClickHook
from tests.dataforge.edc_fakes import FakeKeyboardBackend, FakeMouseBackend, FakePorts
from tests.dataforge.qt_helpers import drain_deleted, qapp, wait_until

PAGE = "dataforge.ui.pages.edc.page"
TARGET = WindowInfo(7, "EDC", "chrome.exe")
CELLS = {2: "SITE-1", 3: "SITE-2", 4: "SITE-3"}
NO_EXCEL = "未检测到正在运行的 Excel，请先打开 Excel 并选中第一个站点所在的单元格"


class _FakeEsc(EscHook):
    def __init__(self, backend=None, parent=None) -> None:
        super().__init__(FakeKeyboardBackend(), parent)


class _FakeMouse(MouseClickHook):
    def __init__(self, backend=None, parent=None) -> None:
        super().__init__(FakeMouseBackend(), parent)


class _FakeOverlay(QObject):
    captured = Signal(str, int, int)
    finished = Signal()
    cancelled = Signal()

    def __init__(self, steps, mouse_hook, esc_hook) -> None:
        super().__init__()
        self.steps = tuple(steps)
        self.mouse_hook = mouse_hook
        self.esc_hook = esc_hook
        self.shown = False

    def show(self) -> None:
        self.shown = True


class EdcPageTests(unittest.TestCase):
    def setUp(self) -> None:
        from dataforge.config.store import ConfigStore
        from dataforge.ui.jobs import JobRunner

        qapp()
        self.runner = JobRunner()
        self._pages: list = []
        self.gates: list[threading.Event] = []
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.cfg_path = self.dir / "config.json"
        self.config = ConfigStore(self.cfg_path)
        self.fake = FakePorts(CELLS, 2)
        self.choices: list[StopChoice] = []
        self.stops: list = []

        def ask(parent, stop):
            self.stops.append(stop)
            return self.choices.pop(0)

        mock.patch(f"{PAGE}.legacy_files", return_value=[]).start()
        self.open_ports = mock.patch(
            f"{PAGE}.open_live_ports",
            side_effect=lambda: contextlib.nullcontext(self.fake.ports()),
        ).start()
        mock.patch(f"{PAGE}.list_windows", return_value=[TARGET]).start()
        self.window_at = mock.patch(f"{PAGE}.window_at", return_value=None).start()
        self.ask = mock.patch(f"{PAGE}.ask_stop_choice", side_effect=ask).start()
        mock.patch(f"{PAGE}.EscHook", _FakeEsc).start()
        mock.patch(f"{PAGE}.MouseClickHook", _FakeMouse).start()
        self.bar = mock.patch(f"{PAGE}.InfoBar").start()
        self.tool_bar = mock.patch("dataforge.ui.components.tool_page.InfoBar").start()
        self.addCleanup(mock.patch.stopall)

    def tearDown(self) -> None:
        for gate in self.gates:
            gate.set()
        wait_until(lambda: not self.runner.is_busy())
        self.runner.shutdown()
        self.runner.dispose()
        for page in self._pages:
            page.close()
        drain_deleted(*self._pages, self.runner)
        self._tmp.cleanup()

    # -- helpers -------------------------------------------------------------
    def _page(self, target: WindowInfo | None = TARGET):
        from dataforge.tools.edc.config import EdcConfig, save_config
        from dataforge.ui.pages.edc.page import EdcPage
        from dataforge.ui.registry import get_tool

        if target is not None:
            save_config(self.config, EdcConfig(target_window=target))
        page = EdcPage(get_tool("edc"), self.runner, config=self.config)
        for name in ("showMinimized", "showNormal", "activateWindow", "raise_"):
            setattr(page, name, mock.Mock(name=name))
        self._pages.append(page)
        return page

    def _section(self) -> dict:
        return json.loads(self.cfg_path.read_text(encoding="utf-8"))["edc_site_adder"]

    def _ended(self, page) -> bool:
        return (
            not self.runner.is_busy()
            and page._session is None
            and bool(self.bar.method_calls or self.tool_bar.method_calls)
        )

    def _run(self, page) -> None:
        page.run_bar.start_requested.emit()
        wait_until(lambda: self._ended(page))

    def _block_first_click(self) -> threading.Event:
        reached, gate = threading.Event(), threading.Event()
        self.gates.append(gate)

        def on_call(call: str) -> None:
            if call == "screen.click" and not reached.is_set():
                reached.set()
                gate.wait(5)

        self.fake.on_call = on_call
        return reached

    def _release(self) -> None:
        for gate in self.gates:
            gate.set()

    def _log(self, page) -> str:
        return page.result_panel.page_text("log")

    # -- tests ---------------------------------------------------------------
    def test_registered_in_business_group(self) -> None:
        from qfluentwidgets import FluentIcon

        from dataforge.ui.registry import TOOLS, ToolGroup, get_tool, load_page_class

        spec = get_tool("edc")
        self.assertEqual(spec.name, "EDC 站点添加")
        self.assertEqual(spec.description, "录制点击位置，从 Excel 逐行回放")
        self.assertIs(spec.group, ToolGroup.BUSINESS)
        self.assertIs(spec.icon, FluentIcon.ROBOT)
        ids = [t.id for t in TOOLS]
        self.assertEqual(ids.index("edc"), ids.index("masking") + 1)
        cls = load_page_class(spec)
        self.assertEqual(cls.__name__, "EdcPage")
        self.assertTrue(cls.USES_CONFIG)

    def test_page_structure(self) -> None:
        page = self._page(target=None)
        self.assertEqual(page.run_bar.primary_button().text(), "开始处理")
        self.assertEqual(page.current_job_kind(), "edc")
        self.assertEqual(page.target_label.text(), "未设置（录制时会自动记住你点击的窗口）")
        self.assertEqual(page.pick_window_button.text(), "选择窗口…")
        self.assertEqual(list(page.position_fields), list(STEP_KEYS))
        for key, (x, y, redo) in page.position_fields.items():
            self.assertEqual((x.value(), y.value()), DEFAULT_POSITIONS[key])
            self.assertEqual((x.minimum(), x.maximum()), (-32768, 32767))
            self.assertEqual((y.minimum(), y.maximum()), (-32768, 32767))
            self.assertEqual(redo.text(), "重录")
        self.assertEqual(page.record_button.text(), "一键录制")
        self.assertEqual(page.replay_button.text(), "回放测试")
        self.assertEqual(page.restore_defaults_button.text(), "恢复默认值")
        self.assertEqual((page.max_loops_spin.minimum(), page.max_loops_spin.maximum()),
                         (1, 9999))
        self.assertEqual(page.max_loops_spin.value(), 100)
        self.assertAlmostEqual(page.step_delay_spin.minimum(), 0.1)
        self.assertAlmostEqual(page.step_delay_spin.maximum(), 5.0)
        self.assertAlmostEqual(page.step_delay_spin.singleStep(), 0.1)
        self.assertAlmostEqual(page.step_delay_spin.value(), 0.3)
        self.assertEqual(page.capture_state(), {})
        self.assertEqual(page.restore_state({"x": 1}), [])
        self.assertEqual(page.summary(), "")
        self.assertFalse(self.cfg_path.exists())  # building the page saves nothing

    def test_full_run_success(self) -> None:
        page = self._page()
        self.assertEqual(page.target_label.text(), "EDC · chrome.exe")
        succeeded: list = []
        page.run_succeeded.connect(lambda s, st: succeeded.append((s, st)))
        self._run(page)
        self.bar.success.assert_called_once()
        self.assertEqual(self.bar.success.call_args.args[:2], ("完成", "成功 3 行"))
        self.assertIn("succeeded: 3", page.result_panel.page_text("result"))
        log = self._log(page)
        self.assertIn("成功的行：", log)
        self.assertIn("A4 SITE-3", log)
        self.assertEqual(succeeded, [])
        backend = page.esc_hook._backend
        self.assertEqual(backend.registered, ["esc"])
        self.assertEqual(len(backend.unhooked), 1)
        self.assertFalse(page.esc_hook.is_active())
        self.ask.assert_not_called()
        page.esc_hook.pressed.emit()  # late (queued) press after the run: ignored
        self.assertNotIn("已按 ESC", self._log(page))

    def test_failure_skip_continues_and_keeps_log(self) -> None:
        self.fake.fail = [{"call": "screen.click", "nth": 8, "message": "点击失败"}]
        self.choices = [StopChoice.SKIP]
        page = self._page()
        self._run(page)
        self.assertEqual(self.ask.call_count, 1)
        self.assertEqual(self.stops[0].cell.address(), "A3")
        self.assertFalse(self.stops[0].by_user)
        self.assertEqual(
            self.bar.warning.call_args.args[:2], ("已结束", "成功 2 行，跳过 1 行，出错 0 行")
        )
        log = self._log(page)
        self.assertIn("Excel A2：SITE-1", log)
        self.assertIn("—— 从 A4 继续 ——", log)
        self.assertLess(log.index("Excel A2：SITE-1"), log.index("—— 从 A4 继续 ——"))
        self.assertEqual(
            [line for line in self.fake.trace if line.startswith("excel.selection")],
            ["excel.selection -> A2"],
        )
        self.assertEqual(self.open_ports.call_count, 2)
        page.showNormal.assert_called()
        page.activateWindow.assert_called()
        self.assertFalse(page.esc_hook.is_active())

    def test_redo_then_end(self) -> None:
        self.fake.fail = [
            {"call": "screen.click", "nth": 8, "message": "点击失败"},
            {"call": "screen.click", "nth": 9, "message": "又失败"},
        ]
        self.choices = [StopChoice.REDO, StopChoice.END]
        page = self._page()
        self._run(page)
        self.assertEqual(self.ask.call_count, 2)
        self.assertEqual([s.cell.address() for s in self.stops], ["A3", "A3"])
        self.assertEqual(
            self.bar.warning.call_args.args[:2], ("已结束", "成功 1 行，跳过 0 行，出错 1 行")
        )
        self.assertIn("—— 从 A3 继续 ——", self._log(page))

    def test_cancel_button_is_soft_stop(self) -> None:
        reached = self._block_first_click()
        self.choices = [StopChoice.END]
        page = self._page()
        page.run_bar.start_requested.emit()
        wait_until(reached.is_set)
        with mock.patch.object(self.runner, "cancel") as cancel:
            page.run_bar.cancel_button().click()
        cancel.assert_not_called()
        self._release()
        wait_until(lambda: self._ended(page))
        self.assertEqual(len(self.stops), 1)
        self.assertTrue(self.stops[0].by_user)
        self.tool_bar.info.assert_not_called()

    def test_esc_signal_sets_stop(self) -> None:
        reached = self._block_first_click()
        self.choices = [StopChoice.END]
        page = self._page()
        page.run_bar.start_requested.emit()
        wait_until(reached.is_set)
        self.assertTrue(page.esc_hook.is_active())
        page.esc_hook.pressed.emit()
        self.assertIn("已按 ESC，当前步骤结束后停止", self._log(page))
        self._release()
        wait_until(lambda: self._ended(page))
        self.assertEqual(len(self.stops), 1)
        self.assertTrue(self.stops[0].by_user)
        self.assertFalse(page.esc_hook.is_active())

    def test_esc_outside_run_ignored(self) -> None:
        page = self._page()
        page.esc_hook.pressed.emit()
        self.assertIsNone(page._stop_event)
        self.assertIsNone(page._session)
        self.assertEqual(page.esc_hook._backend.registered, [])
        self.assertEqual(self._log(page), "")
        self.assertEqual(self.bar.method_calls, [])
        self.assertFalse(self.runner.is_busy())

    def test_no_target_window_blocks_start(self) -> None:
        page = self._page(target=None)
        page.run_bar.start_requested.emit()
        self.assertFalse(self.runner.is_busy())
        self.open_ports.assert_not_called()
        self.assertEqual(
            self.bar.warning.call_args.args[:2],
            ("请先设置目标窗口", "请先“一键录制”，或点击“选择窗口…”指定 EDC 所在的浏览器窗口"),
        )

    def test_target_missing_blocks_start(self) -> None:
        page = self._page(target=WindowInfo(9, "Other", "firefox.exe"))
        page.run_bar.start_requested.emit()
        self.assertFalse(self.runner.is_busy())
        self.open_ports.assert_not_called()
        self.assertEqual(
            self.bar.warning.call_args.args[:2],
            ("找不到目标窗口", "Other（firefox.exe）未打开，请重新选择窗口"),
        )

    def test_excel_error_ends_cleanly(self) -> None:
        self.open_ports.side_effect = DataForgeError(NO_EXCEL)
        page = self._page()
        page.run_bar.start_requested.emit()
        wait_until(lambda: self.tool_bar.error.called)
        wait_until(lambda: not self.runner.is_busy())
        self.assertEqual(self.tool_bar.error.call_args.args[:2], ("失败", NO_EXCEL))
        self.assertIsNone(page._session)
        backend = page.esc_hook._backend
        self.assertEqual(backend.registered, ["esc"])
        self.assertEqual(len(backend.unhooked), 1)
        self.assertFalse(page.esc_hook.is_active())
        self.assertTrue(page.record_button.isEnabled())

    def test_recording_updates_positions_and_target(self) -> None:
        overlays: list[_FakeOverlay] = []

        def make(*args):
            overlays.append(_FakeOverlay(*args))
            return overlays[-1]

        mock.patch(f"{PAGE}.RecordingOverlay", side_effect=make).start()
        self.window_at.return_value = WindowInfo(7, "EDC", "chrome.exe")
        page = self._page(target=None)
        page.record_button.click()
        self.assertEqual(len(overlays), 1)
        overlay = overlays[0]
        self.assertEqual(overlay.steps, STEP_KEYS)
        self.assertTrue(overlay.shown)
        self.assertIsInstance(overlay.esc_hook, EscHook)
        page.showMinimized.assert_called_once()
        overlay.captured.emit("新建", 100, 200)
        overlay.captured.emit("查找", 300, 400)
        overlay.finished.emit()
        x, y, _ = page.position_fields["新建"]
        self.assertEqual((x.value(), y.value()), (100, 200))
        x, y, _ = page.position_fields["查找"]
        self.assertEqual((x.value(), y.value()), (300, 400))
        section = self._section()
        self.assertEqual(section["click_positions"]["新建"], {"x": 100, "y": 200})
        self.assertEqual(section["click_positions"]["查找"], {"x": 300, "y": 400})
        self.assertEqual(section["target_window"],
                         {"hwnd": 7, "title": "EDC", "process": "chrome.exe"})
        self.assertIn("EDC", page.target_label.text())
        self.window_at.assert_called_once_with(100, 200)
        page.showNormal.assert_called()
        page.activateWindow.assert_called()
        self.assertEqual(self.bar.success.call_args.args[:2], ("录制完成", ""))
        self.assertIsNone(page._overlay)

    def test_recording_cancelled_restores_window(self) -> None:
        overlays: list[_FakeOverlay] = []

        def make(*args):
            overlays.append(_FakeOverlay(*args))
            return overlays[-1]

        mock.patch(f"{PAGE}.RecordingOverlay", side_effect=make).start()
        page = self._page()
        page.record_button.click()
        overlays[0].cancelled.emit()
        page.showNormal.assert_called()
        self.assertEqual(self.bar.info.call_args.args[:2], ("已取消录制", ""))
        self.assertIsNone(page._overlay)

    def test_single_step_rerecord_only_that_step(self) -> None:
        overlays: list[_FakeOverlay] = []

        def make(*args):
            overlays.append(_FakeOverlay(*args))
            return overlays[-1]

        mock.patch(f"{PAGE}.RecordingOverlay", side_effect=make).start()
        page = self._page()
        page.position_fields["搜索"][2].click()
        self.assertEqual(overlays[0].steps, ("搜索",))
        overlays[0].captured.emit("搜索", 11, 22)
        overlays[0].finished.emit()
        positions = self._section()["click_positions"]
        for key in STEP_KEYS:
            expected = (11, 22) if key == "搜索" else DEFAULT_POSITIONS[key]
            x, y, _ = page.position_fields[key]
            self.assertEqual((x.value(), y.value()), expected, key)
            self.assertEqual(positions[key], {"x": expected[0], "y": expected[1]}, key)
        self.assertEqual(self._section()["target_window"]["hwnd"], 7)

    def test_v2_config_shown(self) -> None:
        self.cfg_path.write_text(
            json.dumps({"edc_site_adder": {"max_loops": 30, "retry_count": 2,
                                           "click_positions": {"ok": {"x": 5, "y": 6}}}}),
            encoding="utf-8",
        )
        page = self._page(target=None)
        self.assertEqual(page.max_loops_spin.value(), 30)
        x, y, _ = page.position_fields["ok"]
        self.assertEqual((x.value(), y.value()), (5, 6))
        self.assertIn("retry_count", self._section())
        x.setValue(15)
        section = self._section()
        self.assertNotIn("retry_count", section)
        self.assertEqual(section["click_positions"]["ok"], {"x": 15, "y": 6})
        self.assertEqual(section["max_loops"], 30)

    def test_field_changes_autosave(self) -> None:
        page = self._page()
        page.max_loops_spin.setValue(12)
        page.step_delay_spin.setValue(1.5)
        section = self._section()
        self.assertEqual(section["max_loops"], 12)
        self.assertAlmostEqual(section["step_delay"], 1.5)

    def test_save_failure_warns(self) -> None:
        page = self._page()
        with mock.patch(f"{PAGE}.save_config", return_value=False):
            page.max_loops_spin.setValue(12)
        self.assertEqual(
            self.bar.warning.call_args.args[:2], ("配置未保存", "请检查配置文件权限")
        )

    def test_restore_defaults_keeps_target(self) -> None:
        page = self._page()
        page.max_loops_spin.setValue(12)
        page.step_delay_spin.setValue(2.0)
        page.position_fields["确认"][0].setValue(1)
        page.restore_defaults_button.click()
        self.assertEqual(page.max_loops_spin.value(), 100)
        self.assertAlmostEqual(page.step_delay_spin.value(), 0.3)
        self.assertEqual(page.position_fields["确认"][0].value(), DEFAULT_POSITIONS["确认"][0])
        section = self._section()
        self.assertEqual(section["max_loops"], 100)
        self.assertEqual(section["click_positions"]["确认"]["x"], DEFAULT_POSITIONS["确认"][0])
        self.assertEqual(section["target_window"]["hwnd"], 7)
        self.assertEqual(page.target_label.text(), "EDC · chrome.exe")
        self.assertEqual(
            self.bar.success.call_args.args[:2], ("已恢复默认值", "目标窗口未改变")
        )

    def test_pick_window_sets_target(self) -> None:
        chosen = WindowInfo(8, "EDC2", "msedge.exe")
        with mock.patch(f"{PAGE}.pick_window", return_value=chosen) as pick:
            page = self._page(target=None)
            page.pick_window_button.click()
        self.assertEqual(pick.call_args.args[1], [TARGET])
        self.assertIsNone(pick.call_args.args[2])
        self.assertEqual(self._section()["target_window"],
                         {"hwnd": 8, "title": "EDC2", "process": "msedge.exe"})
        self.assertEqual(page.target_label.text(), "EDC2 · msedge.exe")

    def test_pick_window_cancel_keeps_target(self) -> None:
        with mock.patch(f"{PAGE}.pick_window", return_value=None):
            page = self._page()
            page.pick_window_button.click()
        self.assertEqual(page.target_label.text(), "EDC · chrome.exe")

    def test_replay_schedules_markers(self) -> None:
        with mock.patch(f"{PAGE}.schedule_replay", return_value=["m"]) as replay:
            page = self._page()
            page.replay_button.click()
        points = replay.call_args.args[0]
        self.assertEqual(points[0], ("1. 新建", 241, 212))
        self.assertEqual(len(points), 7)
        self.assertEqual(points[6], ("7. 确认", 1038, 728))
        self.assertEqual(page._markers, ["m"])

    def test_locked_while_running(self) -> None:
        reached = self._block_first_click()
        self.choices = [StopChoice.END]
        page = self._page()
        widgets = [
            page.pick_window_button, page.record_button, page.replay_button,
            page.restore_defaults_button, page.max_loops_spin, page.step_delay_spin,
        ]
        for x, y, redo in page.position_fields.values():
            widgets.extend((x, y, redo))
        page.run_bar.start_requested.emit()
        wait_until(reached.is_set)
        for widget in widgets:
            self.assertFalse(widget.isEnabled(), widget)
        page.run_bar.cancel_button().click()
        self._release()
        wait_until(lambda: self._ended(page))
        for widget in widgets:
            self.assertTrue(widget.isEnabled(), widget)

    def test_narrow_mode_compacts_forms(self) -> None:
        from dataforge.ui.components.responsive_form import ResponsiveForm
        from dataforge.ui.layout import LayoutMode

        page = self._page()
        forms = page.findChildren(ResponsiveForm)
        self.assertGreaterEqual(len(forms), 2)
        page.apply_layout_mode(LayoutMode.NARROW)
        self.assertTrue(all(f.is_compact() for f in forms))
        page.apply_layout_mode(LayoutMode.WIDE)
        self.assertFalse(any(f.is_compact() for f in forms))


if __name__ == "__main__":
    unittest.main()
