import json
import tempfile
import unittest
from pathlib import Path

from dataforge.config.store import ConfigStore
from dataforge.tools.edc.config import (
    CONFIG_SECTION,
    DEFAULT_POSITIONS,
    LEGACY_FILE_NAME,
    STEP_KEYS,
    EdcConfig,
    legacy_files,
    load_config,
    save_config,
)
from dataforge.tools.edc.windows import WindowInfo


class EdcConfigTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)
        self.path = self.dir / "cfg.json"
        self.store = ConfigStore(self.path, legacy_path=None)

    def _section(self):
        return json.loads(self.path.read_text(encoding="utf-8"))[CONFIG_SECTION]

    def test_defaults(self):
        c = EdcConfig()
        self.assertEqual(c.max_loops, 100)
        self.assertEqual(c.step_delay, 0.3)
        self.assertEqual(tuple(c.click_positions), STEP_KEYS)
        self.assertEqual(c.click_positions, DEFAULT_POSITIONS)
        self.assertIsNot(c.click_positions, DEFAULT_POSITIONS)
        self.assertIsNone(c.target_window)

    def test_v2_section_values(self):
        self.store.update_section(
            CONFIG_SECTION,
            {
                "max_loops": 30,
                "retry_count": 3,
                "step_delay": 0.5,
                "click_positions": {"新建": {"x": 1, "y": 2}},
            },
        )
        c = load_config(self.store)
        self.assertEqual(c.max_loops, 30)
        self.assertEqual(c.step_delay, 0.5)
        self.assertEqual(c.click_positions["新建"], (1, 2))
        self.assertEqual(c.click_positions["查找"], DEFAULT_POSITIONS["查找"])
        self.assertTrue(save_config(self.store, c))
        self.assertNotIn("retry_count", self._section())

    def test_bad_values_fall_back(self):
        for bad in (0, "abc", True, 10000):
            c = EdcConfig.from_dict({"max_loops": bad})
            self.assertEqual(c.max_loops, 100, bad)
        for bad in (0, 9, True, "1", 5.5):
            c = EdcConfig.from_dict({"step_delay": bad})
            self.assertEqual(c.step_delay, 0.3, bad)
        c = EdcConfig.from_dict({"step_delay": 2})
        self.assertEqual(c.step_delay, 2.0)
        self.assertIsInstance(c.step_delay, float)
        for pos in ({"x": "1"}, {"x": 1}, {"x": True, "y": 2}, "zz"):
            c = EdcConfig.from_dict({"click_positions": {"新建": pos}})
            self.assertEqual(c.click_positions, DEFAULT_POSITIONS, pos)

    def test_target_window_round_trip(self):
        w = WindowInfo(hwnd=123, title="EDC", process="chrome.exe")
        c = EdcConfig(target_window=w)
        self.assertTrue(save_config(self.store, c))
        self.assertEqual(
            self._section()["target_window"],
            {"hwnd": 123, "title": "EDC", "process": "chrome.exe"},
        )
        self.assertEqual(load_config(self.store).target_window, w)
        self.assertIsNone(EdcConfig().to_dict()["target_window"])

    def test_target_window_bad_shape(self):
        for bad in (
            "x",
            {"hwnd": "1", "title": "a", "process": "b"},
            {"hwnd": True, "title": "a", "process": "b"},
            {"hwnd": 1, "title": 2, "process": "b"},
            {"hwnd": 1, "title": "a"},
        ):
            self.assertIsNone(EdcConfig.from_dict({"target_window": bad}).target_window, bad)

    def test_root_level_legacy(self):
        text = json.dumps({"max_loops": 5, "click_positions": {"ok": {"x": 7, "y": 8}}})
        self.path.write_text(text, encoding="utf-8")
        c = load_config(self.store)
        self.assertEqual(c.max_loops, 5)
        self.assertEqual(c.click_positions["ok"], (7, 8))
        self.assertEqual(self.path.read_text(encoding="utf-8"), text)

    def test_legacy_file_migrated(self):
        legacy = self.dir / LEGACY_FILE_NAME
        legacy.write_text(json.dumps({"max_loops": 12, "step_delay": 1}), encoding="utf-8")
        before = legacy.read_bytes()
        c = load_config(self.store, [legacy])
        self.assertEqual(c.max_loops, 12)
        self.assertEqual(self._section()["max_loops"], 12)
        self.assertEqual(legacy.read_bytes(), before)

    def test_legacy_files_candidates(self):
        names = [p.as_posix() for p in legacy_files()]
        self.assertTrue(any(n.endswith("src/gui/widgets/" + LEGACY_FILE_NAME) for n in names))
        self.assertTrue(any(n.endswith("src/utils/" + LEGACY_FILE_NAME) for n in names))


if __name__ == "__main__":
    unittest.main()
