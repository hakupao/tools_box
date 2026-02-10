import os
import tempfile
import unittest

import pandas as pd

from src.utils.data_masking_service import DataMaskingService, Pattern1Profile


class DataMaskingServicePattern1Tests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base = self.temp_dir.name
        self.config_path = os.path.join(self.base, "mask_config.json")
        self.service = DataMaskingService(config_path=self.config_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _write_csv(self, filename: str, rows: list[dict]) -> str:
        path = os.path.join(self.base, filename)
        pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")
        return path

    def _prepare_default_files(self) -> tuple[str, str]:
        dm_file = self._write_csv(
            "DM.csv",
            [
                {
                    "USUBJID": "SUBJ0002",
                    "INVNAM": "Doctor-A",
                    "ICINVNAM": "Doctor-B",
                    "SITEID": "Site-01",
                    "AGE": "45",
                    "STUDYID": "OLD-STUDY",
                    "DMDTC": "2024",
                },
                {
                    "USUBJID": "SUBJ0001",
                    "INVNAM": "Doctor-C",
                    "ICINVNAM": "Doctor-D",
                    "SITEID": "Site-02",
                    "AGE": "30",
                    "STUDYID": "OLD-STUDY",
                    "DMDTC": "2024-05",
                },
                {
                    "USUBJID": "SUBJ0003",
                    "INVNAM": "Doctor-E",
                    "ICINVNAM": "Doctor-F",
                    "SITEID": "Site-03",
                    "AGE": "66",
                    "STUDYID": "OLD-STUDY",
                    "DMDTC": "2024-06-30",
                },
            ],
        )

        ae_file = self._write_csv(
            "AE.csv",
            [
                {
                    "USUBJID": "SUBJ0002",
                    "SUBJID": "SUBJ0002",
                    "STUDYID": "OLD-STUDY",
                    "AESTDTC": "2024-06-15T13:30:00",
                },
                {
                    "USUBJID": "SUBJ0001",
                    "SUBJID": "SUBJ0001",
                    "STUDYID": "OLD-STUDY",
                    "AESTDTC": "2024",
                },
                {
                    "USUBJID": "SUBJ0003",
                    "SUBJID": "SUBJ0003",
                    "STUDYID": "OLD-STUDY",
                    "AESTDTC": "2024-07",
                },
            ],
        )

        return dm_file, ae_file

    def test_pattern1_default_infer_and_iso_output(self):
        dm_file, ae_file = self._prepare_default_files()
        profile = Pattern1Profile(subject_limit=2)

        report = self.service.scan_pattern1([dm_file, ae_file], profile)
        self.assertFalse(report.errors)
        self.assertEqual(report.selected_subjects, ["SUBJ0001", "SUBJ0002", "SUBJ0003"])
        self.assertEqual(report.dm_first_usubjid, "SUBJ0002")

        output_dir = os.path.join(self.base, "out")
        result = self.service.run_pattern1([dm_file, ae_file], output_dir=output_dir, profile=profile, scan_report=report)

        self.assertTrue(os.path.exists(result.mapping_file))
        self.assertTrue(os.path.exists(result.scan_report_file))

        dm_out = pd.read_csv(os.path.join(output_dir, "DM.csv"), dtype=str, na_filter=False)
        ae_out = pd.read_csv(os.path.join(output_dir, "AE.csv"), dtype=str, na_filter=False)

        # Subject filter by DM sorted top-N
        self.assertEqual(sorted(dm_out["USUBJID"].unique().tolist()), ["TEST0001", "TEST0002"])
        self.assertEqual(sorted(ae_out["USUBJID"].unique().tolist()), ["TEST0001", "TEST0002"])

        # Default doctor field only INVNAM replaced
        self.assertEqual(set(dm_out["INVNAM"].tolist()), {"テスト医師"})
        self.assertIn("Doctor-B", dm_out["ICINVNAM"].tolist())
        self.assertIn("Doctor-D", dm_out["ICINVNAM"].tolist())

        # ISO date output with auto-fill and year shift
        self.assertIn("2022-01-01", dm_out["DMDTC"].tolist())
        self.assertIn("2022-05-01", dm_out["DMDTC"].tolist())
        self.assertIn("2022-06-15", ae_out["AESTDTC"].tolist())
        self.assertIn("2022-01-01", ae_out["AESTDTC"].tolist())

    def test_pattern1_extra_doctor_fields_only_in_dm(self):
        dm_file, ae_file = self._prepare_default_files()
        ae_df = pd.read_csv(ae_file, dtype=str, na_filter=False)
        ae_df["INVNAM"] = ["AE-Doctor-1", "AE-Doctor-2", "AE-Doctor-3"]
        ae_df.to_csv(ae_file, index=False, encoding="utf-8-sig")

        profile = Pattern1Profile(subject_limit=2, doctor_fields=["INVNAM", "ICINVNAM"])

        report = self.service.scan_pattern1([dm_file, ae_file], profile)
        self.assertFalse(report.errors)

        output_dir = os.path.join(self.base, "out2")
        self.service.run_pattern1([dm_file, ae_file], output_dir=output_dir, profile=profile, scan_report=report)

        dm_out = pd.read_csv(os.path.join(output_dir, "DM.csv"), dtype=str, na_filter=False)
        ae_out = pd.read_csv(os.path.join(output_dir, "AE.csv"), dtype=str, na_filter=False)

        self.assertEqual(set(dm_out["ICINVNAM"].tolist()), {"テスト医師"})
        self.assertEqual(set(ae_out["INVNAM"].tolist()), {"AE-Doctor-1", "AE-Doctor-2"})

    def test_scan_report_includes_non_empty_and_empty_fields(self):
        dm_file = self._write_csv(
            "DM.csv",
            [
                {"USUBJID": "S001", "INVNAM": "", "PARTIAL": "", "ALL_EMPTY": "", "DMDTC": "2024"},
                {"USUBJID": "S002", "INVNAM": "Doctor-2", "PARTIAL": "X", "ALL_EMPTY": "", "DMDTC": "2024-05"},
            ],
        )
        ae_file = self._write_csv(
            "AE.csv",
            [
                {"USUBJID": "S001", "AESTDTC": "2024-01-01"},
                {"USUBJID": "S002", "AESTDTC": "2024-01-02"},
            ],
        )

        report = self.service.scan_pattern1([dm_file, ae_file], Pattern1Profile(subject_limit=1))
        self.assertFalse(report.errors)

        dm_summary = next(item for item in report.files_summary if item.file_name.upper() == "DM.CSV")
        self.assertIn("PARTIAL", dm_summary.non_empty_fields)
        self.assertIn("ALL_EMPTY", dm_summary.empty_fields)

        text = self.service.format_scan_report(report)
        self.assertIn("有值字段", text)
        self.assertIn("空字段", text)

    def test_dm_overrides_replace_only_non_empty_cells(self):
        dm_file = self._write_csv(
            "DM.csv",
            [
                {"USUBJID": "S001", "INVNAM": "", "SITEID": "", "AGE": "", "STUDYID": "OLD", "DMDTC": "2024"},
                {
                    "USUBJID": "S002",
                    "INVNAM": "Doctor-2",
                    "SITEID": "Site-2",
                    "AGE": "40",
                    "STUDYID": "OLD",
                    "DMDTC": "2024-05",
                },
            ],
        )
        ae_file = self._write_csv(
            "AE.csv",
            [
                {"USUBJID": "S001", "SUBJID": "S001", "STUDYID": "OLD", "AESTDTC": "2024-01-01"},
                {"USUBJID": "S002", "SUBJID": "S002", "STUDYID": "OLD", "AESTDTC": "2024-01-02"},
            ],
        )

        profile = Pattern1Profile(
            subject_limit=2,
            doctor_fields=["INVNAM"],
            doctor_value="テスト医師",
            site_field="SITEID",
            site_value="テスト施設",
            age_field="AGE",
            age_shift_years=-2,
        )

        report = self.service.scan_pattern1([dm_file, ae_file], profile)
        self.assertFalse(report.errors)

        output_dir = os.path.join(self.base, "out_dm_override")
        self.service.run_pattern1([dm_file, ae_file], output_dir=output_dir, profile=profile, scan_report=report)

        dm_out = pd.read_csv(os.path.join(output_dir, "DM.csv"), dtype=str, na_filter=False)
        row_1 = dm_out.loc[dm_out["USUBJID"] == "TEST0001"].iloc[0]
        row_2 = dm_out.loc[dm_out["USUBJID"] == "TEST0002"].iloc[0]

        self.assertEqual(row_1["INVNAM"], "")
        self.assertEqual(row_1["SITEID"], "")
        self.assertEqual(row_1["AGE"], "")

        self.assertEqual(row_2["INVNAM"], "テスト医師")
        self.assertEqual(row_2["SITEID"], "テスト施設")
        self.assertEqual(row_2["AGE"], "38")

    def test_scan_fails_when_any_file_missing_usubjid(self):
        dm_file = self._write_csv(
            "DM.csv",
            [
                {"USUBJID": "S001", "INVNAM": "Doctor-1", "DMDTC": "2024-05"},
                {"USUBJID": "S002", "INVNAM": "Doctor-2", "DMDTC": "2024-06"},
            ],
        )
        ae_file = self._write_csv(
            "AE.csv",
            [
                {"SUBJID": "S001", "AESTDTC": "2024-01-01"},
                {"SUBJID": "S002", "AESTDTC": "2024-01-02"},
            ],
        )

        report = self.service.scan_pattern1([dm_file, ae_file], Pattern1Profile())
        self.assertTrue(report.errors)
        self.assertTrue(any("缺少 USUBJID" in item for item in report.errors))


if __name__ == "__main__":
    unittest.main()
