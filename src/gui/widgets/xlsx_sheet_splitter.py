from __future__ import annotations

import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QFileDialog, QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import BodyLabel, CaptionLabel, LineEdit, PrimaryPushButton, ProgressBar, PushButton, TitleLabel

from ...utils.xlsx_sheet_splitter import XlsxSheetSplitter
from ..qt_common import show_error, show_info, show_warning


class XlsxSheetSplitterPage(QWidget):
    def __init__(self, main_window) -> None:
        super().__init__()
        self.setObjectName("xlsx_sheet_splitter")
        self.main_window = main_window

        self.output_path: str | None = None
        self.sheet_splitter = XlsxSheetSplitter()

        self._build_ui()
        self.setAcceptDrops(True)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(16)

        header_layout = QHBoxLayout()
        header_left = QVBoxLayout()
        title = TitleLabel("工作表拆分工具")
        subtitle = BodyLabel("每次只支持处理一个 Excel 文件")
        subtitle.setTextColor("#6B7280", "#6B7280")
        header_left.addWidget(title)
        header_left.addWidget(subtitle)
        header_left.addStretch(1)

        back_btn = PushButton("返回主页")
        back_btn.clicked.connect(lambda: self.main_window.switch_to(self.main_window.home_interface))

        header_layout.addLayout(header_left, stretch=1)
        header_layout.addWidget(back_btn, alignment=Qt.AlignRight | Qt.AlignTop)
        layout.addLayout(header_layout)

        file_row = QHBoxLayout()
        file_label = BodyLabel("Excel 文件")
        self.file_input = LineEdit()
        self.file_input.setReadOnly(True)
        select_btn = PushButton("选择文件")
        select_btn.clicked.connect(self.select_file)
        clear_btn = PushButton("清空")
        clear_btn.clicked.connect(self.clear_file)

        file_row.addWidget(file_label)
        file_row.addWidget(self.file_input, stretch=1)
        file_row.addWidget(select_btn)
        file_row.addWidget(clear_btn)
        layout.addLayout(file_row)

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

        self.split_btn = PrimaryPushButton("开始拆分")
        self.split_btn.clicked.connect(self.split_file)
        layout.addWidget(self.split_btn, alignment=Qt.AlignLeft)

        self.status_label = CaptionLabel("")
        self.status_label.setTextColor("#7A8190", "#7A8190")
        layout.addWidget(self.status_label)

    def select_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, "选择 Excel 文件", "", "Excel 文件 (*.xlsx)")
        if file_path:
            self._set_file(file_path)

    def clear_file(self) -> None:
        self.file_input.clear()
        self.status_label.setText("")
        self.progress_bar.setValue(0)
        self.progress_label.setText("")

    def select_output_path(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "选择输出文件夹")
        if folder:
            self.output_path = folder
            self.output_note.setText(f"输出到: {folder}")

    def _set_file(self, file_path: str) -> None:
        self.file_input.setText(file_path)
        self.status_label.setText(f"已选择: {os.path.basename(file_path)}")

    def update_progress(self, current: int, total: int, sheet_name: str) -> None:
        if total <= 0:
            return
        progress = int((current / total) * 100)
        self.progress_bar.setValue(progress)
        self.progress_label.setText(f"正在处理: {sheet_name} ({current}/{total}) | {progress}%")
        QApplication.processEvents()

    def split_file(self) -> None:
        input_file = self.file_input.text().strip()
        if not input_file:
            show_warning(self, "提示", "请先选择要处理的 Excel 文件。")
            return

        self.split_btn.setEnabled(False)
        try:
            self.progress_bar.setValue(0)
            self.progress_label.setText("")

            result = self.sheet_splitter.split_file(
                input_file,
                output_path=self.output_path,
                progress_callback=self.update_progress,
            )

            total = result["total_sheets"]
            output_files = result["output_files"]
            errors = result["errors"]
            output_dir = result["output_dir"]

            if errors:
                error_msg = "\n".join(errors)
                show_warning(
                    self,
                    "处理完成",
                    f"已生成 {len(output_files)}/{total} 个 CSV 文件。\n\n"
                    f"输出目录：{output_dir}\n\n错误详情：\n{error_msg}",
                )
            else:
                show_info(self, "处理完成", f"成功拆分 {total} 个工作表！\n\n输出目录：{output_dir}")

            self.status_label.setText(f"输出目录: {output_dir}")
        except Exception as exc:  # pylint: disable=broad-except
            show_error(self, "错误", f"拆分过程中发生错误：{exc}")
        finally:
            self.split_btn.setEnabled(True)
            self.progress_bar.setValue(0)
            self.progress_label.setText("")

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
            if path and path.lower().endswith(".xlsx") and os.path.isfile(path):
                self._set_file(path)
                return
