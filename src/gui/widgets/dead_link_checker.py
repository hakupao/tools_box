from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QApplication, QFileDialog, QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    CheckBox,
    LineEdit,
    PrimaryPushButton,
    ProgressBar,
    PushButton,
    SpinBox,
    TextEdit,
    TitleLabel,
)

from ...utils.dead_link_checker import DeadLinkChecker
from ..qt_common import show_error, show_info, show_warning, mono_font


class DeadLinkCheckerPage(QWidget):
    def __init__(self, main_window) -> None:
        super().__init__()
        self.setObjectName("dead_link_checker")
        self.main_window = main_window

        self.checker = DeadLinkChecker(timeout=10)
        self.last_output_file: str | None = None
        self.is_checking = False

        self._build_ui()
        self.setAcceptDrops(True)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(16)

        header_layout = QHBoxLayout()
        header_left = QVBoxLayout()
        title = TitleLabel("死链检测")
        subtitle = BodyLabel("扫描 HTML 文件并生成检测报告")
        subtitle.setTextColor("#6B7280", "#6B7280")
        header_left.addWidget(title)
        header_left.addWidget(subtitle)
        header_left.addStretch(1)

        back_btn = PushButton("返回主页")
        back_btn.clicked.connect(lambda: self.main_window.switch_to(self.main_window.home_interface))

        header_layout.addLayout(header_left, stretch=1)
        header_layout.addWidget(back_btn, alignment=Qt.AlignRight | Qt.AlignTop)
        layout.addLayout(header_layout)

        path_row = QHBoxLayout()
        path_label = BodyLabel("文件/文件夹")
        self.path_input = LineEdit()
        self.path_input.setPlaceholderText("选择 HTML 文件或文件夹")
        select_file_btn = PushButton("选择文件")
        select_file_btn.clicked.connect(self.select_file)
        select_folder_btn = PushButton("选择文件夹")
        select_folder_btn.clicked.connect(self.select_folder)
        clear_btn = PushButton("清空")
        clear_btn.clicked.connect(self.clear_path)

        path_row.addWidget(path_label)
        path_row.addWidget(self.path_input, stretch=1)
        path_row.addWidget(select_file_btn)
        path_row.addWidget(select_folder_btn)
        path_row.addWidget(clear_btn)
        layout.addLayout(path_row)

        url_row = QHBoxLayout()
        url_label = BodyLabel("基础 URL")
        self.base_url_input = LineEdit()
        self.base_url_input.setPlaceholderText("可选，用于解析相对链接")

        url_row.addWidget(url_label)
        url_row.addWidget(self.base_url_input, stretch=1)
        layout.addLayout(url_row)

        option_row = QHBoxLayout()
        self.include_subfolders = CheckBox("包含子文件夹")
        timeout_label = BodyLabel("超时时间(秒)")
        self.timeout_spin = SpinBox()
        self.timeout_spin.setRange(5, 60)
        self.timeout_spin.setValue(10)

        option_row.addWidget(self.include_subfolders)
        option_row.addSpacing(16)
        option_row.addWidget(timeout_label)
        option_row.addWidget(self.timeout_spin)
        option_row.addStretch(1)
        layout.addLayout(option_row)

        self.progress_bar = ProgressBar()
        self.progress_bar.setValue(0)
        self.progress_label = CaptionLabel("")
        self.progress_label.setTextColor("#7A8190", "#7A8190")
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.progress_label)

        button_row = QHBoxLayout()
        self.check_btn = PrimaryPushButton("开始检测")
        self.check_btn.clicked.connect(self.start_checking)
        self.open_output_btn = PushButton("打开报告文件夹")
        self.open_output_btn.clicked.connect(self.open_output_folder)
        self.open_output_btn.setEnabled(False)

        button_row.addWidget(self.check_btn)
        button_row.addWidget(self.open_output_btn)
        button_row.addStretch(1)
        layout.addLayout(button_row)

        log_label = BodyLabel("检测结果")
        layout.addWidget(log_label)

        self.log_text = TextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(mono_font(10))
        layout.addWidget(self.log_text, stretch=1)

    def select_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择 HTML 文件",
            "",
            "HTML 文件 (*.html *.htm);;所有文件 (*.*)",
        )
        if file_path:
            self.path_input.setText(file_path)

    def select_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "选择包含 HTML 文件的文件夹")
        if folder:
            self.path_input.setText(folder)

    def clear_path(self) -> None:
        self.path_input.clear()
        self.base_url_input.clear()
        self.progress_bar.setValue(0)
        self.progress_label.setText("")
        self.log_text.clear()
        self.open_output_btn.setEnabled(False)
        self.last_output_file = None

    def start_checking(self) -> None:
        if self.is_checking:
            show_warning(self, "提示", "正在检测中，请稍候...")
            return

        path = self.path_input.text().strip()
        if not path:
            show_warning(self, "提示", "请先选择文件或文件夹。")
            return

        if not os.path.exists(path):
            show_error(self, "错误", "选择的路径不存在。")
            return

        self.is_checking = True
        self.last_output_file = None

        try:
            self.check_btn.setEnabled(False)
            self.open_output_btn.setEnabled(False)
            self.progress_bar.setValue(0)
            self.progress_label.setText("")
            self._update_log("开始检测死链...\n")

            self.checker.timeout = int(self.timeout_spin.value())
            base_url = self.base_url_input.text().strip()

            if os.path.isfile(path):
                self._check_single_file(path, base_url)
            else:
                self._check_folder(path, base_url)

        except Exception as exc:  # pylint: disable=broad-except
            show_error(self, "错误", f"检测时发生错误：{exc}")
            self._update_log(f"\n检测失败：{exc}")
        finally:
            self.is_checking = False
            self.check_btn.setEnabled(True)
            self.progress_label.setText("")
            self.progress_bar.setValue(0)

    def _check_single_file(self, file_path: str, base_url: str) -> None:
        result = self.checker.check_html_file(file_path, base_url, progress_callback=self.update_progress)

        output_file = self._generate_output_filename(file_path)
        self.checker.generate_report(result, output_file)

        summary = self._format_summary(result)
        self._update_log(summary)

        show_info(self, "完成", f"检测完成！报告已保存至：\n{output_file}")
        self.last_output_file = output_file
        self.open_output_btn.setEnabled(True)

    def _check_folder(self, folder_path: str, base_url: str) -> None:
        result = self.checker.check_folder(
            folder_path,
            base_url,
            include_subfolders=self.include_subfolders.isChecked(),
            progress_callback=self.update_progress,
        )

        if result["total_files"] == 0:
            show_warning(self, "提示", "未找到 HTML 文件。")
            self._update_log("未找到 HTML 文件。")
            return

        output_file = self._generate_output_filename(folder_path)
        self.checker.generate_report(result, output_file)

        summary = self._format_folder_summary(result)
        self._update_log(summary)

        show_info(self, "完成", f"检测完成！报告已保存至：\n{output_file}")
        self.last_output_file = output_file
        self.open_output_btn.setEnabled(True)

    def update_progress(self, current: int, total: int, item: str) -> None:
        if total <= 0:
            return
        progress = int((current / total) * 100)
        self.progress_bar.setValue(progress)
        self.progress_label.setText(f"正在检测: {item} ({current}/{total}) | {progress}%")
        QApplication.processEvents()

    def open_output_folder(self) -> None:
        if not self.last_output_file:
            return
        output_folder = os.path.dirname(self.last_output_file)
        if os.path.isdir(output_folder):
            if not QDesktopServices.openUrl(QUrl.fromLocalFile(output_folder)):
                try:
                    if sys.platform.startswith("win"):
                        os.startfile(output_folder)  # type: ignore[attr-defined]
                    elif sys.platform == "darwin":
                        subprocess.Popen(["open", output_folder])
                    else:
                        subprocess.Popen(["xdg-open", output_folder])
                except OSError:
                    show_warning(self, "提示", f"无法打开目录：{output_folder}")

    def _generate_output_filename(self, input_path: str) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if os.path.isfile(input_path):
            base_name = Path(input_path).stem
            output_dir = Path(input_path).parent
        else:
            base_name = Path(input_path).name
            output_dir = Path(input_path)

        output_file = output_dir / f"dead_link_report_{base_name}_{timestamp}.txt"
        return str(output_file)

    def _format_summary(self, result: dict) -> str:
        lines = []
        lines.append(f"文件: {result['file']}")
        lines.append(f"总链接数: {result['total_links']}")
        lines.append(f"唯一链接数: {result['unique_links']}")
        lines.append("")

        summary = result["summary"]
        lines.append("检测摘要:")
        lines.append(f"  ✓ 正常: {summary['alive']}")
        lines.append(f"  ✗ 死链: {summary['dead']}")
        lines.append(f"  ⏱ 超时: {summary['timeout']}")
        lines.append(f"  ⚠ 错误: {summary['error']}")
        lines.append(f"  ⊘ 跳过: {summary['skipped']}")
        lines.append("")

        confirmed_dead = []
        potential_false_positives = []
        for check in result["checks"]:
            if check["status"] == "dead":
                if check["status_code"] == 403 and check.get("error") == "HEAD blocked, verified with GET":
                    potential_false_positives.append(check)
                else:
                    confirmed_dead.append(check)

        if confirmed_dead:
            lines.append("确认死链（建议检查）:")
            for check in confirmed_dead[:15]:
                lines.append(f"  [{check['status_code']}] {check['url']}")
            if len(confirmed_dead) > 15:
                lines.append(f"  ... 还有 {len(confirmed_dead) - 15} 个")
            lines.append("")

        if potential_false_positives:
            lines.append(f"可能误报（403 错误 - 反爬虫保护）: {len(potential_false_positives)} 个")
            lines.append("注意: 这些链接在浏览器中可能可以正常访问")
            lines.append("详细列表请查看完整报告")
            lines.append("")

        return "\n".join(lines)

    def _format_folder_summary(self, result: dict) -> str:
        lines = []
        lines.append(f"文件夹: {result['folder']}")
        lines.append(f"总文件数: {result['total_files']}")
        lines.append("")

        total_alive = 0
        total_dead = 0
        total_timeout = 0
        total_error = 0
        total_skipped = 0

        for file_result in result["files"]:
            summary = file_result["summary"]
            total_alive += summary["alive"]
            total_dead += summary["dead"]
            total_timeout += summary["timeout"]
            total_error += summary["error"]
            total_skipped += summary["skipped"]

        lines.append("总体摘要:")
        lines.append(f"  ✓ 正常: {total_alive}")
        lines.append(f"  ✗ 死链: {total_dead}")
        lines.append(f"  ⏱ 超时: {total_timeout}")
        lines.append(f"  ⚠ 错误: {total_error}")
        lines.append(f"  ⊘ 跳过: {total_skipped}")
        lines.append("")

        files_with_dead_links = [f for f in result["files"] if f["summary"]["dead"] > 0]
        if files_with_dead_links:
            lines.append("包含死链的文件:")
            for file_result in files_with_dead_links[:10]:
                file_name = Path(file_result["file"]).name
                lines.append(f"  {file_name}: {file_result['summary']['dead']} 个死链")
            if len(files_with_dead_links) > 10:
                lines.append(f"  ... 还有 {len(files_with_dead_links) - 10} 个文件")

        return "\n".join(lines)

    def _update_log(self, content: str) -> None:
        self.log_text.setPlainText(content)

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
            if not path:
                continue
            if os.path.isdir(path) or path.lower().endswith((".html", ".htm")):
                self.path_input.setText(path)
                return
