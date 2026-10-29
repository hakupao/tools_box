import tempfile
import unittest
from pathlib import Path

from dataforge.config.recent import RecentStore
from dataforge.config.store import ConfigStore


class RecentStoreTests(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.addCleanup(self._td.cleanup)
        tmp = Path(self._td.name)
        self.cfg = ConfigStore(tmp / "c.json", tmp / "legacy.json")
        self.recent = RecentStore(self.cfg)

    def test_add_newest_first(self):
        self.recent.add("a", "A", {"n": 1})
        self.recent.add("b", "B", {"n": 2})
        entries = RecentStore(self.cfg).entries()
        self.assertEqual([e.tool_id for e in entries], ["b", "a"])
        self.assertEqual(entries[1].summary, "A")
        self.assertEqual(entries[1].state, {"n": 1})
        self.assertRegex(entries[0].timestamp, r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d$")

    def test_limit_10(self):
        for i in range(12):
            self.recent.add("t", f"s{i}", {"i": i})
        entries = self.recent.entries()
        self.assertEqual(len(entries), 10)
        self.assertEqual(entries[0].state, {"i": 11})
        self.assertEqual(entries[-1].state, {"i": 2})

    def test_same_state_moves_to_top(self):
        self.recent.add("a", "A", {"n": 1})
        self.recent.add("b", "B", {"n": 2})
        self.recent.add("a", "A again", {"n": 1})
        entries = self.recent.entries()
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0].tool_id, "a")
        self.assertEqual(entries[0].summary, "A again")

    def test_clear(self):
        self.recent.add("a", "A", {})
        self.recent.clear()
        self.assertEqual(self.recent.entries(), [])

    def test_bad_records_skipped(self):
        self.cfg.update_section("recent", {"entries": [{"tool_id": "x"}]})
        self.assertEqual(self.recent.entries(), [])


if __name__ == "__main__":
    unittest.main()
