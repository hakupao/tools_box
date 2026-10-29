import csv
import io
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

from dataforge.core.errors import Cancelled, DataForgeError
from dataforge.core.progress import CancelToken, no_progress
from dataforge.dates import SlashOrder
from dataforge.tools.masking.execute import (
    MaskOptions,
    build_mapping,
    describe_plan,
    missing_orders,
    run,
    shift_age,
    transform_subject_id,
)
from dataforge.tools.masking.profile import MaskingProfile, RuleStep
from dataforge.tools.masking.scan import ScanSettings, scan

NOW = datetime(2026, 1, 2, 3, 4, 5)
FOLDER = "masked_output_20260102_030405"

DM_TEXT = (
    "USUBJID,INVNAM,ICINVNAM,SITEID,AGE,STUDYID,DMDTC\n"
    "SUBJ0002,Doctor-A,Doctor-B,Site-01,45,OLD-STUDY,2024\n"
    "SUBJ0001,Doctor-C,Doctor-D,Site-02,30,OLD-STUDY,2024-05\n"
    "SUBJ0003,Doctor-E,Doctor-F,Site-03,66,OLD-STUDY,2024-06-30\n"
)
AE_TEXT = (
    "USUBJID,SUBJID,STUDYID,AESTDTC\n"
    "SUBJ0002,SUBJ0002,OLD-STUDY,2024-06-15T13:30:00\n"
    "SUBJ0001,SUBJ0001,OLD-STUDY,2024\n"
    "SUBJ0003,SUBJ0003,OLD-STUDY,2024-07\n"
)


def _rows(path: Path) -> list[dict[str, str]]:
    text = path.read_bytes().decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(text, newline="")))


class ExecuteBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)
        self.out_parent = self.dir / "out"
        self.out_parent.mkdir()

    def _write(self, name: str, text: str, encoding: str = "utf-8-sig") -> Path:
        path = self.dir / name
        path.write_bytes(text.encode(encoding))
        return path

    def _scan(self, paths, profile: MaskingProfile):
        result = scan(
            paths, ScanSettings.from_profile(profile), None, {}, no_progress, CancelToken()
        )
        return result.data

    def _run(self, report, profile, date_orders=None, progress=no_progress, cancel=None):
        options = MaskOptions(
            profile=profile,
            output_parent=self.out_parent,
            date_orders=date_orders or {},
            now=NOW,
        )
        return run(report, options, progress, cancel or CancelToken())

    def _default(self, profile: MaskingProfile):
        dm = self._write("DM.csv", DM_TEXT)
        ae = self._write("AE.csv", AE_TEXT)
        report = self._scan([dm, ae], profile)
        self.assertTrue(report.processable, report.errors)
        return report

    def _out(self, name: str) -> list[dict[str, str]]:
        return _rows(self.out_parent / FOLDER / name)


class EndToEndTests(ExecuteBase):
    def test_end_to_end_v2_rules(self):
        profile = MaskingProfile(subject_limit=2, date_detect_min_non_empty=1)
        report = self._default(profile)
        self.assertEqual(report.subjects, ["SUBJ0001", "SUBJ0002", "SUBJ0003"])
        self.assertEqual(report.dm_first_usubjid, "SUBJ0002")
        result = self._run(report, profile)
        dm, ae = self._out("DM.csv"), self._out("AE.csv")
        self.assertEqual({r["USUBJID"] for r in dm}, {"TEST0001", "TEST0002"})
        self.assertEqual({r["USUBJID"] for r in ae}, {"TEST0001", "TEST0002"})
        self.assertEqual({r["INVNAM"] for r in dm}, {"テスト医師"})
        self.assertEqual({r["ICINVNAM"] for r in dm}, {"Doctor-B", "Doctor-D"})
        dmdtc = [r["DMDTC"] for r in dm]
        self.assertIn("2022-01-01", dmdtc)
        self.assertIn("2022-05-01", dmdtc)
        aestdtc = [r["AESTDTC"] for r in ae]
        self.assertIn("2022-06-15T13:30:00", aestdtc)  # v2: 2022-06-15 (time kept now)
        self.assertIn("2022-01-01", aestdtc)
        self.assertEqual({r["SUBJID"] for r in ae}, {""})  # v2: mapped value (cleared now)
        self.assertEqual({r["STUDYID"] for r in ae + dm}, {"[UAT]CIRCULATE"})
        self.assertEqual({r["SITEID"] for r in dm}, {"テスト施設"})
        self.assertEqual(sorted(r["AGE"] for r in dm), ["28", "43"])
        self.assertEqual(
            result.stats,
            {
                "files": 2,
                "subjects": 2,
                "rows": 4,
                "dates_shifted": 4,
                "dates_filled": 3,
                "dates_unparsed": 0,
            },
        )
        self.assertFalse(result.warnings)
        self.assertFalse(result.errors)

    def test_extra_doctor_fields_only_in_dm(self):
        profile = MaskingProfile(
            subject_limit=2, doctor_fields=["INVNAM", "ICINVNAM"], date_detect_min_non_empty=1
        )
        dm = self._write("DM.csv", DM_TEXT)
        ae = self._write(
            "AE.csv",
            "USUBJID,SUBJID,STUDYID,AESTDTC,INVNAM\n"
            "SUBJ0002,SUBJ0002,OLD-STUDY,2024-06-15T13:30:00,AE-Doctor-1\n"
            "SUBJ0001,SUBJ0001,OLD-STUDY,2024,AE-Doctor-2\n"
            "SUBJ0003,SUBJ0003,OLD-STUDY,2024-07,AE-Doctor-3\n",
        )
        report = self._scan([dm, ae], profile)
        self._run(report, profile)
        self.assertEqual({r["ICINVNAM"] for r in self._out("DM.csv")}, {"テスト医師"})
        self.assertEqual({r["INVNAM"] for r in self._out("AE.csv")}, {"AE-Doctor-1", "AE-Doctor-2"})

    def _override_files(self):
        dm = self._write(
            "DM.csv",
            "USUBJID,INVNAM,SITEID,AGE,STUDYID,DMDTC\n"
            "S001,,,,OLD,2024\n"
            "S002,Doctor-2,Site-2,40,OLD,2024-05\n",
        )
        ae = self._write(
            "AE.csv",
            "USUBJID,SUBJID,STUDYID,AESTDTC\nS001,S001,OLD,2024-01-01\nS002,S002,OLD,2024-01-02\n",
        )
        return [dm, ae]

    def test_dm_overrides_replace_only_non_empty_cells(self):
        profile = MaskingProfile(subject_limit=2)
        report = self._scan(self._override_files(), profile)
        self._run(report, profile)
        rows = {r["USUBJID"]: r for r in self._out("DM.csv")}
        self.assertEqual(
            (rows["TEST0001"]["INVNAM"], rows["TEST0001"]["SITEID"], rows["TEST0001"]["AGE"]),
            ("", "", ""),
        )
        self.assertEqual(
            (rows["TEST0002"]["INVNAM"], rows["TEST0002"]["SITEID"], rows["TEST0002"]["AGE"]),
            ("テスト医師", "テスト施設", "38"),
        )

    def test_dm_overrides_skip_when_disabled(self):
        profile = MaskingProfile(
            subject_limit=2, doctor_replace_enabled=False, site_replace_enabled=False
        )
        report = self._scan(self._override_files(), profile)
        self._run(report, profile)
        rows = {r["USUBJID"]: r for r in self._out("DM.csv")}
        self.assertEqual(
            (rows["TEST0001"]["INVNAM"], rows["TEST0001"]["SITEID"], rows["TEST0001"]["AGE"]),
            ("", "", ""),
        )
        self.assertEqual(
            (rows["TEST0002"]["INVNAM"], rows["TEST0002"]["SITEID"], rows["TEST0002"]["AGE"]),
            ("Doctor-2", "Site-2", "38"),
        )

    def test_include_subjid_false_keeps_subjid(self):
        profile = MaskingProfile(subject_limit=2, include_subjid=False)
        report = self._default(profile)
        self._run(report, profile)
        self.assertEqual(sorted(r["SUBJID"] for r in self._out("AE.csv")), ["SUBJ0001", "SUBJ0002"])

    def test_whitespace_and_blank_usubjid(self):
        profile = MaskingProfile(subject_limit=1)
        dm = self._write("DM.csv", "USUBJID,AGE\nS1,40\nS2,50\n")
        ae = self._write("AE.csv", "USUBJID,AETERM\n S1 ,a\n,b\n  ,c\nnan,d\nS2,e\nS1,f\n")
        report = self._scan([dm, ae], profile)
        result = self._run(report, profile)
        ae_rows = self._out("AE.csv")
        self.assertEqual(
            [(r["USUBJID"], r["AETERM"]) for r in ae_rows], [("TEST0001", "a"), ("TEST0001", "f")]
        )
        self.assertEqual(result.stats["rows"], 3)

    def test_empty_invnam_column_not_replaced_and_not_described(self):
        profile = MaskingProfile(subject_limit=2)
        dm = self._write("DM.csv", "USUBJID,INVNAM,AGE\nS1,,40\nS2, ,50\n")
        ae = self._write("AE.csv", "USUBJID,INVNAM\nS1,AE-Doc\n")
        report = self._scan([dm, ae], profile)
        self._run(report, profile)
        self.assertEqual([r["INVNAM"] for r in self._out("DM.csv")], ["", " "])
        self.assertEqual([r["INVNAM"] for r in self._out("AE.csv")], ["AE-Doc"])
        lines = describe_plan(report, profile, {}, None)
        self.assertFalse([line for line in lines if "INVNAM" in line])


class DuplicateColumnTests(ExecuteBase):
    def test_duplicate_named_columns_all_processed(self):
        profile = MaskingProfile(subject_limit=2)
        dm = self._write(
            "DM.csv",
            "USUBJID,INVNAM,invnam,SITEID,siteid,AGE,age\n"
            "S1,,Doc-1,Site-1,,40,41\n"
            "S2,,,,Site-2,50,\n",
        )
        ae = self._write(
            "AE.csv",
            "USUBJID,SUBJID,subjid,STUDYID,StudyId\nS1,S1,X1,OLD,OLD2\nS2,S2,X2,OLD,\n",
        )
        report = self._scan([dm, ae], profile)
        self._run(report, profile)
        dm_rows = (self.out_parent / FOLDER / "DM.csv").read_bytes().decode("utf-8-sig")
        self.assertEqual(
            dm_rows,
            "USUBJID,INVNAM,invnam,SITEID,siteid,AGE,age\r\n"
            "TEST0001,,テスト医師,テスト施設,,38,39\r\n"
            "TEST0002,,,,テスト施設,48,\r\n",
        )
        ae_rows = (self.out_parent / FOLDER / "AE.csv").read_bytes().decode("utf-8-sig")
        self.assertEqual(
            ae_rows,
            "USUBJID,SUBJID,subjid,STUDYID,StudyId\r\n"
            "TEST0001,,,[UAT]CIRCULATE,[UAT]CIRCULATE\r\n"
            "TEST0002,,,[UAT]CIRCULATE,[UAT]CIRCULATE\r\n",
        )

    def test_duplicate_usubjid_column_aborts(self):
        profile = MaskingProfile(subject_limit=2)
        dm = self._write("DM.csv", "USUBJID\nS1\nS2\n")
        ae = self._write("AE.csv", "USUBJID,usubjid\nS1,S1\n")
        report = self._scan([dm, ae], profile)
        self.assertTrue(report.processable, report.errors)
        with self.assertRaises(DataForgeError) as cm:
            self._run(report, profile)
        self.assertEqual(str(cm.exception), "AE.csv：USUBJID 列重复")
        self.assertEqual(list(self.out_parent.iterdir()), [])


class PlanTests(ExecuteBase):
    def test_describe_plan_lines(self):
        profile = MaskingProfile()
        dm = self._write(
            "DM.csv",
            "USUBJID,INVNAM,SITEID,AGE,DMDTC\n"
            + "".join(f"S{i},Doc,Site,40,2024-01-0{i}\n" for i in (3, 1, 5, 2, 4)),
        )
        ae = self._write(
            "AE.csv", "USUBJID,AESTDTC\n" + "".join(f"S1,2024-02-{d:02d}\n" for d in range(1, 21))
        )
        profile.date_detect_min_non_empty = 5
        report = self._scan([dm, ae], profile)
        self.assertEqual(len(report.subjects), 5)
        lines = describe_plan(report, profile, {}, None)
        self.assertEqual(
            lines,
            [
                "受试者：保留 DM 排序后的前 5 个（共 5 个），其他受试者的行全部删除",
                "USUBJID：顺序编号 TEST0001 … TEST0005",
                "SUBJID 列将被清空",
                "STUDYID：全部改为 [UAT]CIRCULATE",
                "日期：2 个日期列偏移 -2 年，时间部分保留",
                "DM：INVNAM 改为 テスト医師",
                "DM：SITEID 改为 テスト施設",
                "DM：AGE 偏移 -2 岁",
                "输出：DM.csv 所在文件夹 下新建 masked_output_<时间> 文件夹",
            ],
        )

    def test_describe_plan_rule_chain_and_options(self):
        profile = MaskingProfile(
            usubjid_mode="rule_chain",
            include_subjid=False,
            doctor_replace_enabled=False,
            subject_limit=1,
            date_detect_min_non_empty=1,
        )
        dm = self._write("DM.csv", "USUBJID,INVNAM\nABCD0002,Doc\nABCD0001,Doc\n")
        ae = self._write("AE.csv", "USUBJID,AESTDTC\nABCD0001,03/04/2024\n")
        report = self._scan([dm, ae], profile)
        lines = describe_plan(report, profile, {}, self.out_parent)
        self.assertEqual(
            lines,
            [
                "受试者：保留 DM 排序后的前 1 个（共 2 个），其他受试者的行全部删除",
                "USUBJID：规则链，例如 ABCD0002 → SKLT0002",
                "SUBJID 列保持不变",
                "STUDYID：全部改为 [UAT]CIRCULATE",
                "日期：1 个日期列偏移 -2 年，时间部分保留",
                "还有 1 个日期列需要选择 日/月 顺序",
                f"输出：{self.out_parent} 下新建 masked_output_<时间> 文件夹",
            ],
        )


    def test_describe_plan_empty_override_fields(self):
        profile = MaskingProfile(doctor_fields=[], site_field="", date_detect_min_non_empty=1)
        dm = self._write("DM.csv", "USUBJID,INVNAM,SITEID\nS1,Doc,Site\n")
        report = self._scan([dm], profile)
        lines = describe_plan(report, profile, {}, None)
        self.assertIn("DM：未指定医生字段，不替换", lines)
        self.assertIn("DM：未指定施设字段，不替换", lines)
        profile.doctor_replace_enabled = False
        profile.site_replace_enabled = False
        lines = describe_plan(report, profile, {}, None)
        self.assertFalse([line for line in lines if "未指定" in line])


class OrderTests(ExecuteBase):
    def _ambiguous(self):
        profile = MaskingProfile(subject_limit=1, date_detect_min_non_empty=1)
        dm = self._write("DM.csv", "USUBJID\nS1\n")
        ae = self._write("AE.csv", "USUBJID,AESTDTC\nS1,03/04/2024\nS1,25/12/2024\n")
        return profile, self._scan([dm, ae], profile)

    def test_missing_order_blocks(self):
        profile, report = self._ambiguous()
        self.assertEqual(len(missing_orders(report, {})), 1)
        with self.assertRaises(DataForgeError) as cm:
            self._run(report, profile)
        self.assertEqual(str(cm.exception), "请先为 1 个日期列选择 日/月 顺序")
        self.assertEqual(list(self.out_parent.iterdir()), [])

    def test_order_applied(self):
        profile, report = self._ambiguous()
        orders = {("AE.csv", "AESTDTC"): SlashOrder.DAY_FIRST}
        self.assertEqual(missing_orders(report, orders), [])
        self._run(report, profile, orders)
        self.assertEqual(
            [r["AESTDTC"] for r in self._out("AE.csv")], ["2022-04-03", "2022-12-25"]
        )


class MappingTests(unittest.TestCase):
    def test_transform_subject_id(self):
        p = MaskingProfile(sequential_prefix="X", sequential_width=0, sequential_start=7)
        self.assertEqual(transform_subject_id("A", p, 3), "X10")
        p = MaskingProfile(
            usubjid_mode="rule_chain",
            rule_chain_steps=[
                RuleStep("Remove_Prefix", "2"),
                RuleStep("remove_suffix", 1),
                RuleStep("bogus", "zz"),
                RuleStep("remove_prefix", -5),
                RuleStep("prepend", "P-"),
                RuleStep("APPEND", 9),
            ],
        )
        self.assertEqual(transform_subject_id("ABCDEF", p, 0), "P-CDE9")
        p.rule_chain_steps = [RuleStep("remove_suffix", 10)]
        self.assertEqual(transform_subject_id("ABC", p, 0), "")

    def test_duplicate_new_ids(self):
        p = MaskingProfile(
            usubjid_mode="rule_chain", rule_chain_steps=[RuleStep("remove_prefix", 10)]
        )
        with self.assertRaises(DataForgeError) as cm:
            build_mapping(["SUBJ0001", "SUBJ0002"], p)
        self.assertEqual(str(cm.exception), "新 USUBJID 为空（原 ID：SUBJ0001）")
        p.rule_chain_steps = [RuleStep("remove_prefix", 4)]
        with self.assertRaises(DataForgeError) as cm:
            build_mapping(["AAAA1", "BBBB1", "CCCC2", "DDDD2", "EEEE3"], p)
        self.assertEqual(str(cm.exception), "新 USUBJID 重复：1, 2")
        self.assertEqual(build_mapping(["AAAA1", "BBBB2"], p), {"AAAA1": "1", "BBBB2": "2"})

    def test_shift_age_values(self):
        self.assertEqual(shift_age("45", -2), "43")
        self.assertEqual(shift_age("1", -2), "0")
        self.assertEqual(shift_age("30.50", -2), "28.50")
        self.assertEqual(shift_age("+45", -2), "43")
        self.assertEqual(shift_age("1.50", -2), "0.00")
        self.assertEqual(shift_age(" 45 ", -2), "43")
        self.assertEqual(shift_age("abc", -2), "abc")
        self.assertEqual(shift_age("", -2), "")
        self.assertEqual(shift_age("  ", -2), "  ")

    def test_shift_age_unicode_digits_output_ascii(self):
        self.assertEqual(shift_age("４５", -2), "43")


class OutputTests(ExecuteBase):
    def test_folder_conflict_suffix(self):
        profile = MaskingProfile(subject_limit=2)
        report = self._default(profile)
        first = self._run(report, profile)
        second = self._run(report, profile)
        self.assertEqual(first.data, self.out_parent / FOLDER)
        self.assertEqual(second.data, self.out_parent / f"{FOLDER}_1")
        self.assertTrue((self.out_parent / f"{FOLDER}_1" / "DM.csv").is_file())
        self.assertEqual(
            sorted(p.name for p in self.out_parent.iterdir()), [FOLDER, f"{FOLDER}_1"]
        )

    def test_default_parent_is_dm_folder(self):
        profile = MaskingProfile(subject_limit=2)
        report = self._default(profile)
        options = MaskOptions(profile=profile, now=NOW)
        result = run(report, options, no_progress, CancelToken())
        self.assertEqual(result.data, self.dir / FOLDER)
        self.assertEqual(
            sorted(p.name for p in result.outputs),
            ["AE.csv", "DM.csv", "pattern1_scan_report.json", "usubjid_mapping.csv"],
        )
        self.assertTrue(all(p.parent == self.dir / FOLDER and p.is_file() for p in result.outputs))

    def test_cancel_leaves_no_folder(self):
        profile = MaskingProfile(subject_limit=2)
        report = self._default(profile)
        token = CancelToken()

        def progress(current, total, label):
            if current == 2:
                token.cancel()

        with self.assertRaises(Cancelled):
            self._run(report, profile, progress=progress, cancel=token)
        self.assertEqual(list(self.out_parent.iterdir()), [])

    def test_output_folder_errors_become_dataforge_error(self):
        profile = MaskingProfile(subject_limit=2)
        report = self._default(profile)
        for target in ("os.rename", "tempfile.mkdtemp"):
            with self.subTest(target=target):
                with mock.patch(target, side_effect=OSError("disk full")):
                    with self.assertRaises(DataForgeError) as cm:
                        self._run(report, profile)
                self.assertEqual(str(cm.exception), "无法创建输出文件夹（disk full）")
                self.assertEqual(list(self.out_parent.iterdir()), [])

    def test_output_parent_mkdir_error_becomes_dataforge_error(self):
        profile = MaskingProfile(subject_limit=2)
        report = self._default(profile)
        blocker = self.dir / "blocker"
        blocker.write_bytes(b"")
        options = MaskOptions(profile=profile, output_parent=blocker / "sub", now=NOW)
        with self.assertRaises(DataForgeError) as cm:
            run(report, options, no_progress, CancelToken())
        self.assertTrue(str(cm.exception).startswith("无法创建输出文件夹（"), str(cm.exception))

    def test_file_changed_after_scan_aborts(self):
        profile = MaskingProfile(subject_limit=2)
        report = self._default(profile)
        (self.dir / "AE.csv").write_bytes(b"USUBJID\r\n\x81\xff\xfe\r\n")
        with self.assertRaises(DataForgeError) as cm:
            self._run(report, profile)
        self.assertIn("请重新扫描", str(cm.exception))
        self.assertTrue(str(cm.exception).startswith("AE.csv：读取失败"))
        self.assertEqual(list(self.out_parent.iterdir()), [])

    def test_validation_errors(self):
        profile = MaskingProfile(subject_limit=0)
        report = self._default(profile)
        with self.assertRaises(DataForgeError) as cm:
            self._run(report, profile)
        self.assertEqual(str(cm.exception), "输出受试者数必须大于 0")
        ae = self._write("AE.csv", AE_TEXT)
        bad = self._scan([ae], profile)
        with self.assertRaises(DataForgeError) as cm:
            self._run(bad, profile)
        self.assertEqual(str(cm.exception), "扫描未通过，无法执行")

    def test_unparsed_date_warning(self):
        profile = MaskingProfile(subject_limit=1, date_detect_min_non_empty=1)
        dm = self._write("DM.csv", "USUBJID\nS1\n")
        ae = self._write(
            "AE.csv",
            "USUBJID,AESTDTC\nS1,2024-01-01\nS1,2024-01-02\nS1,2024-01-03\n"
            "S1,2024-01-04\nS1,2024-UN-UN\n",
        )
        report = self._scan([dm, ae], profile)
        result = self._run(report, profile)
        self.assertEqual(
            [(w.path, w.message) for w in result.warnings],
            [("AE.csv", "AESTDTC 列有 1 个值无法识别为日期，已保持原样")],
        )
        self.assertEqual(result.stats["dates_unparsed"], 1)
        self.assertEqual(result.stats["dates_shifted"], 4)
        self.assertEqual(self._out("AE.csv")[-1]["AESTDTC"], "2024-UN-UN")

    def test_mapping_and_report_files(self):
        profile = MaskingProfile(subject_limit=2, date_detect_min_non_empty=1)
        dm = self._write("DM.csv", "USUBJID\nS2\nS1\nS3\n")
        ae = self._write("AE.csv", "USUBJID,AESTDTC\nS1,03/04/2024\n")
        report = self._scan([dm, ae], profile)
        orders = {("AE.csv", "AESTDTC"): SlashOrder.DAY_FIRST}
        self._run(report, profile, orders)
        folder = self.out_parent / FOLDER
        self.assertEqual(
            (folder / "usubjid_mapping.csv").read_bytes(),
            "﻿OLD_USUBJID,NEW_USUBJID\r\nS1,TEST0001\r\nS2,TEST0002\r\n".encode("utf-8"),
        )
        raw = (folder / "pattern1_scan_report.json").read_bytes()
        self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
        self.assertNotIn(b"\r\n", raw)
        data = json.loads(raw.decode("utf-8"))
        self.assertEqual(data["ambiguous_date_columns"][0]["order"], "dmy")
        self.assertEqual(
            raw.decode("utf-8"),
            json.dumps(report.to_dict(orders), ensure_ascii=False, indent=2) + "\n",
        )


if __name__ == "__main__":
    unittest.main()
