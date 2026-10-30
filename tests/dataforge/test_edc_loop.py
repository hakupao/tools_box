import threading
import unittest

from dataforge.core.errors import Cancelled, DataForgeError
from dataforge.core.progress import CancelToken, no_progress
from dataforge.tools.edc.config import DEFAULT_POSITIONS, STEP_KEYS, EdcConfig
from dataforge.tools.edc.loop import (
    STEP_NAMES,
    CellRef,
    EdcSession,
    RowDone,
    RowStop,
    Segment,
    StopChoice,
    run_segment,
)
from dataforge.tools.edc.windows import WindowInfo
from tests.dataforge.edc_fakes import FakePorts

TARGET = WindowInfo(100, "EDC", "chrome.exe")
FAILSAFE_REASON = "鼠标移到了屏幕角落，已触发安全停止"


def _config(max_loops: int = 100, step_delay: float = 0.3) -> EdcConfig:
    return EdcConfig(max_loops=max_loops, step_delay=step_delay, target_window=TARGET)


def _cell(row: int) -> CellRef:
    return CellRef("Book1", "Sheet1", row, 1)


def _run(fake: FakePorts, config: EdcConfig | None = None, start=None, end_row=None,
         stop=None, cancel=None, progress=no_progress) -> Segment:
    result = run_segment(
        config or _config(),
        fake.ports(),
        start,
        end_row,
        stop or threading.Event(),
        progress,
        cancel or CancelToken(),
    )
    return result.data


def _row_actions(row: int, value: str, delay: str = "0.3") -> list[str]:
    lines = [f"excel.text A{row}", f"clipboard.copy {value}", "sleep 0.1",
             "window.activate", "sleep 0.1"]
    for key in STEP_KEYS:
        x, y = DEFAULT_POSITIONS[key]
        lines.append(f"screen.click {x} {y}")
        if key == "搜索框":
            lines += ["sleep 0.05", "screen.paste"]
        lines.append(f"sleep {delay}")
    lines += [f"excel.focus A{row + 1}", "sleep 0.1"]
    return lines


class StepNamesTests(unittest.TestCase):
    def test_step_names(self):
        self.assertEqual(
            STEP_NAMES,
            (
                "读取单元格",
                "复制到剪贴板",
                "激活目标窗口",
                "点击【新建】",
                "点击【查找】",
                "点击【搜索框】并粘贴",
                "点击【搜索】",
                "点击【选择】",
                "点击【ok】",
                "点击【确认】",
                "切回 Excel 并选中下一行",
            ),
        )

    def test_address(self):
        self.assertEqual(CellRef("B", "S", 5, 1).address(), "A5")
        self.assertEqual(CellRef("B", "S", 3, 27).address(), "AA3")
        self.assertEqual(CellRef("B", "S", 1, 52).address(), "AZ1")
        self.assertEqual(CellRef("B", "S", 1, 26).address(), "Z1")
        self.assertEqual(CellRef("B", "S", 1, 703).address(), "AAA1")

    def test_at_row(self):
        self.assertEqual(_cell(2).at_row(9), _cell(9))

    def test_step_name(self):
        stop = RowStop(_cell(2), "X", 3, "r", False)
        self.assertEqual(stop.step_name, "激活目标窗口")


class RunSegmentTests(unittest.TestCase):
    def test_three_rows_then_empty(self):
        fake = FakePorts({2: "SITE-1", 3: "SITE-2", 4: "SITE-3"}, start_row=2)
        calls = []
        seg = _run(fake, progress=lambda i, n, label: calls.append((i, n, label)))
        self.assertEqual(seg.reached, "empty")
        self.assertIsNone(seg.stop)
        self.assertEqual(seg.start, _cell(2))
        self.assertEqual(seg.end_row, 102)
        self.assertEqual(
            seg.done,
            [RowDone(_cell(2), "SITE-1"), RowDone(_cell(3), "SITE-2"), RowDone(_cell(4), "SITE-3")],
        )
        expected = ["excel.selection -> A2", "excel.text A2", "excel.text A3", "excel.text A4",
                    "excel.text A5"]
        expected += _row_actions(2, "SITE-1") + _row_actions(3, "SITE-2")
        expected += _row_actions(4, "SITE-3") + ["excel.text A5"]
        self.assertEqual(fake.trace, expected)
        self.assertEqual(
            calls,
            [(1, 3, "Excel A2：SITE-1"), (2, 3, "Excel A3：SITE-2"), (3, 3, "Excel A4：SITE-3")],
        )

    def test_clicks_follow_config(self):
        config = _config(step_delay=0.5)
        config.click_positions["查找"] = (7, 8)
        fake = FakePorts({2: "S"}, start_row=2)
        _run(fake, config)
        clicks = [t for t in fake.trace if t.startswith("screen.click")]
        self.assertEqual(clicks[1], "screen.click 7 8")
        self.assertEqual(len(clicks), 7)
        self.assertIn("sleep 0.5", fake.trace)

    def test_whitespace_trimmed_and_blank_is_empty(self):
        fake = FakePorts({2: " SITE ", 3: "   ", 4: "LATER"}, start_row=2)
        seg = _run(fake)
        self.assertEqual(seg.reached, "empty")
        self.assertEqual(seg.done, [RowDone(_cell(2), "SITE")])
        self.assertIn("clipboard.copy SITE", fake.trace)
        self.assertNotIn("excel.text A4", fake.trace)

    def test_limit(self):
        fake = FakePorts({2: "A", 3: "B", 4: "C"}, start_row=2)
        seg = _run(fake, _config(max_loops=2))
        self.assertEqual(seg.reached, "limit")
        self.assertEqual(seg.end_row, 4)
        self.assertEqual([d.value for d in seg.done], ["A", "B"])
        self.assertNotIn("excel.text A4", fake.trace)

    def test_explicit_end_row(self):
        fake = FakePorts({2: "A", 3: "B", 4: "C"}, start_row=2)
        seg = _run(fake, start=_cell(3), end_row=4)
        self.assertEqual(seg.reached, "limit")
        self.assertEqual(seg.done, [RowDone(_cell(3), "B")])

    def test_click_failure_stops_row(self):
        # row 1 makes clicks 1..7; the 2nd click of row 2 (【查找】, step 5) is click #9
        fake = FakePorts({2: "A", 3: "B", 4: "C"}, start_row=2,
                         fail=[{"call": "screen.click", "nth": 9, "message": "boom"}])
        seg = _run(fake)
        self.assertEqual(seg.reached, "stopped")
        self.assertEqual(seg.stop, RowStop(_cell(3), "B", 5, "boom", False))
        self.assertEqual(seg.stop.step_name, "点击【查找】")
        self.assertEqual(seg.done, [RowDone(_cell(2), "A")])
        self.assertEqual(fake.trace[-1], "screen.click 1137 460")

    def test_failsafe_reason(self):
        fake = FakePorts({2: "A"}, start_row=2, fail=[
            {"call": "screen.click", "nth": 1, "message": "corner", "exc": "FailSafeException"}
        ])
        seg = _run(fake)
        self.assertEqual(seg.stop.reason, FAILSAFE_REASON)
        self.assertEqual(seg.stop.step, 4)

    def test_empty_message_uses_class_name(self):
        fake = FakePorts({2: "A"}, start_row=2, fail=[
            {"call": "clipboard.copy", "nth": 1, "message": "", "exc": "ClipError"}
        ])
        seg = _run(fake)
        self.assertEqual((seg.stop.step, seg.stop.reason), (2, "ClipError"))

    def test_window_missing_stops_at_step_3(self):
        msg = "找不到目标窗口：EDC（chrome.exe）"
        fake = FakePorts({2: "A"}, start_row=2, fail=[
            {"call": "window.activate", "nth": 1, "message": msg, "exc": "DataForgeError"}
        ])
        seg = _run(fake)
        self.assertEqual(seg.stop, RowStop(_cell(2), "A", 3, msg, False))
        self.assertEqual(seg.done, [])

    def test_text_failure_stops_at_step_1(self):
        # the pre-count reads A2 and A3 (calls #1, #2); the row read is call #3
        fake = FakePorts({2: "A"}, start_row=2,
                         fail=[{"call": "excel.text", "nth": 3, "message": "com"}])
        seg = _run(fake)
        self.assertEqual(seg.stop, RowStop(_cell(2), "", 1, "com", False))

    def test_count_failure_does_not_stop(self):
        fake = FakePorts({2: "A"}, start_row=2,
                         fail=[{"call": "excel.text", "nth": 1, "message": "com"}])
        calls = []
        seg = _run(fake, _config(max_loops=5), progress=lambda i, n, s: calls.append(n))
        self.assertEqual(seg.reached, "empty")
        self.assertEqual(calls, [5])

    def test_esc_soft_stop(self):
        # selection + 2 count reads + text, copy, sleep, activate, sleep = 8 actions
        fake = FakePorts({2: "A"}, start_row=2, esc_after=8)
        seg = _run(fake, stop=fake.stop_flag())
        self.assertEqual(seg.reached, "stopped")
        self.assertEqual(seg.stop, RowStop(_cell(2), "A", 4, "已按 ESC 停止", True))
        self.assertEqual(len(fake.trace), 8)

    def test_esc_before_first_step(self):
        fake = FakePorts({2: "A"}, start_row=2, esc_after=1)
        seg = _run(fake, stop=fake.stop_flag())
        # step 1 reads the cell before honouring ESC, so the stop carries the value
        self.assertEqual(seg.stop, RowStop(_cell(2), "A", 1, "已按 ESC 停止", True))
        self.assertEqual(fake.trace[-1], "excel.text A2")

    def test_esc_during_last_row_ends_on_empty_cell(self):
        fake = FakePorts({2: "SITE-1"}, start_row=2)

        class _AfterFocus:
            def is_set(self) -> bool:
                return any(line.startswith("excel.focus") for line in fake.trace)

        seg = _run(fake, stop=_AfterFocus())
        self.assertEqual(seg.reached, "empty")
        self.assertIsNone(seg.stop)
        self.assertEqual(seg.done, [RowDone(_cell(2), "SITE-1")])
        self.assertEqual(fake.trace[-1], "excel.text A3")

    def test_hard_cancel_raises(self):
        fake = FakePorts({2: "A"}, start_row=2)
        cancel = CancelToken()
        cancel.cancel()
        with self.assertRaises(Cancelled):
            _run(fake, cancel=cancel)
        self.assertNotIn("clipboard.copy A", fake.trace)

    def test_no_target_window_raises(self):
        fake = FakePorts({2: "A"}, start_row=2)
        with self.assertRaises(DataForgeError) as ctx:
            _run(fake, EdcConfig())
        self.assertEqual(str(ctx.exception), "未设置目标窗口")
        self.assertEqual(fake.trace, [])

    def test_selection_error_wrapped(self):
        fake = FakePorts({2: "A"}, start_row=2,
                         fail=[{"call": "excel.selection", "nth": 1, "message": "no excel"}])
        with self.assertRaises(DataForgeError) as ctx:
            _run(fake)
        self.assertTrue(str(ctx.exception).startswith("无法读取 Excel 选中的单元格"))
        self.assertIn("no excel", str(ctx.exception))

    def test_explicit_start_skips_selection(self):
        fake = FakePorts({2: "A", 3: "B"}, start_row=2)
        seg = _run(fake, start=_cell(3))
        self.assertFalse(any(t.startswith("excel.selection") for t in fake.trace))
        self.assertEqual(seg.done, [RowDone(_cell(3), "B")])
        self.assertEqual(seg.end_row, 103)

    def test_fail_counts_accumulate_across_segments(self):
        fake = FakePorts({2: "A", 3: "B"}, start_row=2,
                         fail=[{"call": "window.activate", "nth": 2, "message": "gone"}])
        first = _run(fake, end_row=3)
        self.assertEqual(first.reached, "limit")
        second = _run(fake, start=_cell(3), end_row=4)
        self.assertEqual(second.stop.step, 3)


class SelectionPassThroughTests(unittest.TestCase):
    def test_real_dataforge_error_not_wrapped(self):
        fake = FakePorts({2: "A"}, start_row=2)
        ports = fake.ports()

        def selection():
            raise DataForgeError("未选中单元格")

        ports.excel.selection = selection
        with self.assertRaises(DataForgeError) as ctx:
            run_segment(_config(), ports, None, None, threading.Event(), no_progress,
                        CancelToken())
        self.assertEqual(str(ctx.exception), "未选中单元格")


class SessionTests(unittest.TestCase):
    def _segment(self, done, stop=None, end_row=10):
        return Segment(_cell(2), end_row, list(done), stop, "stopped" if stop else "empty")

    def test_session_resolve(self):
        first_stop = RowStop(_cell(3), "B", 5, "boom", False)
        session = EdcSession.begin(self._segment([RowDone(_cell(2), "A")], first_stop))
        self.assertEqual(session.first, _cell(2))
        self.assertEqual(session.end_row, 10)
        self.assertEqual(session.done, [RowDone(_cell(2), "A")])

        # REDO: same cell, nothing recorded
        self.assertEqual(session.resolve(first_stop, StopChoice.REDO), _cell(3))
        self.assertEqual((session.skipped, session.failed), ([], []))

        # SKIP: recorded as skipped, next row returned
        self.assertEqual(session.resolve(first_stop, StopChoice.SKIP), _cell(4))
        self.assertEqual(session.skipped, [first_stop])

        session.absorb(self._segment([RowDone(_cell(4), "C")]))
        self.assertEqual([d.cell.row for d in session.done], [2, 4])

        # SKIP at the last allowed row: nothing left
        last = RowStop(_cell(9), "Z", 2, "clip", False)
        self.assertIsNone(session.resolve(last, StopChoice.SKIP))
        self.assertEqual(session.skipped, [first_stop, last])

        # END with step > 1 (even by user): failed
        esc = RowStop(_cell(5), "D", 6, "已按 ESC 停止", True)
        self.assertIsNone(session.resolve(esc, StopChoice.END))
        self.assertEqual(session.failed, [esc])

        # END on an untouched row stopped by the user: not recorded
        untouched = RowStop(_cell(6), "", 1, "已按 ESC 停止", True)
        self.assertIsNone(session.resolve(untouched, StopChoice.END))
        self.assertEqual(session.failed, [esc])

        # END at step 1 caused by an error: failed
        read_err = RowStop(_cell(7), "", 1, "com", False)
        self.assertIsNone(session.resolve(read_err, StopChoice.END))
        self.assertEqual(session.failed, [esc, read_err])

        result = session.to_result()
        self.assertIs(result.data, session)
        self.assertEqual(result.stats, {"succeeded": 2, "skipped": 2, "failed": 2})
        self.assertEqual(
            [(w.path, w.message) for w in result.warnings],
            [
                ("A3", "已跳过（第 5 步「点击【查找】」：boom）"),
                ("A9", "已跳过（第 2 步「复制到剪贴板」：clip）"),
            ],
        )
        self.assertEqual(
            [(e.path, e.message) for e in result.errors],
            [
                ("A5", "出错（第 6 步「点击【搜索框】并粘贴」：已按 ESC 停止）"),
                ("A7", "出错（第 1 步「读取单元格」：com）"),
            ],
        )
        self.assertEqual(session.done_lines(), ["A2 A", "A4 C"])

    def test_clean_result(self):
        session = EdcSession.begin(self._segment([RowDone(_cell(2), "A")]))
        result = session.to_result()
        self.assertTrue(result.ok)
        self.assertEqual(result.stats, {"succeeded": 1, "skipped": 0, "failed": 0})
        self.assertEqual(result.warnings, [])


if __name__ == "__main__":
    unittest.main()
