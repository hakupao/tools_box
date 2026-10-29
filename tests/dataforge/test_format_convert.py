from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from openpyxl import Workbook, load_workbook

from dataforge.core.errors import Cancelled, DataForgeError
from dataforge.core.progress import CancelToken, no_progress
from dataforge.tools.format_convert import ConvertMode, FormatOptions, run

BOM = b"\xef\xbb\xbf"
AMBIGUOUS = "テスト医師\n".encode("cp932")
UNDECODABLE = b"A,\x81\n"


class FormatConvertTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)

    def _csv(self, name: str, data: bytes) -> Path:
        p = self.dir / name
        p.write_bytes(data)
        return p

    def _run(self, files, mode, **kw):
        return run(files, FormatOptions(mode=mode, **kw), no_progress, CancelToken())

    def test_csv_to_xlsx_ragged_and_multiline(self):
        f = self._csv("a.csv", b'a,b\r\n1,"x\ny",extra\r\n2\r\n')
        r = self._run([f], ConvertMode.CSV_TO_XLSX)
        self.assertEqual(r.errors, [])
        ws = load_workbook(self.dir / "a.xlsx")["Sheet1"]
        self.assertEqual(ws["A1"].value, "a")
        self.assertEqual(ws["B1"].value, "b")
        self.assertEqual(ws["A2"].value, "1")
        self.assertEqual(ws["B2"].value, "x\ny")
        self.assertEqual(ws["C2"].value, "extra")
        self.assertEqual(ws["A3"].value, "2")
        for coord in ("A1", "B1", "A2", "B2", "C2", "A3"):
            self.assertEqual(ws[coord].number_format, "@")
        self.assertIsNone(ws["B3"].value)

    def test_csv_to_xlsx_keeps_leading_zero(self):
        f = self._csv("a.csv", b"id\n007\n")
        self._run([f], ConvertMode.CSV_TO_XLSX)
        self.assertEqual(load_workbook(self.dir / "a.xlsx").active["A2"].value, "007")

    def test_xlsx_to_csv_first_and_all(self):
        wb = Workbook()
        wb.active.title = "S1"
        wb.active["A1"] = "x"
        wb.create_sheet("S2")["A1"] = "y"
        src = self.dir / "book.xlsx"
        wb.save(src)
        out1 = self.dir / "o1"
        self._run([src], ConvertMode.XLSX_TO_CSV, output_dir=out1)
        self.assertEqual([p.name for p in out1.iterdir()], ["book.csv"])
        out2 = self.dir / "o2"
        self._run([src], ConvertMode.XLSX_TO_CSV, output_dir=out2, all_sheets=True)
        self.assertEqual(sorted(p.name for p in out2.iterdir()), ["book_S1.csv", "book_S2.csv"])

    def test_bom_converts_gbk_and_skips_bom(self):
        text = "姓名,年龄\n张伟,3\n"
        f = self._csv("g.csv", text.encode("gbk"))
        r = self._run([f], ConvertMode.CSV_TO_BOM)
        self.assertEqual((self.dir / "g_bom.csv").read_bytes(), BOM + text.encode("utf-8"))
        self.assertTrue(any("自动识别为 中文 (GBK)" in w.message for w in r.warnings))
        b = self._csv("b.csv", BOM + b"a,b\n")
        r = self._run([b], ConvertMode.CSV_TO_BOM)
        self.assertFalse((self.dir / "b_bom.csv").exists())
        self.assertEqual(r.outputs, [])
        self.assertEqual([w.message for w in r.warnings], ["已是 UTF-8 BOM，未生成文件"])

    def test_bom_keeps_line_endings(self):
        f = self._csv("l.csv", b"a\r\nb\n")
        self._run([f], ConvertMode.CSV_TO_BOM)
        self.assertEqual((self.dir / "l_bom.csv").read_bytes(), BOM + b"a\r\nb\n")

    def test_bom_overwrite_source(self):
        f = self._csv("o.csv", b"a,b\n")
        r = self._run([f], ConvertMode.CSV_TO_BOM, overwrite_source=True)
        self.assertEqual(f.read_bytes(), BOM + b"a,b\n")
        self.assertEqual(r.outputs, [f])

    def test_unquote_lossless(self):
        f = self._csv("u.csv", b'"a","  b ","c""d"\r\n"x,y","1"\r\n')
        r = self._run([f], ConvertMode.CSV_UNQUOTE)
        self.assertEqual(
            (self.dir / "u_unquoted.csv").read_bytes(),
            b'\xef\xbb\xbfa,  b ,c"d\r\n"x,y",1\r\n',
        )
        self.assertEqual(
            [w.message for w in r.warnings],
            ["1 个字段含分隔符、换行或以引号开头，已保留引号"],
        )

    def test_unquote_tab_delimiter(self):
        f = self._csv("t.csv", b'"a"\t"b"\n')
        self._run([f], ConvertMode.CSV_UNQUOTE)
        self.assertEqual((self.dir / "t_unquoted.csv").read_bytes(), BOM + b"a\tb\r\n")

    def test_unquote_overwrite_source(self):
        f = self._csv("w.csv", b'"a","b"\n')
        self._run([f], ConvertMode.CSV_UNQUOTE, overwrite_source=True)
        self.assertEqual(f.read_bytes(), BOM + b"a,b\r\n")

    def test_ambiguous_becomes_question(self):
        f = self._csv("m.csv", AMBIGUOUS)
        r = self._run([f], ConvertMode.CSV_TO_BOM)
        self.assertEqual(r.outputs, [])
        self.assertEqual(r.errors, [])
        self.assertEqual(len(r.encoding_questions), 1)

    def test_override_resolves_question(self):
        f = self._csv("m.csv", AMBIGUOUS)
        r = self._run([f], ConvertMode.CSV_TO_BOM, encodings={str(f): "cp932"})
        self.assertEqual(len(r.outputs), 1)
        self.assertEqual(r.encoding_questions, [])

    def test_undecodable_is_error(self):
        f = self._csv("x.csv", UNDECODABLE)
        r = self._run([f], ConvertMode.CSV_TO_BOM)
        self.assertEqual(len(r.errors), 1)
        self.assertIn("无法识别文件编码", r.errors[0].message)

    def test_empty_csv(self):
        f = self._csv("e.csv", b"")
        self._run([f], ConvertMode.CSV_TO_XLSX)
        self.assertEqual(load_workbook(self.dir / "e.xlsx").sheetnames, ["Sheet1"])
        self._run([f], ConvertMode.CSV_TO_BOM)
        self.assertEqual((self.dir / "e_bom.csv").read_bytes(), BOM)

    def test_japanese_filename(self):
        f = self._csv("データ.csv", b"a\n")
        self._run([f], ConvertMode.CSV_TO_XLSX)
        self.assertTrue((self.dir / "データ.xlsx").exists())

    def test_cancel_mid_batch_leaves_no_partial(self):
        files = [self._csv(f"f{i}.csv", b"a\n") for i in (1, 2, 3)]
        token = CancelToken()

        def progress(current, total, label):
            if current == 2:
                token.cancel()

        with self.assertRaises(Cancelled):
            run(files, FormatOptions(mode=ConvertMode.CSV_TO_XLSX), progress, token)
        self.assertTrue((self.dir / "f1.xlsx").exists())
        self.assertFalse((self.dir / "f2.xlsx").exists())
        self.assertFalse((self.dir / "f3.xlsx").exists())
        self.assertEqual([p for p in self.dir.iterdir() if ".tmp" in p.name], [])

    def test_overwrite_ignored_for_xlsx_modes(self):
        f = self._csv("a.csv", b"a\n")
        self._run([f], ConvertMode.CSV_TO_XLSX, overwrite_source=True)
        self.assertTrue((self.dir / "a.xlsx").exists())
        self.assertEqual(f.read_bytes(), b"a\n")

    def test_wrong_extension_fails(self):
        f = self._csv("a.txt", b"a\n")
        r = self._run([f], ConvertMode.CSV_TO_BOM)
        self.assertEqual([e.message for e in r.errors], ["文件类型与所选模式不符"])

    def test_no_files(self):
        with self.assertRaises(DataForgeError):
            self._run([], ConvertMode.CSV_TO_BOM)

    def test_forced_utf8_sig_on_plain_file_converts(self):
        f = self._csv("p.csv", b"a,b\n")
        r = self._run([f], ConvertMode.CSV_TO_BOM, encoding="utf-8-sig")
        self.assertEqual(r.warnings, [])
        self.assertEqual((self.dir / "p_bom.csv").read_bytes(), BOM + b"a,b\n")
        self.assertEqual(r.stats, {"files": 1})

    def test_bom_file_is_skipped_with_warning(self):
        f = self._csv("b.csv", BOM + b"a\n")
        r = self._run([f], ConvertMode.CSV_TO_BOM)
        self.assertEqual(r.outputs, [])
        self.assertEqual([w.message for w in r.warnings], ["已是 UTF-8 BOM，未生成文件"])
        self.assertEqual(r.stats, {"skipped": 1})

    def test_forced_gbk_on_bom_file_warns_and_skips(self):
        f = self._csv("b.csv", BOM + "姓名\n".encode("utf-8"))
        r = self._run([f], ConvertMode.CSV_TO_XLSX, encoding="gbk")
        self.assertIn("文件带 UTF-8 BOM，已忽略手动指定的编码", [w.message for w in r.warnings])
        self.assertEqual(load_workbook(self.dir / "b.xlsx").active["A1"].value, "姓名")

    def test_questioned_files_are_not_counted_as_skipped(self):
        ok = self._csv("ok.csv", b"a\n")
        amb = self._csv("m.csv", AMBIGUOUS)
        first = self._run([ok, amb], ConvertMode.CSV_TO_BOM)
        self.assertEqual(first.stats, {"files": 1})
        retry = self._run([amb], ConvertMode.CSV_TO_BOM, encodings={str(amb): "cp932"})
        first.extend(retry)
        self.assertEqual(first.stats, {"files": 2})

    def test_read_permission_error_message(self):
        f = self._csv("p.csv", b"a\n")
        with mock.patch(
            "dataforge.tools.format_convert.read_text", side_effect=PermissionError("x")
        ):
            r = self._run([f], ConvertMode.CSV_TO_BOM)
        self.assertEqual(
            [e.message for e in r.errors], ["无法读取文件（可能已被其他程序打开）"]
        )

    def test_write_permission_error_message(self):
        f = self._csv("p.csv", b"a\n")
        with mock.patch(
            "dataforge.tools.format_convert.write_text", side_effect=PermissionError("x")
        ):
            r = self._run([f], ConvertMode.CSV_TO_BOM)
        self.assertEqual(
            [e.message for e in r.errors], ["无法写入输出文件（可能已被其他程序打开）"]
        )


    def test_csv_to_xlsx_formula_text_stays_string(self):
        f = self._csv("f.csv", b"=SUM(A1),+1\n")
        self._run([f], ConvertMode.CSV_TO_XLSX)
        ws = load_workbook(self.dir / "f.xlsx").active
        self.assertEqual(ws["A1"].value, "=SUM(A1)")
        self.assertEqual(ws["A1"].data_type, "s")
        self.assertEqual(ws["B1"].value, "+1")
        self.assertEqual(ws["B1"].data_type, "s")

    def test_csv_to_xlsx_control_char_is_error(self):
        f = self._csv("c.csv", b"a\nb\x01c\n")
        r = self._run([f], ConvertMode.CSV_TO_XLSX)
        self.assertEqual([e.message for e in r.errors], ["第 2 行含 Excel 不支持的控制字符"])
        self.assertEqual(list(self.dir.glob("*.xlsx")), [])
        self.assertEqual([p for p in self.dir.iterdir() if ".tmp" in p.name], [])

    def test_unquote_quotes_fields_with_any_candidate_delimiter(self):
        f = self._csv("d.csv", b'a;b,c;d,e\r\n"x,y";z;w;v\r\n')
        r = self._run([f], ConvertMode.CSV_UNQUOTE)
        self.assertEqual(
            (self.dir / "d_unquoted.csv").read_bytes(),
            BOM + b'a;"b,c";"d,e"\r\n"x,y";z;w;v\r\n',
        )
        messages = [w.message for w in r.warnings]
        self.assertIn("按「分号」分隔识别", messages)
        self.assertIn("3 个字段含分隔符、换行或以引号开头，已保留引号", messages)

    def test_unquote_tab_warns_delimiter(self):
        f = self._csv("t.csv", b'"a"\t"b"\n')
        r = self._run([f], ConvertMode.CSV_UNQUOTE)
        self.assertEqual([w.message for w in r.warnings], ["按「制表符」分隔识别"])

    def test_stats_files_and_skipped(self):
        ok = self._csv("ok.csv", b"a\n")
        bom = self._csv("bom.csv", BOM + b"a\n")
        amb = self._csv("amb.csv", AMBIGUOUS)
        bad = self._csv("bad.csv", UNDECODABLE)
        r = self._run([ok, bom, amb, bad], ConvertMode.CSV_TO_BOM)
        self.assertEqual(r.stats.get("files"), 1)
        self.assertEqual(r.stats.get("skipped"), 1)  # the ambiguous file is asked, not skipped


if __name__ == "__main__":
    unittest.main()
