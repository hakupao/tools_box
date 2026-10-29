"""Full-width to half-width tool page."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtWidgets import QWidget
from qfluentwidgets import CheckBox, InfoBar, InfoBarPosition, MessageBox

from dataforge.tools import width_convert
from dataforge.tools.width_convert import WidthOptions
from dataforge.ui.components.file_input import FileInputCard
from dataforge.ui.components.output_location import OutputLocationField
from dataforge.ui.components.responsive_form import ResponsiveForm
from dataforge.ui.components.tool_page import ToolPage
from dataforge.ui.jobs import JobFn, JobRunner
from dataforge.ui.registry import ToolSpec


class WidthConvertPage(ToolPage):
    def __init__(self, spec: ToolSpec, runner: JobRunner, parent: QWidget | None = None) -> None:
        super().__init__(spec, runner, parent)

        self.file_input = FileInputCard("Excel 文件", width_convert.SUPPORTED_EXTENSIONS, parent=self)
        self.add_section("输入", self.file_input)

        self.output_field = OutputLocationField(self)
        self.output_combo = self.output_field.combo

        self.overwrite_box = CheckBox("覆盖原文件", self)

        self.form = ResponsiveForm(self)
        self.form.add_row("输出位置", self.output_field)
        self.form.add_row("覆盖原文件", self.overwrite_box, "默认不勾选；勾选后运行前会再次确认")
        self.add_section("参数", self.form)

        self.run_bar.primary_button().setText("开始转换")
        self.overwrite_box.toggled.connect(self._sync_output_enabled)

    def _sync_output_enabled(self, *_args) -> None:
        self.output_field.setEnabled(not self.overwrite_box.isChecked())

    # -- ToolPage hooks ------------------------------------------------------------
    def build_job(self) -> JobFn | None:
        files = self.file_input.files()
        if not files:
            InfoBar.warning("请先选择文件", "请先选择要转换的 Excel 文件", parent=self._info_parent(),
                            position=InfoBarPosition.TOP_RIGHT)
            return None
        overwrite = self.overwrite_box.isChecked()
        if overwrite:
            box = MessageBox("覆盖原文件", "将直接修改原文件且无法撤销。覆盖后，原文件中的图表、图片、数据透视表等可能丢失。确定继续吗？", self.window())
            try:
                accepted = box.exec()
            finally:
                box.deleteLater()
            if not accepted:
                return None
        options = WidthOptions(
            output_dir=self.output_field.output_dir(),
            overwrite_source=overwrite,
        )

        def job(progress, token):
            return width_convert.run(files, options, progress, token)

        return job

    def capture_state(self) -> dict[str, Any]:
        out_dir = self.output_field.output_dir()
        return {
            "files": [str(p) for p in self.file_input.files()],
            "output_dir": str(out_dir) if out_dir else None,
            "overwrite_source": self.overwrite_box.isChecked(),
        }

    def restore_state(self, state: dict[str, Any]) -> list[str]:
        saved = [str(p) for p in state.get("files", [])]
        existing = [Path(p) for p in saved if Path(p).is_file()]
        missing = [p for p in saved if not Path(p).is_file()]
        self.file_input.set_files(existing)
        self.output_field.set_output_dir(state.get("output_dir") or None)
        self.overwrite_box.setChecked(bool(state.get("overwrite_source", False)))
        return missing

    def summary(self) -> str:
        files = self.file_input.files()
        if not files:
            return ""
        if len(files) == 1:
            return files[0].name
        return f"{files[0].name} 等 {len(files)} 个文件"

    def set_inputs_locked(self, locked: bool) -> None:
        self.file_input.set_locked(locked)
        self.output_field.setEnabled(not locked and not self.overwrite_box.isChecked())
        self.overwrite_box.setEnabled(not locked)
