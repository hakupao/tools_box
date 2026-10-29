"""Two-column form that collapses to a single column in narrow windows."""
from __future__ import annotations

from PySide6.QtWidgets import QGridLayout, QWidget
from qfluentwidgets import BodyLabel, CaptionLabel


class ResponsiveForm(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._compact = False
        self._rows: list[tuple[BodyLabel, QWidget, CaptionLabel | None]] = []
        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)

    def add_row(self, label: str, field: QWidget, hint: str | None = None) -> None:
        label_widget = BodyLabel(label, self)
        hint_widget = None
        if hint:
            hint_widget = CaptionLabel(hint, self)
            hint_widget.setWordWrap(True)
        self._rows.append((label_widget, field, hint_widget))
        self._relayout()

    def is_compact(self) -> bool:
        return self._compact

    def set_compact(self, compact: bool) -> None:
        if compact == self._compact:
            return
        self._compact = compact
        self._relayout()

    def _relayout(self) -> None:
        grid = self._grid
        for label, field, hint in self._rows:
            for widget in (label, field, hint):
                if widget is not None:
                    grid.removeWidget(widget)
        grid.setColumnStretch(0, 1 if self._compact else 0)
        grid.setColumnStretch(1, 0 if self._compact else 1)
        row = 0
        for label, field, hint in self._rows:
            if self._compact:
                grid.addWidget(label, row, 0)
                grid.addWidget(field, row + 1, 0)
                row += 2
                if hint is not None:
                    grid.addWidget(hint, row, 0)
                    row += 1
            else:
                grid.addWidget(label, row, 0)
                grid.addWidget(field, row, 1)
                row += 1
                if hint is not None:
                    grid.addWidget(hint, row, 1)
                    row += 1
