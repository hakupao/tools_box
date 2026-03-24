from __future__ import annotations

import mouse
import pyautogui
from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath
from PySide6.QtWidgets import QApplication, QHBoxLayout, QLabel, QPushButton, QWidget


_OVERLAY_HEIGHT = 56


class RecordingOverlay(QWidget):
    """Topmost floating bar guiding the user through coordinate recording."""

    coordinate_captured = Signal(str, int, int)  # (step_key, x, y)
    recording_finished = Signal()
    recording_cancelled = Signal()

    def __init__(self, steps: list[str], parent=None) -> None:
        super().__init__(None)
        self._steps = list(steps)
        self._current_index = 0
        self._hook_handle = None
        self._active = False  # guard against processing clicks before ready

        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        screen = QApplication.primaryScreen()
        geo = screen.availableGeometry() if screen else QApplication.primaryScreen().geometry()
        self.setGeometry(geo.x(), geo.y(), geo.width(), _OVERLAY_HEIGHT)

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setSpacing(16)

        self._hint_label = QLabel()
        self._hint_label.setFont(QFont("Microsoft YaHei UI", 13, QFont.Bold))
        self._hint_label.setStyleSheet("color: white;")
        self._hint_label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)

        self._cancel_btn = QPushButton("取消 (ESC)")
        self._cancel_btn.setFixedSize(100, 32)
        self._cancel_btn.setStyleSheet(
            "QPushButton { background: rgba(255,255,255,0.2); color: white; "
            "border: 1px solid rgba(255,255,255,0.4); border-radius: 6px; font-size: 12px; }"
            "QPushButton:hover { background: rgba(255,255,255,0.35); }"
        )
        self._cancel_btn.clicked.connect(self._cancel)

        layout.addWidget(self._hint_label, stretch=1)
        layout.addWidget(self._cancel_btn)

        self._update_hint()

    def _update_hint(self) -> None:
        if self._current_index < len(self._steps):
            key = self._steps[self._current_index]
            n = self._current_index + 1
            total = len(self._steps)
            self._hint_label.setText(f"请点击【{key}】按钮  ({n}/{total})")

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 0, 0)
        painter.fillPath(path, QColor(15, 23, 42, 210))
        painter.end()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        # Delay hook installation so the overlay show itself doesn't
        # trigger a spurious click capture, and Chrome has time to activate.
        QTimer.singleShot(500, self._activate_recording)

    def _activate_recording(self) -> None:
        self._active = True
        self._install_mouse_hook()

    def closeEvent(self, event) -> None:  # noqa: N802
        self._active = False
        self._remove_mouse_hook()
        super().closeEvent(event)

    def _install_mouse_hook(self) -> None:
        self._remove_mouse_hook()
        # mouse.hook gives us every mouse event (move, button, wheel).
        # We filter for left-button DOWN events in the callback.
        self._hook_handle = mouse.hook(self._on_mouse_event)

    def _remove_mouse_hook(self) -> None:
        if self._hook_handle is not None:
            mouse.unhook(self._hook_handle)
            self._hook_handle = None

    def _on_mouse_event(self, event) -> None:
        if not self._active:
            return

        # Only react to left mouse button press
        if not isinstance(event, mouse.ButtonEvent):
            return
        if event.event_type != mouse.DOWN or event.button != mouse.LEFT:
            return

        x, y = pyautogui.position()

        # Ignore clicks on the overlay bar area
        if y < _OVERLAY_HEIGHT + 10:
            return

        if self._current_index >= len(self._steps):
            return

        key = self._steps[self._current_index]
        self.coordinate_captured.emit(key, x, y)
        self._current_index += 1

        if self._current_index >= len(self._steps):
            self._active = False
            self._remove_mouse_hook()
            self.recording_finished.emit()
            QTimer.singleShot(300, self.close)
        else:
            self._update_hint()

    def _cancel(self) -> None:
        self._active = False
        self._remove_mouse_hook()
        self.recording_cancelled.emit()
        self.close()

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() == Qt.Key_Escape:
            self._cancel()
        else:
            super().keyPressEvent(event)


class FlashIndicator(QWidget):
    """Small topmost circle that briefly flashes at a screen coordinate."""

    def __init__(self, x: int, y: int, label: str = "", radius: int = 20) -> None:
        super().__init__(None)
        self._label = label
        self._radius = radius

        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        label_width = max(len(label) * 14, 40)
        total_w = radius * 2 + label_width + 8
        total_h = radius * 2
        self.setGeometry(x - radius, y - radius, total_w, total_h)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Red circle
        r = self._radius
        painter.setBrush(QColor(220, 38, 38, 180))
        painter.setPen(QColor(255, 255, 255, 220))
        painter.drawEllipse(0, 0, r * 2, r * 2)

        # Crosshair
        cx, cy = r, r
        painter.setPen(QColor(255, 255, 255, 200))
        painter.drawLine(cx - 8, cy, cx + 8, cy)
        painter.drawLine(cx, cy - 8, cx, cy + 8)

        # Label
        if self._label:
            painter.setPen(QColor(255, 255, 255))
            font = QFont("Microsoft YaHei UI", 10, QFont.Bold)
            painter.setFont(font)
            painter.drawText(r * 2 + 6, r + 5, self._label)

        painter.end()


def run_replay_test(positions: dict[str, dict[str, int]], step_keys: list[str]) -> list[FlashIndicator]:
    """Show flash indicators at each coordinate in sequence.

    Returns the list of FlashIndicator widgets so the caller can manage their lifetime.
    """
    indicators: list[FlashIndicator] = []
    for idx, key in enumerate(step_keys):
        pos = positions.get(key)
        if not pos:
            continue
        flash = FlashIndicator(pos["x"], pos["y"], label=f"{idx + 1}. {key}")
        delay = idx * 600
        QTimer.singleShot(delay, flash.show)
        QTimer.singleShot(delay + 1500, flash.close)
        indicators.append(flash)
    return indicators
