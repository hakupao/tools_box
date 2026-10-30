"""Data masking tool page: scan the SDTM files, configure, then execute."""
from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import BodyLabel, InfoBar, InfoBarPosition, PushButton

from dataforge.config.legacy import legacy_file_candidates
from dataforge.config.store import ConfigStore
from dataforge.core.errors import DataForgeError
from dataforge.core.result import Result
from dataforge.tools.masking import execute
from dataforge.tools.masking.execute import (
    MaskOptions,
    StaleScanError,
    describe_plan,
    missing_orders,
)
from dataforge.tools.masking.profile import (
    LEGACY_FILE_NAME,
    MaskingProfile,
    load_profile,
    save_profile,
)
from dataforge.tools.masking.scan import (
    ScanReport,
    ScanSettings,
    export_report,
    scan,
    scan_signature,
    select_files,
)
from dataforge.ui.components.encoding_dialog import ask_encodings
from dataforge.ui.components.encoding_field import EncodingField
from dataforge.ui.components.file_input import FileInputCard
from dataforge.ui.components.output_location import OutputLocationField
from dataforge.ui.components.responsive_form import ResponsiveForm
from dataforge.ui.components.tool_page import ToolPage
from dataforge.ui.jobs import JobFn, JobRunner
from dataforge.ui.pages.masking.profile_form import ProfileForm
from dataforge.ui.pages.masking.scan_view import ScanResultView
from dataforge.ui.registry import ToolSpec

_SCAN_TEXT = "开始扫描"
_RUN_TEXT = "开始处理"
_NO_PLAN = "扫描通过后显示"
_REPORT_FILE = "pattern1_scan_report.json"


class MaskingPage(ToolPage):
    USES_CONFIG = True

    def __init__(
        self,
        spec: ToolSpec,
        runner: JobRunner,
        parent: QWidget | None = None,
        config: ConfigStore | None = None,
    ) -> None:
        super().__init__(spec, runner, parent)
        self._config = config if config is not None else ConfigStore()
        self._report: ScanReport | None = None
        self._encodings: dict[str, str] = {}
        self._stale_event: threading.Event | None = None  # set by the current run job

        self.file_input = FileInputCard("SDTM CSV 文件", (".csv",), parent=self)
        self.add_section("输入", self.file_input)

        self.profile_form = ProfileForm(self)
        self.profile_form.set_profile(
            load_profile(self._config, legacy_file_candidates(LEGACY_FILE_NAME))
        )

        self.encoding_field = EncodingField(self)
        self.output_field = OutputLocationField(self, same_label="DM.csv 所在文件夹")
        encoding_form = ResponsiveForm(self)
        encoding_form.add_row("编码", self.encoding_field, "自动识别有歧义时会询问")
        output_form = ResponsiveForm(self)
        output_form.add_row("输出位置", self.output_field)
        scan_box = QWidget(self)
        scan_layout = QVBoxLayout(scan_box)
        scan_layout.setContentsMargins(0, 0, 0, 0)
        scan_layout.addWidget(encoding_form)
        scan_layout.addWidget(self.profile_form.scan_form)
        scan_layout.addWidget(output_form)
        self.add_section("扫描设置", scan_box)

        self.view = ScanResultView(self)
        self.add_section("扫描结果", self.view)

        self.add_section("受试者与 ID", self.profile_form.id_form)

        self.restore_defaults_button = PushButton("恢复默认值", self)
        dm_box = QWidget(self)
        dm_layout = QVBoxLayout(dm_box)
        dm_layout.setContentsMargins(0, 0, 0, 0)
        dm_layout.addWidget(self.profile_form.dm_form)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(self.restore_defaults_button)
        dm_layout.addLayout(buttons)
        self.add_section("日期与 DM", dm_box)

        self._plan_box = QWidget(self)
        self._plan_layout = QVBoxLayout(self._plan_box)
        self._plan_layout.setContentsMargins(0, 0, 0, 0)
        self._plan_labels: list[BodyLabel] = []
        self.add_section("执行摘要", self._plan_box)

        self.file_input.files_changed.connect(self._on_files_changed)
        self.encoding_field.currentIndexChanged.connect(self._invalidate)
        self.profile_form.scan_settings_changed.connect(self._invalidate)
        self.profile_form.changed.connect(self._refresh_plan)
        self.output_field.combo.currentIndexChanged.connect(self._refresh_plan)
        self.view.orders_changed.connect(self._refresh_plan)
        self.view.rescan_requested.connect(self._on_rescan_requested)
        self.view.export_requested.connect(self._on_export_requested)
        self.restore_defaults_button.clicked.connect(self._on_restore_defaults)

        self._invalidate()

    # -- state helpers ---------------------------------------------------------------
    def _scan_paths(self) -> list[Path]:
        """The files scan() will read (same filter), so signatures compare like for like."""
        return select_files(self.file_input.files())

    def _scan_inputs(self) -> tuple[list[Path], ScanSettings, str | None, dict[str, str]]:
        settings = ScanSettings.from_profile(self.profile_form.profile())
        return self._scan_paths(), settings, self.encoding_field.encoding(), dict(self._encodings)

    def _set_report(self, report: ScanReport | None) -> None:
        self._report = report
        self.view.show_report(report)
        self.profile_form.set_preview_source(report.dm_first_usubjid if report else None)
        self.run_bar.set_primary_text(_RUN_TEXT if self.current_job_kind() == "run"
                                      else _SCAN_TEXT)
        self._refresh_plan()

    def _invalidate(self, *_args: object) -> None:
        self._set_report(None)

    def _refresh_plan(self, *_args: object) -> None:
        report = self._report
        if report is None or not report.processable:
            lines = [_NO_PLAN]
        else:
            lines = describe_plan(report, self.profile_form.profile(), self.view.orders(),
                                  self.output_field.output_dir())
        for label in self._plan_labels:
            self._plan_layout.removeWidget(label)
            label.deleteLater()
        self._plan_labels = []
        for line in lines:
            label = BodyLabel(line, self._plan_box)
            label.setWordWrap(True)
            self._plan_layout.addWidget(label)
            self._plan_labels.append(label)

    def summary_lines(self) -> list[str]:
        return [label.text() for label in self._plan_labels]

    def _warn(self, title: str, content: str) -> None:
        InfoBar.warning(title, content, parent=self._info_parent(),
                        position=InfoBarPosition.TOP_RIGHT)

    # -- signal handlers -------------------------------------------------------------
    def _on_files_changed(self, files: list[Path]) -> None:
        keep = {str(p) for p in files}
        self._encodings = {k: v for k, v in self._encodings.items() if k in keep}
        self._invalidate()

    def _on_restore_defaults(self) -> None:
        self.profile_form.set_profile(MaskingProfile())
        InfoBar.success("已恢复默认值", "下次执行时保存", parent=self._info_parent(),
                        position=InfoBarPosition.TOP_RIGHT)

    def _on_rescan_requested(self) -> None:
        job = self._build_scan_job()
        if job is not None:
            self.submit_job(job, "scan")

    def _on_export_requested(self) -> None:
        report = self._report
        if report is None:
            return
        name, selected = QFileDialog.getSaveFileName(
            self, "导出扫描报告", _REPORT_FILE, "JSON (*.json);;CSV (*.csv)"
        )
        if not name:
            return
        target = Path(name)
        if target.suffix.lower() not in (".json", ".csv"):
            target = target.with_name(target.name + (".csv" if "csv" in selected.lower()
                                                      else ".json"))
        pos = InfoBarPosition.TOP_RIGHT
        try:
            export_report(report, target, self.view.orders())
        except (OSError, DataForgeError) as exc:
            InfoBar.error("导出失败", str(exc), parent=self._info_parent(), position=pos)
            return
        InfoBar.success("已导出", str(target), parent=self._info_parent(), position=pos)

    # -- jobs ------------------------------------------------------------------------
    def _build_scan_job(self) -> JobFn | None:
        if not self.file_input.files():
            self._warn("请先添加文件", "请先添加 SDTM CSV 文件")
            return None
        paths, settings, encoding, encodings = self._scan_inputs()

        def job(progress, token):
            return scan(paths, settings, encoding, encodings, progress, token)

        return job

    def _build_run_job(self, report: ScanReport) -> JobFn | None:
        if scan_signature(*self._scan_inputs()) != report.signature:
            self._invalidate()
            self._warn("需要重新扫描", "文件或扫描设置已变化，请重新扫描")
            return None
        orders = self.view.orders()
        missing = missing_orders(report, orders)
        if missing:
            self._warn("请选择日期顺序", f"还有 {len(missing)} 个日期列需要选择 日/月 顺序")
            return None
        profile = self.profile_form.profile()
        if not save_profile(self._config, profile):
            self._warn("配置未保存", "配置保存失败，本次仍按当前设置执行")
        options = MaskOptions(profile, self.output_field.output_dir(), dict(orders))

        stale = threading.Event()
        self._stale_event = stale

        def job(progress, token):
            try:
                return execute.run(report, options, progress, token)
            except StaleScanError:
                stale.set()
                raise

        return job

    # -- ToolPage hooks ----------------------------------------------------------------
    def current_job_kind(self) -> str:
        report = self._report
        return "run" if report is not None and report.processable else "scan"

    def build_job(self) -> JobFn | None:
        report = self._report
        if not self.file_input.files():
            self._warn("请先添加文件", "请先添加 SDTM CSV 文件")
            return None
        if report is not None and report.processable:
            return self._build_run_job(report)
        return self._build_scan_job()

    def on_aux_finished(self, kind: str, result: Result) -> None:
        if kind != "scan":
            return
        self.result_panel.show_result(result)
        report = result.data if isinstance(result.data, ScanReport) else None
        questions = list(result.encoding_questions)
        if questions:
            answers = ask_encodings(self.window(), questions)
            if answers:
                self._encodings.update(answers)
                job = self._build_scan_job()
                if job is not None:
                    # DM and the "exactly one DM" rule span files, so rescan the whole batch.
                    self.submit_job_when_idle(job, "scan")
                    return
        self._set_report(report)
        if report is None:
            return
        pos = InfoBarPosition.TOP_RIGHT
        if report.processable:
            InfoBar.success(
                "扫描通过",
                f"{len(report.files)} 个文件，DM 受试者 {len(report.subjects)} 个",
                parent=self._info_parent(),
                position=pos,
            )
        else:
            first = report.errors[0] if report.errors else "请查看结果区"
            self._warn("扫描未通过", first)

    def _on_failed(self, tool_id: str, message: str) -> None:
        was_run = tool_id == self.spec.id and self._job_kind == "run"
        stale = self._stale_event
        super()._on_failed(tool_id, message)
        if was_run and stale is not None and stale.is_set():
            self._invalidate()  # the files changed since the scan; the report is stale

    def capture_state(self) -> dict[str, Any]:
        out_dir = self.output_field.output_dir()
        return {
            "files": [str(p) for p in self.file_input.files()],
            "encoding": self.encoding_field.encoding(),
            "output_dir": str(out_dir) if out_dir else None,
        }

    def restore_state(self, state: dict[str, Any]) -> list[str]:
        saved = [str(p) for p in state.get("files", [])]
        existing = [Path(p) for p in saved if Path(p).is_file()]
        missing = [p for p in saved if not Path(p).is_file()]
        self.file_input.set_files(existing)
        self.encoding_field.set_encoding(state.get("encoding"))
        self.output_field.set_output_dir(state.get("output_dir") or None)
        self._invalidate()
        return missing

    def summary(self) -> str:
        return f"{len(self.file_input.files())} 个 CSV"

    def set_inputs_locked(self, locked: bool) -> None:
        self.file_input.set_locked(locked)
        self.encoding_field.setEnabled(not locked)
        self.output_field.setEnabled(not locked)
        self.profile_form.set_locked(locked)
        self.view.set_locked(locked)
        self.restore_defaults_button.setEnabled(not locked)
