from __future__ import annotations

import copy
import json
import time
from pathlib import Path
from typing import Callable

import pyautogui
import pyperclip
import win32com.client


LogCallback = Callable[[str], None]


class EdcSiteAdderService:
    DEFAULT_CONFIG = {
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

    def __init__(self, config_path: str | Path | None = None) -> None:
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.5

        self.processing = False
        self.default_config = copy.deepcopy(self.DEFAULT_CONFIG)
        self.config_path = Path(config_path) if config_path else self._default_config_path()
        self.config = copy.deepcopy(self.default_config)
        self.load_config()

    @staticmethod
    def _default_config_path() -> Path:
        return Path(__file__).resolve().with_name("edc_site_adder_config.json")

    def load_config(self) -> None:
        try:
            if self.config_path.exists():
                with self.config_path.open("r", encoding="utf-8") as file:
                    loaded_config = json.load(file)
                self.config = self._merge_with_defaults(loaded_config)
                return
        except Exception:
            pass
        self.config = copy.deepcopy(self.default_config)

    def save_config(self) -> bool:
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with self.config_path.open("w", encoding="utf-8") as file:
                json.dump(self.config, file, indent=4, ensure_ascii=False)
            return True
        except Exception:
            return False

    def reset_to_default_config(self) -> bool:
        self.config = copy.deepcopy(self.default_config)
        return self.save_config()

    def stop_processing(self) -> None:
        self.processing = False

    def start_processing(self, log_callback: LogCallback) -> None:
        if self.processing:
            return

        self.processing = True
        log_callback("开始处理...")

        try:
            self._run(log_callback)
        except Exception as exc:  # pylint: disable=broad-except
            log_callback(f"错误: {exc}")
        finally:
            self.processing = False

    def _run(self, log_callback: LogCallback) -> None:
        log_callback("正在连接 Excel...")
        xl = win32com.client.Dispatch("Excel.Application")
        cell = xl.Selection
        if not cell:
            log_callback("错误: 未选中 Excel 单元格")
            self.processing = False
            return

        for i in range(int(self.config.get("max_loops", 0))):
            if not self._ensure_running(log_callback):
                break

            cell_value = str(cell.Text).strip()
            if not cell_value:
                log_callback(f"第 {i + 1} 行为空，自动终止处理")
                break

            log_callback(f"处理第 {i + 1} 行: {cell_value}")
            pyperclip.copy(cell_value)
            time.sleep(0.1)

            if not self._ensure_running(log_callback):
                break

            log_callback("切换到 Chrome 窗口...")
            chrome_windows = pyautogui.getWindowsWithTitle("Chrome")
            if not chrome_windows:
                log_callback("错误: 未找到 Chrome 窗口")
                self.processing = False
                return

            chrome_windows[0].activate()
            time.sleep(0.1)

            if not self._ensure_running(log_callback):
                break

            log_callback("执行点击操作...")
            if not self._run_click_sequence(log_callback):
                break

            if not self._ensure_running(log_callback):
                break

            log_callback("切回 Excel 窗口...")
            xl.ActiveWindow.Activate()
            time.sleep(0.1)

            try:
                current_address = cell.Address
                current_row = cell.Row
                current_column = cell.Column
                log_callback(f"当前单元格: {current_address} (行: {current_row}, 列: {current_column})")

                next_row = current_row + 1
                next_cell = xl.ActiveSheet.Cells(next_row, current_column)
                next_cell.Select()
                cell = xl.Selection
                log_callback(f"已移动到下一行: {current_address} -> {cell.Address}")
            except Exception as exc:  # pylint: disable=broad-except
                log_callback(f"错误: 无法移动到下一行 - {exc}")
                break

            time.sleep(0.1)

        if self.processing:
            log_callback("处理完成")

    def _run_click_sequence(self, log_callback: LogCallback) -> bool:
        for key in ("新建", "查找", "搜索框", "搜索", "选择", "ok", "确认"):
            self._click(key)
            if key == "搜索框":
                pyautogui.hotkey("ctrl", "v")
                time.sleep(0.1)
            if not self._ensure_running(log_callback):
                return False
        return True

    def _click(self, key: str) -> None:
        if not self.processing:
            return
        pos = self.config["click_positions"][key]
        pyautogui.click(pos["x"], pos["y"])
        time.sleep(0.1)

    def _ensure_running(self, log_callback: LogCallback) -> bool:
        if self.processing:
            return True
        log_callback("处理已停止")
        return False

    def _merge_with_defaults(self, loaded_config: object) -> dict:
        merged_config = copy.deepcopy(self.default_config)
        if not isinstance(loaded_config, dict):
            return merged_config

        max_loops = loaded_config.get("max_loops")
        if isinstance(max_loops, int) and max_loops > 0:
            merged_config["max_loops"] = max_loops

        loaded_positions = loaded_config.get("click_positions")
        if not isinstance(loaded_positions, dict):
            return merged_config

        for key in merged_config["click_positions"]:
            loaded_position = loaded_positions.get(key)
            if not isinstance(loaded_position, dict):
                continue
            x = loaded_position.get("x")
            y = loaded_position.get("y")
            if isinstance(x, int) and isinstance(y, int):
                merged_config["click_positions"][key]["x"] = x
                merged_config["click_positions"][key]["y"] = y

        return merged_config
