from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PySide6.QtWidgets import QLineEdit

from dataforge.core.result import Result
from dataforge.fileio import paths as paths_module
from dataforge.ui.components.file_input import FileInputCard
from dataforge.ui.components.responsive_form import ResponsiveForm
from dataforge.ui.components.result_panel import ResultPanel
from dataforge.ui.components.run_bar import RunBar
from tests.dataforge.qt_helpers import qapp


def _pos(form: ResponsiveForm, widget) -> tuple[int, int]:
    row, col, _, _ = form.layout().getItemPosition(form.layout().indexOf(widget))
    return row, col


class ComponentTests(unittest.TestCase):
    def setUp(self) -> None:
        qapp()

    def test_form_compact_moves_label_above(self) -> None:
        form = ResponsiveForm()
        field = QLineEdit()
        form.add_row("名称", field, hint="提示")
        label = form._rows[0][0]
        lr, lc = _pos(form, label)
        fr, fc = _pos(form, field)
        self.assertEqual(fr, lr)
        self.assertNotEqual(fc, lc)
        form.set_compact(True)
        self.assertTrue(form.is_compact())
        lr, lc = _pos(form, label)
        fr, fc = _pos(form, field)
        self.assertEqual(fr, lr + 1)
        self.assertEqual(fc, lc)
        form.set_compact(False)
        lr, lc = _pos(form, label)
        fr, fc = _pos(form, field)
        self.assertEqual((fr, fc), (lr, lc + 1))

    def test_file_card_filters_and_dedupes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for n in ["a.xlsx", "~$b.xlsx", "n.txt"]:
                (root / n).write_text("x")
            card = FileInputCard("输入", (".xlsx",))
            emitted: list[list] = []
            card.files_changed.connect(emitted.append)
            card.set_files([root / "a.xlsx", root / "a.xlsx", root / "~$b.xlsx", root / "n.txt"])
            self.assertEqual(card.files(), [root / "a.xlsx"])
            self.assertEqual(len(emitted), 1)
            card.set_files([root / "a.xlsx"])
            self.assertEqual(len(emitted), 1)
            card._add([root])
            self.assertEqual(len(emitted), 1)
            card.clear()
            self.assertEqual(card.files(), [])
            self.assertEqual(len(emitted), 2)

    def test_file_card_skips_unreadable_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            good = root / "a.xlsx"
            good.write_text("x")
            bad = root / "locked"
            card = FileInputCard("输入", (".xlsx",))
            real = paths_module.iter_input_files

            def fake(paths, extensions, recursive=False):
                if Path(list(paths)[0]) == bad:
                    raise PermissionError("denied")
                return real(paths, extensions, recursive)

            with mock.patch("dataforge.ui.components.file_input.iter_input_files", fake):
                with self.assertLogs("dataforge.ui.components.file_input", "WARNING"):
                    card.set_files([bad, good])
            self.assertEqual(card.files(), [good])

    def test_run_bar_running_state(self) -> None:
        bar = RunBar()
        bar.set_running(True)
        self.assertFalse(bar._primary.isEnabled())
        self.assertTrue(bar._cancel.isEnabled())
        self.assertFalse(bar._bar.isHidden())
        bar.set_progress(0, 0, "处理中")
        self.assertTrue(bar._bar.isHidden())
        self.assertFalse(bar._indeterminate.isHidden())
        bar.set_progress(1, 4, "处理中")
        self.assertFalse(bar._bar.isHidden())
        self.assertTrue(bar._indeterminate.isHidden())
        bar.set_running(False)
        self.assertTrue(bar._primary.isEnabled())
        self.assertTrue(bar._bar.isHidden())
        bar.set_blocked("格式转换 正在运行")
        self.assertFalse(bar._primary.isEnabled())
        self.assertIn("格式转换 正在运行", bar._reason.text())
        bar.set_blocked(None)
        self.assertTrue(bar._primary.isEnabled())

    def test_result_panel_counts(self) -> None:
        panel = ResultPanel()
        result = Result(outputs=[Path("a.csv"), Path("b.csv")], stats={"rows": 3})
        result.warn("w.xlsx", "空表")
        result.fail("f.xlsx", "无法读取")
        panel.show_result(result)
        self.assertIn("(2)", panel._tabs.items["warnings"].text())
        self.assertIn("(2)", panel._tabs.items["result"].text())
        self.assertEqual(panel.summary_text(), "2 个输出 · 2 个问题")
        self.assertEqual(
            panel._edits["warnings"].toPlainText(), "w.xlsx: 空表\nf.xlsx: 无法读取"
        )
        self.assertIn("rows: 3", panel._edits["result"].toPlainText())
        panel.append_log("hello")
        self.assertIn("hello", panel._edits["log"].toPlainText())
        panel.set_collapsed(True)
        self.assertTrue(panel._stack.isHidden())
        self.assertFalse(panel._summary.isHidden())
        panel._summary.click()
        self.assertFalse(panel._stack.isHidden())
        panel.clear()
        self.assertEqual(panel.summary_text(), "0 个输出 · 0 个问题")


if __name__ == "__main__":
    unittest.main()
