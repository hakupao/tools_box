from __future__ import annotations

import unittest

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QBoxLayout

from dataforge.dates import to_iso8601
from dataforge.tools.date_convert import convert_text
from dataforge.ui.jobs import JobRunner
from dataforge.ui.registry import get_tool, load_page_class

from .qt_helpers import qapp

CASES = [
    ("2021/2/3", "2021-02-03"), ("2020/02/29", "2020-02-29"),
    ("2021/02/31", "2021-02"),
    ("2010/99/99", "2010"), ("2010/10/99", "2010-10"), ("2010/10", "2010-10"),
    (" 2010/1 ", "2010-01"), ("", ""), ("abc", "abc"), ("2010", "2010"),
    ("999/01/01", "999/01/01"), ("2010/10/ab", "2010/10/ab"), ("2010/", "2010/"),
    ("2010/1/2/3", "2010/1/2/3"),
    ("2010/99/ab", "2010"), ("2010/99/", "2010"), ("2010/99/1/2", "2010"),
    ("2010/13/x/y", "2010"),
]


class DatesTests(unittest.TestCase):
    def test_to_iso8601_cases(self) -> None:
        for raw, want in CASES:
            with self.subTest(raw=raw):
                self.assertEqual(to_iso8601(raw), want)

    def test_convert_text_lines(self) -> None:
        self.assertEqual(convert_text("2021/2/3\n\nabc"), "2021-02-03\n\nabc")


class DateConvertPageTests(unittest.TestCase):
    def _page(self):
        qapp()
        spec = get_tool("date_convert")
        return load_page_class(spec)(spec, JobRunner())

    def test_convert_fills_result(self) -> None:
        page = self._page()
        page.input_edit.setPlainText("2021/2/3\nabc")
        page.convert_button.click()
        self.assertEqual(page.result_edit.toPlainText(), "2021-02-03\nabc")
        self.assertTrue(page.result_edit.isReadOnly())

    def test_copy_puts_result_on_clipboard(self) -> None:
        page = self._page()
        page.input_edit.setPlainText("2021/2/3")
        page.convert_button.click()
        page.copy_button.click()
        self.assertEqual(QGuiApplication.clipboard().text(), "2021-02-03")

    def test_copy_empty_does_not_touch_clipboard(self) -> None:
        page = self._page()
        QGuiApplication.clipboard().setText("keep")
        page.copy_button.click()
        self.assertEqual(QGuiApplication.clipboard().text(), "keep")

    def test_orientation_switch_keeps_widgets(self) -> None:
        page = self._page()
        inp, res = page.input_edit, page.result_edit
        page.apply_layout_width(1200)
        self.assertEqual(page.body_layout.direction(), QBoxLayout.Direction.LeftToRight)
        page.apply_layout_width(700)
        self.assertEqual(page.body_layout.direction(), QBoxLayout.Direction.TopToBottom)
        page.apply_layout_width(800)
        self.assertEqual(page.body_layout.direction(), QBoxLayout.Direction.LeftToRight)
        self.assertIs(page.input_edit, inp)
        self.assertIs(page.result_edit, res)

    def test_restore_state(self) -> None:
        self.assertEqual(self._page().restore_state({}), [])


if __name__ == "__main__":
    unittest.main()
