"""Encoding drop-down: auto-detect or a fixed encoding."""
from __future__ import annotations

from PySide6.QtWidgets import QWidget
from qfluentwidgets import ComboBox

_CHOICES: list[tuple[str, str | None]] = [
    ("自动识别", None),
    ("UTF-8", "utf-8"),
    ("UTF-8 (BOM)", "utf-8-sig"),
    ("日文 (cp932)", "cp932"),
    ("中文 (GBK)", "gbk"),
]


class EncodingField(ComboBox):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.addItems([label for label, _ in _CHOICES])

    def encoding(self) -> str | None:
        index = self.currentIndex()
        return _CHOICES[index][1] if 0 <= index < len(_CHOICES) else None

    def set_encoding(self, value: str | None) -> None:
        for index, (_, code) in enumerate(_CHOICES):
            if code == value:
                self.setCurrentIndex(index)
                return
        self.setCurrentIndex(0)
