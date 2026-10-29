"""Sheet split tool page: every worksheet becomes one CSV."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtWidgets import QWidget
from qfluentwidgets import InfoBar, InfoBarPosition

from dataforge.tools import sheet_split
from dataforge.tools.sheet_split import SplitOptions
from dataforge.ui.components.file_input import FileInputCard
from dataforge.ui.components.output_location import OutputLocationField
from dataforge.ui.components.responsive_form import ResponsiveForm
from dataforge.ui.components.tool_page import ToolPage
from dataforge.ui.jobs import JobFn, JobRunner
from dataforge.ui.registry import ToolSpec


class SheetSplitPage(ToolPage):
    def __init__(self, spec: ToolSpec, runner: JobRunner, parent: QWidget | None = None) -> None:
        super().__init__(spec, runner, parent)

        self.file_input = FileInputCard("Excel 文件", sheet_split.SUPPORTED_EXTENSIONS, parent=self)
        self.add_section("输入", self.file_input)

        self.output_field = OutputLocationField(self)
        self.form = ResponsiveForm(self)
        self.form.add_row("输出位置", self.output_field)
        self.add_section("参数", self.form)

        self.run_bar.primary_button().setText("开始拆分")

    # -- ToolPage hooks ------------------------------------------------------------
    def build_job(self) -> JobFn | None:
        files = self.file_input.files()
        if not files:
            InfoBar.warning("请先选择文件", "请先选择要拆分的 Excel 文件", parent=self._info_parent(),
                            position=InfoBarPosition.TOP_RIGHT)
            return None
        options = SplitOptions(output_dir=self.output_field.output_dir())

        def job(progress, token):
            return sheet_split.run(files, options, progress, token)

        return job

    def capture_state(self) -> dict[str, Any]:
        out_dir = self.output_field.output_dir()
        return {
            "files": [str(p) for p in self.file_input.files()],
            "output_dir": str(out_dir) if out_dir else None,
        }

    def restore_state(self, state: dict[str, Any]) -> list[str]:
        saved = [str(p) for p in state.get("files", [])]
        existing = [Path(p) for p in saved if Path(p).is_file()]
        missing = [p for p in saved if not Path(p).is_file()]
        self.file_input.set_files(existing)
        self.output_field.set_output_dir(state.get("output_dir") or None)
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
        self.output_field.setEnabled(not locked)
