"""Home page (placeholder; replaced by the full implementation in Task 11)."""
from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import QVBoxLayout, QWidget
from qfluentwidgets import TitleLabel

from dataforge.config.recent import RecentStore
from dataforge.ui.registry import ToolSpec


class HomePage(QWidget):
    def __init__(
        self,
        tools: tuple[ToolSpec, ...],
        recent: RecentStore,
        open_tool: Callable[[str, dict | None], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._tools = tools
        self._recent = recent
        self._open_tool = open_tool
        layout = QVBoxLayout(self)
        layout.addWidget(TitleLabel("DataForge Studio", self))
        layout.addStretch(1)

    def refresh(self) -> None:
        """Re-read the recent list (no-op in the placeholder)."""
