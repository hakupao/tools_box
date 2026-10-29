from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PySide6.QtCore import QMimeData, QPointF, Qt, QUrl
from PySide6.QtGui import QDropEvent
from PySide6.QtWidgets import QLineEdit
from qfluentwidgets import BodyLabel, CaptionLabel, IndeterminateProgressBar, ListWidget, PushButton

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


def _labels(form: ResponsiveForm) -> dict[str, BodyLabel]:
    return {w.text(): w for w in form.findChildren(BodyLabel)}


def _drop_event(paths: list[Path]) -> QDropEvent:
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(p)) for p in paths])
    event = QDropEvent(
        QPointF(5, 5),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    event._mime = mime  # keep the mime data alive for the event's lifetime
    return event


class ComponentTests(unittest.TestCase):
    def setUp(self) -> None:
        qapp()

    def test_form_compact_moves_label_above(self) -> None:
        form = ResponsiveForm()
        field = QLineEdit()
        form.add_row("名称", field, hint="提示")
        label = _labels(form)["名称"]
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

    def test_form_repeated_toggles_and_two_rows(self) -> None:
        form = ResponsiveForm()
        f1, f2 = QLineEdit(), QLineEdit()
        form.add_row("甲", f1, hint="提示甲")
        form.add_row("乙", f2)
        labels = _labels(form)
        hint = next(w for w in form.findChildren(CaptionLabel) if w.text() == "提示甲")
        for i in range(6):
            compact = i % 2 == 0
            form.set_compact(compact)
            lay = form.layout()
            self.assertEqual(lay.count(), 5)
            items = [lay.itemAt(n).widget() for n in range(lay.count())]
            self.assertEqual(len({id(w) for w in items}), 5)
            r_l1, c_l1 = _pos(form, labels["甲"])
            r_f1, c_f1 = _pos(form, f1)
            r_h, c_h = _pos(form, hint)
            r_l2, c_l2 = _pos(form, labels["乙"])
            r_f2, c_f2 = _pos(form, f2)
            if compact:
                self.assertEqual([r_l1, r_f1, r_h, r_l2, r_f2], [0, 1, 2, 3, 4])
                self.assertEqual({c_l1, c_f1, c_h, c_l2, c_f2}, {0})
            else:
                self.assertEqual([r_l1, r_f1, r_h, r_l2, r_f2], [0, 0, 1, 2, 2])
                self.assertEqual([c_l1, c_f1, c_h, c_l2, c_f2], [0, 1, 1, 0, 1])

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
            card.add_paths([root])
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

    def test_file_card_drop_files_and_folder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.xlsx").write_text("x")
            folder = root / "sub"
            folder.mkdir()
            (folder / "b.xlsx").write_text("x")
            (folder / "c.txt").write_text("x")
            card = FileInputCard("输入", (".xlsx",))
            emitted: list[list] = []
            card.files_changed.connect(emitted.append)
            card.dropEvent(_drop_event([root / "a.xlsx", folder]))
            self.assertEqual(card.files(), [root / "a.xlsx", folder / "b.xlsx"])
            self.assertEqual(len(emitted), 1)

    def test_file_card_drop_on_inner_list_reaches_card(self) -> None:
        # Qt (QWidgetWindow) routes a drop to the first widget at or above the
        # one under the cursor that has acceptDrops(); synthetic QDropEvents
        # sent with sendEvent are not routed offscreen, so check that walk.
        card = FileInputCard("输入", (".xlsx",))
        card.show()
        inner = card.findChild(ListWidget)
        target = inner.viewport()
        while target is not card and not target.acceptDrops():
            target = target.parentWidget()
        self.assertIs(target, card)
        card.close()

    def test_file_card_locked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.xlsx").write_text("x")
            card = FileInputCard("输入", (".xlsx",))
            card.set_locked(True)
            self.assertTrue(card.is_locked())
            buttons = card.findChildren(PushButton)
            self.assertEqual(len(buttons), 3)
            self.assertTrue(all(not b.isEnabled() for b in buttons))
            event = _drop_event([root / "a.xlsx"])
            card.dropEvent(event)
            self.assertFalse(event.isAccepted())
            self.assertEqual(card.files(), [])
            card.set_locked(False)
            self.assertTrue(all(b.isEnabled() for b in buttons))

    def test_run_bar_running_state(self) -> None:
        bar = RunBar()
        bar.set_running(True)
        self.assertFalse(bar.primary_button().isEnabled())
        self.assertTrue(bar.cancel_button().isEnabled())
        self.assertFalse(bar.progress_bar().isHidden())
        bar.set_progress(0, 0, "处理中")
        self.assertTrue(bar.progress_bar().isHidden())
        self.assertFalse(bar.indeterminate_bar().isHidden())
        bar.set_progress(1, 4, "处理中")
        self.assertFalse(bar.progress_bar().isHidden())
        self.assertTrue(bar.indeterminate_bar().isHidden())
        bar.set_running(False)
        self.assertTrue(bar.primary_button().isEnabled())
        self.assertTrue(bar.progress_bar().isHidden())
        bar.set_blocked("格式转换 正在运行")
        self.assertFalse(bar.primary_button().isEnabled())
        self.assertIn("格式转换 正在运行", bar.reason_text())
        bar.set_blocked(None)
        self.assertTrue(bar.primary_button().isEnabled())

    def test_run_bar_indeterminate_not_restarted(self) -> None:
        bar = RunBar()
        bar.set_running(True)
        with mock.patch.object(
            IndeterminateProgressBar,
            "start",
            autospec=True,
            side_effect=IndeterminateProgressBar.start,
        ) as start:
            bar.set_progress(0, 0, "a")
            bar.set_progress(1, 0, "b")
            bar.set_progress(2, 0, "c")
        self.assertEqual(start.call_count, 1)
        self.assertTrue(bar.indeterminate_bar().isStarted())

    def test_result_panel_counts(self) -> None:
        panel = ResultPanel()
        result = Result(outputs=[Path("a.csv"), Path("b.csv")], stats={"rows": 3})
        result.warn("w.xlsx", "空表")
        result.fail("f.xlsx", "无法读取")
        panel.show_result(result)
        self.assertIn("(2)", panel.tab_text("warnings"))
        self.assertIn("(2)", panel.tab_text("result"))
        self.assertEqual(panel.summary_text(), "2 个输出 · 2 个问题")
        self.assertEqual(panel.page_text("warnings"), "w.xlsx: 空表\nf.xlsx: 无法读取")
        self.assertIn("rows: 3", panel.page_text("result"))
        panel.append_log("hello")
        self.assertIn("hello", panel.page_text("log"))
        panel.set_collapsed(True)
        self.assertTrue(panel.is_collapsed())
        self.assertFalse(panel.summary_button().isHidden())
        panel.summary_button().click()
        self.assertFalse(panel.is_collapsed())
        panel.clear()
        self.assertEqual(panel.summary_text(), "0 个输出 · 0 个问题")


if __name__ == "__main__":
    unittest.main()
