import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from dataforge.config.store import ConfigStore, default_config_path, legacy_config_path


class ConfigStoreTests(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.addCleanup(self._td.cleanup)
        self.tmp = Path(self._td.name)
        self.path = self.tmp / "new" / "cfg.json"
        self.legacy = self.tmp / "legacy" / "old.json"

    def test_update_preserves_other_sections(self):
        s = ConfigStore(self.path, self.legacy)
        self.assertTrue(s.update_section("a", {"x": 1}))
        self.assertTrue(s.update_section("b", {"y": 2}))
        s2 = ConfigStore(self.path, self.legacy)
        self.assertEqual(s2.section("a"), {"x": 1})
        self.assertEqual(s2.section("b"), {"y": 2})
        self.assertEqual(s2.section("missing"), {})

    def test_section_returns_copy(self):
        s = ConfigStore(self.path, self.legacy)
        s.update_section("a", {"x": [1]})
        s.section("a")["x"].append(2)
        self.assertEqual(s.section("a"), {"x": [1]})

    def test_corrupt_file_is_backed_up(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text("{not json", encoding="utf-8")
        self.assertEqual(ConfigStore(self.path, self.legacy).section("a"), {})
        baks = list(self.path.parent.glob("*.corrupt-*.bak"))
        self.assertEqual(len(baks), 1)
        self.assertEqual(baks[0].read_text(encoding="utf-8"), "{not json")

    def test_non_dict_top_level_is_backed_up(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text("[1, 2]", encoding="utf-8")
        self.assertEqual(ConfigStore(self.path, self.legacy).section("a"), {})
        self.assertEqual(len(list(self.path.parent.glob("*.corrupt-*.bak"))), 1)

    def test_reads_legacy_when_new_missing(self):
        self.legacy.parent.mkdir(parents=True)
        text = json.dumps({"edc_site_adder": {"max_loops": 5}})
        self.legacy.write_text(text, encoding="utf-8")
        s = ConfigStore(self.path, self.legacy)
        self.assertEqual(s.section("edc_site_adder"), {"max_loops": 5})
        self.assertTrue(s.update_section("other", {"k": 1}))
        self.assertTrue(self.path.exists())
        self.assertEqual(self.legacy.read_text(encoding="utf-8"), text)
        self.assertEqual(ConfigStore(self.path, self.legacy).section("other"), {"k": 1})

    def test_write_failure_returns_false(self):
        s = ConfigStore(self.path, self.legacy)
        with patch("os.replace", side_effect=PermissionError):
            self.assertFalse(s.update_section("a", {"x": 1}))
        self.assertEqual(list(self.path.parent.glob("*.tmp")), [])
        self.assertFalse(self.path.exists())

    def test_read_error_does_not_back_up(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text('{"a": {"x": 1}}', encoding="utf-8")
        s = ConfigStore(self.path, self.legacy)
        with patch.object(Path, "read_text", side_effect=PermissionError):
            self.assertEqual(s.section("a"), {})
        self.assertEqual(list(self.path.parent.glob("*.bak")), [])
        self.assertEqual(s.section("a"), {"x": 1})

    def test_update_does_not_overwrite_unreadable_config(self):
        self.path.parent.mkdir(parents=True)
        text = '{"a": {"x": 1}}'
        self.path.write_text(text, encoding="utf-8")
        s = ConfigStore(self.path, self.legacy)
        with patch.object(Path, "read_text", side_effect=PermissionError):
            self.assertFalse(s.update_section("b", {"y": 2}))
        self.assertEqual(self.path.read_text(encoding="utf-8"), text)
        self.assertEqual(list(self.path.parent.iterdir()), [self.path])

    def test_non_utf8_file_is_backed_up(self):
        self.path.parent.mkdir(parents=True)
        bad = bytes([0xFF, 0xFE, 0x7B])
        self.path.write_bytes(bad)
        self.assertEqual(ConfigStore(self.path, self.legacy).section("a"), {})
        baks = list(self.path.parent.glob("*.corrupt-*.bak"))
        self.assertEqual(len(baks), 1)
        self.assertEqual(baks[0].read_bytes(), bad)
        self.assertFalse(self.path.exists())

    def test_non_utf8_legacy_left_untouched(self):
        self.legacy.parent.mkdir(parents=True)
        bad = bytes([0xFF, 0xFE, 0x7B])
        self.legacy.write_bytes(bad)
        s = ConfigStore(self.path, self.legacy)
        self.assertEqual(s.section("a"), {})
        self.assertEqual(self.legacy.read_bytes(), bad)
        self.assertEqual(list(self.legacy.parent.iterdir()), [self.legacy])

    def test_env_var_overrides_path(self):
        p = self.tmp / "env.json"
        with patch.dict(os.environ, {"DATAFORGE_STUDIO_CONFIG_PATH": str(p)}):
            self.assertEqual(default_config_path(), p)

    def test_legacy_env_var_used_as_fallback(self):
        p = self.tmp / "tb.json"
        env = {"TOOLS_BOX_CONFIG_PATH": str(p)}
        with patch.dict(os.environ, env):
            os.environ.pop("DATAFORGE_STUDIO_CONFIG_PATH", None)
            self.assertEqual(default_config_path(), p)

    def test_default_paths_from_platformdirs(self):
        with patch.dict(os.environ, {}):
            os.environ.pop("DATAFORGE_STUDIO_CONFIG_PATH", None)
            os.environ.pop("TOOLS_BOX_CONFIG_PATH", None)
            with patch("dataforge.config.store.user_config_dir", lambda n, **k: str(self.tmp / n)):
                self.assertEqual(
                    default_config_path(),
                    self.tmp / "dataforge_studio" / "dataforge_studio_config.json",
                )
                self.assertEqual(
                    legacy_config_path(), self.tmp / "tools_box" / "tools_box_config.json"
                )


if __name__ == "__main__":
    unittest.main()
