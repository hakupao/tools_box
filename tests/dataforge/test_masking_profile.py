import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from dataforge.config.legacy import legacy_file_candidates
from dataforge.config.store import ConfigStore
from dataforge.tools.masking.profile import (
    CONFIG_SECTION,
    LEGACY_FILE_NAME,
    MaskingProfile,
    RuleStep,
    load_profile,
    save_profile,
)


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)
        self.path = self.dir / "cfg.json"
        self.store = ConfigStore(self.path, legacy_path=None)

    def test_defaults(self):
        p = MaskingProfile()
        self.assertEqual(p.studyid_value, "[UAT]CIRCULATE")
        self.assertEqual(p.rule_chain_steps[2], RuleStep("prepend", "SKLT"))
        self.assertEqual(p.doctor_value, "テスト医師")
        self.assertFalse(hasattr(p, "subject_sort"))

    def test_section_round_trip_keeps_other_sections(self):
        self.path.write_text(json.dumps({"app": {"theme": "dark"}}), encoding="utf-8")
        self.assertTrue(save_profile(self.store, MaskingProfile(subject_limit=7)))
        data = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(data["app"], {"theme": "dark"})
        self.assertIn(CONFIG_SECTION, data)
        self.assertEqual(load_profile(self.store), MaskingProfile(subject_limit=7))

    def test_removed_keys_ignored_and_not_written(self):
        self.store.update_section(
            CONFIG_SECTION,
            {
                "subject_sort": "x",
                "date_output_format": "y",
                "partial_date_policy": "z",
                "subject_limit": 3,
            },
        )
        p = load_profile(self.store)
        self.assertEqual(p.subject_limit, 3)
        save_profile(self.store, p)
        sec = json.loads(self.path.read_text(encoding="utf-8"))[CONFIG_SECTION]
        for k in ("subject_sort", "date_output_format", "partial_date_policy"):
            self.assertNotIn(k, sec)

    def test_v2_values_kept(self):
        p = MaskingProfile.from_dict(
            {
                "include_subjid": False,
                "subject_limit": "30",
                "doctor_fields": [" INVNAM ", "", "ICINVNAM"],
            }
        )
        self.assertIs(p.include_subjid, False)
        self.assertEqual(p.subject_limit, 30)
        self.assertEqual(p.doctor_fields, ["INVNAM", "ICINVNAM"])

    def test_bad_values_fall_back(self):
        self.assertEqual(MaskingProfile.from_dict({"subject_limit": "abc"}).subject_limit, 100)
        self.assertIs(MaskingProfile.from_dict({"include_subjid": "maybe"}).include_subjid, True)
        self.assertIs(MaskingProfile.from_dict({"include_subjid": "no"}).include_subjid, False)
        self.assertEqual(MaskingProfile.from_dict({"usubjid_mode": "x"}).usubjid_mode, "sequential")
        self.assertEqual(
            MaskingProfile.from_dict({"usubjid_mode": "rule_chain"}).usubjid_mode, "rule_chain"
        )
        self.assertEqual(MaskingProfile.from_dict({"unknown": 1}), MaskingProfile())

    def test_rule_chain_steps(self):
        p = MaskingProfile.from_dict(
            {"rule_chain_steps": [{"op": " append ", "value": "Z"}, "junk"]}
        )
        self.assertEqual(p.rule_chain_steps, [RuleStep("append", "Z")])
        self.assertEqual(p.to_dict()["rule_chain_steps"], [{"op": "append", "value": "Z"}])
        self.assertEqual(
            MaskingProfile.from_dict({"rule_chain_steps": []}).rule_chain_steps,
            MaskingProfile().rule_chain_steps,
        )

    def test_root_level_legacy_profile(self):
        text = json.dumps({"studyid_value": "S1"})
        self.path.write_text(text, encoding="utf-8")
        self.assertEqual(load_profile(self.store).studyid_value, "S1")
        self.assertEqual(self.path.read_text(encoding="utf-8"), text)

    def test_legacy_file_migrated(self):
        old = self.dir / LEGACY_FILE_NAME
        old.write_text(json.dumps({"subject_limit": 5}), encoding="utf-8")
        before = old.read_bytes()
        self.assertEqual(load_profile(self.store, [old]).subject_limit, 5)
        self.assertIn(CONFIG_SECTION, json.loads(self.path.read_text(encoding="utf-8")))
        self.assertEqual(old.read_bytes(), before)

    def test_section_wins_over_legacy_file(self):
        old = self.dir / LEGACY_FILE_NAME
        old.write_text(json.dumps({"subject_limit": 5}), encoding="utf-8")
        self.store.update_section(CONFIG_SECTION, {"subject_limit": 8})
        self.assertEqual(load_profile(self.store, [old]).subject_limit, 8)

    def test_broken_legacy_file_skipped(self):
        old = self.dir / LEGACY_FILE_NAME
        old.write_text("{", encoding="utf-8")
        self.assertEqual(load_profile(self.store, [old]), MaskingProfile())
        self.assertFalse(self.path.exists())

    def test_candidates(self):
        paths = legacy_file_candidates(LEGACY_FILE_NAME)
        self.assertIn(
            Path(__file__).resolve().parents[2] / "src" / "utils" / LEGACY_FILE_NAME, paths
        )
        with mock.patch.object(sys, "frozen", True, create=True), mock.patch.object(
            sys, "executable", str(self.dir / "app.exe")
        ):
            first = legacy_file_candidates(LEGACY_FILE_NAME)[0]
        self.assertEqual(first, self.dir.resolve() / LEGACY_FILE_NAME)
