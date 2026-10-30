from __future__ import annotations

import unittest

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QVBoxLayout, QWidget
from qfluentwidgets import CompactSpinBox, DoubleSpinBox, SpinBox

from tests.dataforge.qt_helpers import drain_deleted, qapp


class FluentSpinBoxEditFieldTests(unittest.TestCase):
    """PySide6 6.11.3 / 6.12.0 give a stylesheet spin box with NoButtons a 1 px edit field.

    qfluentwidgets spin boxes use exactly that combination, so the value is invisible there.
    requirements.txt caps PySide6 below 6.11.3; this test catches a lifted cap.
    """

    def test_edit_field_is_wide_enough_to_show_the_value(self) -> None:
        qapp()
        host = QWidget()
        layout = QVBoxLayout(host)
        boxes = [SpinBox(host), CompactSpinBox(host), DoubleSpinBox(host)]
        for box in boxes:
            box.setRange(0, 9999)
            box.setValue(241)
            layout.addWidget(box)
        host.resize(300, 200)
        host.show()
        QCoreApplication.sendPostedEvents()
        try:
            for box in boxes:
                with self.subTest(type(box).__name__):
                    self.assertTrue(box.lineEdit().text().startswith("241"))
                    self.assertGreater(box.lineEdit().width(), 20)
        finally:
            host.hide()
            drain_deleted(host)


if __name__ == "__main__":
    unittest.main()
