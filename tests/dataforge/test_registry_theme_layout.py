from __future__ import annotations

import unittest

from qfluentwidgets import Theme

from dataforge.ui.layout import MIN_WINDOW_WIDTH, LayoutMode, layout_mode_for_width
from dataforge.ui.registry import TOOLS, ToolGroup, get_tool, load_page_class
from dataforge.ui.theme import apply_theme_mode

from .qt_helpers import qapp


class RegistryTests(unittest.TestCase):
    def test_ids_unique(self) -> None:
        ids = [t.id for t in TOOLS]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(ids, ["date_convert", "width_convert"])

    def test_get_tool(self) -> None:
        spec = get_tool("date_convert")
        self.assertEqual(spec.name, "日期转换")
        self.assertIs(spec.group, ToolGroup.UTILS)
        self.assertEqual(spec.page, "dataforge.ui.pages.date_convert_page:DateConvertPage")

    def test_get_tool_unknown_raises(self) -> None:
        with self.assertRaises(KeyError):
            get_tool("nope")

    def test_group_order(self) -> None:
        self.assertEqual(
            [g.value for g in ToolGroup], ["文件处理", "业务", "小工具"]
        )

    def test_load_page_class(self) -> None:
        from dataclasses import replace

        spec = replace(get_tool("date_convert"), page="collections:OrderedDict")
        import collections

        self.assertIs(load_page_class(spec), collections.OrderedDict)


class LayoutTests(unittest.TestCase):
    def test_layout_breakpoints(self) -> None:
        cases = [
            (1100, LayoutMode.WIDE),
            (1099, LayoutMode.MEDIUM),
            (750, LayoutMode.MEDIUM),
            (749, LayoutMode.NARROW),
            (640, LayoutMode.NARROW),
        ]
        for width, mode in cases:
            with self.subTest(width=width):
                self.assertIs(layout_mode_for_width(width), mode)
        self.assertEqual(MIN_WINDOW_WIDTH, 640)


class ThemeTests(unittest.TestCase):
    def test_apply_theme_mode_unknown_falls_back_to_auto(self) -> None:
        qapp()
        self.assertIs(apply_theme_mode("bogus"), Theme.AUTO)

    def test_apply_theme_mode_known(self) -> None:
        qapp()
        self.assertIs(apply_theme_mode("dark"), Theme.DARK)
        self.assertIs(apply_theme_mode("light"), Theme.LIGHT)
        self.assertIs(apply_theme_mode("auto"), Theme.AUTO)


if __name__ == "__main__":
    unittest.main()
