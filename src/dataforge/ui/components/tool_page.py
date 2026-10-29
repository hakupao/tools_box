"""Responsive base class for file-based tool pages."""
from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QBoxLayout, QFrame, QVBoxLayout, QWidget
from qfluentwidgets import (
    CaptionLabel,
    InfoBar,
    InfoBarPosition,
    SimpleCardWidget,
    SmoothScrollArea,
    StrongBodyLabel,
    TitleLabel,
)

from dataforge.core.result import Result
from dataforge.ui.components.responsive_form import ResponsiveForm
from dataforge.ui.components.result_panel import ResultPanel
from dataforge.ui.components.run_bar import RunBar
from dataforge.ui.jobs import JobFn, JobRunner
from dataforge.ui.layout import LayoutMode, layout_mode_for_width
from dataforge.ui.registry import ToolSpec, get_tool

_SETTINGS_STRETCH = 55
_RESULT_STRETCH = 45


class ToolPage(QWidget):
    """Title + settings cards + result panel + run bar, wired to the global JobRunner."""

    run_succeeded = Signal(str, dict)

    def __init__(self, spec: ToolSpec, runner: JobRunner, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.spec = spec
        self.runner = runner
        self.setObjectName(spec.id)
        self._mode: LayoutMode | None = None

        self.result_panel = ResultPanel(self)
        self.run_bar = RunBar(self)

        self._settings_host = QWidget(self)
        self._settings_layout = QVBoxLayout(self._settings_host)
        self._settings_layout.setContentsMargins(0, 0, 0, 0)
        self._settings_layout.addStretch(1)
        self._scroll = SmoothScrollArea(self)
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setWidget(self._settings_host)
        self._scroll.viewport().setAutoFillBackground(False)
        self._settings_host.setAutoFillBackground(False)

        self._body = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        self._body.setContentsMargins(0, 0, 0, 0)
        self._body.addWidget(self._scroll, _SETTINGS_STRETCH)
        self._body.addWidget(self.result_panel, _RESULT_STRETCH)

        header = QVBoxLayout()
        header.setSpacing(2)
        header.addWidget(TitleLabel(spec.name, self))
        header.addWidget(CaptionLabel(spec.description, self))

        root = QVBoxLayout(self)
        root.addLayout(header)
        root.addLayout(self._body, 1)
        root.addWidget(self.run_bar)

        self.run_bar.start_requested.connect(self._on_start_requested)
        self.run_bar.cancel_requested.connect(self._on_cancel_requested)
        runner.started.connect(self._on_started)
        runner.progress.connect(self._on_progress)
        runner.log.connect(self._on_log)
        runner.finished.connect(self._on_finished)
        runner.failed.connect(self._on_failed)
        runner.cancelled.connect(self._on_cancelled)
        runner.busy_changed.connect(self._on_busy_changed)
        self._on_busy_changed(runner.is_busy())
        self.apply_layout_mode(LayoutMode.WIDE)

    # -- structure ---------------------------------------------------------
    def add_section(self, title: str, widget: QWidget) -> SimpleCardWidget:
        card = SimpleCardWidget(self._settings_host)
        layout = QVBoxLayout(card)
        layout.addWidget(StrongBodyLabel(title, card))
        layout.addWidget(widget)
        self._settings_layout.insertWidget(self._settings_layout.count() - 1, card)
        if self._mode is LayoutMode.NARROW:
            for form in card.findChildren(ResponsiveForm):
                form.set_compact(True)
        return card

    # -- layout --------------------------------------------------------------
    def layout_mode(self) -> LayoutMode:
        return self._mode if self._mode is not None else LayoutMode.WIDE

    def apply_layout_mode(self, mode: LayoutMode) -> None:
        self._mode = mode
        wide = mode is LayoutMode.WIDE
        self._body.setDirection(
            QBoxLayout.Direction.LeftToRight if wide else QBoxLayout.Direction.TopToBottom
        )
        self._body.setStretchFactor(self._scroll, _SETTINGS_STRETCH if wide else 1)
        self._body.setStretchFactor(self.result_panel, _RESULT_STRETCH if wide else 1)
        narrow = mode is LayoutMode.NARROW
        for form in self._settings_host.findChildren(ResponsiveForm):
            form.set_compact(narrow)
        self.result_panel.set_collapsed(narrow)

    def update_layout_mode(self) -> None:
        mode = layout_mode_for_width(self.window().width())
        if mode is not self._mode:
            self.apply_layout_mode(mode)

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt override
        super().resizeEvent(event)
        self.update_layout_mode()

    # -- subclass hooks --------------------------------------------------------
    def build_job(self) -> JobFn | None:
        raise NotImplementedError

    def capture_state(self) -> dict[str, Any]:
        raise NotImplementedError

    def restore_state(self, state: dict[str, Any]) -> list[str]:
        raise NotImplementedError

    def summary(self) -> str:
        raise NotImplementedError

    def set_inputs_locked(self, locked: bool) -> None:
        raise NotImplementedError

    # -- run flow ----------------------------------------------------------------
    def _is_mine(self) -> bool:
        return self.runner.current_tool() == self.spec.id

    def _info_parent(self) -> QWidget:
        return self.window()

    def _on_start_requested(self) -> None:
        fn = self.build_job()
        if fn is None:
            return
        if not self.runner.submit(self.spec.id, fn):
            InfoBar.warning("无法开始", "已有任务正在运行", parent=self._info_parent(),
                            position=InfoBarPosition.TOP_RIGHT)

    def _on_cancel_requested(self) -> None:
        if self._is_mine():
            self.runner.cancel()

    def _on_started(self, tool_id: str) -> None:
        if tool_id != self.spec.id:
            return
        self.set_inputs_locked(True)
        self.run_bar.set_running(True)
        self.result_panel.clear()

    def _on_progress(self, current: int, total: int, label: str) -> None:
        if self._is_mine():
            self.run_bar.set_progress(current, total, label)

    def _on_log(self, line: str) -> None:
        if self._is_mine():
            self.result_panel.append_log(line)

    def _end_run(self) -> None:
        self.set_inputs_locked(False)
        self.run_bar.set_running(False)

    def _on_finished(self, tool_id: str, result: Result) -> None:
        if tool_id != self.spec.id:
            return
        self._end_run()
        self.result_panel.show_result(result)
        parent = self._info_parent()
        if result.errors:
            InfoBar.warning("部分文件失败", f"{len(result.errors)} 个文件处理失败",
                            parent=parent, position=InfoBarPosition.TOP_RIGHT)
        else:
            InfoBar.success("完成", f"已生成 {len(result.outputs)} 个输出",
                            parent=parent, position=InfoBarPosition.TOP_RIGHT)
        if result.outputs:
            self.run_succeeded.emit(self.summary(), self.capture_state())

    def _on_failed(self, tool_id: str, message: str) -> None:
        if tool_id != self.spec.id:
            return
        self._end_run()
        InfoBar.error("失败", message, parent=self._info_parent(),
                      position=InfoBarPosition.TOP_RIGHT)

    def _on_cancelled(self, tool_id: str) -> None:
        if tool_id != self.spec.id:
            return
        self._end_run()
        InfoBar.info("已取消", "", parent=self._info_parent(),
                     position=InfoBarPosition.TOP_RIGHT)

    def _on_busy_changed(self, busy: bool) -> None:
        other = self.runner.current_tool() if busy else None
        if busy and other is not None and other != self.spec.id:
            try:
                name = get_tool(other).name
            except KeyError:
                name = other
            self.run_bar.set_blocked(f"{name} 正在运行")
        else:
            self.run_bar.set_blocked(None)
