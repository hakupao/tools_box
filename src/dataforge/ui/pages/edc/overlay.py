"""Recording overlay bar and replay flash markers for the EDC site adder.

The system hooks emit Qt signals from their own thread; every slot here runs on the main
thread. Colours are fixed ``QColor`` values (no stylesheets).
"""
from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import QPoint, QRect, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFontMetrics, QGuiApplication, QPainter, QPalette, QPen
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget
from qfluentwidgets import PrimaryPushButton, PushButton

from dataforge.ui.pages.edc.hooks import EscHook, MouseClickHook

BAR_HEIGHT = 60
REPLAY_INTERVAL_MS = 600
REPLAY_VISIBLE_MS = 1500
MARKER_RADIUS = 20


def physical_to_logical(x: int, y: int) -> QPoint:
    """Convert a physical-pixel screen point (mouse hook) to Qt logical coordinates."""
    for s in QGuiApplication.screens():
        g = s.geometry()
        d = s.devicePixelRatio()
        physical = QRect(g.x(), g.y(), round(g.width() * d), round(g.height() * d))
        if physical.contains(x, y):
            return QPoint(g.x() + round((x - g.x()) / d), g.y() + round((y - g.y()) / d))
    primary = QGuiApplication.primaryScreen()
    d = primary.devicePixelRatio() if primary is not None else 1.0
    return QPoint(round(x / d), round(y / d))


class RecordingOverlay(QWidget):
    captured = Signal(str, int, int)
    finished = Signal()
    cancelled = Signal()

    def __init__(
        self, steps: Sequence[str], mouse_hook: MouseClickHook, esc_hook: EscHook
    ) -> None:
        super().__init__(None)
        self._steps = list(steps)
        self._mouse_hook = mouse_hook
        self._esc_hook = esc_hook
        self._index = 0
        self._recording = False
        self._done = False
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self._label = QLabel(self)
        palette = self._label.palette()
        palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
        self._label.setPalette(palette)
        self._start_btn = PrimaryPushButton("开始", self)
        self._cancel_btn = PushButton("取消（ESC）", self)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.addWidget(self._label, 1)
        layout.addWidget(self._start_btn)
        layout.addWidget(self._cancel_btn)
        self._label.setText(f"请切换到 EDC 页面，准备好后点击「开始」（共 {len(self._steps)} 步）")

        self._start_btn.clicked.connect(self._on_start)
        self._cancel_btn.clicked.connect(self._cancel)
        self._esc_hook.pressed.connect(self._cancel)
        self._mouse_hook.clicked.connect(self._on_click)

        screen = QGuiApplication.primaryScreen()
        if screen is not None:
            area = screen.availableGeometry()
            self.setGeometry(area.x(), area.y(), area.width(), BAR_HEIGHT)
        else:
            self.setGeometry(0, 0, 800, BAR_HEIGHT)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(15, 23, 42, 210))
        painter.end()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        if not self._done:
            self._esc_hook.start()

    def closeEvent(self, event) -> None:  # noqa: N802
        self._done = True
        self._stop_hooks()
        super().closeEvent(event)

    def _stop_hooks(self) -> None:
        self._mouse_hook.stop()
        self._esc_hook.stop()

    def _on_start(self) -> None:
        if self._recording or self._done or not self._steps:
            return
        self._recording = True
        self._start_btn.hide()
        self._show_prompt()
        QTimer.singleShot(300, self._start_mouse)

    def _start_mouse(self) -> None:
        if self._done or not self.isVisible():
            return
        self._mouse_hook.start()

    def _show_prompt(self) -> None:
        n = len(self._steps)
        self._label.setText(f"请点击【{self._steps[self._index]}】（{self._index + 1}/{n}）")

    def _on_click(self, x: int, y: int) -> None:
        if not self._recording or self._done:
            return
        p = physical_to_logical(x, y)
        if self.geometry().adjusted(0, 0, 0, 10).contains(p):
            return
        key = self._steps[self._index]
        self.captured.emit(key, x, y)
        self._index += 1
        if self._index >= len(self._steps):
            self._done = True
            self._stop_hooks()
            self.finished.emit()
            self.close()
        else:
            self._show_prompt()

    def _cancel(self) -> None:
        if self._done:
            return
        self._done = True
        self._stop_hooks()
        self.cancelled.emit()
        self.close()


class FlashMarker(QWidget):
    def __init__(self, label: str, x: int, y: int) -> None:
        super().__init__(None)
        self._text = label
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        fm = QFontMetrics(self.font())
        text_w = fm.horizontalAdvance(label)
        width = max(2 * MARKER_RADIUS + 4, text_w + 12)
        height = 2 * MARKER_RADIUS + 4 + fm.height() + 2
        self._cx = width // 2
        self._cy = MARKER_RADIUS + 2
        self.resize(width, height)
        p = physical_to_logical(x, y)
        self.move(p.x() - self._cx, p.y() - self._cy)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(255, 255, 255, 220), 2))
        painter.setBrush(QColor(220, 38, 38, 180))
        r = MARKER_RADIUS
        painter.drawEllipse(QPoint(self._cx, self._cy), r, r)
        painter.drawLine(self._cx - r, self._cy, self._cx + r, self._cy)
        painter.drawLine(self._cx, self._cy - r, self._cx, self._cy + r)
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(
            QRect(0, 2 * r + 4, self.width(), self.height() - 2 * r - 4),
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
            self._text,
        )
        painter.end()


def schedule_replay(points: Sequence[tuple[str, int, int]]) -> list[FlashMarker]:
    markers: list[FlashMarker] = []
    for i, (label, x, y) in enumerate(points):
        marker = FlashMarker(label, x, y)
        markers.append(marker)
        QTimer.singleShot(i * REPLAY_INTERVAL_MS, marker.show)
        QTimer.singleShot(i * REPLAY_INTERVAL_MS + REPLAY_VISIBLE_MS, marker.close)
    return markers
