"""Field extraction tool page: summarise the header fields of a folder's files."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtWidgets import QWidget
from qfluentwidgets import CheckBox, InfoBar, InfoBarPosition, SpinBox

from dataforge.core.result import Result
from dataforge.tools import field_extract
from dataforge.tools.field_extract import FieldOptions
from dataforge.ui.components.encoding_field import EncodingField
from dataforge.ui.components.folder_picker import FolderPicker
from dataforge.ui.components.output_location import OutputLocationField
from dataforge.ui.components.responsive_form import ResponsiveForm
from dataforge.ui.components.tool_page import ToolPage
from dataforge.ui.jobs import JobFn, JobRunner
from dataforge.ui.registry import ToolSpec


class FieldExtractPage(ToolPage):
    # The summary is a single file, so a retry re-runs everything and replaces the first run.
    RETRY_MERGES = False

    def __init__(self, spec: ToolSpec, runner: JobRunner, parent: QWidget | None = None) -> None:
        super().__init__(spec, runner, parent)

        self.folder_picker = FolderPicker(self)
        self.add_section("输入", self.folder_picker)

        self.header_spin = SpinBox(self)
        self.header_spin.setRange(1, 1000)
        self.header_spin.setValue(1)
        self.subfolder_box = CheckBox("包含子文件夹", self)
        self.encoding_field = EncodingField(self)
        self.output_field = OutputLocationField(self, same_label="所选文件夹")

        self.form = ResponsiveForm(self)
        self.form.add_row("列名行号", self.header_spin, "表头所在的行（从 1 开始）")
        self.form.add_row("包含子文件夹", self.subfolder_box)
        self.form.add_row("编码", self.encoding_field, "仅对 CSV 有效；自动识别有歧义时会询问")
        self.form.add_row("汇总输出位置", self.output_field)
        self.add_section("参数", self.form)

        self.run_bar.primary_button().setText("开始获取")

    def _options(self, folder: Path) -> FieldOptions:
        return FieldOptions(
            header_row=self.header_spin.value(),
            include_subfolders=self.subfolder_box.isChecked(),
            output_dir=self.output_field.output_dir(),
            encoding=self.encoding_field.encoding(),
        )

    # -- ToolPage hooks ------------------------------------------------------------
    def build_job(self) -> JobFn | None:
        folder = self.folder_picker.folder()
        if folder is None:
            InfoBar.warning("请先选择文件夹", "请先选择要读取的文件夹", parent=self._info_parent(),
                            position=InfoBarPosition.TOP_RIGHT)
            return None
        options = self._options(folder)

        def job(progress, token):
            return field_extract.run(folder, options, progress, token)

        return job

    def build_retry_job(self, encodings: dict[str, str]) -> JobFn | None:
        folder = self.folder_picker.folder()
        carried = self.carried_result()
        if folder is None or carried is None:
            return None
        options = self._options(folder)
        options.encodings = dict(encodings)
        old_outputs = list(carried.outputs)
        old_warnings = list(carried.warnings)

        def job(progress, token):
            # Runs on the worker: drop the first-run summary so only one remains.
            for old in old_outputs:
                try:
                    Path(old).unlink()
                except FileNotFoundError:
                    pass
            result: Result = field_extract.run(folder, options, progress, token)
            # Files still unanswered were already reported as skipped in the first run.
            result.encoding_questions = []
            result.warnings = old_warnings + result.warnings
            return result

        return job

    def capture_state(self) -> dict[str, Any]:
        folder = self.folder_picker.folder()
        out_dir = self.output_field.output_dir()
        return {
            "folder": str(folder) if folder else None,
            "header_row": self.header_spin.value(),
            "include_subfolders": self.subfolder_box.isChecked(),
            "encoding": self.encoding_field.encoding(),
            "output_dir": str(out_dir) if out_dir else None,
        }

    def restore_state(self, state: dict[str, Any]) -> list[str]:
        missing: list[str] = []
        saved = state.get("folder")
        if saved and Path(saved).is_dir():
            self.folder_picker.set_folder(Path(saved))
        else:
            self.folder_picker.set_folder(None)
            if saved:
                missing.append(str(saved))
        self.header_spin.setValue(int(state.get("header_row", 1)))
        self.subfolder_box.setChecked(bool(state.get("include_subfolders", False)))
        self.encoding_field.set_encoding(state.get("encoding"))
        self.output_field.set_output_dir(state.get("output_dir") or None)
        return missing

    def summary(self) -> str:
        folder = self.folder_picker.folder()
        return folder.name if folder else ""

    def set_inputs_locked(self, locked: bool) -> None:
        self.folder_picker.set_locked(locked)
        self.header_spin.setEnabled(not locked)
        self.subfolder_box.setEnabled(not locked)
        self.encoding_field.setEnabled(not locked)
        self.output_field.setEnabled(not locked)
