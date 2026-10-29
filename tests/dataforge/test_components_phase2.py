from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PySide6.QtCore import QMimeData, QPoint, QPointF, Qt, QUrl
from PySide6.QtGui import QDropEvent
from PySide6.QtWidgets import QWidget

from dataforge.core.result import EncodingQuestion
from tests.dataforge.qt_helpers import qapp


def _drop(widget, paths: list[Path]) -> bool:
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(p)) for p in paths])
    event = QDropEvent(
        QPointF(QPoint(1, 1)), Qt.DropAction.CopyAction, mime,
        Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
    )
    event.setAccepted(False)
    widget.dropEvent(event)
    return event.isAccepted()


class _FakeDialog:
    def __init__(self, script: list[tuple[bool, str, bool]], calls: list[str]) -> None:
        self._script = script
        self._calls = calls
        self._cur: tuple[bool, str, bool] | None = None

    def for_question(self, parent, question):
        self._calls.append(question.path)
        self._cur = self._script[len(self._calls) - 1]
        return self

    def exec(self) -> bool:
        return self._cur[0]

    def chosen(self) -> str:
        return self._cur[1]

    def apply_to_rest(self) -> bool:
        return self._cur[2]


def _questions() -> list[EncodingQuestion]:
    return [
        EncodingQuestion(f"{n}.csv", {"cp932": "a", "gbk": "b"}) for n in ("a", "b", "c")
    ]


class WidgetTests(unittest.TestCase):
    def setUp(self) -> None:
        qapp()
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_output_location_extracted(self) -> None:
        from dataforge.ui.components.output_location import OutputLocationField

        field = OutputLocationField()
        self.assertIsNone(field.output_dir())
        patch = "dataforge.ui.components.output_location.QFileDialog.getExistingDirectory"
        with mock.patch(patch, return_value=str(self.dir)):
            field.combo.setCurrentIndex(1)
        self.assertEqual(field.output_dir(), self.dir)
        self.assertEqual(field.path_label.text(), str(self.dir))
        with mock.patch(patch, return_value=""):
            field.combo.setCurrentIndex(0)
            field.combo.setCurrentIndex(1)
        self.assertEqual(field.combo.currentIndex(), 0)
        self.assertIsNone(field.output_dir())
        field.set_output_dir(self.dir)
        self.assertEqual(field.combo.currentIndex(), 1)
        self.assertEqual(field.output_dir(), self.dir)
        field.setEnabled(False)
        self.assertFalse(field.combo.isEnabled())

    def test_folder_picker_drop_and_lock(self) -> None:
        from dataforge.ui.components.folder_picker import FolderPicker

        picker = FolderPicker()
        got: list = []
        picker.folder_changed.connect(got.append)
        sub = self.dir / "sub"
        sub.mkdir()
        self.assertTrue(_drop(picker, [sub]))
        self.assertEqual(picker.folder(), sub)
        self.assertEqual(got, [sub])
        f = self.dir / "x.txt"
        f.write_text("x")
        self.assertFalse(_drop(picker, [f]))
        self.assertFalse(_drop(picker, [sub, self.dir]))
        picker.set_locked(True)
        other = self.dir / "other"
        other.mkdir()
        self.assertFalse(_drop(picker, [other]))
        self.assertEqual(picker.folder(), sub)
        patch = "dataforge.ui.components.folder_picker.QFileDialog.getExistingDirectory"
        picker.set_locked(False)
        with mock.patch(patch, return_value=str(other)):
            picker._button.click()
        self.assertEqual(picker.folder(), other)
        picker.set_folder(None)
        self.assertIsNone(picker.folder())

    def test_encoding_field_values(self) -> None:
        from dataforge.ui.components.encoding_field import EncodingField

        field = EncodingField()
        labels = [field.itemText(i) for i in range(field.count())]
        self.assertEqual(labels, ["自动识别", "UTF-8", "UTF-8 (BOM)", "日文 (cp932)", "中文 (GBK)"])
        values = []
        for i in range(field.count()):
            field.setCurrentIndex(i)
            values.append(field.encoding())
        self.assertEqual(values, [None, "utf-8", "utf-8-sig", "cp932", "gbk"])
        field.set_encoding("gbk")
        self.assertEqual(field.currentIndex(), 4)
        field.set_encoding(None)
        self.assertEqual(field.currentIndex(), 0)

    def test_dialog_defaults(self) -> None:
        from dataforge.ui.components.encoding_dialog import EncodingChoiceDialog

        q = EncodingQuestion("d/a.csv", {"cp932": "日本", "gbk": "中文"})
        host = QWidget()
        host.resize(800, 600)
        dlg = EncodingChoiceDialog(host, q)
        self.assertEqual(dlg.chosen(), "cp932")
        self.assertFalse(dlg.apply_to_rest())
        dlg._radios["gbk"].setChecked(True)
        dlg._rest.setChecked(True)
        self.assertEqual(dlg.chosen(), "gbk")
        self.assertTrue(dlg.apply_to_rest())

    def test_ask_encodings_apply_to_rest(self) -> None:
        from dataforge.ui.components.encoding_dialog import ask_encodings

        calls: list[str] = []
        fake = _FakeDialog([(True, "gbk", True)], calls)
        answers = ask_encodings(None, _questions(), fake.for_question)
        self.assertEqual(calls, ["a.csv"])
        self.assertEqual(answers, {"a.csv": "gbk", "b.csv": "gbk", "c.csv": "gbk"})

    def test_ask_encodings_cancel_stops(self) -> None:
        from dataforge.ui.components.encoding_dialog import ask_encodings

        calls: list[str] = []
        fake = _FakeDialog([(True, "cp932", False), (False, "", False)], calls)
        answers = ask_encodings(None, _questions(), fake.for_question)
        self.assertEqual(calls, ["a.csv", "b.csv"])
        self.assertEqual(answers, {"a.csv": "cp932"})


if __name__ == "__main__":
    unittest.main()
