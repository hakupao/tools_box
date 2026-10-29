"""Output location field: same folder as the source, or a chosen folder."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QVBoxLayout, QWidget
from qfluentwidgets import CaptionLabel, ComboBox

_SAME_DIR = 0
_CUSTOM_DIR = 1


class OutputLocationField(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._output_dir: str | None = None
        self.combo = ComboBox(self)
        self.combo.addItems(["与原文件相同", "指定文件夹…"])
        self.path_label = CaptionLabel("", self)
        self.path_label.setWordWrap(True)
        self.path_label.setVisible(False)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.combo)
        layout.addWidget(self.path_label)
        self.combo.currentIndexChanged.connect(self._on_changed)

    def output_dir(self) -> Path | None:
        return Path(self._output_dir) if self._output_dir else None

    def set_output_dir(self, path: Path | str | None) -> None:
        folder = str(path) if path else None
        self.combo.blockSignals(True)
        self.combo.setCurrentIndex(_CUSTOM_DIR if folder else _SAME_DIR)
        self.combo.blockSignals(False)
        self._apply(folder)

    def _apply(self, folder: str | None) -> None:
        self._output_dir = folder
        self.path_label.setText(folder or "")
        self.path_label.setVisible(bool(folder))

    def _on_changed(self, index: int) -> None:
        if index != _CUSTOM_DIR:
            self._apply(None)
            return
        folder = QFileDialog.getExistingDirectory(self, "选择输出文件夹")
        if folder:
            self._apply(folder)
        else:
            self.combo.setCurrentIndex(_SAME_DIR)
