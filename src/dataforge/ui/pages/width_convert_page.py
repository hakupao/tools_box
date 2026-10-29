"""Full-width to half-width tool page."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtWidgets import QFileDialog, QVBoxLayout, QWidget
from qfluentwidgets import CaptionLabel, CheckBox, ComboBox, InfoBar, InfoBarPosition, MessageBox

from dataforge.tools import width_convert
from dataforge.tools.width_convert import WidthOptions
from dataforge.ui.components.file_input import FileInputCard
from dataforge.ui.components.responsive_form import ResponsiveForm
from dataforge.ui.components.tool_page import ToolPage
from dataforge.ui.jobs import JobFn, JobRunner
from dataforge.ui.registry import ToolSpec

_SAME_DIR = 0
_CUSTOM_DIR = 1


class WidthConvertPage(ToolPage):
    def __init__(self, spec: ToolSpec, runner: JobRunner, parent: QWidget | None = None) -> None:
        super().__init__(spec, runner, parent)
        self._output_dir: str | None = None

        self.file_input = FileInputCard("Excel 文件", width_convert.SUPPORTED_EXTENSIONS, parent=self)
        self.add_section("输入", self.file_input)

        self.output_combo = ComboBox(self)
        self.output_combo.addItems(["与原文件相同", "指定文件夹…"])
        self.output_path_label = CaptionLabel("", self)
        self.output_path_label.setWordWrap(True)
        self.output_path_label.setVisible(False)
        output_host = QWidget(self)
        output_layout = QVBoxLayout(output_host)
        output_layout.setContentsMargins(0, 0, 0, 0)
        output_layout.addWidget(self.output_combo)
        output_layout.addWidget(self.output_path_label)

        self.overwrite_box = CheckBox("覆盖原文件", self)

        self.form = ResponsiveForm(self)
        self.form.add_row("输出位置", output_host)
        self.form.add_row("覆盖原文件", self.overwrite_box, "默认不勾选；勾选后运行前会再次确认")
        self.add_section("参数", self.form)

        self.run_bar.primary_button().setText("开始转换")
        self.output_combo.currentIndexChanged.connect(self._on_output_changed)

    # -- output folder -------------------------------------------------------
    def _set_output_dir(self, folder: str | None) -> None:
        self._output_dir = folder
        self.output_path_label.setText(folder or "")
        self.output_path_label.setVisible(bool(folder))

    def _on_output_changed(self, index: int) -> None:
        if index != _CUSTOM_DIR:
            self._set_output_dir(None)
            return
        folder = QFileDialog.getExistingDirectory(self, "选择输出文件夹")
        if folder:
            self._set_output_dir(folder)
        else:
            self.output_combo.setCurrentIndex(_SAME_DIR)

    # -- ToolPage hooks ------------------------------------------------------------
    def build_job(self) -> JobFn | None:
        files = self.file_input.files()
        if not files:
            InfoBar.warning("请先选择文件", "请先选择要转换的 Excel 文件", parent=self._info_parent(),
                            position=InfoBarPosition.TOP_RIGHT)
            return None
        overwrite = self.overwrite_box.isChecked()
        if overwrite:
            box = MessageBox("覆盖原文件", "将直接修改原文件且无法撤销，确定继续吗？", self.window())
            if not box.exec():
                return None
        options = WidthOptions(
            output_dir=Path(self._output_dir) if self._output_dir else None,
            overwrite_source=overwrite,
        )

        def job(progress, token):
            return width_convert.run(files, options, progress, token)

        return job

    def capture_state(self) -> dict[str, Any]:
        return {
            "files": [str(p) for p in self.file_input.files()],
            "output_dir": self._output_dir,
            "overwrite_source": self.overwrite_box.isChecked(),
        }

    def restore_state(self, state: dict[str, Any]) -> list[str]:
        saved = [str(p) for p in state.get("files", [])]
        existing = [Path(p) for p in saved if Path(p).is_file()]
        missing = [p for p in saved if not Path(p).is_file()]
        self.file_input.set_files(existing)
        folder = state.get("output_dir")
        self.output_combo.blockSignals(True)
        self.output_combo.setCurrentIndex(_CUSTOM_DIR if folder else _SAME_DIR)
        self.output_combo.blockSignals(False)
        self._set_output_dir(folder or None)
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
        self.output_combo.setEnabled(not locked)
        self.overwrite_box.setEnabled(not locked)
