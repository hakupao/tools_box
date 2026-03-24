import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.utils.data_masking_service import DataMaskingService, Pattern1Profile
from src.utils.edc_site_adder_service import EdcSiteAdderService


class UnifiedConfigServicesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base = Path(self.temp_dir.name)
        self.config_path = self.base / "tools_box_config.json"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_data_masking_save_profile_writes_section_and_keeps_other_section(self):
        self.config_path.write_text(
            json.dumps({"edc_site_adder": {"max_loops": 77}}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        service = DataMaskingService(config_path=str(self.config_path))
        profile = Pattern1Profile(studyid_value="UNIT-STUDY", subject_limit=88)
        self.assertTrue(service.save_profile(profile))

        payload = json.loads(self.config_path.read_text(encoding="utf-8"))
        self.assertIn("edc_site_adder", payload)
        self.assertIn("data_masking_pattern1", payload)
        self.assertEqual(payload["edc_site_adder"]["max_loops"], 77)
        self.assertEqual(payload["data_masking_pattern1"]["studyid_value"], "UNIT-STUDY")
        self.assertEqual(payload["data_masking_pattern1"]["subject_limit"], 88)

    def test_edc_save_config_writes_section_and_keeps_other_section(self):
        self.config_path.write_text(
            json.dumps(
                {"data_masking_pattern1": {"studyid_value": "BASE", "subject_limit": 10}},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        service = EdcSiteAdderService(config_path=self.config_path)
        service.config["max_loops"] = 123
        self.assertTrue(service.save_config())

        payload = json.loads(self.config_path.read_text(encoding="utf-8"))
        self.assertIn("data_masking_pattern1", payload)
        self.assertIn("edc_site_adder", payload)
        self.assertEqual(payload["data_masking_pattern1"]["studyid_value"], "BASE")
        self.assertEqual(payload["edc_site_adder"]["max_loops"], 123)

    def test_data_masking_can_migrate_legacy_profile_file(self):
        legacy_path = self.base / "data_masking_pattern1_config.json"
        legacy_payload = {"studyid_value": "LEGACY-STUDY", "subject_limit": 66, "include_subjid": False}
        legacy_path.write_text(json.dumps(legacy_payload, ensure_ascii=False, indent=2), encoding="utf-8")

        with patch.dict(os.environ, {"TOOLS_BOX_CONFIG_PATH": str(self.config_path)}):
            with patch.object(
                DataMaskingService,
                "_legacy_config_paths",
                return_value=[legacy_path],
            ):
                service = DataMaskingService()

        self.assertEqual(service.profile.studyid_value, "LEGACY-STUDY")
        self.assertEqual(service.profile.subject_limit, 66)
        self.assertFalse(service.profile.include_subjid)

        payload = json.loads(self.config_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["data_masking_pattern1"]["studyid_value"], "LEGACY-STUDY")
        self.assertEqual(payload["data_masking_pattern1"]["subject_limit"], 66)

    def test_edc_can_migrate_legacy_profile_file(self):
        legacy_path = self.base / "edc_site_adder_config.json"
        legacy_payload = {
            "max_loops": 222,
            "click_positions": {
                "新建": {"x": 1, "y": 2},
                "查找": {"x": 3, "y": 4},
                "搜索框": {"x": 5, "y": 6},
                "搜索": {"x": 7, "y": 8},
                "选择": {"x": 9, "y": 10},
                "ok": {"x": 11, "y": 12},
                "确认": {"x": 13, "y": 14},
            },
        }
        legacy_path.write_text(json.dumps(legacy_payload, ensure_ascii=False, indent=2), encoding="utf-8")

        with patch.dict(os.environ, {"TOOLS_BOX_CONFIG_PATH": str(self.config_path)}):
            with patch.object(
                EdcSiteAdderService,
                "_legacy_config_paths",
                return_value=[legacy_path],
            ):
                service = EdcSiteAdderService()

        self.assertEqual(service.config["max_loops"], 222)
        self.assertEqual(service.config["click_positions"]["新建"]["x"], 1)
        self.assertEqual(service.config["click_positions"]["确认"]["y"], 14)

        payload = json.loads(self.config_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["edc_site_adder"]["max_loops"], 222)
        self.assertEqual(payload["edc_site_adder"]["click_positions"]["新建"]["x"], 1)


    # ── New config fields: backward compat & round-trip ──

    def test_edc_new_fields_get_defaults_when_missing(self):
        """Old config without retry_count/step_delay should get defaults."""
        old_config = {
            "edc_site_adder": {
                "max_loops": 50,
                "click_positions": {
                    "新建": {"x": 10, "y": 20},
                    "查找": {"x": 30, "y": 40},
                    "搜索框": {"x": 50, "y": 60},
                    "搜索": {"x": 70, "y": 80},
                    "选择": {"x": 90, "y": 100},
                    "ok": {"x": 110, "y": 120},
                    "确认": {"x": 130, "y": 140},
                },
            }
        }
        self.config_path.write_text(json.dumps(old_config, ensure_ascii=False, indent=2), encoding="utf-8")

        service = EdcSiteAdderService(config_path=self.config_path)
        self.assertEqual(service.config["max_loops"], 50)
        self.assertEqual(service.config["retry_count"], 1)
        self.assertEqual(service.config["step_delay"], 0.3)
        self.assertEqual(service.config["click_positions"]["新建"]["x"], 10)

    def test_edc_new_fields_round_trip(self):
        """Save config with new fields, reload, verify values."""
        service = EdcSiteAdderService(config_path=self.config_path)
        service.config["retry_count"] = 3
        service.config["step_delay"] = 0.5
        service.config["max_loops"] = 200
        self.assertTrue(service.save_config())

        service2 = EdcSiteAdderService(config_path=self.config_path)
        self.assertEqual(service2.config["retry_count"], 3)
        self.assertEqual(service2.config["step_delay"], 0.5)
        self.assertEqual(service2.config["max_loops"], 200)

    def test_edc_reset_restores_new_field_defaults(self):
        service = EdcSiteAdderService(config_path=self.config_path)
        service.config["retry_count"] = 5
        service.config["step_delay"] = 2.0
        service.save_config()

        service.reset_to_default_config()
        self.assertEqual(service.config["retry_count"], 1)
        self.assertEqual(service.config["step_delay"], 0.3)


if __name__ == "__main__":
    unittest.main()
