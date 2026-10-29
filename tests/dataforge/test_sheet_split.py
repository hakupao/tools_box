from __future__ import annotations

import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest import mock

from openpyxl import Workbook

from dataforge.core.errors import DataForgeError
from dataforge.core.progress import CancelToken, no_progress
from dataforge.core.result import Result
from dataforge.tools import sheet_split
from dataforge.tools.sheet_split import (
    SplitOptions,
    export_workbook,
    run,
    sanitize_sheet_name,
)


def _make_book(path: Path) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "数据"
    ws["A1"] = date(2020, 3, 4)
    ws["A1"].number_format = "yyyy/mm/dd"
    ws["B1"] = datetime(2020, 3, 4, 10, 5)
    ws["B1"].number_format = "yyyy-mm-dd hh:mm"
    ws["A2"] = 12
    ws["B2"] = 1.5
    ws["C4"] = None  # trailing blank column / rows
    ws["A4"] = None
    wb.create_sheet("a<b")["A1"] = "x"
    wb.save(path)


class SheetSplitTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)

    def _export(self, src: Path, *, all_sheets: bool = True) -> Result:
        result = Result()
        export_workbook(src, all_sheets=all_sheets, output_dir=None, result=result,
                        cancel=CancelToken())
        return result

    def test_sanitize(self) -> None:
        for raw, want in [("a/b:c", "a_b_c"), ("CON", "CON_"), ("x. ", "x"),
                          ("", "Sheet"), ("..", "Sheet")]:
            self.assertEqual(sanitize_sheet_name(raw), want, raw)

    def test_split_names_and_dates(self) -> None:
        src = self.dir / "book.xlsx"
        _make_book(src)
        result = self._export(src)
        self.assertEqual(result.errors, [])
        self.assertEqual(sorted(p.name for p in self.dir.glob("*.csv")),
                         ["book_a_b.csv", "book_数据.csv"])
        data = (self.dir / "book_数据.csv").read_bytes()
        self.assertEqual(data, b"\xef\xbb\xbf2020/03/04,2020-03-04 10:05\r\n12,1.5\r\n")
        self.assertEqual(result.stats["sheets"], 2)

    def test_duplicate_sanitized_names(self) -> None:
        src = self.dir / "book.xlsx"
        wb = Workbook()
        wb.active.title = "a<b"
        wb.create_sheet("a>b")
        wb.save(src)
        self._export(src)
        self.assertEqual(sorted(p.name for p in self.dir.glob("*.csv")),
                         ["book_a_b.csv", "book_a_b_1.csv"])

    def test_existing_output_gets_suffix(self) -> None:
        src = self.dir / "book.xlsx"
        _make_book(src)
        (self.dir / "book_数据.csv").write_bytes(b"old")
        result = self._export(src)
        self.assertTrue((self.dir / "book_数据_1.csv").is_file())
        self.assertEqual((self.dir / "book_数据.csv").read_bytes(), b"old")
        self.assertEqual(len(result.outputs), 2)

    def test_empty_sheet_writes_empty_csv(self) -> None:
        src = self.dir / "book.xlsx"
        Workbook().save(src)
        self._export(src)
        self.assertEqual((self.dir / "book_Sheet.csv").read_bytes(), b"\xef\xbb\xbf")

    def test_permission_error_continues(self) -> None:
        a, b = self.dir / "a.xlsx", self.dir / "b.xlsx"
        _make_book(a)
        _make_book(b)
        real = sheet_split.load_workbook
        calls = {"n": 0}

        def fake(*args, **kwargs):
            calls["n"] += 1
            if calls["n"] == 1:
                raise PermissionError("locked")
            return real(*args, **kwargs)

        with mock.patch.object(sheet_split, "load_workbook", fake):
            result = run([a, b], SplitOptions(), no_progress, CancelToken())
        self.assertEqual(len(result.errors), 1)
        self.assertEqual(result.errors[0].message, "无法读取文件（可能已在 Excel 中打开）")
        self.assertTrue((self.dir / "b_数据.csv").is_file())
        self.assertEqual(result.stats["files"], 1)

    def test_first_sheet_only(self) -> None:
        src = self.dir / "book.xlsx"
        _make_book(src)
        self._export(src, all_sheets=False)
        self.assertEqual([p.name for p in self.dir.glob("*.csv")], ["book.csv"])

    def test_run_empty_raises(self) -> None:
        with self.assertRaises(DataForgeError):
            run([], SplitOptions(), no_progress, CancelToken())

    def test_output_dir(self) -> None:
        src = self.dir / "book.xlsx"
        _make_book(src)
        out = self.dir / "out"
        run([src], SplitOptions(output_dir=out), no_progress, CancelToken())
        self.assertTrue((out / "book_数据.csv").is_file())


if __name__ == "__main__":
    unittest.main()
