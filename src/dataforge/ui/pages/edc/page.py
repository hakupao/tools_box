"""EDC site adder page: record click positions, then replay them row by row from Excel."""
from __future__ import annotations

import dataclasses
import threading
from collections.abc import Sequence
from typing import Any

from PySide6.QtCore import QSignalBlocker
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    DoubleSpinBox,
    InfoBar,
    InfoBarPosition,
    PrimaryPushButton,
    PushButton,
    SpinBox,
)

from dataforge.config.store import ConfigStore
from dataforge.core.result import Result
from dataforge.tools.edc.config import (
    DEFAULT_POSITIONS,
    MAX_LOOPS_RANGE,
    STEP_DELAY_RANGE,
    STEP_KEYS,
    EdcConfig,
    legacy_files,
    load_config,
    save_config,
)
from dataforge.tools.edc.live import open_live_ports
from dataforge.tools.edc.loop import (
    CellRef,
    EdcSession,
    RowStop,
    Segment,
    StopChoice,
    run_segment,
)
from dataforge.tools.edc.windows import (
    WindowInfo,
    activate_window,
    find_target,
    list_windows,
    window_at,
)
from dataforge.ui.components.responsive_form import ResponsiveForm
from dataforge.ui.components.tool_page import ToolPage
from dataforge.ui.jobs import JobFn, JobRunner
from dataforge.ui.pages.edc.dialogs import ask_stop_choice, pick_window
from dataforge.ui.pages.edc.hooks import EscHook, MouseClickHook
from dataforge.ui.pages.edc.overlay import RecordingOverlay, schedule_replay
from dataforge.ui.registry import ToolSpec

_KIND = "edc"
_RUN_TEXT = "开始处理"
_NO_TARGET = "未设置（录制时会自动记住你点击的窗口）"
_COORD_RANGE = (-32768, 32767)
_NOTES = (
    "开始前：Excel 已打开并选中第一个站点所在的单元格；浏览器已打开 EDC 页面。",
    "运行期间不要操作鼠标和键盘；按 ESC 可在当前步骤结束后停止。",
    "限制：程序只按记录的位置点击，无法判断点击是否真正生效，请抽查 EDC 中的结果。",
)


def _target_text(window: WindowInfo | None) -> str:
    return f"{window.title} · {window.process}" if window is not None else _NO_TARGET


class EdcPage(ToolPage):
    USES_CONFIG = True

    def __init__(
        self,
        spec: ToolSpec,
        runner: JobRunner,
        parent: QWidget | None = None,
        config: ConfigStore | None = None,
    ) -> None:
        super().__init__(spec, runner, parent)
        self._store = config if config is not None else ConfigStore()
        self._cfg: EdcConfig = load_config(self._store, legacy_files())
        self._session: EdcSession | None = None
        self._pending_redo: RowStop | None = None
        self._stop_event: threading.Event | None = None
        self._overlay: Any = None
        self._recording_hooks: tuple[Any, ...] = ()
        self._first_capture = False
        self._restore_maximized = False
        self._markers: list[Any] = []
        self.esc_hook = EscHook(parent=self)

        # 目标窗口
        self.target_label = BodyLabel(_target_text(self._cfg.target_window), self)
        self.target_label.setWordWrap(True)
        self.pick_window_button = PushButton("选择窗口…", self)
        target_box = QWidget(self)
        target_layout = QHBoxLayout(target_box)
        target_layout.setContentsMargins(0, 0, 0, 0)
        target_layout.addWidget(self.target_label, 1)
        target_layout.addWidget(self.pick_window_button)
        self.add_section("目标窗口", target_box)

        # 点击位置
        self.position_fields: dict[str, tuple[SpinBox, SpinBox, PushButton]] = {}
        positions_form = ResponsiveForm(self)
        for index, key in enumerate(STEP_KEYS, start=1):
            row = QWidget(self)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            x_spin, y_spin = SpinBox(row), SpinBox(row)
            for spin in (x_spin, y_spin):
                spin.setRange(*_COORD_RANGE)
            redo = PushButton("重录", row)
            row_layout.addWidget(BodyLabel("X", row))
            row_layout.addWidget(x_spin, 1)
            row_layout.addWidget(BodyLabel("Y", row))
            row_layout.addWidget(y_spin, 1)
            row_layout.addWidget(redo)
            positions_form.add_row(f"{index}. {key}", row)
            self.position_fields[key] = (x_spin, y_spin, redo)
        self.record_button = PrimaryPushButton("一键录制", self)
        self.replay_button = PushButton("回放测试", self)
        self.restore_defaults_button = PushButton("恢复默认值", self)
        positions_box = QWidget(self)
        positions_layout = QVBoxLayout(positions_box)
        positions_layout.setContentsMargins(0, 0, 0, 0)
        positions_layout.addWidget(positions_form)
        buttons = QHBoxLayout()
        buttons.addWidget(self.record_button)
        buttons.addWidget(self.replay_button)
        buttons.addStretch(1)
        buttons.addWidget(self.restore_defaults_button)
        positions_layout.addLayout(buttons)
        self.add_section("点击位置", positions_box)

        # 运行参数
        self.max_loops_spin = SpinBox(self)
        self.max_loops_spin.setRange(*MAX_LOOPS_RANGE)
        self.step_delay_spin = DoubleSpinBox(self)
        self.step_delay_spin.setRange(*STEP_DELAY_RANGE)
        self.step_delay_spin.setSingleStep(0.1)
        self.step_delay_spin.setDecimals(1)
        params_form = ResponsiveForm(self)
        params_form.add_row("最多处理行数", self.max_loops_spin, "遇到空单元格会提前结束")
        params_form.add_row("每步间隔（秒）", self.step_delay_spin, "网页反应慢时调大")
        self.add_section("运行参数", params_form)

        # 使用说明
        notes_box = QWidget(self)
        notes_layout = QVBoxLayout(notes_box)
        notes_layout.setContentsMargins(0, 0, 0, 0)
        for text in _NOTES:
            label = BodyLabel(text, notes_box)
            label.setWordWrap(True)
            notes_layout.addWidget(label)
        self.add_section("使用说明", notes_box)

        self._show_config()
        self.run_bar.set_primary_text(_RUN_TEXT)

        for key, (x_spin, y_spin, redo) in self.position_fields.items():
            x_spin.valueChanged.connect(self._on_field_changed)
            y_spin.valueChanged.connect(self._on_field_changed)
            redo.clicked.connect(lambda _checked=False, k=key: self._start_recording((k,)))
        self.max_loops_spin.valueChanged.connect(self._on_field_changed)
        self.step_delay_spin.valueChanged.connect(self._on_field_changed)
        self.pick_window_button.clicked.connect(self._on_pick_window)
        self.record_button.clicked.connect(lambda: self._start_recording(STEP_KEYS))
        self.replay_button.clicked.connect(self._on_replay)
        self.restore_defaults_button.clicked.connect(self._on_restore_defaults)
        self.esc_hook.pressed.connect(self._on_esc_pressed)

    # -- config <-> widgets ------------------------------------------------------------
    def _show_config(self) -> None:
        """Put the config into the widgets without triggering an autosave."""
        cfg = self._cfg
        for key, (x_spin, y_spin, _redo) in self.position_fields.items():
            x, y = cfg.click_positions.get(key, DEFAULT_POSITIONS[key])
            self._set_spin(x_spin, x)
            self._set_spin(y_spin, y)
        self._set_spin(self.max_loops_spin, cfg.max_loops)
        self._set_spin(self.step_delay_spin, cfg.step_delay)
        self.target_label.setText(_target_text(cfg.target_window))

    @staticmethod
    def _set_spin(spin: SpinBox | DoubleSpinBox, value: float) -> None:
        with QSignalBlocker(spin):
            spin.setValue(value)

    def _on_field_changed(self, *_args: object) -> None:
        cfg = self._cfg
        cfg.click_positions = {
            key: (x_spin.value(), y_spin.value())
            for key, (x_spin, y_spin, _redo) in self.position_fields.items()
        }
        cfg.max_loops = self.max_loops_spin.value()
        cfg.step_delay = round(self.step_delay_spin.value(), 1)
        self._save()

    def _save(self) -> None:
        if not save_config(self._store, self._cfg):
            self._warn("配置未保存", "请检查配置文件权限")

    def _set_target(self, window: WindowInfo) -> None:
        self._cfg.target_window = window
        self.target_label.setText(_target_text(window))

    # -- InfoBar helpers ---------------------------------------------------------------
    def _warn(self, title: str, content: str) -> None:
        InfoBar.warning(title, content, parent=self._info_parent(),
                        position=InfoBarPosition.TOP_RIGHT)

    def _success(self, title: str, content: str) -> None:
        InfoBar.success(title, content, parent=self._info_parent(),
                        position=InfoBarPosition.TOP_RIGHT)

    # -- buttons -----------------------------------------------------------------------
    def _on_pick_window(self) -> None:
        chosen = pick_window(self.window(), list_windows(), self._cfg.target_window)
        if chosen is None:
            return
        self._set_target(chosen)
        self._save()

    def _on_replay(self) -> None:
        points = [
            (f"{i}. {key}", *self._cfg.click_positions[key])
            for i, key in enumerate(STEP_KEYS, start=1)
        ]
        self._markers = schedule_replay(points)

    def _on_restore_defaults(self) -> None:
        defaults = EdcConfig()
        self._cfg.click_positions = dict(DEFAULT_POSITIONS)
        self._cfg.max_loops = defaults.max_loops
        self._cfg.step_delay = defaults.step_delay
        self._show_config()
        self._save()
        self._success("已恢复默认值", "目标窗口未改变")

    # -- recording ---------------------------------------------------------------------
    def _bring_to_front(self) -> None:
        """Raise the main window and ask Windows to focus it (the foreground lock may refuse)."""
        window = self.window()
        window.raise_()
        try:
            activate_window(int(window.winId()))
        except Exception:
            pass

    def _start_recording(self, keys: Sequence[str]) -> None:
        # Two live ESC hooks share keyboard's per-key state, so never record during a run.
        if self._overlay is not None or self._running_here():
            return
        mouse_hook = MouseClickHook(parent=self)
        esc_hook = EscHook(parent=self)
        overlay = RecordingOverlay(tuple(keys), mouse_hook, esc_hook)
        self._overlay = overlay
        self._recording_hooks = (mouse_hook, esc_hook)
        self._first_capture = True
        overlay.captured.connect(self._on_captured)
        overlay.finished.connect(self._on_recording_finished)
        overlay.cancelled.connect(self._on_recording_cancelled)
        window = self.window()
        self._restore_maximized = window.isMaximized()
        window.showMinimized()
        overlay.show()

    def _on_captured(self, key: str, x: int, y: int) -> None:
        if key not in self.position_fields:
            return
        x_spin, y_spin, _redo = self.position_fields[key]
        self._set_spin(x_spin, x)
        self._set_spin(y_spin, y)
        self._cfg.click_positions[key] = (x_spin.value(), y_spin.value())
        if self._first_capture:
            self._first_capture = False
            window = window_at(x, y)
            if window is not None:
                self._set_target(window)
        self._save()

    def _end_recording(self) -> None:
        overlay, self._overlay = self._overlay, None
        hooks, self._recording_hooks = self._recording_hooks, ()
        for hook in hooks:
            hook.stop()
            hook.deleteLater()
        if overlay is not None:
            overlay.deleteLater()
        window = self.window()
        if self._restore_maximized:
            window.showMaximized()
        else:
            window.showNormal()
        self._bring_to_front()

    def _on_recording_finished(self) -> None:
        self._end_recording()
        self._success("录制完成", "")

    def _on_recording_cancelled(self) -> None:
        self._end_recording()
        InfoBar.info("已取消录制", "", parent=self._info_parent(),
                     position=InfoBarPosition.TOP_RIGHT)

    # -- run ---------------------------------------------------------------------------
    def _running_here(self) -> bool:
        return self._is_mine() and self._stop_event is not None

    def _on_esc_pressed(self) -> None:
        # A press may be delivered (queued) after the hook was stopped; ignore it then.
        if not (self._running_here() and self.esc_hook.is_active()):
            return
        assert self._stop_event is not None
        self._stop_event.set()
        self.result_panel.append_log("已按 ESC，当前步骤结束后停止")

    def _on_cancel_requested(self) -> None:
        if self._running_here():
            assert self._stop_event is not None
            self._stop_event.set()  # soft stop: finish the current step, then ask

    def _segment_job(self, start: CellRef | None, end_row: int | None) -> JobFn:
        event = threading.Event()
        self._stop_event = event
        cfg = dataclasses.replace(self._cfg, click_positions=dict(self._cfg.click_positions))

        def job(progress, token) -> Result:
            with open_live_ports() as ports:
                return run_segment(cfg, ports, start, end_row, event, progress, token)

        return job

    def current_job_kind(self) -> str:
        return _KIND

    def build_job(self) -> JobFn | None:
        if self._overlay is not None:
            self._warn("正在录制", "请先完成或取消录制")
            return None
        target = self._cfg.target_window
        if target is None:
            self._warn(
                "请先设置目标窗口",
                "请先“一键录制”，或点击“选择窗口…”指定 EDC 所在的浏览器窗口",
            )
            return None
        if find_target(target, list_windows()) is None:
            self._warn("找不到目标窗口", f"{target.title}（{target.process}）未打开，请重新选择窗口")
            return None
        self._session = None
        self._pending_redo = None
        return self._segment_job(None, None)

    def _on_started(self, tool_id: str) -> None:
        super()._on_started(tool_id)
        if tool_id == self.spec.id:
            self.esc_hook.start()

    def on_aux_finished(self, kind: str, result: Result) -> None:
        self.esc_hook.stop()
        if kind != _KIND:
            return
        seg = result.data
        if not isinstance(seg, Segment):
            self._stop_event = None
            return
        self._pending_redo = None  # the continuation segment came back normally
        if self._session is None:
            self._session = EdcSession.begin(seg)
        else:
            self._session.absorb(seg)
        session = self._session
        if seg.stop is not None:
            window = self.window()
            if window.isMinimized():
                window.showNormal()
            self._bring_to_front()
            choice: StopChoice = ask_stop_choice(window, seg.stop)
            nxt = session.resolve(seg.stop, choice)
            if nxt is not None:
                if choice is StopChoice.REDO:
                    self._pending_redo = seg.stop
                self.keep_log_for_next_start(f"—— 从 {nxt.address()} 继续 ——")
                self.submit_job_when_idle(self._segment_job(nxt, session.end_row), _KIND)
                return
        self._finish_session(session)

    def _finish_session(self, session: EdcSession) -> None:
        self._stop_event = None
        self._session = None
        self.result_panel.show_result(session.to_result())
        self.result_panel.append_log("成功的行：")
        for line in session.done_lines():
            self.result_panel.append_log(line)
        ok, skipped, failed = len(session.done), len(session.skipped), len(session.failed)
        if ok > 0 and skipped == 0 and failed == 0:
            self._success("完成", f"成功 {ok} 行")
        elif ok == 0 and skipped == 0 and failed == 0:
            self._warn("没有处理任何行", "选中的单元格为空")
        else:
            self._warn("已结束", f"成功 {ok} 行，跳过 {skipped} 行，出错 {failed} 行")

    def _drop_session(self, reason: str) -> None:
        self._stop_event = None
        session, self._session = self._session, None
        pending, self._pending_redo = self._pending_redo, None
        if session is not None:
            if pending is not None:  # the redo never ran: the row has no result otherwise
                session.failed.append(
                    dataclasses.replace(pending, reason=f"重做未完成：{reason}", by_user=False)
                )
            self.result_panel.show_result(session.to_result())

    def _on_failed(self, tool_id: str, message: str) -> None:
        if tool_id != self.spec.id:
            super()._on_failed(tool_id, message)
            return
        self.esc_hook.stop()
        super()._on_failed(tool_id, message)
        self._drop_session(message)

    def _on_cancelled(self, tool_id: str) -> None:
        if tool_id != self.spec.id:
            super()._on_cancelled(tool_id)
            return
        self.esc_hook.stop()
        super()._on_cancelled(tool_id)
        self._drop_session("已取消")

    # -- ToolPage hooks ----------------------------------------------------------------
    def capture_state(self) -> dict[str, Any]:
        return {}

    def restore_state(self, state: dict[str, Any]) -> list[str]:
        return []

    def summary(self) -> str:
        return ""

    def set_inputs_locked(self, locked: bool) -> None:
        widgets: list[QWidget] = [
            self.pick_window_button,
            self.record_button,
            self.replay_button,
            self.restore_defaults_button,
            self.max_loops_spin,
            self.step_delay_spin,
        ]
        for x_spin, y_spin, redo in self.position_fields.values():
            widgets.extend((x_spin, y_spin, redo))
        for widget in widgets:
            widget.setEnabled(not locked)
