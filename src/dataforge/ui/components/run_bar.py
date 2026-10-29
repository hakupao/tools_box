"""Start/cancel buttons plus progress display."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import (
    CaptionLabel,
    IndeterminateProgressBar,
    PrimaryPushButton,
    ProgressBar,
    PushButton,
)


class RunBar(QWidget):
    start_requested = Signal()
    cancel_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._running = False
        self._blocked = False
        self._primary = PrimaryPushButton("开始", self)
        self._cancel = PushButton("取消", self)
        self._reason = CaptionLabel("", self)
        self._label = CaptionLabel("", self)
        self._bar = ProgressBar(self)
        self._indeterminate = IndeterminateProgressBar(self, start=False)

        top = QHBoxLayout()
        top.addWidget(self._primary)
        top.addWidget(self._cancel)
        top.addWidget(self._reason, 1)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(top)
        layout.addWidget(self._label)
        layout.addWidget(self._bar)
        layout.addWidget(self._indeterminate)

        self._primary.clicked.connect(self.start_requested)
        self._cancel.clicked.connect(self.cancel_requested)
        self._reason.setVisible(False)
        self.set_running(False)

    def set_primary_text(self, text: str) -> None:
        self._primary.setText(text)

    def set_running(self, running: bool) -> None:
        self._running = running
        self._cancel.setEnabled(running)
        self._label.setVisible(running)
        self._bar.setVisible(running)
        self._indeterminate.setVisible(False)
        if not running:
            self._indeterminate.stop()
            self._bar.setValue(0)
            self._label.setText("")
        self._refresh_primary()

    def set_progress(self, current: int, total: int, label: str) -> None:
        self._label.setText(label)
        if total <= 0:
            self._bar.setVisible(False)
            self._indeterminate.setVisible(self._running)
            if self._running:
                self._indeterminate.start()
        else:
            self._indeterminate.stop()
            self._indeterminate.setVisible(False)
            self._bar.setVisible(self._running)
            self._bar.setRange(0, total)
            self._bar.setValue(min(max(current, 0), total))

    def set_blocked(self, reason: str | None) -> None:
        self._blocked = reason is not None
        self._reason.setText(reason or "")
        self._reason.setVisible(self._blocked)
        self._refresh_primary()

    def _refresh_primary(self) -> None:
        self._primary.setEnabled(not self._running and not self._blocked)
