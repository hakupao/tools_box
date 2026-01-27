from __future__ import annotations

import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QFileDialog, QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    ComboBox,
    PrimaryPushButton,
    ProgressBar,
    PushButton,
    TitleLabel,
)

from ...utils.csv_encoding_converter import CsvEncodingConverter
from ...utils.csv_to_xlsx_converter import CsvToXlsxConverter
from ...utils.xlsx_to_csv_converter import XlsxToCsvConverter
from ..qt_common import FileListWidget, show_error, show_info, show_warning


class FileFormatConverterPage(QWidget):
    """文件格式转换页面：CSV/XLSX/BOM 三种模式。"""

    def __init__(self, main_window) -> None:
        super().__init__()
        self.setObjectName("file_format")
        self.main_window = main_window

        self.output_path: str | None = None
        self.csv_to_xlsx = CsvToXlsxConverter()
        self.xlsx_to_csv = XlsxToCsvConverter()
        self.csv_bom = CsvEncodingConverter()

        self.mode_config = {
            "csv_to_xlsx": {
                "label": "CSV 转 XLSX",
                "input_exts": [".csv"],
                "output_note": "默认输出到原文件所在目录",
            },
            "xlsx_to_csv": {
                "label": "XLSX 转 CSV（UTF-8 BOM）",
                "input_exts": [".xlsx"],
                "output_note": "默认输出到原文件所在目录（UTF-8 BOM）",
            },
            "csv_bom": {
                "label": "CSV 转 UTF-8(BOM)",
                "input_exts": [".csv"],
                "output_note": "默认覆盖原文件；选择输出路径则另存",
            },
        }

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(16)

        header_layout = QHBoxLayout()
        header_left = QVBoxLayout()
        title = TitleLabel("文件格式转换")
        subtitle = BodyLabel("CSV / XLSX / UTF-8 BOM 一体化转换")
        subtitle.setTextColor("#6B7280", "#6B7280")
        header_left.addWidget(title)
        header_left.addWidget(subtitle)
        header_left.addStretch(1)

        back_btn = PushButton("返回主页")
        back_btn.clicked.connect(lambda: self.main_window.switch_to(self.main_window.home_interface))
        header_layout.addLayout(header_left, stretch=1)
        header_layout.addWidget(back_btn, alignment=Qt.AlignRight | Qt.AlignTop)
        layout.addLayout(header_layout)

        mode_row = QHBoxLayout()
        mode_label = BodyLabel("转换模式")
        self.mode_combo = ComboBox()
        for key, cfg in self.mode_config.items():
            self.mode_combo.addItem(cfg["label"], userData=key)
        self.mode_combo.currentIndexChanged.connect(self.on_mode_change)

        mode_row.addWidget(mode_label)
        mode_row.addWidget(self.mode_combo, stretch=1)
        mode_row.addStretch(1)
        layout.addLayout(mode_row)

        self.info_label = CaptionLabel("当前模式：CSV 转 XLSX")
        self.info_label.setTextColor("#7A8190", "#7A8190")
        layout.addWidget(self.info_label)

        action_row = QHBoxLayout()
        select_folder_btn = PushButton("选择文件夹")
        select_folder_btn.clicked.connect(self.select_folder)
        select_file_btn = PushButton("选择文件")
        select_file_btn.clicked.connect(self.select_file)
        clear_btn = PushButton("清空列表")
        clear_btn.clicked.connect(self.clear_file_list)

        action_row.addWidget(select_folder_btn)
        action_row.addWidget(select_file_btn)
        action_row.addWidget(clear_btn)
        action_row.addStretch(1)
        layout.addLayout(action_row)

        self.file_list = FileListWidget(allowed_exts=self.mode_config["csv_to_xlsx"]["input_exts"])
        layout.addWidget(self.file_list, stretch=1)

        output_row = QHBoxLayout()
        output_label = BodyLabel("输出路径")
        self.output_note = CaptionLabel(self.mode_config["csv_to_xlsx"]["output_note"])
        self.output_note.setTextColor("#7A8190", "#7A8190")
        select_output_btn = PushButton("选择输出路径")
        select_output_btn.clicked.connect(self.select_output_path)

        output_row.addWidget(output_label)
        output_row.addWidget(self.output_note, stretch=1)
        output_row.addWidget(select_output_btn)
        layout.addLayout(output_row)

        self.progress_bar = ProgressBar()
        self.progress_bar.setValue(0)
        self.progress_label = CaptionLabel("")
        self.progress_label.setTextColor("#7A8190", "#7A8190")
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.progress_label)

        self.convert_btn = PrimaryPushButton("开始转换")
        self.convert_btn.clicked.connect(self.convert_files)
        layout.addWidget(self.convert_btn, alignment=Qt.AlignLeft)

        self.status_label = CaptionLabel("")
        self.status_label.setTextColor("#7A8190", "#7A8190")
        layout.addWidget(self.status_label)

    def current_mode(self) -> str:
        mode = self.mode_combo.currentData()
        return mode or "csv_to_xlsx"

    def on_mode_change(self) -> None:
        mode = self.current_mode()
        cfg = self.mode_config[mode]
        self.info_label.setText(f"当前模式：{cfg['label']}")
        if self.output_path:
            self.output_note.setText(f"输出到: {self.output_path}")
        else:
            self.output_note.setText(cfg["output_note"])
        removed = self.file_list.filter_by_exts(cfg["input_exts"])
        if removed:
            self.status_label.setText(f"已移除 {removed} 个不符合当前模式的文件")
        else:
            self.status_label.setText("")
        self.file_list.set_allowed_exts(cfg["input_exts"])

    def select_file(self) -> None:
        mode = self.current_mode()
        allowed_exts = self.mode_config[mode]["input_exts"]
        file_filter = "CSV 文件 (*.csv)" if ".csv" in allowed_exts else "Excel 文件 (*.xlsx)"
        files, _ = QFileDialog.getOpenFileNames(self, "选择文件", "", file_filter)
        if files:
            self.file_list.add_paths(files)

    def select_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "选择包含文件的文件夹")
        if folder:
            self.file_list.add_paths([folder])

    def select_output_path(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "选择输出文件夹")
        if folder:
            self.output_path = folder
            self.output_note.setText(f"输出到: {folder}")

    def update_progress(self, current: int, total: int, current_file: str) -> None:
        if total <= 0:
            return
        progress = int((current / total) * 100)
        self.progress_bar.setValue(progress)
        self.progress_label.setText(f"正在处理: {current_file} ({current}/{total})")
        QApplication.processEvents()

    def _convert_single(self, file_path: str):
        mode = self.current_mode()
        if mode == "csv_to_xlsx":
            return self.csv_to_xlsx.convert_file(file_path, self.output_path)
        if mode == "xlsx_to_csv":
            return self.xlsx_to_csv.convert_file(file_path, self.output_path)
        return self.csv_bom.convert_file(file_path, self.output_path)

    def convert_files(self) -> None:
        files = self.file_list.paths()
        if not files:
            show_warning(self, "警告", "请先选择要转换的文件！")
            return

        self.convert_btn.setEnabled(False)

        try:
            total = len(files)
            success_count = 0
            error_files = []

            for i, file in enumerate(files, 1):
                try:
                    self.update_progress(i, total, os.path.basename(file))
                    success, error_msg = self._convert_single(file)
                    if success:
                        success_count += 1
                    else:
                        error_files.append(f"{file} (错误: {error_msg})")
                except Exception as exc:  # pylint: disable=broad-except
                    error_files.append(f"{file} (错误: {exc})")

            if error_files:
                error_msg = "以下文件转换失败：\n\n" + "\n".join(error_files)
                show_warning(self, "转换完成", f"成功转换 {success_count}/{total} 个文件\n\n{error_msg}")
            else:
                show_info(self, "转换完成", f"成功转换所有 {total} 个文件！")

            self.progress_bar.setValue(0)
            self.progress_label.setText("")
        except Exception as exc:  # pylint: disable=broad-except
            show_error(self, "错误", f"转换过程中发生错误：{exc}")
        finally:
            self.convert_btn.setEnabled(True)

    def clear_file_list(self) -> None:
        self.file_list.clear()
        self.status_label.setText("")
