from __future__ import annotations

import os
from typing import Iterable

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QAbstractItemView, QListWidget, QListWidgetItem, QMessageBox


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


def show_info(parent, title: str, message: str) -> None:
    QMessageBox.information(parent, title, message, QMessageBox.Ok)


def show_warning(parent, title: str, message: str) -> None:
    QMessageBox.warning(parent, title, message, QMessageBox.Ok)


def show_error(parent, title: str, message: str) -> None:
    QMessageBox.critical(parent, title, message, QMessageBox.Ok)


def ask_yes_no(parent, title: str, message: str) -> bool:
    return QMessageBox.question(parent, title, message, QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes


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
