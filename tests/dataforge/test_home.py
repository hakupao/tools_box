import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from tests.dataforge.qt_helpers import qapp

from dataforge.config.recent import RecentStore
from dataforge.config.store import ConfigStore
from dataforge.ui.home import HomePage, format_recent_time
from dataforge.ui.registry import TOOLS


class FormatRecentTimeTests(unittest.TestCase):
    NOW = datetime(2026, 10, 29, 15, 0, 0)

    def test_today(self):
        self.assertEqual(format_recent_time("2026-10-29T09:05:00", self.NOW), "今天 09:05")

    def test_yesterday(self):
        self.assertEqual(format_recent_time("2026-10-28T23:59:00", self.NOW), "昨天")

    def test_older(self):
        self.assertEqual(format_recent_time("2026-10-01T08:00:00", self.NOW), "2026-10-01")

    def test_bad_timestamp_falls_back(self):
        self.assertEqual(format_recent_time("garbage", self.NOW), "garbage")


class HomePageTests(unittest.TestCase):
    def setUp(self):
        qapp()
        self._td = tempfile.TemporaryDirectory()
        self.addCleanup(self._td.cleanup)
        tmp = Path(self._td.name)
        self.recent = RecentStore(ConfigStore(tmp / "c.json", tmp / "legacy.json"))
        self.opened: list[tuple[str, dict | None]] = []
        self.page = HomePage(TOOLS, self.recent, lambda i, s: self.opened.append((i, s)))
        self.addCleanup(self.page.deleteLater)

    def test_scroll_body_does_not_paint_background(self):
        # autoFill would paint the light palette under white dark-theme text.
        from qfluentwidgets import SmoothScrollArea

        scroll = self.page.findChild(SmoothScrollArea)
        self.assertFalse(scroll.widget().autoFillBackground())

    def test_unknown_tool_entries_hidden(self):
        self.recent.add("dead_link", "x", {})
        self.recent.add("date_convert", "y", {"a": 1})
        self.page.refresh()
        self.assertEqual([e.tool_id for e in self.page.visible_recent()], ["date_convert"])

    def test_click_recent_opens_with_state(self):
        self.recent.add("date_convert", "y", {"a": 1})
        self.page.refresh()
        self.page.recent_cards()[0].clicked.emit()
        self.assertEqual(self.opened, [("date_convert", {"a": 1})])

    def test_click_tool_card_opens_without_state(self):
        cards = self.page.tool_cards()
        self.assertEqual(len(cards), len(TOOLS))
        cards[0].clicked.emit()
        self.assertEqual(self.opened, [(TOOLS[0].id, None)])

    def test_refresh_after_add(self):
        self.assertEqual(len(self.page.visible_recent()), 0)
        self.recent.add("date_convert", "y", {})
        self.page.refresh()
        self.assertEqual(len(self.page.visible_recent()), 1)
        self.assertEqual(len(self.page.recent_cards()), 1)
        self.recent.add("width_convert", "z", {})
        self.page.refresh()
        self.assertEqual(len(self.page.recent_cards()), 2)


if __name__ == "__main__":
    unittest.main()
