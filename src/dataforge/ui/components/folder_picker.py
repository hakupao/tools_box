"""Single-folder picker with drag-and-drop."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QWidget
from qfluentwidgets import LineEdit, PushButton


class FolderPicker(QWidget):
    folder_changed = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._folder: Path | None = None
        self._locked = False
        self.setAcceptDrops(True)
        self._edit = LineEdit(self)
        self._edit.setReadOnly(True)
        self._edit.setAcceptDrops(False)
        self._button = PushButton("选择文件夹", self)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._edit, 1)
        layout.addWidget(self._button)
        self._button.clicked.connect(self._on_pick)

    def folder(self) -> Path | None:
        return self._folder

    def set_folder(self, path: Path | None) -> None:
        if path == self._folder:
            return
        self._folder = path
        self._edit.setText(str(path) if path else "")
        self.folder_changed.emit(path)

    def is_locked(self) -> bool:
        return self._locked

    def set_locked(self, locked: bool) -> None:
        self._locked = locked
        self._button.setEnabled(not locked)

    def _on_pick(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if folder:
            self.set_folder(Path(folder))

    @staticmethod
    def _dropped_folder(event) -> Path | None:
        urls = [u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]
        if len(urls) == 1 and Path(urls[0]).is_dir():
            return Path(urls[0])
        return None

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        if not self._locked and event.mimeData().hasUrls() and self._dropped_folder(event):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event) -> None:  # noqa: N802
        folder = None if self._locked else self._dropped_folder(event)
        if folder is None:
            event.ignore()
            return
        self.set_folder(folder)
        event.acceptProposedAction()
