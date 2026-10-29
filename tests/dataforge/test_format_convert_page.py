from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from openpyxl import Workbook

from tests.dataforge.qt_helpers import drain_deleted, qapp, wait_until

AMBIGUOUS = "テスト医師\n".encode("cp932")


class FormatConvertPageTests(unittest.TestCase):
    def setUp(self) -> None:
        from dataforge.ui.jobs import JobRunner

        qapp()
        self.runner = JobRunner()
        self._pages: list = []
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self) -> None:
        wait_until(lambda: not self.runner.is_busy())
        self.runner.shutdown()
        self.runner.dispose()
        drain_deleted(*self._pages, self.runner)
        self._tmp.cleanup()

    def _page(self):
        from dataforge.ui.pages.format_convert_page import FormatConvertPage
        from dataforge.ui.registry import get_tool

        page = FormatConvertPage(get_tool("format_convert"), self.runner)
        self._pages.append(page)
        return page

    def _run(self, page) -> None:
        with mock.patch("dataforge.ui.components.tool_page.InfoBar") as bar:
            page.run_bar.start_requested.emit()
            wait_until(lambda: bar.method_calls != [])
            wait_until(lambda: not self.runner.is_busy())

    def _hidden(self, page) -> dict[str, bool]:
        return {
            "encoding": page.encoding_field.isHidden(),
            "all_sheets": page.all_sheets_box.isHidden(),
            "overwrite": page.overwrite_box.isHidden(),
        }

    def test_mode_switch_updates_controls(self) -> None:
        from dataforge.tools.format_convert import ConvertMode as M

        page = self._page()
        expected = {
            M.CSV_TO_XLSX: {"encoding": False, "all_sheets": True, "overwrite": True},
            M.XLSX_TO_CSV: {"encoding": True, "all_sheets": False, "overwrite": True},
            M.CSV_TO_BOM: {"encoding": False, "all_sheets": True, "overwrite": False},
            M.CSV_UNQUOTE: {"encoding": False, "all_sheets": True, "overwrite": False},
        }
        for mode, hidden in expected.items():
            with self.subTest(mode=mode):
                page.set_mode(mode)
                self.assertEqual(self._hidden(page), hidden)
        texts = {
            M.CSV_TO_XLSX: "每个 CSV 转为一个 XLSX，所有单元格按文本保存",
            M.XLSX_TO_CSV: "导出为 UTF-8 BOM 的 CSV，默认只导出第一个工作表",
            M.CSV_TO_BOM: "自动识别编码后另存为 UTF-8 BOM",
            M.CSV_UNQUOTE: "去掉字段外层引号，内容保持不变",
        }
        for mode, text in texts.items():
            page.set_mode(mode)
            self.assertEqual(page.mode_caption.text(), text)
        self.assertEqual(page.run_bar.primary_button().text(), "开始转换")
        self.assertFalse(page.all_sheets_box.isChecked())

    def test_mode_switch_via_segmented_item(self) -> None:
        from dataforge.tools.format_convert import ConvertMode as M

        page = self._page()
        page.mode_bar.widget(M.CSV_UNQUOTE.value).click()
        self.assertIs(page.mode(), M.CSV_UNQUOTE)
        self.assertEqual(
            [page.mode_bar.widget(m.value).text() for m in M],
            ["CSV → XLSX", "XLSX → CSV", "转 UTF-8 BOM", "去除引号"],
        )

    def test_mode_switch_drops_mismatched_files(self) -> None:
        from dataforge.tools.format_convert import ConvertMode as M

        a, b, c = (self.dir / n for n in ("a.csv", "b.xlsx", "c.csv"))
        for p in (a, b, c):
            p.write_text("x")
        page = self._page()
        page.file_input.set_files([a, c])
        with mock.patch("dataforge.ui.pages.format_convert_page.InfoBar") as bar:
            page.set_mode(M.XLSX_TO_CSV)
        self.assertEqual(page.file_input.files(), [])
        bar.info.assert_called_once()
        self.assertIn("2", " ".join(str(x) for x in bar.info.call_args.args))
        page.file_input.set_files([b])
        with mock.patch("dataforge.ui.pages.format_convert_page.InfoBar") as bar:
            page.set_mode(M.XLSX_TO_CSV)  # unchanged mode: nothing removed, no notice
            page.set_mode(M.CSV_TO_BOM)
        self.assertEqual(page.file_input.files(), [])
        self.assertEqual(bar.info.call_count, 1)
        page.file_input.set_files([a])
        with mock.patch("dataforge.ui.pages.format_convert_page.InfoBar") as bar:
            page.set_mode(M.CSV_TO_XLSX)  # nothing to drop -> silent
        self.assertEqual(page.file_input.files(), [a])
        bar.info.assert_not_called()

    def test_overwrite_hidden_when_leaving_mode_and_disables_output(self) -> None:
        from dataforge.tools.format_convert import ConvertMode as M

        page = self._page()
        page.set_mode(M.CSV_TO_BOM)
        page.overwrite_box.setChecked(True)
        self.assertFalse(page.output_field.isEnabled())
        page.set_mode(M.CSV_TO_XLSX)
        self.assertFalse(page.overwrite_box.isChecked())
        self.assertTrue(page.output_field.isEnabled())
        self.assertFalse(page.capture_state()["overwrite_source"])

    def test_build_job_requires_files(self) -> None:
        page = self._page()
        with mock.patch("dataforge.ui.pages.format_convert_page.InfoBar") as bar:
            self.assertIsNone(page.build_job())
        bar.warning.assert_called_once()

    def test_overwrite_confirm_cancel_aborts(self) -> None:
        from dataforge.tools.format_convert import ConvertMode as M

        a = self.dir / "a.csv"
        a.write_text("x")
        page = self._page()
        page.set_mode(M.CSV_TO_BOM)
        page.file_input.set_files([a])
        page.overwrite_box.setChecked(True)
        with mock.patch("dataforge.ui.pages.format_convert_page.MessageBox") as box:
            box.return_value.exec.return_value = False
            self.assertIsNone(page.build_job())
            box.return_value.deleteLater.assert_called()
            box.return_value.exec.return_value = True
            self.assertIsNotNone(page.build_job())
        self.assertIn("无法撤销", box.call_args.args[1])

    def test_state_roundtrip(self) -> None:
        from dataforge.tools.format_convert import ConvertMode as M

        a, b = self.dir / "a.csv", self.dir / "b.csv"
        a.write_text("x")
        b.write_text("x")
        page = self._page()
        state = {
            "mode": M.CSV_UNQUOTE.value,
            "files": [str(a), str(b)],
            "encoding": "gbk",
            "all_sheets": False,
            "output_dir": str(self.dir),
            "overwrite_source": False,
        }
        self.assertEqual(page.restore_state(state), [])
        self.assertEqual(page.capture_state(), state)
        self.assertEqual(page.summary(), "去除引号 · a.csv 等 2 个文件")
        page.file_input.set_files([a])
        self.assertEqual(page.summary(), "去除引号 · a.csv")
        page.file_input.clear()
        self.assertEqual(page.summary(), "")
        gone = str(self.dir / "gone.csv")
        state2 = {**state, "mode": M.XLSX_TO_CSV.value, "files": [], "all_sheets": True,
                  "encoding": None}
        self.assertEqual(page.restore_state(state2), [])
        self.assertEqual(page.capture_state(), state2)
        state3 = {**state, "mode": M.CSV_TO_BOM.value, "files": [str(a), gone],
                  "overwrite_source": True}
        self.assertEqual(page.restore_state(state3), [gone])
        self.assertEqual(page.capture_state(), {**state3, "files": [str(a)]})
        self.assertTrue(page.overwrite_box.isChecked())

    def test_locking(self) -> None:
        page = self._page()
        page.set_inputs_locked(True)
        self.assertTrue(page.file_input.is_locked())
        self.assertFalse(page.mode_bar.isEnabled())
        self.assertFalse(page.encoding_field.isEnabled())
        self.assertFalse(page.output_field.isEnabled())
        page.set_inputs_locked(False)
        self.assertFalse(page.file_input.is_locked())
        self.assertTrue(page.mode_bar.isEnabled())
        self.assertTrue(page.output_field.isEnabled())

    def test_run_end_to_end_each_mode(self) -> None:
        from dataforge.tools.format_convert import ConvertMode as M

        (self.dir / "c.csv").write_bytes(b"a,b\r\n=1+1,x\r\n")
        wb = Workbook()
        wb.active.append(["h1", "h2"])
        wb.active.append(["v1", "v2"])
        wb.save(self.dir / "x.xlsx")
        (self.dir / "p.csv").write_bytes(b"a,b\n1,2\n")
        (self.dir / "q.csv").write_bytes(b'"a","b"\n"1","2"\n')

        def go(mode, name):
            page = self._page()
            page.set_mode(mode)
            page.file_input.set_files([self.dir / name])
            self._run(page)
            return page

        go(M.CSV_TO_XLSX, "c.csv")
        self.assertTrue((self.dir / "c.xlsx").is_file())
        go(M.XLSX_TO_CSV, "x.xlsx")
        csvs = list(self.dir.glob("x*.csv"))
        self.assertEqual(len(csvs), 1)
        self.assertEqual(csvs[0].read_bytes()[:3], b"\xef\xbb\xbf")
        go(M.CSV_TO_BOM, "p.csv")
        self.assertEqual((self.dir / "p_bom.csv").read_bytes(), b"\xef\xbb\xbfa,b\n1,2\n")
        page = go(M.CSV_UNQUOTE, "q.csv")
        self.assertEqual(
            (self.dir / "q_unquoted.csv").read_bytes(), b"\xef\xbb\xbfa,b\r\n1,2\r\n"
        )
        self.assertIn("q_unquoted.csv", page.result_panel.page_text("result"))

    def test_encoding_retry_only_answered_files(self) -> None:
        from dataforge.tools.format_convert import ConvertMode as M

        good, amb = self.dir / "good.csv", self.dir / "amb.csv"
        good.write_bytes(b"id\n1\n")
        amb.write_bytes(AMBIGUOUS)
        page = self._page()
        page.set_mode(M.CSV_TO_XLSX)
        page.file_input.set_files([good, amb])
        answers = {str(amb): "cp932"}
        with mock.patch(
            "dataforge.ui.components.tool_page.ask_encodings", return_value=answers
        ), mock.patch("dataforge.ui.components.tool_page.InfoBar") as bar:
            page.run_bar.start_requested.emit()
            wait_until(lambda: bar.method_calls != [])
            wait_until(lambda: not self.runner.is_busy())
        self.assertEqual(
            sorted(p.name for p in self.dir.glob("*.xlsx")), ["amb.xlsx", "good.xlsx"]
        )
        self.assertIn("amb.xlsx", page.result_panel.page_text("result"))
        self.assertIn("good.xlsx", page.result_panel.page_text("result"))

    def test_retry_uses_captured_options(self) -> None:
        from dataforge.core.progress import CancelToken, no_progress
        from dataforge.tools.format_convert import ConvertMode as M

        a, b = self.dir / "a.csv", self.dir / "b.csv"
        a.write_text("x")
        b.write_text("x")
        page = self._page()
        page.set_mode(M.CSV_TO_XLSX)
        page.file_input.set_files([a, b])
        page.encoding_field.set_encoding("gbk")
        page.output_field.set_output_dir(self.dir)
        self.assertIsNotNone(page.build_job())
        # Widgets change after the first run was built; the retry must not see that.
        page.set_mode(M.CSV_UNQUOTE)
        page.encoding_field.set_encoding("utf-8")
        page.output_field.set_output_dir(None)
        page.file_input.clear()
        with mock.patch("dataforge.ui.pages.format_convert_page.format_convert.run") as run:
            job = page.build_retry_job({str(b): "cp932"})
            job(no_progress, CancelToken())
        files, options = run.call_args.args[:2]
        self.assertEqual(files, [b])
        self.assertIs(options.mode, M.CSV_TO_XLSX)
        self.assertEqual(options.encoding, "gbk")
        self.assertEqual(options.encodings, {str(b): "cp932"})
        self.assertEqual(options.output_dir, self.dir)
        self.assertFalse(options.overwrite_source)

    def test_retry_without_first_run_returns_none(self) -> None:
        page = self._page()
        self.assertIsNone(page.build_retry_job({"x": "gbk"}))


if __name__ == "__main__":
    unittest.main()
