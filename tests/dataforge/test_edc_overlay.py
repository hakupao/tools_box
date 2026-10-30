from __future__ import annotations

import unittest
from unittest import mock

from PySide6.QtCore import QRect
from PySide6.QtWidgets import QWidget

from dataforge.tools.edc.loop import CellRef, RowStop, StopChoice
from dataforge.tools.edc.windows import WindowInfo
from dataforge.ui.pages.edc import overlay
from dataforge.ui.pages.edc.dialogs import StopDialog, WindowPickerDialog
from dataforge.ui.pages.edc.hooks import EscHook, MouseClickHook
from dataforge.ui.pages.edc.overlay import RecordingOverlay, physical_to_logical, schedule_replay
from tests.dataforge.edc_fakes import FakeKeyboardBackend, FakeMouseBackend
from tests.dataforge.qt_helpers import drain_deleted, qapp


class _FakeScreen:
    def __init__(self, rect: QRect, dpr: float) -> None:
        self._rect, self._dpr = rect, dpr

    def geometry(self) -> QRect:
        return self._rect

    def devicePixelRatio(self) -> float:
        return self._dpr


class _FakeTimer:
    calls: list = []

    @staticmethod
    def singleShot(ms, fn) -> None:
        _FakeTimer.calls.append((ms, fn))


class _ImmediateTimer:
    @staticmethod
    def singleShot(ms, fn) -> None:
        fn()


class CoordinateTests(unittest.TestCase):
    def test_physical_to_logical_identity(self) -> None:
        qapp()
        p = physical_to_logical(120, 340)
        self.assertEqual((p.x(), p.y()), (120, 340))

    def test_physical_to_logical_scaled(self) -> None:
        qapp()
        screen = _FakeScreen(QRect(0, 0, 1280, 720), 1.5)
        with mock.patch.object(overlay.QGuiApplication, "screens", return_value=[screen]):
            p = physical_to_logical(300, 150)
        self.assertEqual((p.x(), p.y()), (200, 100))


class OverlayTests(unittest.TestCase):
    def setUp(self) -> None:
        qapp()
        self.kb = FakeKeyboardBackend()
        self.ms = FakeMouseBackend()
        self.esc = EscHook(backend=self.kb)
        self.mouse = MouseClickHook(backend=self.ms)
        self.overlay = RecordingOverlay(["a", "b", "c"], self.mouse, self.esc)

    def tearDown(self) -> None:
        drain_deleted(self.overlay, self.esc, self.mouse)

    def test_recording_sequence(self) -> None:
        captured, finished = [], []
        self.overlay.captured.connect(lambda k, x, y: captured.append((k, x, y)))
        self.overlay.finished.connect(lambda: finished.append(True))
        self.overlay.show()
        self.assertTrue(self.esc.is_active())
        with mock.patch.object(overlay, "QTimer", _ImmediateTimer):
            self.overlay._start_btn.click()
        self.assertTrue(self.mouse.is_active())
        self.mouse.clicked.emit(5, 20)  # inside the bar
        self.assertEqual(captured, [])
        for x, y in [(100, 300), (200, 400), (300, 500)]:
            self.mouse.clicked.emit(x, y)
        self.assertEqual(captured, [("a", 100, 300), ("b", 200, 400), ("c", 300, 500)])
        self.assertEqual(finished, [True])
        self.assertFalse(self.mouse.is_active())
        self.assertFalse(self.esc.is_active())
        self.assertFalse(self.overlay.isVisible())

    def test_cancel_before_deferred_mouse_start_leaks_no_hook(self) -> None:
        pending = []

        class _Deferred:
            @staticmethod
            def singleShot(ms, fn) -> None:
                pending.append(fn)

        self.overlay.show()
        with mock.patch.object(overlay, "QTimer", _Deferred):
            self.overlay._start_btn.click()
        self.esc.pressed.emit()
        for fn in pending:
            fn()
        self.assertFalse(self.mouse.is_active())
        self.assertEqual(self.ms.hooked, [])

    def test_recording_esc_cancels(self) -> None:
        cancelled = []
        self.overlay.cancelled.connect(lambda: cancelled.append(True))
        self.overlay.show()
        self.esc.pressed.emit()
        self.assertEqual(cancelled, [True])
        self.assertFalse(self.overlay.isVisible())
        self.assertFalse(self.esc.is_active())
        self.assertFalse(self.mouse.is_active())

    def test_overlay_has_no_stylesheet(self) -> None:
        # Fluent buttons install their own theme QSS; ours must set none anywhere else.
        for w in [self.overlay, *self.overlay.findChildren(QWidget)]:
            if type(w).__module__.startswith("qfluentwidgets"):
                continue
            self.assertEqual(w.styleSheet(), "")


class ReplayTests(unittest.TestCase):
    def test_replay_schedule(self) -> None:
        qapp()
        _FakeTimer.calls = []
        with mock.patch.object(overlay, "QTimer", _FakeTimer):
            markers = schedule_replay([("a", 1, 2), ("b", 3, 4), ("c", 5, 6)])
        self.assertEqual(len(markers), 3)
        by_fn: dict[str, list[int]] = {}
        for ms, fn in _FakeTimer.calls:
            by_fn.setdefault(fn.__name__, []).append(ms)
        self.assertEqual(by_fn["show"], [0, 600, 1200])
        self.assertEqual(by_fn["close"], [1500, 2100, 2700])
        drain_deleted(*markers)


class DialogTests(unittest.TestCase):
    def setUp(self) -> None:
        qapp()
        self.parent = QWidget()
        self.parent.resize(800, 600)
        self.stop = RowStop(CellRef("B", "S", 3, 1), "SITE-1", 5, "boom", True)

    def tearDown(self) -> None:
        drain_deleted(self.parent)

    def test_stop_dialog_texts_and_choices(self) -> None:
        d = StopDialog(self.parent, self.stop)
        self.assertEqual(d.title_label.text(), "已停止")
        self.assertIn("A3", d.body_label.text())
        self.assertIn("第 5 步「点击【查找】」", d.body_label.text())
        self.assertIn("boom", d.body_label.text())
        self.assertEqual(d.choice(), StopChoice.END)
        texts = [d.buttonLayout.itemAt(i).widget().text() for i in range(d.buttonLayout.count())
                 if d.buttonLayout.itemAt(i).widget() is not None]
        self.assertEqual(texts, ["重做本行", "跳到下一行", "结束"])
        d.skipButton.click()
        self.assertEqual(d.choice(), StopChoice.SKIP)
        d.yesButton.click()
        self.assertEqual(d.choice(), StopChoice.REDO)
        d.cancelButton.click()
        self.assertEqual(d.choice(), StopChoice.END)
        err = StopDialog(self.parent, RowStop(self.stop.cell, "v", 5, "r", False))
        self.assertEqual(err.title_label.text(), "处理出错")
        drain_deleted(d, err)

    def test_window_picker(self) -> None:
        w1 = WindowInfo(1, "Mail", "outlook.exe")
        w2 = WindowInfo(2, "EDC", "chrome.exe")
        d = WindowPickerDialog(self.parent, [w1, w2], WindowInfo(2, "EDC", "chrome.exe"))
        self.assertEqual(d.list_widget.currentRow(), 1)
        self.assertEqual(d.selected(), w2)
        drain_deleted(d)
        d = WindowPickerDialog(self.parent, [w1, w2], None)
        self.assertFalse(d.yesButton.isEnabled())
        self.assertIsNone(d.selected())
        d.list_widget.setCurrentRow(1)
        self.assertTrue(d.yesButton.isEnabled())
        self.assertEqual(d.selected(), w2)
        drain_deleted(d)


if __name__ == "__main__":
    unittest.main()
