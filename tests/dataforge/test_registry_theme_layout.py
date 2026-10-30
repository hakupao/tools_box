from __future__ import annotations

import unittest
from pathlib import Path
from unittest import mock

from PySide6.QtCore import QCoreApplication, QObject
from qfluentwidgets import FluentIcon, PushButton, Theme, isDarkTheme, qconfig, setTheme

from dataforge.ui.layout import MIN_WINDOW_WIDTH, LayoutMode, layout_mode_for_width
from dataforge.ui.registry import TOOLS, ToolGroup, get_tool, load_page_class
from dataforge.ui.theme import apply_theme_mode, start_system_theme_listener

from .qt_helpers import qapp, wait_until


class RegistryTests(unittest.TestCase):
    def test_ids_unique(self) -> None:
        ids = [t.id for t in TOOLS]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(
            ids,
            [
                "format_convert",
                "sheet_split",
                "field_extract",
                "masking",
                "edc",
                "date_convert",
                "width_convert",
            ],
        )

    def test_files_group_order(self) -> None:
        files = [t.id for t in TOOLS if t.group is ToolGroup.FILES]
        self.assertEqual(files, ["format_convert", "sheet_split", "field_extract"])

    def test_business_group(self) -> None:
        business = [t for t in TOOLS if t.group is ToolGroup.BUSINESS]
        self.assertEqual([t.id for t in business], ["masking", "edc"])
        spec = business[0]
        self.assertEqual(spec.name, "数据模糊化")
        self.assertEqual(spec.description, "SDTM Pattern1：扫描 → 配置 → 执行")
        self.assertIs(spec.icon, FluentIcon.HIDE)
        self.assertEqual(spec.page, "dataforge.ui.pages.masking.page:MaskingPage")
        edc = business[1]
        self.assertEqual(edc.name, "EDC 站点添加")
        self.assertEqual(edc.description, "录制点击位置，从 Excel 逐行回放")
        self.assertIs(edc.icon, FluentIcon.ROBOT)
        self.assertEqual(edc.page, "dataforge.ui.pages.edc.page:EdcPage")

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

    def tearDown(self) -> None:
        setTheme(Theme.AUTO)

    def _watcher(self, watch):
        parent = QObject()
        self.addCleanup(parent.deleteLater)
        watcher = start_system_theme_listener(parent, watch=watch)
        return watcher

    def test_watcher_applies_system_dark(self) -> None:
        qapp()
        with mock.patch("darkdetect.theme", return_value="Dark"):
            with mock.patch("darkdetect.theme", return_value="Light"):
                setTheme(Theme.LIGHT)
                setTheme(Theme.AUTO)
            self.assertFalse(isDarkTheme())
            btn = PushButton("x")
            btn.show()
            QCoreApplication.processEvents()
            before = btn.styleSheet()
            self._watcher(lambda cb: cb("Dark"))
            wait_until(isDarkTheme)
            QCoreApplication.processEvents()
            self.assertNotEqual(btn.styleSheet(), before)
            btn.close()

    def test_watcher_emits_theme_changed(self) -> None:
        qapp()
        with mock.patch("darkdetect.theme", return_value="Light"):
            setTheme(Theme.LIGHT)
            setTheme(Theme.AUTO)
        got: list[Theme] = []
        qconfig.themeChanged.connect(got.append)
        self.addCleanup(qconfig.themeChanged.disconnect, got.append)
        with mock.patch("darkdetect.theme", return_value="Dark"):
            self._watcher(lambda cb: cb("Dark"))
            wait_until(lambda: bool(got))
        self.assertEqual(got, [Theme.AUTO])

    def test_watcher_unchanged_theme_does_not_emit(self) -> None:
        qapp()
        called: list[str] = []
        with mock.patch("darkdetect.theme", return_value="Light"):
            setTheme(Theme.LIGHT)
            setTheme(Theme.AUTO)
            got: list[Theme] = []
            qconfig.themeChanged.connect(got.append)
            self.addCleanup(qconfig.themeChanged.disconnect, got.append)
            self._watcher(lambda cb: (cb("Light"), called.append("x")))
            wait_until(lambda: bool(called))
            for _ in range(5):
                QCoreApplication.processEvents()
        self.assertEqual(got, [])

    def test_watcher_ignored_in_fixed_mode(self) -> None:
        qapp()
        setTheme(Theme.LIGHT)
        called: list[str] = []
        with mock.patch("darkdetect.theme", return_value="Dark"):
            watcher = self._watcher(lambda cb: (cb("Dark"), called.append("x")))
            wait_until(lambda: bool(called))
            for _ in range(5):
                QCoreApplication.processEvents()
            self.assertFalse(isDarkTheme())
        self.assertIsNotNone(watcher)

    def test_watch_exception_does_not_crash(self) -> None:
        qapp()

        def boom(cb):
            raise RuntimeError("no listener")

        with self.assertLogs("dataforge.ui.theme", "ERROR"):
            watcher = self._watcher(boom)
            watcher._thread.join(5)
        self.assertFalse(watcher._thread.is_alive())

    def test_theme_module_has_no_terminate(self) -> None:
        root = Path(__file__).resolve().parents[2] / "src" / "dataforge"
        for rel in ("ui/theme.py", "app.py"):
            self.assertNotIn("terminate(", (root / rel).read_text(encoding="utf-8"), rel)


if __name__ == "__main__":
    unittest.main()
