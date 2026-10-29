"""Date conversion page: a simplified instant tool (no file jobs)."""
from __future__ import annotations

from typing import Any

from PySide6.QtGui import QGuiApplication, QResizeEvent
from PySide6.QtWidgets import QBoxLayout, QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import (
    CaptionLabel,
    InfoBar,
    InfoBarPosition,
    PlainTextEdit,
    PrimaryPushButton,
    PushButton,
    TitleLabel,
)

from dataforge.tools.date_convert import convert_text
from dataforge.ui.jobs import JobRunner
from dataforge.ui.layout import LayoutMode, layout_mode_for_width
from dataforge.ui.registry import ToolSpec


class DateConvertPage(QWidget):
    """Input and result editors side by side (wide) or stacked (narrow)."""

    def __init__(self, spec: ToolSpec, runner: JobRunner, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.spec = spec
        self.runner = runner  # unused: instant tool, kept for uniform construction
        self.setObjectName(spec.id)

        self.input_edit = PlainTextEdit(self)
        self.input_edit.setPlaceholderText("每行一个日期，例如 2021/2/3")
        self.result_edit = PlainTextEdit(self)
        self.result_edit.setReadOnly(True)
        self.result_edit.setPlaceholderText("转换结果")

        self.convert_button = PrimaryPushButton("转换", self)
        self.copy_button = PushButton("复制结果", self)
        self.convert_button.clicked.connect(self._on_convert)
        self.copy_button.clicked.connect(self._on_copy)

        self.body_layout = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        self.body_layout.setSpacing(12)
        self.body_layout.addLayout(self._column("输入", self.input_edit), 1)
        self.body_layout.addLayout(self._column("结果", self.result_edit), 1)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(self.copy_button)
        buttons.addWidget(self.convert_button)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 16, 24, 16)
        root.setSpacing(12)
        root.addWidget(TitleLabel(spec.name, self))
        root.addWidget(CaptionLabel(spec.description, self))
        root.addLayout(self.body_layout, 1)
        root.addLayout(buttons)

        self._mode: LayoutMode | None = None
        self.apply_layout_width(self._window_width())

    def _column(self, title: str, edit: PlainTextEdit) -> QVBoxLayout:
        col = QVBoxLayout()
        col.setSpacing(4)
        col.addWidget(CaptionLabel(title, self))
        col.addWidget(edit, 1)
        return col

    def _window_width(self) -> int:
        return self.window().width()

    def apply_layout_width(self, width: int) -> None:
        """Re-evaluate orientation for a window width; widgets are never recreated."""
        mode = layout_mode_for_width(width)
        if mode is self._mode:
            return
        self._mode = mode
        direction = (
            QBoxLayout.Direction.TopToBottom
            if mode is LayoutMode.NARROW
            else QBoxLayout.Direction.LeftToRight
        )
        self.body_layout.setDirection(direction)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self.apply_layout_width(self._window_width())

    def restore_state(self, state: dict[str, Any]) -> list[str]:
        return []

    def _on_convert(self) -> None:
        self.result_edit.setPlainText(convert_text(self.input_edit.toPlainText()))

    def _on_copy(self) -> None:
        text = self.result_edit.toPlainText()
        if not text:
            InfoBar.info("没有可复制的内容", "", parent=self, position=InfoBarPosition.TOP, duration=2000)
            return
        QGuiApplication.clipboard().setText(text)
        InfoBar.success("已复制", "", parent=self, position=InfoBarPosition.TOP, duration=2000)
