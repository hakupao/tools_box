from __future__ import annotations

import time
from typing import Any

import ctypes

import pyautogui
import pyperclip
import win32com.client
from PySide6.QtCore import QThread, Signal

from .edc_site_adder_service import CLICK_STEP_KEYS


def _activate_window_by_title(title: str) -> bool:
    """Find a window whose title contains *title* and bring it to foreground.

    Uses win32 API directly so we don't depend on pygetwindow at all.
    """
    user32 = ctypes.windll.user32

    found_hwnd = None

    def enum_cb(hwnd, _):
        nonlocal found_hwnd
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return True
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        if title in buf.value:
            found_hwnd = hwnd
            return False  # stop enumeration
        return True

    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int))
    user32.EnumWindows(WNDENUMPROC(enum_cb), 0)

    if found_hwnd is None:
        return False

    SW_RESTORE = 9
    if user32.IsIconic(found_hwnd):
        user32.ShowWindow(found_hwnd, SW_RESTORE)
    user32.SetForegroundWindow(found_hwnd)
    return True


class EdcSiteAdderWorker(QThread):
    log = Signal(str)
    progress = Signal(int, int)  # (current_row_1based, total_rows)
    finished_ok = Signal()
    finished_error = Signal(str)
    finished_stopped = Signal()  # emitted when user cancels via ESC

    def __init__(self, config: dict[str, Any], parent=None) -> None:
        super().__init__(parent)
        self._config = config
        self._stop_requested = False

    def request_stop(self) -> None:
        self._stop_requested = True

    def run(self) -> None:
        import pythoncom

        pythoncom.CoInitialize()
        try:
            self._run()
            if self._stop_requested:
                self.finished_stopped.emit()
        except Exception as exc:
            self.finished_error.emit(str(exc))
        finally:
            pythoncom.CoUninitialize()

    def _run(self) -> None:
        self.log.emit("正在连接 Excel...")
        xl = win32com.client.Dispatch("Excel.Application")
        cell = xl.Selection
        if not cell:
            self.finished_error.emit("未选中 Excel 单元格")
            return

        max_loops = int(self._config.get("max_loops", 100))
        retry_count = int(self._config.get("retry_count", 1))
        step_delay = float(self._config.get("step_delay", 0.3))

        # Count total rows (scan ahead for non-empty cells)
        total = self._count_rows(xl, cell, max_loops)
        self.log.emit(f"预计处理 {total} 行数据")

        for i in range(max_loops):
            if self._stop_requested:
                self.log.emit("处理已停止")
                return

            cell_value = str(cell.Text).strip()
            if not cell_value:
                self.log.emit(f"第 {i + 1} 行为空，自动终止处理")
                break

            self.progress.emit(i + 1, total)
            self.log.emit(f"处理第 {i + 1}/{total} 行: {cell_value}")
            pyperclip.copy(cell_value)
            time.sleep(0.1)

            if self._stop_requested:
                self.log.emit("处理已停止")
                return

            self.log.emit("切换到 Chrome 窗口...")
            if not _activate_window_by_title("Chrome"):
                self.finished_error.emit("未找到 Chrome 窗口")
                return
            time.sleep(0.1)

            if self._stop_requested:
                self.log.emit("处理已停止")
                return

            self.log.emit("执行点击操作...")
            success = self._run_click_sequence_with_retry(step_delay, retry_count)
            if not success:
                if self._stop_requested:
                    self.log.emit("处理已停止")
                    return
                self.finished_error.emit(f"第 {i + 1} 行点击操作失败，已重试 {retry_count} 次")
                return

            if self._stop_requested:
                self.log.emit("处理已停止")
                return

            self.log.emit("切回 Excel 窗口...")
            xl.ActiveWindow.Activate()
            time.sleep(0.1)

            try:
                current_address = cell.Address
                current_row = cell.Row
                current_column = cell.Column
                next_cell = xl.ActiveSheet.Cells(current_row + 1, current_column)
                next_cell.Select()
                cell = xl.Selection
                self.log.emit(f"已移动到下一行: {current_address} -> {cell.Address}")
            except Exception as exc:
                self.finished_error.emit(f"无法移动到下一行 - {exc}")
                return

            time.sleep(0.1)

        self.log.emit("处理完成")
        self.finished_ok.emit()

    def _run_click_sequence_with_retry(self, step_delay: float, max_retries: int) -> bool:
        for attempt in range(max_retries + 1):
            try:
                success = self._run_click_sequence(step_delay)
                if success:
                    return True
                if attempt < max_retries:
                    self.log.emit(f"点击操作失败，第 {attempt + 2} 次重试...")
                    time.sleep(0.5)
            except Exception as exc:
                if attempt < max_retries:
                    self.log.emit(f"异常: {exc}，第 {attempt + 2} 次重试...")
                    time.sleep(0.5)
                else:
                    self.log.emit(f"异常: {exc}")
        return False

    def _run_click_sequence(self, step_delay: float) -> bool:
        positions = self._config.get("click_positions", {})
        for key in CLICK_STEP_KEYS:
            if self._stop_requested:
                return False
            pos = positions.get(key)
            if not pos:
                self.log.emit(f"警告: 未找到 [{key}] 的坐标配置")
                return False
            pyautogui.click(pos["x"], pos["y"])
            if key == "搜索框":
                time.sleep(0.05)
                pyautogui.hotkey("ctrl", "v")
            time.sleep(step_delay)
        return True

    @staticmethod
    def _count_rows(xl: Any, start_cell: Any, max_loops: int) -> int:
        """Scan ahead to count non-empty rows for progress display."""
        try:
            sheet = xl.ActiveSheet
            row = start_cell.Row
            col = start_cell.Column
            count = 0
            for _ in range(max_loops):
                val = str(sheet.Cells(row, col).Text).strip()
                if not val:
                    break
                count += 1
                row += 1
            return max(count, 1)
        except Exception:
            return max_loops
