from __future__ import annotations

import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QFileDialog, QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import BodyLabel, CaptionLabel, PrimaryPushButton, ProgressBar, PushButton, TitleLabel

from ...utils.codelist_process import CodelistProcessor
from ..qt_common import FileListWidget, show_error, show_info, show_warning


class CodelistProcessorPage(QWidget):
    def __init__(self, main_window) -> None:
        super().__init__()
        self.setObjectName("codelist_processor")
        self.main_window = main_window

        self.output_path: str | None = None
        self.processor = CodelistProcessor()

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(16)

        header_layout = QHBoxLayout()
        header_left = QVBoxLayout()
        title = TitleLabel("Codelist 处理工具")
        subtitle = BodyLabel("根据 Codelist 规则处理 CSV")
        subtitle.setTextColor("#6B7280", "#6B7280")
        header_left.addWidget(title)
        header_left.addWidget(subtitle)
        header_left.addStretch(1)

        back_btn = PushButton("返回主页")
        back_btn.clicked.connect(lambda: self.main_window.switch_to(self.main_window.home_interface))

        header_layout.addLayout(header_left, stretch=1)
        header_layout.addWidget(back_btn, alignment=Qt.AlignRight | Qt.AlignTop)
        layout.addLayout(header_layout)

        action_row = QHBoxLayout()
        upload_codelist_btn = PushButton("上传 Codelist")
        upload_codelist_btn.clicked.connect(self.select_codelist_file)
        select_file_btn = PushButton("选择文件")
        select_file_btn.clicked.connect(self.select_file)
        select_folder_btn = PushButton("选择文件夹")
        select_folder_btn.clicked.connect(self.select_folder)
        clear_btn = PushButton("清空列表")
        clear_btn.clicked.connect(self.clear_file_list)

        action_row.addWidget(upload_codelist_btn)
        action_row.addWidget(select_file_btn)
        action_row.addWidget(select_folder_btn)
        action_row.addWidget(clear_btn)
        action_row.addStretch(1)
        layout.addLayout(action_row)

        self.file_list = FileListWidget(allowed_exts=[".csv"])
        layout.addWidget(self.file_list, stretch=1)

        output_row = QHBoxLayout()
        output_label = BodyLabel("输出路径")
        self.output_note = CaptionLabel("默认输出到原文件所在目录")
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

        self.process_btn = PrimaryPushButton("开始处理")
        self.process_btn.clicked.connect(self.process_files)
        layout.addWidget(self.process_btn, alignment=Qt.AlignLeft)

        self.status_label = CaptionLabel("")
        self.status_label.setTextColor("#7A8190", "#7A8190")
        layout.addWidget(self.status_label)

    def select_codelist_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, "选择 Codelist 文件", "", "Excel 文件 (*.xlsx)")
        if file_path:
            try:
                self.processor.select_codelist_file(file_path)
                self.status_label.setText(f"已加载 Codelist: {os.path.basename(file_path)}")
            except Exception as exc:  # pylint: disable=broad-except
                show_error(self, "错误", f"加载 Codelist 时发生错误: {exc}")

    def select_file(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, "选择 CSV 文件", "", "CSV 文件 (*.csv)")
        if files:
            self.file_list.add_paths(files)

    def select_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "选择包含 CSV 文件的文件夹")
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
        self.progress_label.setText(f"正在处理: {current_file} ({current}/{total}) | {progress}%")
        QApplication.processEvents()

    def process_files(self) -> None:
        files = self.file_list.paths()
        if not files:
            show_warning(self, "警告", "请先选择要处理的 CSV 文件！")
            return

        if not getattr(self.processor, "codelist_file", None):
            show_warning(self, "警告", "请先上传 Codelist 文件！")
            return

        self.process_btn.setEnabled(False)
        try:
            total = len(files)
            success_count = 0
            error_files = []

            for i, file in enumerate(files, 1):
                try:
                    self.update_progress(i, total, os.path.basename(file))
                    success = self.processor.process_csv_file(file, self.output_path)
                    if success:
                        success_count += 1
                    else:
                        error_files.append(file)
                except Exception as exc:  # pylint: disable=broad-except
                    error_files.append(f"{file} (错误: {exc})")

            if error_files:
                error_msg = "以下文件处理失败：\n\n" + "\n".join(error_files)
                show_warning(self, "处理完成", f"成功处理 {success_count}/{total} 个文件\n\n{error_msg}")
            else:
                show_info(self, "处理完成", f"成功处理所有 {total} 个文件！")

            self.progress_bar.setValue(0)
            self.progress_label.setText("")
        except Exception as exc:  # pylint: disable=broad-except
            show_error(self, "错误", f"处理过程中发生错误：{exc}")
        finally:
            self.process_btn.setEnabled(True)

    def clear_file_list(self) -> None:
        self.file_list.clear()
        self.status_label.setText("")
