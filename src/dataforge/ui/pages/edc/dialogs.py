"""Dialogs for the EDC site adder: what to do after a row stops, and window picking."""
from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtWidgets import QWidget
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    ListWidget,
    MessageBoxBase,
    PushButton,
    StrongBodyLabel,
)

from dataforge.tools.edc.loop import RowStop, StopChoice
from dataforge.tools.edc.windows import WindowInfo, find_target


class StopDialog(MessageBoxBase):
    def __init__(self, parent: QWidget, stop: RowStop) -> None:
        super().__init__(parent)
        self._choice = StopChoice.END
        self.title_label = StrongBodyLabel("已停止" if stop.by_user else "处理出错", self)
        self.body_label = BodyLabel(
            f"Excel {stop.cell.address()}（{stop.value}）在第 {stop.step} 步"
            f"「{stop.step_name}」停止：{stop.reason}",
            self,
        )
        self.body_label.setWordWrap(True)
        self.note_label = CaptionLabel(
            "重做前请先在 EDC 中确认这一行是否已经添加过，避免重复添加。", self
        )
        self.note_label.setWordWrap(True)
        self.viewLayout.addWidget(self.title_label)
        self.viewLayout.addWidget(self.body_label)
        self.viewLayout.addWidget(self.note_label)
        self.yesButton.setText("重做本行")
        self.cancelButton.setText("结束")
        self.skipButton = PushButton("跳到下一行", self)
        self.buttonLayout.insertWidget(1, self.skipButton)
        self.yesButton.clicked.connect(lambda: self._set(StopChoice.REDO))
        self.skipButton.clicked.connect(self._on_skip)
        self.cancelButton.clicked.connect(lambda: self._set(StopChoice.END))

    def _set(self, choice: StopChoice) -> None:
        self._choice = choice

    def _on_skip(self) -> None:
        self._choice = StopChoice.SKIP
        self.accept()

    def choice(self) -> StopChoice:
        return self._choice


def ask_stop_choice(parent: QWidget, stop: RowStop) -> StopChoice:
    dialog = StopDialog(parent, stop)
    try:
        dialog.exec()
        return dialog.choice()
    finally:
        dialog.deleteLater()


class WindowPickerDialog(MessageBoxBase):
    def __init__(
        self, parent: QWidget, windows: Sequence[WindowInfo], current: WindowInfo | None
    ) -> None:
        super().__init__(parent)
        self._windows = list(windows)
        self.viewLayout.addWidget(StrongBodyLabel("选择目标窗口", self))
        self.list_widget = ListWidget(self)
        for w in self._windows:
            self.list_widget.addItem(f"{w.title} — {w.process}")
        self.viewLayout.addWidget(self.list_widget)
        self.yesButton.setText("确定")
        self.cancelButton.setText("取消")
        self.list_widget.itemSelectionChanged.connect(self._refresh)
        match = find_target(current, self._windows) if current is not None else None
        if match is not None:
            self.list_widget.setCurrentRow(self._windows.index(match))
        self._refresh()

    def _refresh(self, *_: object) -> None:
        self.yesButton.setEnabled(bool(self.list_widget.selectedItems()))

    def selected(self) -> WindowInfo | None:
        items = self.list_widget.selectedItems()
        row = self.list_widget.row(items[0]) if items else -1
        return self._windows[row] if 0 <= row < len(self._windows) else None


def pick_window(
    parent: QWidget, windows: Sequence[WindowInfo], current: WindowInfo | None
) -> WindowInfo | None:
    dialog = WindowPickerDialog(parent, windows, current)
    try:
        return dialog.selected() if dialog.exec() else None
    finally:
        dialog.deleteLater()
