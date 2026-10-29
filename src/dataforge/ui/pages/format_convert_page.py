"""Format conversion tool page: CSV <-> XLSX, UTF-8 BOM, quote removal."""
from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Any

from PySide6.QtWidgets import QVBoxLayout, QWidget
from qfluentwidgets import (
    CaptionLabel,
    CheckBox,
    InfoBar,
    InfoBarPosition,
    MessageBox,
    SegmentedWidget,
)

from dataforge.tools import format_convert
from dataforge.tools.format_convert import MODE_EXTENSIONS, ConvertMode, FormatOptions
from dataforge.ui.components.confirm import use_chinese_buttons
from dataforge.ui.components.encoding_field import EncodingField
from dataforge.ui.components.file_input import FileInputCard
from dataforge.ui.components.output_location import OutputLocationField
from dataforge.ui.components.responsive_form import ResponsiveForm
from dataforge.ui.components.tool_page import ToolPage
from dataforge.ui.jobs import JobFn, JobRunner
from dataforge.ui.registry import ToolSpec

_MODE_TEXT: dict[ConvertMode, str] = {
    ConvertMode.CSV_TO_XLSX: "CSV → XLSX",
    ConvertMode.XLSX_TO_CSV: "XLSX → CSV",
    ConvertMode.CSV_TO_BOM: "转 UTF-8 BOM",
    ConvertMode.CSV_UNQUOTE: "去除引号",
}
_MODE_DESCRIPTION: dict[ConvertMode, str] = {
    ConvertMode.CSV_TO_XLSX: "每个 CSV 转为一个 XLSX，所有单元格按文本保存",
    ConvertMode.XLSX_TO_CSV: "导出为 UTF-8 BOM 的 CSV，默认只导出第一个工作表",
    ConvertMode.CSV_TO_BOM: "自动识别编码后另存为 UTF-8 BOM",
    ConvertMode.CSV_UNQUOTE: "去掉字段外层引号，内容保持不变",
}
_ENCODING_MODES = (ConvertMode.CSV_TO_XLSX, ConvertMode.CSV_TO_BOM, ConvertMode.CSV_UNQUOTE)
_OVERWRITE_MODES = (ConvertMode.CSV_TO_BOM, ConvertMode.CSV_UNQUOTE)


class FormatConvertPage(ToolPage):
    def __init__(self, spec: ToolSpec, runner: JobRunner, parent: QWidget | None = None) -> None:
        super().__init__(spec, runner, parent)
        self._mode = ConvertMode.CSV_TO_XLSX
        self._first_options: FormatOptions | None = None

        self.mode_bar = SegmentedWidget(self)
        for mode, text in _MODE_TEXT.items():
            self.mode_bar.addItem(mode.value, text, onClick=lambda *_, m=mode: self.set_mode(m))
        self.mode_caption = CaptionLabel("", self)
        self.mode_caption.setWordWrap(True)
        mode_box = QWidget(self)
        mode_layout = QVBoxLayout(mode_box)
        mode_layout.setContentsMargins(0, 0, 0, 0)
        mode_layout.addWidget(self.mode_bar)
        mode_layout.addWidget(self.mode_caption)
        self.add_section("转换方式", mode_box)

        self.file_input = FileInputCard("文件", MODE_EXTENSIONS[self._mode], parent=self)
        self.add_section("输入", self.file_input)

        self.encoding_field = EncodingField(self)
        self.all_sheets_box = CheckBox("导出全部工作表", self)
        self.output_field = OutputLocationField(self)
        self.overwrite_box = CheckBox("覆盖原文件", self)

        self.form = ResponsiveForm(self)
        self.form.add_row("编码", self.encoding_field, "自动识别有歧义时会询问")
        self.form.add_row("全部工作表", self.all_sheets_box, "默认只导出第一个工作表")
        self.form.add_row("输出位置", self.output_field)
        self.form.add_row("覆盖原文件", self.overwrite_box, "默认不勾选；勾选后运行前会再次确认")
        self.add_section("参数", self.form)

        self.run_bar.primary_button().setText("开始转换")
        self.overwrite_box.toggled.connect(self._sync_output_enabled)
        self._show_mode(notify=False)

    # -- mode handling -------------------------------------------------------------
    def mode(self) -> ConvertMode:
        return self._mode

    def set_mode(self, mode: ConvertMode, notify: bool = True) -> None:
        self._mode = mode
        self._show_mode(notify)

    def _show_mode(self, notify: bool) -> None:
        mode = self._mode
        self.mode_bar.setCurrentItem(mode.value)
        self.mode_caption.setText(_MODE_DESCRIPTION[mode])
        removed = self.file_input.set_extensions(MODE_EXTENSIONS[mode])
        if removed and notify:
            InfoBar.info("已移除不符的文件", f"已移除 {len(removed)} 个与当前转换方式不符的文件",
                         parent=self._info_parent(), position=InfoBarPosition.TOP_RIGHT)
        self.form.set_row_visible(self.encoding_field, mode in _ENCODING_MODES)
        self.form.set_row_visible(self.all_sheets_box, mode is ConvertMode.XLSX_TO_CSV)
        can_overwrite = mode in _OVERWRITE_MODES
        if not can_overwrite:
            self.overwrite_box.setChecked(False)  # a hidden tick must never take effect
        self.form.set_row_visible(self.overwrite_box, can_overwrite)
        self._sync_output_enabled()

    def _sync_output_enabled(self, *_args) -> None:
        self.output_field.setEnabled(not self.overwrite_box.isChecked())

    # -- ToolPage hooks ------------------------------------------------------------
    def build_job(self) -> JobFn | None:
        files = self.file_input.files()
        if not files:
            InfoBar.warning("请先选择文件", "请先选择要转换的文件", parent=self._info_parent(),
                            position=InfoBarPosition.TOP_RIGHT)
            return None
        overwrite = self.overwrite_box.isChecked() and self._mode in _OVERWRITE_MODES
        if overwrite:
            box = use_chinese_buttons(MessageBox("覆盖原文件", "将直接修改原文件且无法撤销。确定继续吗？", self.window()))
            try:
                accepted = box.exec()
            finally:
                box.deleteLater()
            if not accepted:
                return None
        options = FormatOptions(
            mode=self._mode,
            output_dir=self.output_field.output_dir(),
            overwrite_source=overwrite,
            all_sheets=self.all_sheets_box.isChecked(),
            encoding=self.encoding_field.encoding(),
        )
        self._first_options = options

        def job(progress, token):
            return format_convert.run(files, options, progress, token)

        return job

    def build_retry_job(self, encodings: dict[str, str]) -> JobFn | None:
        first = self._first_options
        if first is None or not encodings:
            return None
        options = dataclasses.replace(first, encodings=dict(encodings))
        files = [Path(p) for p in encodings]

        def job(progress, token):
            return format_convert.run(files, options, progress, token)

        return job

    def capture_state(self) -> dict[str, Any]:
        out_dir = self.output_field.output_dir()
        return {
            "mode": self._mode.value,
            "files": [str(p) for p in self.file_input.files()],
            "encoding": self.encoding_field.encoding(),
            "all_sheets": self.all_sheets_box.isChecked(),
            "output_dir": str(out_dir) if out_dir else None,
            "overwrite_source": self.overwrite_box.isChecked(),
        }

    def restore_state(self, state: dict[str, Any]) -> list[str]:
        try:
            mode = ConvertMode(state.get("mode", ConvertMode.CSV_TO_XLSX.value))
        except ValueError:
            mode = ConvertMode.CSV_TO_XLSX
        self.set_mode(mode, notify=False)
        saved = [str(p) for p in state.get("files", [])]
        existing = [Path(p) for p in saved if Path(p).is_file()]
        missing = [p for p in saved if not Path(p).is_file()]
        self.file_input.set_files(existing)
        self.encoding_field.set_encoding(state.get("encoding"))
        self.all_sheets_box.setChecked(bool(state.get("all_sheets", False)))
        self.output_field.set_output_dir(state.get("output_dir") or None)
        self.overwrite_box.setChecked(
            bool(state.get("overwrite_source", False)) and mode in _OVERWRITE_MODES
        )
        return missing

    def summary(self) -> str:
        files = self.file_input.files()
        if not files:
            return ""
        label = _MODE_TEXT[self._mode]
        if len(files) == 1:
            return f"{label} · {files[0].name}"
        return f"{label} · {files[0].name} 等 {len(files)} 个文件"

    def set_inputs_locked(self, locked: bool) -> None:
        self.mode_bar.setEnabled(not locked)
        self.file_input.set_locked(locked)
        self.encoding_field.setEnabled(not locked)
        self.all_sheets_box.setEnabled(not locked)
        self.output_field.setEnabled(not locked and not self.overwrite_box.isChecked())
        self.overwrite_box.setEnabled(not locked)
