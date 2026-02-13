from __future__ import annotations

import ctypes
import os
import sys
from typing import Iterable

from PySide6.QtCore import QEvent, QObject, Qt, Signal
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QAbstractItemView, QFileDialog, QListWidget, QListWidgetItem, QMessageBox, QWidget


def pick_font(candidates: list[str], fallback: str) -> str:
    families = set(QFontDatabase.families())
    for name in candidates:
        if name in families:
            return name
    return fallback


def mono_font(point_size: int = 10) -> QFont:
    font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
    font.setPointSize(point_size)
    return font


def ensure_light_title_bar(widget: QWidget | None) -> None:
    """Force Windows title bar to light mode for a specific top-level widget."""
    if widget is None or sys.platform != "win32":
        return

    try:
        hwnd = int(widget.winId())
    except Exception:
        return

    if hwnd <= 0:
        return

    value = ctypes.c_int(0)
    size = ctypes.sizeof(value)
    dwm_set_attr = ctypes.windll.dwmapi.DwmSetWindowAttribute  # type: ignore[attr-defined]

    # Windows 10/11 use either 20 or 19 depending on build.
    for attr in (20, 19):
        try:
            dwm_set_attr(hwnd, attr, ctypes.byref(value), size)
        except Exception:
            continue


class LightTitleBarEventFilter(QObject):
    """Apply light title bar to every shown top-level Qt window/dialog on Windows."""

    def eventFilter(self, watched, event):  # noqa: N802
        if (
            event.type() in (QEvent.Show, QEvent.WinIdChange)
            and isinstance(watched, QWidget)
            and watched.isWindow()
        ):
            ensure_light_title_bar(watched)
        return super().eventFilter(watched, event)


_LIGHT_DIALOG_STYLE = """
QDialog, QMessageBox, QFileDialog {
    background: #F5F6F8;
    color: #0F172A;
}
QDialog QLabel, QMessageBox QLabel, QFileDialog QLabel {
    color: #0F172A;
}
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QAbstractSpinBox {
    background: #FFFFFF;
    color: #111827;
    border: 1px solid #DCE3ED;
    border-radius: 6px;
    selection-background-color: #DDEBFF;
    selection-color: #0F172A;
}
QPushButton {
    background: #FFFFFF;
    color: #0F172A;
    border: 1px solid #D1D9E6;
    border-radius: 6px;
    padding: 5px 12px;
    min-height: 26px;
}
QPushButton:hover {
    background: #F8FAFC;
}
QPushButton:pressed {
    background: #EEF2F7;
}
QFileDialog QToolButton {
    background: #EEF3F9;
    color: #0F172A;
    border: 1px solid #D1D9E6;
    border-radius: 5px;
    padding: 0px;
    min-width: 24px;
    min-height: 24px;
    qproperty-iconSize: 16px 16px;
}
QFileDialog QToolButton:hover {
    background: #E3EBF7;
}
QFileDialog QToolButton:pressed {
    background: #D6E2F3;
}
QAbstractItemView,
QListView,
QTreeView,
QTableView {
    background: #FFFFFF;
    color: #111827;
    border: 1px solid #DCE3ED;
    alternate-background-color: #F8FAFC;
    outline: none;
}
QAbstractItemView::item,
QListView::item,
QTreeView::item,
QTableView::item {
    color: #111827;
}
QAbstractItemView::item:selected,
QAbstractItemView::item:selected:active,
QAbstractItemView::item:selected:!active,
QListView::item:selected,
QListView::item:selected:active,
QListView::item:selected:!active,
QTreeView::item:selected,
QTreeView::item:selected:active,
QTreeView::item:selected:!active,
QTableView::item:selected,
QTableView::item:selected:active,
QTableView::item:selected:!active {
    background: #DDEBFF;
    color: #0F172A;
}
QHeaderView::section {
    background: #EEF3F9;
    color: #334155;
    border: 1px solid #DCE3ED;
    padding: 4px 6px;
}
QTableCornerButton::section {
    background: #EEF3F9;
    border: 1px solid #DCE3ED;
}
QSplitter::handle {
    background: #E3E8EF;
}
QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 6px 3px 6px 0;
}
QScrollBar::handle:vertical {
    background: #C7D3E3;
    min-height: 48px;
    border-radius: 5px;
}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0px;
    background: transparent;
}
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {
    background: transparent;
}
QScrollBar:horizontal {
    background: transparent;
    height: 10px;
    margin: 0 6px 3px 6px;
}
QScrollBar::handle:horizontal {
    background: #C7D3E3;
    min-width: 48px;
    border-radius: 5px;
}
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {
    width: 0px;
    background: transparent;
}
QScrollBar::add-page:horizontal,
QScrollBar::sub-page:horizontal {
    background: transparent;
}
"""


def _apply_light_dialog_style(widget: QWidget) -> None:
    widget.setStyleSheet(_LIGHT_DIALOG_STYLE)
    ensure_light_title_bar(widget)


def _show_message_box(
    parent,
    title: str,
    message: str,
    *,
    icon: QMessageBox.Icon,
    with_cancel: bool,
    yes_text: str,
    cancel_text: str = "取消",
) -> bool:
    box = QMessageBox(parent)
    box.setIcon(icon)
    box.setWindowTitle(title)
    box.setText(message)
    box.setTextFormat(Qt.PlainText)
    box.setStandardButtons(QMessageBox.StandardButton.NoButton)

    yes_button = box.addButton(yes_text, QMessageBox.ButtonRole.AcceptRole)
    cancel_button = None
    if with_cancel:
        cancel_button = box.addButton(cancel_text, QMessageBox.ButtonRole.RejectRole)

    box.setDefaultButton(yes_button)
    box.setEscapeButton(cancel_button or yes_button)
    _apply_light_dialog_style(box)
    box.exec()
    return box.clickedButton() is yes_button


def show_info(parent, title: str, message: str) -> None:
    _show_message_box(parent, title, message, icon=QMessageBox.Icon.Information, with_cancel=False, yes_text="确定")


def show_warning(parent, title: str, message: str) -> None:
    _show_message_box(parent, title, message, icon=QMessageBox.Icon.Warning, with_cancel=False, yes_text="确定")


def show_error(parent, title: str, message: str) -> None:
    _show_message_box(parent, title, message, icon=QMessageBox.Icon.Critical, with_cancel=False, yes_text="确定")


def ask_yes_no(parent, title: str, message: str) -> bool:
    return _show_message_box(
        parent,
        title,
        message,
        icon=QMessageBox.Icon.Question,
        with_cancel=True,
        yes_text="是",
        cancel_text="否",
    )


def select_open_file(parent, title: str, directory: str = "", file_filter: str = "") -> tuple[str, str]:
    dialog = QFileDialog(parent, title, directory, file_filter)
    dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
    dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptOpen)
    dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
    _apply_light_dialog_style(dialog)

    if dialog.exec() == QFileDialog.DialogCode.Accepted:
        files = dialog.selectedFiles()
        return (files[0] if files else "", dialog.selectedNameFilter())
    return ("", dialog.selectedNameFilter())


def select_open_files(parent, title: str, directory: str = "", file_filter: str = "") -> tuple[list[str], str]:
    dialog = QFileDialog(parent, title, directory, file_filter)
    dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
    dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptOpen)
    dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
    _apply_light_dialog_style(dialog)

    if dialog.exec() == QFileDialog.DialogCode.Accepted:
        return (dialog.selectedFiles(), dialog.selectedNameFilter())
    return ([], dialog.selectedNameFilter())


def select_existing_directory(parent, title: str, directory: str = "") -> str:
    dialog = QFileDialog(parent, title, directory)
    dialog.setFileMode(QFileDialog.FileMode.Directory)
    dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptOpen)
    dialog.setOption(QFileDialog.Option.ShowDirsOnly, True)
    dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
    _apply_light_dialog_style(dialog)

    if dialog.exec() == QFileDialog.DialogCode.Accepted:
        files = dialog.selectedFiles()
        return files[0] if files else ""
    return ""


def select_save_file(parent, title: str, directory: str = "", file_filter: str = "") -> tuple[str, str]:
    dialog = QFileDialog(parent, title, directory, file_filter)
    dialog.setFileMode(QFileDialog.FileMode.AnyFile)
    dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
    dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
    _apply_light_dialog_style(dialog)

    if dialog.exec() == QFileDialog.DialogCode.Accepted:
        files = dialog.selectedFiles()
        return (files[0] if files else "", dialog.selectedNameFilter())
    return ("", dialog.selectedNameFilter())


class FileListWidget(QListWidget):
    filesAdded = Signal(list)

    def __init__(
        self,
        allowed_exts: Iterable[str] | None = None,
        allow_dirs: bool = True,
        recursive: bool = True,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragEnabled(False)
        self.setDragDropMode(QAbstractItemView.DropOnly)
        self.setDropIndicatorShown(True)
        self.setDefaultDropAction(Qt.CopyAction)
        self.viewport().setAcceptDrops(True)
        self.viewport().installEventFilter(self)
        self.setSelectionMode(QListWidget.ExtendedSelection)
        self.setStyleSheet(
            """
            QListWidget {
                background: #F8FAFC;
                border: 1px solid #E3E8EF;
                border-radius: 10px;
                color: #1F2937;
            }
            QListWidget::item {
                padding: 6px 10px;
            }
            QListWidget::item:selected {
                background: #DDEBFF;
                color: #0F172A;
            }
            """
        )
        self.allowed_exts = [ext.lower() for ext in allowed_exts] if allowed_exts else None
        self.allow_dirs = allow_dirs
        self.recursive = recursive

    def set_allowed_exts(self, exts: Iterable[str] | None) -> None:
        self.allowed_exts = [ext.lower() for ext in exts] if exts else None

    def dragEnterEvent(self, event):  # noqa: N802
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.CopyAction)
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):  # noqa: N802
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.CopyAction)
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):  # noqa: N802
        if not event.mimeData().hasUrls():
            event.ignore()
            return
        paths = [url.toLocalFile() for url in event.mimeData().urls()]
        added = self.add_paths(paths)
        if added:
            self.filesAdded.emit(added)
        event.acceptProposedAction()

    def eventFilter(self, watched, event):  # noqa: N802
        if watched is self.viewport():
            if event.type() in (QEvent.DragEnter, QEvent.DragMove):
                if event.mimeData().hasUrls():
                    event.setDropAction(Qt.CopyAction)
                    event.acceptProposedAction()
                    return True
            if event.type() == QEvent.Drop:
                if event.mimeData().hasUrls():
                    paths = [url.toLocalFile() for url in event.mimeData().urls()]
                    added = self.add_paths(paths)
                    if added:
                        self.filesAdded.emit(added)
                    event.acceptProposedAction()
                    return True
        return super().eventFilter(watched, event)

    def add_paths(self, paths: Iterable[str]) -> list[str]:
        files: list[str] = []
        for path in paths:
            if not path:
                continue
            if os.path.isfile(path):
                files.append(path)
                continue
            if os.path.isdir(path) and self.allow_dirs:
                for root, _, filenames in os.walk(path):
                    for filename in filenames:
                        files.append(os.path.join(root, filename))
                    if not self.recursive:
                        break

        if self.allowed_exts:
            files = [f for f in files if any(f.lower().endswith(ext) for ext in self.allowed_exts)]

        existing = set(self.paths())
        added: list[str] = []
        for file_path in files:
            if file_path in existing:
                continue
            self.addItem(QListWidgetItem(file_path))
            existing.add(file_path)
            added.append(file_path)
        return added

    def paths(self) -> list[str]:
        return [self.item(i).text() for i in range(self.count())]

    def filter_by_exts(self, allowed_exts: Iterable[str] | None) -> int:
        allowed = [ext.lower() for ext in allowed_exts] if allowed_exts else None
        removed = 0
        for index in reversed(range(self.count())):
            text = self.item(index).text()
            if allowed and not any(text.lower().endswith(ext) for ext in allowed):
                self.takeItem(index)
                removed += 1
        return removed
