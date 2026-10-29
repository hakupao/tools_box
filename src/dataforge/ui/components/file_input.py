"""Drag-and-drop file/folder input card."""
from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import ListWidget, PushButton, SimpleCardWidget, StrongBodyLabel

from dataforge.fileio.paths import iter_input_files

logger = logging.getLogger(__name__)


class FileInputCard(SimpleCardWidget):
    files_changed = Signal(list)

    def __init__(
        self,
        title: str,
        extensions: tuple[str, ...],
        allow_folder: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._extensions = extensions
        self._files: list[Path] = []
        self._locked = False
        self.setAcceptDrops(True)

        self._list = ListWidget(self)
        # Let drops on the list fall through to the card, which handles them.
        self._list.setAcceptDrops(False)
        self._list.viewport().setAcceptDrops(False)
        self._pick_files = PushButton("选择文件", self)
        self._pick_folder = PushButton("选择文件夹", self)
        self._pick_folder.setVisible(allow_folder)
        self._clear = PushButton("清空", self)

        buttons = QHBoxLayout()
        buttons.addWidget(self._pick_files)
        buttons.addWidget(self._pick_folder)
        buttons.addStretch(1)
        buttons.addWidget(self._clear)
        layout = QVBoxLayout(self)
        layout.addWidget(StrongBodyLabel(title, self))
        layout.addWidget(self._list, 1)
        layout.addLayout(buttons)

        self._pick_files.clicked.connect(self._on_pick_files)
        self._pick_folder.clicked.connect(self._on_pick_folder)
        self._clear.clicked.connect(self.clear)

    def files(self) -> list[Path]:
        return list(self._files)

    def set_files(self, paths: list[Path]) -> None:
        self._apply([], paths)

    def clear(self) -> None:
        self._apply([], [])

    def is_locked(self) -> bool:
        return self._locked

    def set_locked(self, locked: bool) -> None:
        self._locked = locked
        for widget in (self._pick_files, self._pick_folder, self._clear):
            widget.setEnabled(not locked)

    def _expand(self, paths: list[Path]) -> list[Path]:
        found: list[Path] = []
        for path in paths:
            try:
                found.extend(iter_input_files([Path(path)], self._extensions))
            except OSError:
                logger.warning("Skipping unreadable input: %s", path, exc_info=True)
        return found

    def _apply(self, base: list[Path], new: list[Path]) -> None:
        merged: list[Path] = []
        seen: set[Path] = set()
        for path in [*base, *self._expand(new)]:
            key = path.resolve()
            if key not in seen:
                seen.add(key)
                merged.append(path)
        if merged == self._files:
            return
        self._files = merged
        self._list.clear()
        self._list.addItems([str(p) for p in merged])
        self.files_changed.emit(self.files())

    def add_paths(self, paths: list[Path]) -> None:
        """Merge files/folders into the current list."""
        self._apply(self._files, paths)

    def _on_pick_files(self) -> None:
        pattern = " ".join(f"*{e}" for e in self._extensions)
        names, _ = QFileDialog.getOpenFileNames(self, "选择文件", "", f"文件 ({pattern})")
        if names:
            self.add_paths([Path(n) for n in names])

    def _on_pick_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if folder:
            self.add_paths([Path(folder)])

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        if not self._locked and event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event) -> None:  # noqa: N802
        if self._locked:
            event.ignore()
            return
        urls = [u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]
        self.add_paths([Path(u) for u in urls])
        event.acceptProposedAction()
