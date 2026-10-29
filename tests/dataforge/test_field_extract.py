from __future__ import annotations

import csv
import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from openpyxl import Workbook

from dataforge.core.errors import Cancelled, DataForgeError
from dataforge.core.progress import CancelToken, no_progress
from dataforge.tools.field_extract import SUMMARY_NAME, FieldOptions, run

BOM = b"\xef\xbb\xbf"
AMBIGUOUS = "テスト医師\n".encode("cp932")


class FieldExtractTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)

    def _run(self, **kw):
        return run(self.dir, FieldOptions(**kw), no_progress, CancelToken())

    def _rows(self, name: str = SUMMARY_NAME) -> list[list[str]]:
        data = (self.dir / name).read_bytes()
        self.assertTrue(data.startswith(BOM))
        return list(csv.reader(io.StringIO(data[3:].decode("utf-8"), newline="")))

    def test_csv_and_excel_fields(self):
        (self.dir / "a.csv").write_bytes(b"id,name,id,\n1,2,3,4\n")
        wb = Workbook()
        wb.active.title = "S1"
        wb.active["A1"], wb.active["B1"], wb.active["D1"] = "x", "y", None
        wb.active["C1"] = ""
        wb.save(self.dir / "b.xlsx")
        r = self._run()
        self.assertEqual(r.errors, [])
        self.assertEqual(
            self._rows(),
            [
                ["文件名", "字段名"],
                ["a.csv", "id"],
                ["a.csv", "name"],
                ["a.csv", "id"],
                ["a.csv", ""],
                ["b.xlsx", "S1: x"],
                ["b.xlsx", "S1: y"],
            ],
        )
        self.assertEqual(r.stats, {"files": 2, "fields": 6})
        self.assertEqual(r.outputs, [self.dir / SUMMARY_NAME])

    def test_header_row_2(self):
        (self.dir / "a.csv").write_bytes(b"junk\nid,name\n1,2\n")
        (self.dir / "b.csv").write_bytes(b"only\n")
        self._run(header_row=2)
        self.assertEqual(
            self._rows(),
            [["文件名", "字段名"], ["a.csv", "id"], ["a.csv", "name"], ["b.csv", ""]],
        )

    def test_previous_summary_excluded(self):
        (self.dir / "a.csv").write_bytes(b"id\n")
        (self.dir / "file_fields_summary.csv").write_bytes(b"x\n")
        (self.dir / "File_Fields_Summary_1.csv").write_bytes(b"x\n")
        r = self._run()
        self.assertEqual(r.outputs, [self.dir / "file_fields_summary_2.csv"])
        self.assertEqual(self._rows("file_fields_summary_2.csv")[1:], [["a.csv", "id"]])

    def test_subfolders_relative_names(self):
        (self.dir / "sub").mkdir()
        (self.dir / "sub" / "c.csv").write_bytes(b"k\n")
        (self.dir / "a.csv").write_bytes(b"j\n")
        self._run()
        self.assertEqual(self._rows()[1:], [["a.csv", "j"]])
        (self.dir / SUMMARY_NAME).unlink()
        self._run(include_subfolders=True)
        self.assertEqual(self._rows()[1:], [["a.csv", "j"], ["sub/c.csv", "k"]])

    def test_empty_csv_writes_blank_row(self):
        (self.dir / "e.csv").write_bytes(b"")
        r = self._run()
        self.assertEqual(self._rows()[1:], [["e.csv", ""]])
        self.assertEqual(r.stats, {"files": 1, "fields": 0})

    def test_lock_files_skipped(self):
        (self.dir / "a.csv").write_bytes(b"id\n")
        (self.dir / "~$b.xlsx").write_bytes(b"lock")
        self._run()
        self.assertEqual(self._rows()[1:], [["a.csv", "id"]])

    def test_ambiguous_csv_question(self):
        (self.dir / "a.csv").write_bytes(b"id\n")
        (self.dir / "amb.csv").write_bytes(AMBIGUOUS)
        r = self._run()
        self.assertEqual(len(r.encoding_questions), 1)
        self.assertEqual(self._rows()[1:], [["a.csv", "id"]])
        self.assertEqual(r.stats.get("files"), 1)
        # per-file encoding retry
        r2 = run(
            self.dir,
            FieldOptions(encodings={str(self.dir / "amb.csv"): "cp932"}),
            no_progress,
            CancelToken(),
        )
        self.assertEqual(r2.encoding_questions, [])
        self.assertEqual(self._rows("file_fields_summary_1.csv")[2:], [["amb.csv", "テスト医師"]])

    def test_undecodable_csv_error_row(self):
        (self.dir / "bad.csv").write_bytes(b"A,\x81\n")
        r = self._run()
        self.assertEqual(len(r.errors), 1)
        self.assertEqual(self._rows()[1:], [["bad.csv", ""]])
        self.assertEqual(r.stats.get("files", 0), 0)

    def test_broken_excel_error_row(self):
        (self.dir / "bad.xlsx").write_bytes(b"not a zip")
        r = self._run()
        self.assertEqual(len(r.errors), 1)
        self.assertIn("读取失败", r.errors[0].message)
        self.assertEqual(self._rows()[1:], [["bad.xlsx", ""]])

    def test_excel_permission_error(self):
        wb = Workbook()
        wb.save(self.dir / "b.xlsx")
        with mock.patch(
            "dataforge.tools.field_extract.load_workbook", side_effect=PermissionError
        ):
            r = self._run()
        self.assertIn("可能已在 Excel 中打开", r.errors[0].message)

    def test_excel_sheet_with_fewer_rows(self):
        wb = Workbook()
        wb.active.title = "S1"
        wb.active["A1"] = "h"
        wb.save(self.dir / "b.xlsx")
        self._run(header_row=3)
        self.assertEqual(self._rows()[1:], [["b.xlsx", ""]])

    def test_cancel(self):
        (self.dir / "a.csv").write_bytes(b"id\n")
        token = CancelToken()
        token.cancel()
        with self.assertRaises(Cancelled):
            run(self.dir, FieldOptions(), no_progress, token)

    def test_output_dir(self):
        (self.dir / "a.csv").write_bytes(b"id\n")
        out = self.dir / "out"
        r = self._run(output_dir=out)
        self.assertEqual(r.outputs, [out / SUMMARY_NAME])

    def test_invalid_inputs(self):
        with self.assertRaises(DataForgeError):
            run(self.dir / "nope", FieldOptions(), no_progress, CancelToken())
        (self.dir / "a.csv").write_bytes(b"id\n")
        with self.assertRaises(DataForgeError):
            self._run(header_row=0)
        (self.dir / "a.csv").unlink()
        with self.assertRaises(DataForgeError):
            self._run()


if __name__ == "__main__":
    unittest.main()
