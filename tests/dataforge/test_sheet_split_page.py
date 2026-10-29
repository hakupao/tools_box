from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from openpyxl import Workbook

from tests.dataforge.qt_helpers import drain_deleted, qapp, wait_until


def _make_book(path: Path) -> None:
    wb = Workbook()
    wb.active.title = "One"
    wb.active["A1"] = "x"
    wb.create_sheet("Two")["A1"] = "y"
    wb.save(path)


class SheetSplitPageTests(unittest.TestCase):
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
        from dataforge.ui.pages.sheet_split_page import SheetSplitPage
        from dataforge.ui.registry import get_tool

        page = SheetSplitPage(get_tool("sheet_split"), self.runner)
        self._pages.append(page)
        return page

    def test_build_job_validation(self) -> None:
        page = self._page()
        with mock.patch("dataforge.ui.pages.sheet_split_page.InfoBar") as bar:
            self.assertIsNone(page.build_job())
        bar.warning.assert_called_once()

    def test_state_roundtrip(self) -> None:
        a, b, z = self.dir / "a.xlsx", self.dir / "b.xlsx", self.dir / "z.xlsx"
        _make_book(a)
        _make_book(b)
        page = self._page()
        missing = page.restore_state({"files": [str(a), str(z)], "output_dir": str(self.dir)})
        self.assertEqual(missing, [str(z)])
        self.assertEqual(page.capture_state(), {"files": [str(a)], "output_dir": str(self.dir)})
        self.assertEqual(page.summary(), "a.xlsx")
        page.file_input.set_files([a, b])
        self.assertEqual(page.summary(), "a.xlsx 等 2 个文件")
        self.assertEqual(page.run_bar.primary_button().text(), "开始拆分")

    def test_run_end_to_end(self) -> None:
        a = self.dir / "a.xlsx"
        _make_book(a)
        page = self._page()
        page.file_input.set_files([a])
        with mock.patch("dataforge.ui.components.tool_page.InfoBar") as bar:
            page.run_bar.start_requested.emit()
            wait_until(lambda: bar.method_calls != [])
            wait_until(lambda: not self.runner.is_busy())
        self.assertTrue((self.dir / "a_One.csv").is_file())
        self.assertTrue((self.dir / "a_Two.csv").is_file())
        self.assertIn("a_One.csv", page.result_panel.page_text("result"))


if __name__ == "__main__":
    unittest.main()
