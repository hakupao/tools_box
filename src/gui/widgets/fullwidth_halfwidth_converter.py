from __future__ import annotations

import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QFileDialog, QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import BodyLabel, CaptionLabel, PrimaryPushButton, ProgressBar, PushButton, TitleLabel

from ...utils.fullwidth_to_halfwidth_converter import FullwidthToHalfwidthConverter
from ..qt_common import FileListWidget, ask_yes_no, show_error, show_info, show_warning


class FullwidthHalfwidthConverterPage(QWidget):
    def __init__(self, main_window) -> None:
        super().__init__()
        self.setObjectName("fullwidth_halfwidth")
        self.main_window = main_window

        self.output_path: str | None = None
        self.converter = FullwidthToHalfwidthConverter()

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(16)

        header_layout = QHBoxLayout()
        header_left = QVBoxLayout()
        title = TitleLabel("全角转半角工具")
        subtitle = BodyLabel("将 Excel 文件中的全角字符转换为半角")
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
        select_file_btn = PushButton("选择文件")
        select_file_btn.clicked.connect(self.select_file)
        select_folder_btn = PushButton("选择文件夹")
        select_folder_btn.clicked.connect(self.select_folder)
        clear_btn = PushButton("清空列表")
        clear_btn.clicked.connect(self.clear_file_list)

        action_row.addWidget(select_file_btn)
        action_row.addWidget(select_folder_btn)
        action_row.addWidget(clear_btn)
        action_row.addStretch(1)
        layout.addLayout(action_row)

        self.file_list = FileListWidget(allowed_exts=[".xlsx"])
        layout.addWidget(self.file_list, stretch=1)

        output_row = QHBoxLayout()
        output_label = BodyLabel("输出路径")
        self.output_note = CaptionLabel("默认直接覆盖原文件")
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

    def select_file(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, "选择 Excel 文件", "", "Excel 文件 (*.xlsx)")
        if files:
            self.file_list.add_paths(files)

    def select_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "选择包含 Excel 文件的文件夹")
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

    def convert_files(self) -> None:
        files = self.file_list.paths()
        if not files:
            show_warning(self, "警告", "请先选择要转换的 Excel 文件！")
            return

        if self.output_path is None:
            if not ask_yes_no(self, "确认操作", f"即将转换 {len(files)} 个文件，原文件将被覆盖。\n\n是否继续？"):
                return

        self.convert_btn.setEnabled(False)
        try:
            total = len(files)
            success_count = 0
            error_files = []

            for i, file in enumerate(files, 1):
                try:
                    self.update_progress(i, total, os.path.basename(file))
                    success = self.converter.convert_file(file, self.output_path)
                    if success:
                        success_count += 1
                    else:
                        error_files.append(file)
                except Exception as exc:  # pylint: disable=broad-except
                    error_files.append(f"{file} (错误: {exc})")

            if error_files:
                error_msg = "以下文件转换失败：\n\n" + "\n".join(error_files)
                show_warning(self, "转换完成", f"成功转换 {success_count}/{total} 个文件\n\n{error_msg}")
            else:
                if self.output_path is None:
                    show_info(self, "转换完成", f"成功转换所有 {total} 个文件！\n原文件已更新")
                else:
                    show_info(self, "转换完成", f"成功转换所有 {total} 个文件！\n文件已保存到指定目录")

            self.progress_bar.setValue(0)
            self.progress_label.setText("")
        except Exception as exc:  # pylint: disable=broad-except
            show_error(self, "错误", f"转换过程中发生错误：{exc}")
        finally:
            self.convert_btn.setEnabled(True)

    def clear_file_list(self) -> None:
        self.file_list.clear()
        self.status_label.setText("")
