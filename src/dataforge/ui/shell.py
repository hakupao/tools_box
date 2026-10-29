"""Main window: FluentWindow shell with lazily created tool pages."""
from __future__ import annotations

import logging
from typing import Any

from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    FluentIcon,
    FluentWindow,
    InfoBar,
    MessageBox,
    NavigationItemPosition,
)

from dataforge import __version__
from dataforge.config.recent import RecentStore
from dataforge.config.store import ConfigStore
from dataforge.ui.home import HomePage
from dataforge.ui.jobs import JobRunner
from dataforge.ui.layout import MIN_WINDOW_WIDTH, WIDE_MIN_WIDTH
from dataforge.ui.registry import TOOLS, ToolGroup, ToolSpec, get_tool, load_page_class
from dataforge.ui.settings import SettingsPage

logger = logging.getLogger(__name__)


class MainWindow(FluentWindow):
    def __init__(self, config: ConfigStore, runner: JobRunner, recent: RecentStore) -> None:
        super().__init__()
        self._config = config
        self._runner = runner
        self._recent = recent
        self._containers: dict[str, QWidget] = {}
        self._pages: dict[str, QWidget] = {}

        self.setWindowTitle(f"DataForge Studio {__version__}")
        self.setMinimumWidth(MIN_WINDOW_WIDTH)
        self.resize(1100, 720)
        self.setMicaEffectEnabled(True)
        self.navigationInterface.setMinimumExpandWidth(WIDE_MIN_WIDTH)

        self.home = HomePage(TOOLS, recent, self.open_tool)
        self.home.setObjectName("home")
        self.addSubInterface(self.home, FluentIcon.HOME, "主页", NavigationItemPosition.TOP)

        for group in ToolGroup:
            specs = [s for s in TOOLS if s.group is group]
            if not specs:
                continue
            self.navigationInterface.addSeparator()
            for spec in specs:
                container = QWidget()
                container.setObjectName(spec.id)
                QVBoxLayout(container).setContentsMargins(0, 0, 0, 0)
                self._containers[spec.id] = container
                self.addSubInterface(container, spec.icon, spec.name, NavigationItemPosition.TOP)

        self.settings = SettingsPage(config, recent)
        self.settings.recent_cleared.connect(self.home.refresh)
        self.addSubInterface(
            self.settings, FluentIcon.SETTING, "设置", NavigationItemPosition.BOTTOM
        )

        self.stackedWidget.currentChanged.connect(self._on_current_changed)

    # -- public API ---------------------------------------------------------
    def page_for(self, tool_id: str) -> QWidget | None:
        return self._pages.get(tool_id)

    def open_tool(self, tool_id: str, state: dict[str, Any] | None = None) -> None:
        container = self._containers.get(tool_id)
        if container is None:
            logger.warning("Unknown tool id %s", tool_id)
            return
        self.switchTo(container)
        page = self._ensure_page(tool_id)
        if state is None or page is None:
            return
        if self._runner.current_tool() == tool_id:  # inputs are locked while it runs
            InfoBar.info(title="任务运行中，已保留当前输入", content="", parent=self)
            return
        missing = page.restore_state(state)
        if missing:
            InfoBar.warning(title="部分文件已不存在", content="、".join(missing), parent=self)

    # -- lazy loading -------------------------------------------------------
    def _on_current_changed(self, _index: int) -> None:
        current = self.stackedWidget.currentWidget()
        for tool_id, container in self._containers.items():
            if container is current:
                self._ensure_page(tool_id)
                return

    def _ensure_page(self, tool_id: str) -> QWidget | None:
        if tool_id in self._pages:
            return self._pages[tool_id]
        container = self._containers[tool_id]
        if container.layout().count():  # an earlier load failure left its message here
            return None
        spec = get_tool(tool_id)
        try:
            page = load_page_class(spec)(spec, self._runner)
        except Exception as exc:  # noqa: BLE001 - never crash the window
            logger.exception("Failed to load page for %s", tool_id)
            container.layout().addWidget(BodyLabel(f"页面加载失败：{exc}", container))
            InfoBar.error(title="页面加载失败", content=str(exc), parent=self)
            return None
        container.layout().addWidget(page)
        self._pages[tool_id] = page
        if hasattr(page, "run_succeeded"):
            page.run_succeeded.connect(
                lambda summary, state, s=spec: self._on_run_succeeded(s, summary, state)
            )
        return page

    def _on_run_succeeded(self, spec: ToolSpec, summary: str, state: dict) -> None:
        self._recent.add(spec.id, summary, state)
        self.home.refresh()

    # -- closing ------------------------------------------------------------
    def closeEvent(self, event: QCloseEvent) -> None:
        if self._runner.is_busy():
            box = MessageBox("任务仍在运行", "确定退出？正在运行的任务会被取消。", self)
            try:
                accepted = box.exec()
            finally:
                box.deleteLater()
            if not accepted:
                event.ignore()
                return
        self._runner.shutdown()
        super().closeEvent(event)
