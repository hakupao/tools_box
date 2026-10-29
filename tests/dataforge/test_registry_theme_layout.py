from __future__ import annotations

import unittest
from unittest import mock

from PySide6.QtCore import QCoreApplication, QObject
from qfluentwidgets import PushButton, Theme, isDarkTheme

from dataforge.ui.layout import MIN_WINDOW_WIDTH, LayoutMode, layout_mode_for_width
from dataforge.ui.registry import TOOLS, ToolGroup, get_tool, load_page_class
from dataforge.ui.theme import apply_theme_mode, start_system_theme_listener

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


class PageImportTests(unittest.TestCase):
    def test_every_page_importable(self) -> None:
        for spec in TOOLS:
            with self.subTest(tool=spec.id):
                self.assertTrue(isinstance(load_page_class(spec), type))


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

    def test_system_theme_change_restyles_widgets(self) -> None:
        qapp()
        with mock.patch("darkdetect.theme", return_value="Light"):
            apply_theme_mode("auto")
            btn = PushButton("x")
            btn.show()
            QCoreApplication.processEvents()
            before = btn.styleSheet()
            self.assertFalse(isDarkTheme())
            parent = QObject()
            listener = start_system_theme_listener(parent)
            listener.terminate()
            listener.wait()
            with mock.patch("darkdetect.theme", return_value="Dark"):
                listener._onThemeChanged("dark")
                QCoreApplication.processEvents()
                self.assertTrue(isDarkTheme())
                self.assertNotEqual(btn.styleSheet(), before)
            btn.close()
        apply_theme_mode("auto")

    def test_system_theme_change_ignored_in_fixed_mode(self) -> None:
        qapp()
        apply_theme_mode("light")
        parent = QObject()
        bridge_calls: list[int] = []
        with mock.patch("dataforge.ui.theme.setTheme") as st:
            listener = start_system_theme_listener(parent)
            listener.terminate()
            listener.wait()
            listener.systemThemeChanged.emit()
            QCoreApplication.processEvents()
            bridge_calls.append(st.call_count)
        self.assertEqual(bridge_calls, [0])
        apply_theme_mode("auto")


if __name__ == "__main__":
    unittest.main()
