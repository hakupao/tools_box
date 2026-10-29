import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from dataforge.config.legacy import legacy_file_candidates, load_section_with_legacy
from dataforge.config.store import ConfigStore


class RootTests(unittest.TestCase):
    def test_root_returns_deep_copy_and_empty_on_missing(self):
        with tempfile.TemporaryDirectory() as d:
            store = ConfigStore(Path(d) / "c.json", legacy_path=None)
            self.assertEqual(store.root(), {})
            store.update_section("a", {"x": 1})
            root = store.root()
            root["a"]["x"] = 2
            self.assertEqual(store.section("a"), {"x": 1})


class LoadSectionTests(unittest.TestCase):
    def test_section_wins(self):
        with tempfile.TemporaryDirectory() as d:
            store = ConfigStore(Path(d) / "c.json", legacy_path=None)
            store.update_section("s", {"k": 1})
            legacy = Path(d) / "old.json"
            legacy.write_text('{"k": 9}', encoding="utf-8")
            self.assertEqual(load_section_with_legacy(store, "s", {"k"}, [legacy]), {"k": 1})

    def test_candidates_non_frozen_includes_src_utils(self):
        paths = legacy_file_candidates("x.json")
        self.assertIn(Path(__file__).resolve().parents[2] / "src" / "utils" / "x.json", paths)

    def test_candidates_frozen_first_and_dedup(self):
        with tempfile.TemporaryDirectory() as d:
            exe = Path(d) / "app.exe"
            with mock.patch.object(sys, "frozen", True, create=True), mock.patch.object(
                sys, "executable", str(exe)
            ):
                paths = legacy_file_candidates("x.json", Path(d))
            self.assertEqual(paths[0], Path(d).resolve() / "x.json")
            self.assertEqual(len(paths), len(set(paths)))

    def test_non_object_legacy_skipped(self):
        with tempfile.TemporaryDirectory() as d:
            store = ConfigStore(Path(d) / "c.json", legacy_path=None)
            legacy = Path(d) / "old.json"
            legacy.write_text("[1]", encoding="utf-8")
            self.assertEqual(load_section_with_legacy(store, "s", {"k"}, [legacy]), {})
            self.assertFalse((Path(d) / "c.json").exists())

    def test_legacy_bom_and_no_matching_key(self):
        with tempfile.TemporaryDirectory() as d:
            store = ConfigStore(Path(d) / "c.json", legacy_path=None)
            a = Path(d) / "a.json"
            a.write_text('{"other": 1}', encoding="utf-8")
            b = Path(d) / "b.json"
            b.write_bytes(b"\xef\xbb\xbf" + json.dumps({"k": 2}).encode())
            self.assertEqual(load_section_with_legacy(store, "s", {"k"}, [a, b]), {"k": 2})
