from __future__ import annotations

import json
import os
import sys
import threading
import time

import keyboard
import pyautogui
import pyperclip
import win32com.client
from PySide6.QtCore import Qt, QTimer, Signal
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
    PushButton,
    SpinBox,
    TextEdit,
    TitleLabel,
)

from ..qt_common import show_error, show_info, mono_font


class EdcSiteAdderPage(QWidget):
    log_signal = Signal(str)
    stop_signal = Signal()

    def __init__(self, main_window) -> None:
        super().__init__()
        self.setObjectName("edc_site_adder")
        self.main_window = main_window

        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.5

        self.processing = False

        self.default_config = {
            "max_loops": 100,
            "click_positions": {
                "新建": {"x": 241, "y": 212},
                "查找": {"x": 1137, "y": 460},
                "搜索框": {"x": 817, "y": 409},
                "搜索": {"x": 1040, "y": 406},
                "选择": {"x": 699, "y": 471},
                "ok": {"x": 1121, "y": 758},
                "确认": {"x": 1038, "y": 728},
            },
        }
        self.config = self.default_config.copy()
        self.load_config()

        self.log_signal.connect(self.append_log)
        self.stop_signal.connect(self.stop_processing)

        self.esc_thread = threading.Thread(target=self.esc_listener, daemon=True)
        self.esc_thread.start()

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(16)

        header_layout = QHBoxLayout()
        header_left = QVBoxLayout()
        title = TitleLabel("EDC 站点添加工具")
        subtitle = CaptionLabel("自动化批量添加站点信息")
        subtitle.setTextColor("#6B7280", "#6B7280")
        header_left.addWidget(title)
        header_left.addWidget(subtitle)
        header_left.addStretch(1)

        back_btn = PushButton("返回主页")
        back_btn.clicked.connect(lambda: self.main_window.switch_to(self.main_window.home_interface))
        config_btn = PushButton("配置参数")
        config_btn.clicked.connect(self.show_config_dialog)

        header_layout.addLayout(header_left, stretch=1)
        header_layout.addWidget(config_btn, alignment=Qt.AlignRight | Qt.AlignTop)
        header_layout.addWidget(back_btn, alignment=Qt.AlignRight | Qt.AlignTop)
        layout.addLayout(header_layout)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(16)

        instruction_box = QVBoxLayout()
        instruction_title = BodyLabel("使用说明")
        instruction_text = TextEdit()
        instruction_text.setReadOnly(True)
        instruction_text.setFont(mono_font(9))
        instruction_text.setPlainText(self._instruction_text())

        instruction_box.addWidget(instruction_title)
        instruction_box.addWidget(instruction_text)

        right_box = QVBoxLayout()
        self.start_btn = PrimaryPushButton("开始处理")
        self.start_btn.clicked.connect(self.start_processing)

        log_label = BodyLabel("处理日志")
        self.log_text = TextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(mono_font(9))

        right_box.addWidget(self.start_btn, alignment=Qt.AlignLeft)
        right_box.addWidget(log_label)
        right_box.addWidget(self.log_text, stretch=1)

        content_layout.addLayout(instruction_box, stretch=1)
        content_layout.addLayout(right_box, stretch=1)

        layout.addLayout(content_layout)

    def _instruction_text(self) -> str:
        return (
            "EDC 站点添加工具使用说明：\n\n"
            "【前提准备】\n"
            "1. 请确保 Excel 已打开，并包含需要添加到 EDC 系统的站点名称列表\n"
            "2. 请确保 Chrome 浏览器已打开并登录到 EDC 系统\n"
            "3. 在 Excel 中选中包含第一个站点名称的单元格\n\n"
            "【操作步骤】\n"
            "1. 点击“开始处理”按钮，系统将自动执行以下操作：\n"
            "   - 获取当前 Excel 单元格的站点名称\n"
            "   - 切换到 Chrome 浏览器\n"
            "   - 按顺序点击：新建→查找→搜索框→粘贴站点名称→搜索→选择→OK→确认\n"
            "   - 返回 Excel 并自动移动到下一行\n"
            "   - 重复上述过程直到遇到空单元格或达到最大循环次数\n\n"
            "【注意事项】\n"
            "1. 处理过程中请勿移动鼠标或使用键盘，否则可能导致点击位置错误\n"
            "2. 按 ESC 键可随时紧急终止处理（停止处理的唯一方式）\n"
            "3. 若界面或按钮位置有变化，请点击“配置参数”重新调整坐标\n\n"
            "【自动化流程】\n"
            "系统将按照预设坐标依次点击 EDC 系统中的对应按钮，完成站点添加过程，\n"
            "整个操作过程将在“处理日志”区域实时显示"
        )

    def get_config_path(self) -> str:
        if getattr(sys, "frozen", False):
            app_dir = os.path.dirname(sys.executable)
        else:
            app_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(app_dir, "edc_site_adder_config.json")

    def load_config(self) -> None:
        config_path = self.get_config_path()
        try:
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    self.config = json.load(f)
            else:
                self.config = self.default_config.copy()
        except Exception:
            self.config = self.default_config.copy()

    def save_config(self) -> bool:
        config_path = self.get_config_path()
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            return True
        except Exception:
            return False

    def reset_to_default_config(self) -> None:
        self.config = self.default_config.copy()
        if self.save_config():
            show_info(self, "成功", "已重置为默认配置")
        else:
            show_error(self, "错误", "重置配置失败，请检查文件权限")

    def esc_listener(self) -> None:
        while True:
            if keyboard.is_pressed("esc") and self.processing:
                self.processing = False
                self.log_signal.emit("用户按下 ESC 键，正在停止处理...")
                self.stop_signal.emit()
            time.sleep(0.05)

    def append_log(self, message: str) -> None:
        self.log_text.append(message)
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        QApplication.processEvents()

    def start_processing(self) -> None:
        if self.processing:
            show_info(self, "提示", "处理已在进行中")
            return

        self.processing = True
        self.append_log("开始处理...")

        try:
            self.append_log("正在连接 Excel...")
            xl = win32com.client.Dispatch("Excel.Application")
            cell = xl.Selection
            if not cell:
                self.append_log("错误: 未选中 Excel 单元格")
                self.processing = False
                return

            for i in range(self.config["max_loops"]):
                if not self.processing:
                    self.append_log("处理已停止")
                    break

                cell_value = cell.Text.strip()
                if not cell_value:
                    self.append_log(f"第 {i + 1} 行为空，自动终止处理")
                    break

                self.append_log(f"处理第 {i + 1} 行: {cell_value}")
                pyperclip.copy(cell_value)
                time.sleep(0.1)

                if not self.processing:
                    self.append_log("处理已停止")
                    break

                self.append_log("切换到 Chrome 窗口...")
                chrome_window = pyautogui.getWindowsWithTitle("Chrome")
                if not chrome_window:
                    self.append_log("错误: 未找到 Chrome 窗口")
                    self.processing = False
                    return

                chrome_window[0].activate()
                time.sleep(0.1)

                if not self.processing:
                    self.append_log("处理已停止")
                    break

                self.append_log("执行点击操作...")
                self._click("新建")
                if not self.processing:
                    self.append_log("处理已停止")
                    break
                self._click("查找")
                if not self.processing:
                    self.append_log("处理已停止")
                    break
                self._click("搜索框")
                pyautogui.hotkey("ctrl", "v")
                time.sleep(0.1)
                if not self.processing:
                    self.append_log("处理已停止")
                    break
                self._click("搜索")
                if not self.processing:
                    self.append_log("处理已停止")
                    break
                self._click("选择")
                if not self.processing:
                    self.append_log("处理已停止")
                    break
                self._click("ok")
                if not self.processing:
                    self.append_log("处理已停止")
                    break
                self._click("确认")

                if not self.processing:
                    self.append_log("处理已停止")
                    break

                self.append_log("切回 Excel 窗口...")
                xl.ActiveWindow.Activate()
                time.sleep(0.1)

                try:
                    current_address = cell.Address
                    current_row = cell.Row
                    current_column = cell.Column
                    self.append_log(
                        f"当前单元格: {current_address} (行: {current_row}, 列: {current_column})"
                    )

                    next_row = current_row + 1
                    next_cell = xl.ActiveSheet.Cells(next_row, current_column)
                    next_cell.Select()
                    cell = xl.Selection
                    self.append_log(
                        f"已移动到下一行: {current_address} -> {cell.Address}"
                    )
                except Exception as exc:
                    self.append_log(f"错误: 无法移动到下一行 - {exc}")
                    break

                time.sleep(0.1)

            if self.processing:
                self.append_log("处理完成")

        except Exception as exc:
            self.append_log(f"错误: {exc}")
        finally:
            self.processing = False

    def _click(self, key: str) -> None:
        if not self.processing:
            return
        pos = self.config["click_positions"][key]
        pyautogui.click(pos["x"], pos["y"])
        time.sleep(0.1)

    def stop_processing(self) -> None:
        if not self.processing:
            show_info(self, "提示", "当前没有正在进行的处理")
            return
        show_info(self, "提示", "处理已停止")

    def show_config_dialog(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("配置参数")
        dialog.resize(680, 620)

        dialog_layout = QVBoxLayout(dialog)
        dialog_layout.setContentsMargins(24, 24, 24, 24)
        dialog_layout.setSpacing(16)

        loop_row = QHBoxLayout()
        loop_label = BodyLabel("最大循环次数")
        loop_spin = SpinBox()
        loop_spin.setRange(1, 9999)
        loop_spin.setValue(int(self.config.get("max_loops", 100)))
        loop_row.addWidget(loop_label)
        loop_row.addWidget(loop_spin)
        loop_row.addStretch(1)
        dialog_layout.addLayout(loop_row)

        coord_row = QHBoxLayout()
        coord_label = BodyLabel("坐标获取")
        coord_display = CaptionLabel("X: 0, Y: 0")
        coord_display.setTextColor("#7A8190", "#7A8190")
        lock_label = CaptionLabel("按 F2 锁定/解锁坐标")
        lock_label.setTextColor("#7A8190", "#7A8190")
        coord_btn = PushButton("开始获取")
        coord_row.addWidget(coord_label)
        coord_row.addWidget(coord_display)
        coord_row.addWidget(lock_label)
        coord_row.addWidget(coord_btn)
        coord_row.addStretch(1)
        dialog_layout.addLayout(coord_row)

        table = QTableWidget()
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(["按钮", "X", "Y"])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)

        positions = list(self.config["click_positions"].items())
        table.setRowCount(len(positions))
        for row, (key, coord) in enumerate(positions):
            table.setItem(row, 0, QTableWidgetItem(key))
            table.setItem(row, 1, QTableWidgetItem(str(coord["x"])))
            table.setItem(row, 2, QTableWidgetItem(str(coord["y"])))

        dialog_layout.addWidget(table, stretch=1)

        button_row = QHBoxLayout()
        save_btn = PrimaryPushButton("保存配置")
        reset_btn = PushButton("重置默认")
        cancel_btn = PushButton("取消")
        button_row.addStretch(1)
        button_row.addWidget(reset_btn)
        button_row.addWidget(cancel_btn)
        button_row.addWidget(save_btn)
        dialog_layout.addLayout(button_row)

        timer = QTimer(dialog)
        locked_coords: tuple[int, int] | None = None

        def update_coords():
            nonlocal locked_coords
            if locked_coords is not None:
                x, y = locked_coords
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
            nonlocal locked_coords
            if locked_coords is None:
                locked_coords = pyautogui.position()
                lock_label.setText("坐标已锁定 (F2 解锁)")
                lock_label.setTextColor("#D14343", "#D14343")
            else:
                locked_coords = None
                lock_label.setText("按 F2 锁定/解锁坐标")
                lock_label.setTextColor("#7A8190", "#7A8190")

        coord_btn.clicked.connect(toggle_capture)
        timer.timeout.connect(update_coords)

        # Use a local QShortcut to handle F2
        from PySide6.QtGui import QShortcut

        lock_shortcut = QShortcut(QKeySequence("F2"), dialog)
        lock_shortcut.activated.connect(toggle_lock)

        def save_config_values() -> None:
            try:
                self.config["max_loops"] = int(loop_spin.value())
                for row, (key, _coord) in enumerate(positions):
                    x_item = table.item(row, 1)
                    y_item = table.item(row, 2)
                    if not x_item or not y_item:
                        continue
                    self.config["click_positions"][key]["x"] = int(x_item.text())
                    self.config["click_positions"][key]["y"] = int(y_item.text())

                if self.save_config():
                    show_info(self, "成功", "配置已保存")
                    dialog.accept()
                else:
                    show_error(self, "错误", "保存配置失败，请检查文件权限")
            except ValueError:
                show_error(self, "错误", "请输入有效的数字")

        def reset_config() -> None:
            self.reset_to_default_config()
            dialog.accept()

        save_btn.clicked.connect(save_config_values)
        reset_btn.clicked.connect(reset_config)
        cancel_btn.clicked.connect(dialog.reject)

        dialog.exec()
