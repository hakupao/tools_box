"""Settings page: theme, folders, recent history, version."""
from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import BodyLabel, ComboBox, PushButton, SubtitleLabel

from dataforge import __version__
from dataforge.config.recent import RecentStore
from dataforge.config.store import ConfigStore
from dataforge.core.logs import default_log_dir
from dataforge.ui.theme import THEME_MODES, apply_theme_mode

logger = logging.getLogger(__name__)

APP_SECTION = "app"
_MODE_LABELS: tuple[tuple[str, str], ...] = (
    ("auto", "跟随系统"),
    ("light", "浅色"),
    ("dark", "深色"),
)


class SettingsPage(QWidget):
    recent_cleared = Signal()

    def __init__(
        self, config: ConfigStore, recent: RecentStore, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._config = config
        self._recent = recent
        self.setObjectName("settings")

        layout = QVBoxLayout(self)
        layout.addWidget(SubtitleLabel("设置", self))

        layout.addWidget(BodyLabel("主题", self))
        self.theme_combo = ComboBox(self)
        for mode, label in _MODE_LABELS:
            self.theme_combo.addItem(label, userData=mode)
        current = self._config.section(APP_SECTION).get("theme", "auto")
        if current not in THEME_MODES:
            current = "auto"
        self.theme_combo.setCurrentIndex([m for m, _ in _MODE_LABELS].index(current))
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        layout.addWidget(self.theme_combo)

        row = QHBoxLayout()
        self.open_logs_button = PushButton("打开日志文件夹", self)
        self.open_logs_button.clicked.connect(lambda: self._open_dir(default_log_dir()))
        self.open_config_button = PushButton("打开配置文件夹", self)
        self.open_config_button.clicked.connect(lambda: self._open_dir(self._config.path.parent))
        row.addWidget(self.open_logs_button)
        row.addWidget(self.open_config_button)
        row.addStretch(1)
        layout.addLayout(row)

        self.clear_recent_button = PushButton("清空最近使用", self)
        self.clear_recent_button.clicked.connect(self._on_clear_recent)
        clear_row = QHBoxLayout()
        clear_row.addWidget(self.clear_recent_button)
        clear_row.addStretch(1)
        layout.addLayout(clear_row)

        self.version_label = BodyLabel(f"版本 {__version__}", self)
        layout.addWidget(self.version_label)
        layout.addStretch(1)

    def _on_theme_changed(self, index: int) -> None:
        mode = self.theme_combo.itemData(index)
        if mode not in THEME_MODES:
            return
        apply_theme_mode(mode)
        data = self._config.section(APP_SECTION)
        data["theme"] = mode
        self._config.update_section(APP_SECTION, data)

    def _on_clear_recent(self) -> None:
        self._recent.clear()
        self.recent_cleared.emit()

    @staticmethod
    def _open_dir(path: Path) -> None:
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError:
            logger.exception("Could not create %s", path)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
