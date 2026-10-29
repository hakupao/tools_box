from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font

from dataforge.core.errors import Cancelled, DataForgeError
from dataforge.core.progress import CancelToken, no_progress
from dataforge.tools.width_convert import WidthOptions, run, to_halfwidth


def _make_sample(path: Path) -> None:
    wb = Workbook()
    ws = wb.active
    ws["A1"] = "ＮＡＭＥ"
    ws["A1"].font = Font(bold=True)
    ws["A2"] = "ＡＢＣ"
    ws["B2"] = "=LEN(A2)"
    ws["A3"] = "１２"
    ws.merge_cells("A3:B3")
    wb.save(path)


class ToHalfwidthTests(unittest.TestCase):
    def test_to_halfwidth(self) -> None:
        self.assertEqual(to_halfwidth("ＡＢＣ１２３！　ｘ"), "ABC123! x")
        self.assertEqual(to_halfwidth("テスト医師ｱｲｳ"), "テスト医師ｱｲｳ")


class RunTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_run_keeps_formatting_and_formula(self) -> None:
        src = self.dir / "sample.xlsx"
        _make_sample(src)
        before = src.read_bytes()
        result = run([src], WidthOptions(), no_progress, CancelToken())
        self.assertEqual(result.stats, {"files": 1, "cells_changed": 3})
        self.assertEqual(result.outputs, [self.dir / "sample_halfwidth.xlsx"])
        ws = load_workbook(result.outputs[0]).active
        self.assertEqual(ws["A1"].value, "NAME")
        self.assertTrue(ws["A1"].font.bold)
        self.assertEqual(ws["A2"].value, "ABC")
        self.assertEqual(ws["B2"].value, "=LEN(A2)")
        self.assertEqual(ws["A3"].value, "12")
        self.assertEqual([str(r) for r in ws.merged_cells.ranges], ["A3:B3"])
        self.assertEqual(src.read_bytes(), before)

    def test_existing_output_gets_suffix(self) -> None:
        src = self.dir / "sample.xlsx"
        _make_sample(src)
        (self.dir / "sample_halfwidth.xlsx").write_bytes(b"x")
        result = run([src], WidthOptions(), no_progress, CancelToken())
        self.assertEqual(result.outputs, [self.dir / "sample_halfwidth_1.xlsx"])

    def test_output_dir(self) -> None:
        src = self.dir / "sample.xlsx"
        _make_sample(src)
        out = self.dir / "out"
        result = run([src], WidthOptions(output_dir=out), no_progress, CancelToken())
        self.assertEqual(result.outputs, [out / "sample_halfwidth.xlsx"])

    def test_overwrite_source(self) -> None:
        src = self.dir / "sample.xlsx"
        _make_sample(src)
        result = run([src], WidthOptions(overwrite_source=True), no_progress, CancelToken())
        self.assertEqual(result.outputs, [src])
        self.assertEqual(load_workbook(src).active["A1"].value, "NAME")

    def test_conflict_and_permission_error_continue(self) -> None:
        a, b = self.dir / "a.xlsx", self.dir / "b.xlsx"
        _make_sample(a)
        _make_sample(b)
        real_save = Workbook.save
        calls = {"n": 0}

        def flaky(self_wb, filename):
            calls["n"] += 1
            if calls["n"] == 1:
                raise PermissionError("locked")
            return real_save(self_wb, filename)

        with mock.patch.object(Workbook, "save", flaky):
            result = run([a, b], WidthOptions(), no_progress, CancelToken())
        self.assertEqual(len(result.errors), 1)
        self.assertEqual(result.errors[0].path, str(a))
        self.assertIn("Excel", result.errors[0].message)
        self.assertEqual(result.outputs, [self.dir / "b_halfwidth.xlsx"])
        self.assertEqual(result.stats["files"], 1)

    def test_bad_file_reports_error(self) -> None:
        bad = self.dir / "bad.xlsx"
        bad.write_bytes(b"not a zip")
        result = run([bad], WidthOptions(), no_progress, CancelToken())
        self.assertEqual(len(result.errors), 1)
        self.assertTrue(result.errors[0].message.startswith("转换失败"))
        self.assertEqual(result.outputs, [])

    def test_cancel_before_second_file(self) -> None:
        a, b = self.dir / "a.xlsx", self.dir / "b.xlsx"
        _make_sample(a)
        _make_sample(b)
        token = CancelToken()

        def progress(cur: int, total: int, label: str) -> None:
            if cur == 1:
                token.cancel()

        with self.assertRaises(Cancelled):
            run([a, b], WidthOptions(), progress, token)

    def test_empty_files_raises(self) -> None:
        with self.assertRaises(DataForgeError):
            run([], WidthOptions(), no_progress, CancelToken())


class PageTests(unittest.TestCase):
    def setUp(self) -> None:
        from dataforge.ui.jobs import JobRunner
        from tests.dataforge.qt_helpers import qapp

        qapp()
        self.runner = JobRunner()
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self) -> None:
        self.runner.shutdown()
        self.runner.dispose()
        self._tmp.cleanup()

    def _page(self):
        from dataforge.ui.pages.width_convert_page import WidthConvertPage
        from dataforge.ui.registry import get_tool

        return WidthConvertPage(get_tool("width_convert"), self.runner)

    def test_page_restore_reports_missing(self) -> None:
        a, z = self.dir / "a.xlsx", self.dir / "z.xlsx"
        _make_sample(a)
        page = self._page()
        missing = page.restore_state(
            {"files": [str(a), str(z)], "output_dir": None, "overwrite_source": False}
        )
        self.assertEqual(missing, [str(z)])
        self.assertEqual(page.file_input.files(), [a])

    def test_state_and_summary(self) -> None:
        a, b = self.dir / "a.xlsx", self.dir / "b.xlsx"
        _make_sample(a)
        _make_sample(b)
        page = self._page()
        page.restore_state(
            {"files": [str(a)], "output_dir": str(self.dir), "overwrite_source": False}
        )
        self.assertEqual(page.summary(), "a.xlsx")
        page.file_input.set_files([a, b])
        self.assertEqual(page.summary(), "a.xlsx 等 2 个文件")
        self.assertEqual(
            page.capture_state(),
            {"files": [str(a), str(b)], "output_dir": str(self.dir), "overwrite_source": False},
        )

    def test_build_job_requires_files(self) -> None:
        page = self._page()
        with mock.patch("dataforge.ui.pages.width_convert_page.InfoBar") as bar:
            self.assertIsNone(page.build_job())
        bar.warning.assert_called_once()

    def test_overwrite_requires_confirmation(self) -> None:
        a = self.dir / "a.xlsx"
        _make_sample(a)
        page = self._page()
        page.file_input.set_files([a])
        page.overwrite_box.setChecked(True)
        with mock.patch("dataforge.ui.pages.width_convert_page.MessageBox") as box:
            box.return_value.exec.return_value = False
            self.assertIsNone(page.build_job())
            box.return_value.exec.return_value = True
            self.assertIsNotNone(page.build_job())

    def test_output_dir_choice_and_cancel(self) -> None:
        page = self._page()
        target = str(self.dir)
        with mock.patch(
            "dataforge.ui.pages.width_convert_page.QFileDialog.getExistingDirectory",
            return_value=target,
        ):
            page.output_combo.setCurrentIndex(1)
        self.assertEqual(page.capture_state()["output_dir"], target)
        with mock.patch(
            "dataforge.ui.pages.width_convert_page.QFileDialog.getExistingDirectory",
            return_value="",
        ):
            page.output_combo.setCurrentIndex(0)
            page.output_combo.setCurrentIndex(1)
        self.assertEqual(page.output_combo.currentIndex(), 0)
        self.assertIsNone(page.capture_state()["output_dir"])


if __name__ == "__main__":
    unittest.main()
