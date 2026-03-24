from __future__ import annotations

from pathlib import Path

import keyboard
import pyautogui
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    PrimaryPushButton,
    ProgressBar,
    PushButton,
    SpinBox,
    TextEdit,
    TitleLabel,
)

from ...utils.edc_site_adder_service import CLICK_STEP_KEYS, EdcSiteAdderService
from ...utils.edc_site_adder_worker import EdcSiteAdderWorker
from ..qt_common import ensure_light_title_bar, mono_font, select_save_file, show_error, show_info
from .edc_recording_overlay import FlashIndicator, RecordingOverlay, run_replay_test


class EdcSiteAdderPage(QWidget):
    def __init__(self, main_window) -> None:
        super().__init__()
        self.setObjectName("edc_site_adder")
        self.main_window = main_window
        self.service = EdcSiteAdderService()
        self._worker: EdcSiteAdderWorker | None = None
        self._replay_indicators: list[FlashIndicator] = []
        self._overlay: RecordingOverlay | None = None

        keyboard.on_press_key("esc", self._on_esc_pressed)

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 20, 32, 24)
        layout.setSpacing(12)

        # Header
        header_layout = QHBoxLayout()
        header_left = QVBoxLayout()
        title = TitleLabel("EDC 站点添加工具")
        subtitle = CaptionLabel("自动化批量添加站点信息")
        subtitle.setTextColor("#6B7280", "#6B7280")
        header_left.addWidget(title)
        header_left.addWidget(subtitle)

        back_btn = PushButton("返回主页")
        back_btn.clicked.connect(lambda: self.main_window.switch_to(self.main_window.home_interface))
        config_btn = PushButton("配置参数")
        config_btn.clicked.connect(self.show_config_dialog)

        header_layout.addLayout(header_left, stretch=1)
        header_layout.addWidget(config_btn, alignment=Qt.AlignRight | Qt.AlignTop)
        header_layout.addWidget(back_btn, alignment=Qt.AlignRight | Qt.AlignTop)
        layout.addLayout(header_layout, stretch=0)

        # Content
        content_layout = QHBoxLayout()
        content_layout.setSpacing(16)

        # Left: instruction
        instruction_box = QVBoxLayout()
        instruction_title = BodyLabel("使用说明")
        instruction_text = TextEdit()
        instruction_text.setReadOnly(True)
        instruction_text.setFont(mono_font(9))
        instruction_text.setPlainText(self._instruction_text())
        instruction_box.addWidget(instruction_title)
        instruction_box.addWidget(instruction_text, stretch=1)

        # Right: controls + log
        right_box = QVBoxLayout()

        # Start button
        self.start_btn = PrimaryPushButton("开始处理")
        self.start_btn.clicked.connect(self.start_processing)

        # Progress
        progress_row = QHBoxLayout()
        self.progress_bar = ProgressBar()
        self.progress_bar.setValue(0)
        self.progress_label = CaptionLabel("就绪")
        self.progress_label.setTextColor("#6B7280", "#6B7280")
        progress_row.addWidget(self.progress_bar, stretch=1)
        progress_row.addWidget(self.progress_label)

        # Log header with buttons
        log_header = QHBoxLayout()
        log_label = BodyLabel("处理日志")
        clear_log_btn = PushButton("清空")
        clear_log_btn.setFixedWidth(60)
        clear_log_btn.clicked.connect(lambda: self.log_text.clear())
        export_log_btn = PushButton("导出")
        export_log_btn.setFixedWidth(60)
        export_log_btn.clicked.connect(self._export_log)
        log_header.addWidget(log_label)
        log_header.addStretch(1)
        log_header.addWidget(clear_log_btn)
        log_header.addWidget(export_log_btn)

        self.log_text = TextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(mono_font(9))

        right_box.addWidget(self.start_btn, alignment=Qt.AlignLeft)
        right_box.addLayout(progress_row)
        right_box.addLayout(log_header)
        right_box.addWidget(self.log_text, stretch=1)

        content_layout.addLayout(instruction_box, stretch=3)
        content_layout.addLayout(right_box, stretch=1)
        layout.addLayout(content_layout, stretch=1)

    def _instruction_text(self) -> str:
        return (
            "EDC 站点添加工具使用说明：\n\n"
            "【前提准备】\n"
            "1. 请确保 Excel 已打开，并包含需要添加到 EDC 系统的站点名称列表\n"
            "2. 请确保 Chrome 浏览器已打开并登录到 EDC 系统\n"
            "3. 在 Excel 中选中包含第一个站点名称的单元格\n\n"
            "【操作步骤】\n"
            "1. 点击「配置参数」按钮，使用「一键录制」快速配置坐标\n"
            "2. 点击「开始处理」按钮，系统将自动执行以下操作：\n"
            "   - 获取当前 Excel 单元格的站点名称\n"
            "   - 切换到 Chrome 浏览器\n"
            "   - 按顺序点击：新建→查找→搜索框→粘贴站点名称→搜索→选择→OK→确认\n"
            "   - 返回 Excel 并自动移动到下一行\n"
            "   - 重复上述过程直到遇到空单元格或达到最大循环次数\n\n"
            "【注意事项】\n"
            "1. 处理过程中请勿移动鼠标或使用键盘，否则可能导致点击位置错误\n"
            "2. 按 ESC 键可随时紧急终止处理\n"
            "3. 若界面或按钮位置有变化，请点击「配置参数」→「一键录制」重新配置\n\n"
            "【坐标录制】\n"
            "点击「一键录制」后，屏幕顶部会出现引导提示条，\n"
            "按提示依次点击 EDC 系统中的 7 个按钮即可完成坐标配置。\n"
            "也可双击表格中的某一行，单独重新录制该步骤的坐标。"
        )

    # ── ESC hook ──────────────────────────────────────────────

    def _on_esc_pressed(self, _event) -> None:
        if self._worker and self._worker.isRunning():
            self.append_log("用户按下 ESC 键，正在停止处理...")
            self._worker.request_stop()

    # ── Processing ────────────────────────────────────────────

    def start_processing(self) -> None:
        if self._worker and self._worker.isRunning():
            show_info(self, "提示", "处理已在进行中")
            return

        self.log_text.clear()
        self.progress_bar.setValue(0)
        self.progress_label.setText("准备中...")
        self.start_btn.setEnabled(False)

        self._worker = EdcSiteAdderWorker(self.service.config, parent=self)
        self._worker.log.connect(self.append_log)
        self._worker.progress.connect(self._update_progress)
        self._worker.finished_ok.connect(self._on_finished)
        self._worker.finished_error.connect(self._on_error)
        self._worker.finished_stopped.connect(self._on_stopped)
        self._worker.start()

    def _update_progress(self, current: int, total: int) -> None:
        pct = int(current / total * 100) if total > 0 else 0
        self.progress_bar.setValue(pct)
        self.progress_label.setText(f"第 {current}/{total} 行")

    def _on_finished(self) -> None:
        self.start_btn.setEnabled(True)
        self.progress_bar.setValue(100)
        self.progress_label.setText("处理完成")
        show_info(self, "完成", "所有行处理完成")

    def _on_stopped(self) -> None:
        self.start_btn.setEnabled(True)
        self.progress_label.setText("已停止")
        show_info(self, "提示", "处理已停止")

    def _on_error(self, msg: str) -> None:
        self.start_btn.setEnabled(True)
        self.progress_label.setText("处理异常")
        show_error(self, "错误", msg)

    def append_log(self, message: str) -> None:
        self.log_text.append(message)
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    # ── Log export ────────────────────────────────────────────

    def _export_log(self) -> None:
        content = self.log_text.toPlainText()
        if not content.strip():
            show_info(self, "提示", "日志为空，无需导出")
            return
        path, _ = select_save_file(self, "导出日志", "", "文本文件 (*.txt)")
        if path:
            Path(path).write_text(content, encoding="utf-8")
            show_info(self, "成功", f"日志已导出到 {path}")

    # ── Config dialog ─────────────────────────────────────────

    def show_config_dialog(self) -> None:
        dialog = QDialog(self)
        dialog.setObjectName("edcConfigDialog")
        dialog.setWindowTitle("配置参数")
        dialog.resize(700, 680)
        dialog.setStyleSheet(_CONFIG_DIALOG_STYLE)

        dialog_layout = QVBoxLayout(dialog)
        dialog_layout.setContentsMargins(24, 24, 24, 24)
        dialog_layout.setSpacing(16)
        ensure_light_title_bar(dialog)

        # ── Row 1: max loops ──
        loop_row = QHBoxLayout()
        loop_label = BodyLabel("最大循环次数")
        loop_spin = SpinBox()
        loop_spin.setRange(1, 9999)
        loop_spin.setValue(int(self.service.config.get("max_loops", 100)))
        loop_row.addWidget(loop_label)
        loop_row.addWidget(loop_spin)
        loop_row.addStretch(1)
        dialog_layout.addLayout(loop_row)

        # ── Row 2: retry count + step delay ──
        extra_row = QHBoxLayout()
        retry_label = BodyLabel("重试次数")
        retry_spin = SpinBox()
        retry_spin.setRange(0, 5)
        retry_spin.setValue(int(self.service.config.get("retry_count", 1)))

        delay_label = BodyLabel("步骤间隔(秒)")
        delay_spin = SpinBox()
        delay_spin.setRange(1, 50)
        delay_spin.setValue(int(self.service.config.get("step_delay", 0.3) * 10))
        delay_hint = CaptionLabel("×0.1秒")
        delay_hint.setTextColor("#7A8190", "#7A8190")

        extra_row.addWidget(retry_label)
        extra_row.addWidget(retry_spin)
        extra_row.addSpacing(24)
        extra_row.addWidget(delay_label)
        extra_row.addWidget(delay_spin)
        extra_row.addWidget(delay_hint)
        extra_row.addStretch(1)
        dialog_layout.addLayout(extra_row)

        # ── Row 3: coordinate tools ──
        coord_row = QHBoxLayout()
        record_btn = PrimaryPushButton("一键录制")
        replay_btn = PushButton("回放测试")

        coord_label = BodyLabel("坐标获取")
        coord_display = CaptionLabel("X: 0, Y: 0")
        coord_display.setTextColor("#7A8190", "#7A8190")
        lock_label = CaptionLabel("按 F2 锁定/解锁坐标")
        lock_label.setTextColor("#7A8190", "#7A8190")
        coord_btn = PushButton("开始获取")

        coord_row.addWidget(record_btn)
        coord_row.addWidget(replay_btn)
        coord_row.addSpacing(16)
        coord_row.addWidget(coord_label)
        coord_row.addWidget(coord_display)
        coord_row.addWidget(lock_label)
        coord_row.addWidget(coord_btn)
        coord_row.addStretch(1)
        dialog_layout.addLayout(coord_row)

        # ── Table ──
        table = QTableWidget()
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(["按钮", "X", "Y"])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        table.setAlternatingRowColors(True)

        positions = list(self.service.config["click_positions"].items())
        table.setRowCount(len(positions))
        for row, (key, coord) in enumerate(positions):
            name_item = QTableWidgetItem(key)
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            table.setItem(row, 0, name_item)
            table.setItem(row, 1, QTableWidgetItem(str(coord["x"])))
            table.setItem(row, 2, QTableWidgetItem(str(coord["y"])))

        # Double-click row to re-record single step
        table.cellDoubleClicked.connect(
            lambda row, col: self._start_single_step_recording(dialog, table, positions, row)
        )

        dialog_layout.addWidget(table, stretch=1)

        hint_label = CaptionLabel("提示：双击表格中的某一行可单独重新录制该步骤的坐标")
        hint_label.setTextColor("#7A8190", "#7A8190")
        dialog_layout.addWidget(hint_label)

        # ── Buttons ──
        button_row = QHBoxLayout()
        save_btn = PrimaryPushButton("保存配置")
        reset_btn = PushButton("重置默认")
        cancel_btn = PushButton("取消")
        button_row.addStretch(1)
        button_row.addWidget(reset_btn)
        button_row.addWidget(cancel_btn)
        button_row.addWidget(save_btn)
        dialog_layout.addLayout(button_row)

        # ── Manual coordinate capture (legacy) ──
        timer = QTimer(dialog)
        locked_coords: list[tuple[int, int] | None] = [None]

        def update_coords():
            if locked_coords[0] is not None:
                x, y = locked_coords[0]
            else:
                x, y = pyautogui.position()
            coord_display.setText(f"X: {x}, Y: {y}")

        def toggle_capture():
            if timer.isActive():
                timer.stop()
                coord_btn.setText("开始获取")
            else:
                timer.start(100)
                coord_btn.setText("停止获取")

        def toggle_lock():
            if locked_coords[0] is None:
                locked_coords[0] = pyautogui.position()
                lock_label.setText("坐标已锁定 (F2 解锁)")
                lock_label.setTextColor("#D14343", "#D14343")
            else:
                locked_coords[0] = None
                lock_label.setText("按 F2 锁定/解锁坐标")
                lock_label.setTextColor("#7A8190", "#7A8190")

        coord_btn.clicked.connect(toggle_capture)
        timer.timeout.connect(update_coords)

        from PySide6.QtGui import QShortcut

        lock_shortcut = QShortcut(QKeySequence("F2"), dialog)
        lock_shortcut.activated.connect(toggle_lock)

        # ── Recording mode ──
        record_btn.clicked.connect(lambda: self._start_recording(dialog, table, positions))
        replay_btn.clicked.connect(lambda: self._start_replay(table, positions))

        # ── Save / Reset / Cancel ──
        def save_config_values() -> None:
            try:
                self.service.config["max_loops"] = int(loop_spin.value())
                self.service.config["retry_count"] = int(retry_spin.value())
                self.service.config["step_delay"] = round(delay_spin.value() * 0.1, 2)

                for row, (key, _coord) in enumerate(positions):
                    x_item = table.item(row, 1)
                    y_item = table.item(row, 2)
                    if not x_item or not y_item:
                        continue
                    self.service.config["click_positions"][key]["x"] = int(x_item.text())
                    self.service.config["click_positions"][key]["y"] = int(y_item.text())

                if self.service.save_config():
                    show_info(self, "成功", "配置已保存")
                    dialog.accept()
                else:
                    show_error(self, "错误", "保存配置失败，请检查文件权限")
            except ValueError:
                show_error(self, "错误", "请输入有效的数字")

        def reset_config() -> None:
            if self.service.reset_to_default_config():
                show_info(self, "成功", "已重置为默认配置")
            else:
                show_error(self, "错误", "重置配置失败，请检查文件权限")
            dialog.accept()

        save_btn.clicked.connect(save_config_values)
        reset_btn.clicked.connect(reset_config)
        cancel_btn.clicked.connect(dialog.reject)

        dialog.exec()

    # ── Recording helpers ─────────────────────────────────────

    def _start_recording(
        self,
        dialog: QDialog,
        table: QTableWidget,
        positions: list[tuple[str, dict]],
    ) -> None:
        dialog.hide()
        # Minimize main window so Chrome is fully visible
        self.main_window.showMinimized()

        # Activate Chrome so user clicks land on the right window
        chrome_windows = pyautogui.getWindowsWithTitle("Chrome")
        if chrome_windows:
            chrome_windows[0].activate()

        steps = [key for key, _ in positions]
        self._overlay = RecordingOverlay(steps)
        self._overlay.coordinate_captured.connect(
            lambda key, x, y: self._on_coord_captured(table, positions, key, x, y)
        )
        self._overlay.recording_finished.connect(lambda: self._on_recording_done(dialog))
        self._overlay.recording_cancelled.connect(lambda: self._on_recording_done(dialog))
        self._overlay.show()

    def _start_single_step_recording(
        self,
        dialog: QDialog,
        table: QTableWidget,
        positions: list[tuple[str, dict]],
        row: int,
    ) -> None:
        if row < 0 or row >= len(positions):
            return
        key = positions[row][0]
        dialog.hide()
        self.main_window.showMinimized()

        chrome_windows = pyautogui.getWindowsWithTitle("Chrome")
        if chrome_windows:
            chrome_windows[0].activate()

        self._overlay = RecordingOverlay([key])
        self._overlay.coordinate_captured.connect(
            lambda k, x, y: self._on_coord_captured(table, positions, k, x, y)
        )
        self._overlay.recording_finished.connect(lambda: self._on_recording_done(dialog))
        self._overlay.recording_cancelled.connect(lambda: self._on_recording_done(dialog))
        self._overlay.show()

    def _on_coord_captured(
        self,
        table: QTableWidget,
        positions: list[tuple[str, dict]],
        key: str,
        x: int,
        y: int,
    ) -> None:
        for row, (k, _) in enumerate(positions):
            if k == key:
                table.item(row, 1).setText(str(x))
                table.item(row, 2).setText(str(y))
                break

    def _on_recording_done(self, dialog: QDialog) -> None:
        self._overlay = None
        self.main_window.showNormal()
        self.main_window.activateWindow()
        dialog.show()
        dialog.activateWindow()

    def _start_replay(
        self,
        table: QTableWidget,
        positions: list[tuple[str, dict]],
    ) -> None:
        # Build positions dict from current table values
        current_positions: dict[str, dict[str, int]] = {}
        step_keys: list[str] = []
        for row, (key, _) in enumerate(positions):
            x_item = table.item(row, 1)
            y_item = table.item(row, 2)
            if x_item and y_item:
                try:
                    current_positions[key] = {"x": int(x_item.text()), "y": int(y_item.text())}
                    step_keys.append(key)
                except ValueError:
                    continue

        self._replay_indicators = run_replay_test(current_positions, step_keys)

    # ── Cleanup ───────────────────────────────────────────────

    def closeEvent(self, event) -> None:  # noqa: N802
        try:
            keyboard.unhook_all()
        except Exception:
            pass
        if self._worker and self._worker.isRunning():
            self._worker.request_stop()
            self._worker.wait(3000)
        super().closeEvent(event)


_CONFIG_DIALOG_STYLE = """
QDialog#edcConfigDialog {
    background: #F5F6F8;
}
QDialog#edcConfigDialog QLabel {
    color: #1F2937;
}
QDialog#edcConfigDialog QAbstractSpinBox,
QDialog#edcConfigDialog QLineEdit {
    background: #FFFFFF;
    color: #1F2937;
    border: 1px solid #DCE3ED;
    border-radius: 8px;
    padding: 4px 8px;
}
QDialog#edcConfigDialog QTableWidget {
    background: #FFFFFF;
    color: #1F2937;
    border: 1px solid #DCE3ED;
    border-radius: 10px;
    gridline-color: #E8EDF4;
    alternate-background-color: #F8FAFC;
}
QDialog#edcConfigDialog QTableWidget::item {
    background: #FFFFFF;
    color: #1F2937;
    padding: 4px 6px;
    border: none;
    border-bottom: 1px solid #EEF2F7;
}
QDialog#edcConfigDialog QTableWidget::item:alternate {
    background: #F8FAFC;
}
QDialog#edcConfigDialog QTableWidget::item:selected {
    background: #DDEBFF;
    color: #0F172A;
}
QDialog#edcConfigDialog QHeaderView {
    background: #EEF3F9;
}
QDialog#edcConfigDialog QHeaderView::section {
    background: #EEF3F9;
    color: #334155;
    border: none;
    border-bottom: 1px solid #DCE3ED;
    padding: 6px;
    font-weight: 600;
}
QDialog#edcConfigDialog QHeaderView::section:vertical {
    color: #475569;
    border-right: 1px solid #DCE3ED;
    border-bottom: 1px solid #DCE3ED;
}
QDialog#edcConfigDialog QTableCornerButton::section {
    background: #EEF3F9;
    border: none;
    border-bottom: 1px solid #DCE3ED;
}
"""
