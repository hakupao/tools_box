from __future__ import annotations

import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QFileDialog, QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    CheckBox,
    LineEdit,
    PrimaryPushButton,
    SpinBox,
    TextEdit,
    TitleLabel,
)

from ...utils.file_field_extractor import FileFieldExtractor
from ..qt_common import show_error, show_info, show_warning, mono_font


class FileFieldExtractorPage(QWidget):
    def __init__(self, main_window) -> None:
        super().__init__()
        self.setObjectName("file_field_extractor")
        self.main_window = main_window

        self.extractor = FileFieldExtractor()
        self.output_file: str | None = None

        self._build_ui()
        self.setAcceptDrops(True)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(16)

        header_layout = QHBoxLayout()
        header_left = QVBoxLayout()
        title = TitleLabel("获取文件字段")
        subtitle = BodyLabel("批量提取 CSV / XLSX 字段并输出汇总")
        subtitle.setTextColor("#6B7280", "#6B7280")
        header_left.addWidget(title)
        header_left.addWidget(subtitle)
        header_left.addStretch(1)

        back_btn = PrimaryPushButton("返回主页")
        back_btn.clicked.connect(lambda: self.main_window.switch_to(self.main_window.home_interface))

        header_layout.addLayout(header_left, stretch=1)
        header_layout.addWidget(back_btn, alignment=Qt.AlignRight | Qt.AlignTop)
        layout.addLayout(header_layout)

        path_row = QHBoxLayout()
        path_label = BodyLabel("文件夹路径")
        self.path_input = LineEdit()
        self.path_input.setPlaceholderText("选择包含数据文件的文件夹")
        select_btn = PrimaryPushButton("选择文件夹")
        select_btn.clicked.connect(self.select_folder)
        clear_button = PrimaryPushButton("清空")
        clear_button.clicked.connect(self.clear_folder_path)

        path_row.addWidget(path_label)
        path_row.addWidget(self.path_input, stretch=1)
        path_row.addWidget(select_btn)
        path_row.addWidget(clear_button)
        layout.addLayout(path_row)

        option_row = QHBoxLayout()
        self.include_subfolders = CheckBox("包含子文件夹")
        header_label = BodyLabel("列名行")
        self.header_spin = SpinBox()
        self.header_spin.setRange(1, 999)
        self.header_spin.setValue(1)

        option_row.addWidget(self.include_subfolders)
        option_row.addSpacing(16)
        option_row.addWidget(header_label)
        option_row.addWidget(self.header_spin)
        option_row.addStretch(1)
        layout.addLayout(option_row)

        self.progress_label = CaptionLabel("")
        self.progress_label.setTextColor("#7A8190", "#7A8190")
        layout.addWidget(self.progress_label)

        self.extract_btn = PrimaryPushButton("开始提取字段")
        self.extract_btn.clicked.connect(self.start_extraction)
        layout.addWidget(self.extract_btn, alignment=Qt.AlignLeft)

        log_label = BodyLabel("字段预览")
        layout.addWidget(log_label)

        self.log_text = TextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(mono_font(10))
        layout.addWidget(self.log_text, stretch=1)

    def select_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "选择包含数据文件的文件夹")
        if folder:
            self.path_input.setText(folder)

    def clear_folder_path(self) -> None:
        self.path_input.clear()
        self.progress_label.setText("")
        self.log_text.clear()

    def start_extraction(self) -> None:
        folder_path = self.path_input.text().strip()
        if not folder_path:
            show_warning(self, "提示", "请先选择文件夹路径。")
            return

        try:
            header_row = int(self.header_spin.value())
        except ValueError:
            show_warning(self, "提示", "列名行请输入有效的数字。")
            return

        if header_row < 1:
            show_warning(self, "提示", "列名行必须大于等于 1。")
            return

        self.extract_btn.setEnabled(False)
        self.progress_label.setText("")
        self.log_text.setPlainText("开始提取字段...\n")

        try:
            result = self.extractor.extract_fields(
                folder_path,
                include_subfolders=self.include_subfolders.isChecked(),
                header_row=header_row,
                progress_callback=self.update_progress,
            )

            output_file = result["output_file"]
            errors = result["errors"]
            details = result["details"]
            total_fields = result["total_fields"]
            processed_files = result["processed_files"]

            preview_lines = [f"输出文件：{output_file}"]
            preview_lines.append(f"共处理 {processed_files} 个文件，提取字段 {total_fields} 个。")
            if errors:
                preview_lines.append("\n出现问题的文件：")
                preview_lines.extend(f"- {err}" for err in errors)

            preview_lines.append("\n字段列表预览：")
            for rel_path, fields in self._format_details(folder_path, details):
                if not fields:
                    preview_lines.append(f"{rel_path} -> 未检测到字段")
                else:
                    preview_lines.append(f"{rel_path}:")
                    preview_lines.extend(f"  - {field}" for field in fields[:20])
                    if len(fields) > 20:
                        preview_lines.append("  ...")

            self.log_text.setPlainText("\n".join(preview_lines))
            show_info(self, "完成", f"字段提取完成！结果已保存至：\n{output_file}")

        except Exception as exc:  # pylint: disable=broad-except
            show_error(self, "错误", f"提取字段时发生错误：{exc}")
            self.log_text.setPlainText(f"提取失败：{exc}")
        finally:
            self.extract_btn.setEnabled(True)
            self.progress_label.setText("")

    def update_progress(self, current: int, total: int, filename: str) -> None:
        if total <= 0:
            return
        progress = int((current / total) * 100)
        self.progress_label.setText(f"正在处理：{filename} ({current}/{total}) | {progress}%")
        QApplication.processEvents()

    def _format_details(self, folder_path: str, details):
        formatted = []
        for absolute_path, fields in details.items():
            rel = os.path.relpath(absolute_path, folder_path)
            formatted.append((rel, fields))
        formatted.sort()
        return formatted

    def dragEnterEvent(self, event):  # noqa: N802
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):  # noqa: N802
        if not event.mimeData().hasUrls():
            return
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path and os.path.isdir(path):
                self.path_input.setText(path)
                return
