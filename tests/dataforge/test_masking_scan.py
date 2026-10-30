import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from dataforge.core.errors import Cancelled, DataForgeError
from dataforge.core.progress import CancelToken, no_progress
from dataforge.dates import SlashOrder
from dataforge.tools.masking import table as table_mod
from dataforge.tools.masking.profile import MaskingProfile
from dataforge.tools.masking.scan import (
    ScanSettings,
    export_report,
    scan,
    scan_signature,
)
from dataforge.tools.masking.table import find_column, is_blank, read_table

SETTINGS = ScanSettings()


class ScanBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)

    def _write(self, name, text, encoding="utf-8-sig", sub=None):
        folder = self.dir / sub if sub else self.dir
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / name
        path.write_bytes(text.encode(encoding))
        return path

    def _scan(self, paths, settings=SETTINGS, encoding=None, encodings=None, cancel=None):
        return scan(
            paths, settings, encoding, encodings or {}, no_progress, cancel or CancelToken()
        )


class SelectFilesTests(ScanBase):
    def test_select_files_filters_and_dedups(self):
        from dataforge.tools.masking.scan import select_files

        a = self._write("a.CSV", "USUBJID\nS1\n")
        b = self._write("b.txt", "x")
        missing = self.dir / "不存在.csv"
        folder = self.dir / "文件夹.csv"
        folder.mkdir()
        self.assertEqual(select_files([a, a, b, missing, folder]), [a])


class TableTests(ScanBase):
    def test_helpers(self):
        self.assertTrue(is_blank("  "))
        self.assertTrue(is_blank("NaN"))
        self.assertFalse(is_blank("0"))
        self.assertEqual(find_column(["a", "UsubjId"], "USUBJID"), 1)
        self.assertIsNone(find_column(["a", " USUBJID"], "USUBJID"))

    def test_ragged_rows(self):
        p = self._write("a.csv", "A,B,C\n1\n\n2,3,4\n")
        t = read_table(p, None)
        self.assertEqual(t.rows, [["1", "", ""], ["2", "3", "4"]])
        self.assertEqual(t.header, ["A", "B", "C"])
        p2 = self._write("b.csv", "A,B\n1,2,3\n")
        with self.assertRaises(DataForgeError) as cm:
            read_table(p2, None)
        self.assertIn("字段数多于表头", str(cm.exception))
        with self.assertRaises(DataForgeError):
            read_table(self._write("c.csv", ""), None)


class ScanTests(ScanBase):
    def test_basic_report(self):
        dm = self._write(
            "DM.csv", "USUBJID,DMDTC,ARM\nS2,2024-01-01,\nS1,2024-02-01,\nS3,2024-03-01,\n"
        )
        ae = self._write("AE.csv", "USUBJID,AETERM\nS1,x\n")
        res = self._scan([dm, ae], ScanSettings(min_non_empty=1))
        report = res.data
        self.assertTrue(report.processable)
        self.assertEqual(report.subjects, ["S1", "S2", "S3"])
        self.assertEqual(report.dm_first_usubjid, "S2")
        self.assertEqual(report.dm_file, "DM.csv")
        fs = report.files[0]
        self.assertEqual(fs.empty_fields, ["ARM"])
        self.assertIn("DMDTC", fs.date_fields)
        self.assertEqual(fs.unique_usubjid_count, 3)
        self.assertEqual(fs.row_count, 3)
        self.assertEqual(res.stats["files"], 2)
        self.assertEqual(res.stats["subjects"], 3)

    def test_missing_usubjid_blocks(self):
        dm = self._write("DM.csv", "USUBJID\nS1\n")
        ae = self._write("AE.csv", "SUBJ\nS1\n")
        res = self._scan([dm, ae])
        self.assertFalse(res.data.processable)
        self.assertIn("文件缺少 USUBJID 列：AE.csv", [e.message for e in res.errors])
        self.assertEqual(res.errors[0].path, "AE.csv")

    def test_two_dm_files_error(self):
        a = self._write("dm.csv", "USUBJID\nS1\n", sub="a")
        b = self._write("dm.csv", "USUBJID\nS2\n", sub="b")
        res = self._scan([a, b])
        msgs = [e.message for e in res.errors]
        self.assertIn("DM.csv 必须且只能有 1 个", msgs)
        self.assertTrue(any(m.startswith("文件名重复：") for m in msgs))
        self.assertFalse(res.data.processable)

    def test_duplicate_domain_names_error(self):
        dm = self._write("DM.csv", "USUBJID\nS1\n")
        a = self._write("AE.csv", "USUBJID\nS1\n", sub="a")
        b = self._write("ae.csv", "USUBJID\nS1\n", sub="b")
        res = self._scan([dm, a, b])
        self.assertEqual(
            [e.message for e in res.errors if e.message.startswith("文件名重复")],
            ["文件名重复：AE.csv（输出时会互相覆盖）"],
        )

    def test_input_named_like_mapping_output_error(self):
        dm = self._write("DM.csv", "USUBJID\nS1\n")
        clash = self._write("USUBJID_Mapping.csv", "USUBJID\nS1\n")
        res = self._scan([dm, clash])
        self.assertEqual(
            [(e.path, e.message) for e in res.errors],
            [("USUBJID_Mapping.csv", "USUBJID_Mapping.csv：文件名与输出文件 usubjid_mapping.csv 冲突")],
        )
        self.assertFalse(res.data.processable)
        self.assertEqual(res.data.errors, [res.errors[0].message])

    def test_no_csv(self):
        res = self._scan([self.dir / "x.txt"])
        self.assertEqual(res.errors[0].message, "未选择任何 CSV 文件")
        self.assertEqual(res.errors[0].path, "")
        self.assertFalse(res.data.processable)

    def test_no_dm_and_empty_dm_subjects(self):
        ae = self._write("AE.csv", "USUBJID\nS1\n")
        res = self._scan([ae])
        self.assertIn("DM.csv 必须且只能有 1 个", [e.message for e in res.errors])
        dm = self._write("DM.csv", "USUBJID\n \nnan\n", sub="x")
        res = self._scan([dm])
        self.assertIn("DM.csv 中没有有效的 USUBJID", [e.message for e in res.errors])

    def test_permission_error_other_files_scanned(self):
        dm = self._write("DM.csv", "USUBJID\nS1\n")
        ae = self._write("AE.csv", "USUBJID\nS1\n")
        real = table_mod.read_text

        def fake(path, encoding):
            if path.name == "AE.csv":
                raise PermissionError("locked")
            return real(path, encoding)

        with mock.patch.object(table_mod, "read_text", fake):
            res = self._scan([dm, ae])
        self.assertTrue(
            any("无法读取文件（可能已在 Excel 中打开）" in e.message for e in res.errors)
        )
        self.assertEqual([f.file_name for f in res.data.files], ["DM.csv"])

    def test_ambiguous_encoding_asks(self):
        dm = self._write("DM.csv", "USUBJID\nS1\n")
        ae = self._write("AE.csv", "USUBJID,AETERM\nS1,テスト医師\n", encoding="cp932")
        res = self._scan([dm, ae])
        self.assertEqual([q.path for q in res.encoding_questions], [str(ae)])
        self.assertFalse(res.data.processable)
        self.assertIn("未确定编码：AE.csv", [e.message for e in res.errors])
        res = self._scan([dm, ae], encodings={str(ae): "cp932"})
        self.assertEqual(res.encoding_questions, [])
        self.assertTrue(res.data.processable)
        by_name = {f.file_name: f for f in res.data.files}
        self.assertEqual(by_name["AE.csv"].encoding, "cp932")

    def test_all_ambiguous_column_is_date_column(self):
        rows = "".join("S1,01/02/2024\n" for _ in range(20))
        dm = self._write("DM.csv", "USUBJID,D\n" + rows)
        res = self._scan([dm])
        report = res.data
        self.assertIn("D", report.files[0].date_fields)
        self.assertEqual(len(report.ambiguous_columns), 1)
        self.assertEqual(report.ambiguous_columns[0].ambiguous, 20)
        self.assertIn(
            "D 列有 20 个日期无法判断是 日/月 还是 月/日，请选择顺序",
            [w.message for w in res.warnings],
        )
        d = report.to_dict({("DM.csv", "D"): SlashOrder.DAY_FIRST})
        self.assertEqual(d["ambiguous_date_columns"][0]["order"], "dmy")
        self.assertIsNone(report.to_dict()["ambiguous_date_columns"][0]["order"])

    def test_mixed_only_kinds_warn(self):
        dm = self._write("DM.csv", "USUBJID,D\nS1,13/01/2024\nS1,01/13/2024\n")
        res = self._scan([dm], ScanSettings(min_non_empty=1))
        self.assertIn(
            "D 列同时有只能按 日/月 和只能按 月/日 解读的日期，请检查数据",
            [w.message for w in res.warnings],
        )

    def test_detection_thresholds(self):
        vals_a = ["2024-01-01"] * 4 + ["abc"]
        vals_b = ["2024-01-01"] * 20 + ["abc"] * 5
        text = "USUBJID,A,B\n" + "".join(
            f"S1,{vals_a[i] if i < 5 else ''},{vals_b[i]}\n" for i in range(25)
        )
        dm = self._write("DM.csv", text)
        fs = self._scan([dm]).data.files[0]
        self.assertNotIn("A", fs.date_fields)
        self.assertIn("B", fs.date_fields)

    def test_signature_changes_on_mtime(self):
        dm = self._write("DM.csv", "USUBJID\nS1\n")
        s1 = scan_signature([dm], SETTINGS, None, {})
        os.utime(dm, ns=(1_000_000_000, 1_000_000_000))
        s2 = scan_signature([dm], SETTINGS, None, {})
        self.assertNotEqual(s1, s2)
        self.assertNotEqual(s2, scan_signature([dm], ScanSettings(ratio=0.5), None, {}))
        self.assertNotEqual(s2, scan_signature([dm], SETTINGS, "cp932", {}))
        self.assertNotEqual(s2, scan_signature([dm], SETTINGS, None, {str(dm): "gbk"}))
        self.assertEqual(s2, scan_signature([dm], SETTINGS, None, {}))
        scan_signature([self.dir / "gone.csv"], SETTINGS, None, {})

    def test_report_json_has_no_absolute_paths(self):
        dm = self._write("DM.csv", "USUBJID\nS1\n")
        res = self._scan([dm])
        d = res.data.to_dict()
        text = json.dumps(d, ensure_ascii=False)
        self.assertNotIn(str(self.dir), text)
        self.assertNotIn(self.dir.as_posix(), text)
        self.assertEqual(
            list(d),
            [
                "dm_file", "dm_first_usubjid", "subject_count", "subjects", "date_detect",
                "files", "ambiguous_date_columns", "errors", "warnings",
            ],
        )

    def test_cancel(self):
        dm = self._write("DM.csv", "USUBJID\nS1\n")
        token = CancelToken()
        token.cancel()
        with self.assertRaises(Cancelled):
            self._scan([dm], cancel=token)

    def test_settings_from_profile(self):
        p = MaskingProfile(
            date_detect_sample_size=5, date_detect_min_non_empty=2, date_detect_success_ratio=0.5
        )
        self.assertEqual(ScanSettings.from_profile(p), ScanSettings(5, 2, 0.5))

    def test_export_report(self):
        dm = self._write("DM.csv", "USUBJID,D,E\nS1,2024-01-01,\n")
        res = self._scan([dm], ScanSettings(min_non_empty=1))
        csv_path = export_report(res.data, self.dir / "r.csv")
        text = csv_path.read_bytes().decode("utf-8-sig")
        self.assertEqual(
            text.splitlines()[0],
            "file_name,row_count,unique_usubjid_count,non_empty_fields,empty_fields,date_fields",
        )
        self.assertIn("DM.csv,1,1,USUBJID|D,E,D", text)
        js = export_report(res.data, self.dir / "r.json")
        self.assertEqual(json.loads(js.read_text(encoding="utf-8"))["dm_file"], "DM.csv")


class ScanFixRoundTests(ScanBase):
    def test_missing_csv_dropped_silently(self):
        dm = self._write("DM.csv", "USUBJID\nS1\n")
        ae = self._write("AE.csv", "USUBJID\nS1\n")
        res = self._scan([dm, self.dir / "gone.csv", ae])
        self.assertTrue(res.ok)
        self.assertTrue(res.data.processable)
        self.assertEqual([f.file_name for f in res.data.files], ["DM.csv", "AE.csv"])

    def test_all_missing_is_no_csv_error(self):
        res = self._scan([self.dir / "gone.csv"])
        self.assertEqual(res.errors[0].message, "未选择任何 CSV 文件")

    def test_csv_error_becomes_file_error(self):
        dm = self._write("DM.csv", "USUBJID\nS1\n")
        ae = self._write("AE.csv", "USUBJID,X\nS1," + "a" * 50 + "\n")
        import csv

        old = csv.field_size_limit(10)
        self.addCleanup(csv.field_size_limit, old)
        res = self._scan([dm, ae])
        msgs = [e.message for e in res.errors]
        self.assertTrue(any(m.startswith("AE.csv：") for m in msgs), msgs)

    def test_encoding_note_becomes_warning(self):
        dm = self._write("DM.csv", "USUBJID\nS1\n")
        ae = self._write("AE.csv", "USUBJID,ｼﾒｲ\nA001,ﾔﾏﾀﾞ\n", encoding="cp932")
        res = self._scan([dm, ae])
        self.assertTrue(any("自动识别为" in w.message for w in res.warnings))
        self.assertEqual(res.data.warnings, [w.message for w in res.warnings])

    def test_duplicate_path_scanned_once(self):
        dm = self._write("DM.csv", "USUBJID\nS1\n")
        res = self._scan([dm, dm])
        self.assertTrue(res.ok)
        self.assertEqual(len(res.data.files), 1)
