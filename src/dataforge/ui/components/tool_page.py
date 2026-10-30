"""Responsive base class for file-based tool pages."""
from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, QTimer, Signal
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
from dataforge.ui.components.encoding_dialog import ask_encodings
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

    # When True the retry result is merged into the first-run result; when False the
    # retry result alone is displayed (the subclass trims carried_result() itself).
    RETRY_MERGES: bool = True

    def __init__(self, spec: ToolSpec, runner: JobRunner, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.spec = spec
        self.runner = runner
        self.setObjectName(spec.id)
        self._mode: LayoutMode | None = None
        self._snapshot: tuple[str, dict[str, Any]] | None = None
        self._carry: Result | None = None
        self._retrying = False
        self._retry_snapshot: tuple[str, dict[str, Any]] | None = None
        self._job_kind = "run"
        self._keep_log_separator: str | None = None

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

    def build_retry_job(self, encodings: dict[str, str]) -> JobFn | None:
        """Job re-running the files whose encoding was ambiguous; None = retry unsupported."""
        return None

    def carried_result(self) -> Result | None:
        """The first-run Result held while a retry is pending or running, else None."""
        return self._carry

    def current_job_kind(self) -> str:
        """Kind of job the main button submits; anything but "run" is an auxiliary job."""
        return "run"

    def on_aux_finished(self, kind: str, result: Result) -> None:
        """Called when an auxiliary (non-"run") job finished successfully.

        The runner is still busy while this hook runs (it is released when the worker
        thread ends), so queue any follow-up job with submit_job_when_idle(), never
        submit_job().
        """
        raise NotImplementedError

    def submit_job_when_idle(self, fn: JobFn, kind: str = "run") -> None:
        """submit_job() now if the runner is idle, else as soon as it becomes idle."""
        if not self.runner.is_busy():
            self.submit_job(fn, kind)
            return

        def on_busy_changed(busy: bool) -> None:
            if busy:
                return
            self.runner.busy_changed.disconnect(on_busy_changed)
            if self.runner.is_closing():
                return  # the app is exiting; dropping the follow-up is silent by design
            self.submit_job(fn, kind)  # warns if another tool grabbed the runner first

        self.runner.busy_changed.connect(on_busy_changed)

    def keep_log_for_next_start(self, separator: str) -> None:
        """Next job start keeps the result panel and appends ``separator`` to the log."""
        self._keep_log_separator = separator

    # -- run flow ----------------------------------------------------------------
    def _is_mine(self) -> bool:
        return self.runner.current_tool() == self.spec.id

    def _info_parent(self) -> QWidget:
        return self.window()

    def _on_start_requested(self) -> None:
        kind = self.current_job_kind()
        fn = self.build_job()
        if fn is None:
            return
        self.submit_job(fn, kind)

    def submit_job(self, fn: JobFn, kind: str = "run") -> bool:
        """Queue a job; only "run" jobs snapshot state for the recent list."""
        previous = self._job_kind
        self._job_kind = kind
        if self.runner.submit(self.spec.id, fn):
            if kind == "run":
                # Snapshot at start so the recent entry matches what actually ran.
                self._snapshot = (self.summary(), self.capture_state())
            return True
        self._job_kind = previous
        self._keep_log_separator = None  # must not leak into a later, unrelated start
        InfoBar.warning("无法开始", "已有任务正在运行", parent=self._info_parent(),
                        position=InfoBarPosition.TOP_RIGHT)
        return False

    def _on_cancel_requested(self) -> None:
        if self._is_mine():
            self.runner.cancel()

    def _on_started(self, tool_id: str) -> None:
        if tool_id != self.spec.id:
            return
        self.set_inputs_locked(True)
        self.run_bar.set_running(True)
        separator, self._keep_log_separator = self._keep_log_separator, None
        if separator is not None:
            self.result_panel.append_log(separator)
        elif self._retrying:
            self.result_panel.append_log("—— 重新处理编码有歧义的文件 ——")
        else:
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
        self._snapshot = None
        self._carry = None
        self._retrying = False
        self._retry_snapshot = None
        self._job_kind = "run"

    def _supports_retry(self) -> bool:
        return type(self).build_retry_job is not ToolPage.build_retry_job

    def _start_retry(self, result: Result) -> bool:
        """Ask for encodings and queue the retry job. False = nothing queued."""
        questions = list(result.encoding_questions)
        answers = ask_encodings(self.window(), questions)
        for question in questions:
            if question.path not in answers:
                result.warn(question.path, "未选择编码，已跳过")
                result.count("skipped")
        result.encoding_questions = []
        if not answers:
            return False
        self._carry = result
        job = self.build_retry_job(answers)
        if job is None:
            self._carry = None
            return False
        self._retrying = True
        self._retry_snapshot = self._snapshot
        QTimer.singleShot(0, lambda: self._submit_retry(job))
        return True

    def _submit_retry(self, job: JobFn) -> None:
        if not self._retrying or self._carry is None:
            return
        if self.runner.submit(self.spec.id, job):
            return
        carried, snapshot = self._carry, self._retry_snapshot
        self._end_run()
        carried.warn("", "重新处理未能开始（已有任务正在运行）")
        self._complete(carried, snapshot)

    def _on_finished(self, tool_id: str, result: Result) -> None:
        if tool_id != self.spec.id:
            return
        if self._job_kind != "run":
            kind = self._job_kind
            self._end_run()
            self.on_aux_finished(kind, result)
            return
        if self._retrying and self._carry is not None:
            carried, snapshot = self._carry, self._retry_snapshot
            if self.RETRY_MERGES:
                carried.extend(result)
                result = carried
            self._end_run()
            self._complete(result, snapshot)
            return
        if result.encoding_questions and self._supports_retry():
            self.result_panel.show_result(result)
            if self._start_retry(result):
                return
        snapshot = self._snapshot
        self._end_run()
        self._complete(result, snapshot)

    def _complete(self, result: Result, snapshot: tuple[str, dict[str, Any]] | None) -> None:
        self.result_panel.show_result(result)
        parent = self._info_parent()
        pos = InfoBarPosition.TOP_RIGHT
        if not result.outputs and result.errors:
            InfoBar.error("失败", result.errors[0].message, parent=parent, position=pos)
        elif not result.outputs and result.warnings:
            InfoBar.warning("未生成文件", result.warnings[0].message, parent=parent, position=pos)
        elif result.errors:
            InfoBar.warning("部分文件失败", f"{len(result.errors)} 个文件处理失败",
                            parent=parent, position=pos)
        elif not result.outputs:
            InfoBar.info("未生成文件", "本次运行没有生成任何文件", parent=parent, position=pos)
        else:
            InfoBar.success("完成", f"已生成 {len(result.outputs)} 个输出",
                            parent=parent, position=pos)
        if result.outputs:
            self.run_succeeded.emit(*(snapshot or (self.summary(), self.capture_state())))

    def _show_carried(
        self, carried: Result | None, snapshot: tuple[str, dict[str, Any]] | None
    ) -> None:
        """A retry that failed or was cancelled: the first run's outputs still count."""
        if carried is None:
            return
        self.result_panel.show_result(carried)
        if carried.outputs:
            self.run_succeeded.emit(*(snapshot or (self.summary(), self.capture_state())))

    def _on_failed(self, tool_id: str, message: str) -> None:
        if tool_id != self.spec.id:
            return
        aux = self._job_kind != "run"
        carried, snapshot = (None, None) if aux else (self._carry, self._retry_snapshot)
        self._end_run()
        self._show_carried(carried, snapshot)
        InfoBar.error("失败", message, parent=self._info_parent(),
                      position=InfoBarPosition.TOP_RIGHT)

    def _on_cancelled(self, tool_id: str) -> None:
        if tool_id != self.spec.id:
            return
        aux = self._job_kind != "run"
        carried, snapshot = (None, None) if aux else (self._carry, self._retry_snapshot)
        self._end_run()
        self._show_carried(carried, snapshot)
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
