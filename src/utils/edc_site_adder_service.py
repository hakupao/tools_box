from __future__ import annotations

import copy
import json
import sys
import time
from pathlib import Path
from typing import Any, Callable

import pyautogui
import pyperclip
import win32com.client

from .app_config import get_app_config_path, load_app_config, save_app_config


LogCallback = Callable[[str], None]


class EdcSiteAdderService:
    CONFIG_SECTION = "edc_site_adder"

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
        self._using_default_config_path = config_path is None
        self.config_path = Path(config_path) if config_path else self._default_config_path()
        self.config = copy.deepcopy(self.default_config)
        self.load_config()

    @staticmethod
    def _default_config_path() -> Path:
        return get_app_config_path()

    def load_config(self) -> None:
        root_config = load_app_config(self.config_path)

        section_config = root_config.get(self.CONFIG_SECTION)
        if isinstance(section_config, dict):
            self.config = self._merge_with_defaults(section_config)
            return

        if self._looks_like_legacy_payload(root_config):
            self.config = self._merge_with_defaults(root_config)
            return

        if self._using_default_config_path:
            legacy_config = self._load_legacy_config()
            if legacy_config is not None:
                self.config = self._merge_with_defaults(legacy_config)
                self.save_config()
                return

        self.config = copy.deepcopy(self.default_config)

    def save_config(self) -> bool:
        root_config = load_app_config(self.config_path)
        root_config[self.CONFIG_SECTION] = copy.deepcopy(self.config)
        return save_app_config(root_config, self.config_path)

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

    @staticmethod
    def _looks_like_legacy_payload(raw: object) -> bool:
        if not isinstance(raw, dict):
            return False
        return "max_loops" in raw or "click_positions" in raw

    def _load_legacy_config(self) -> dict[str, Any] | None:
        for path in self._legacy_config_paths():
            loaded = self._load_json_dict(path)
            if loaded is not None and self._looks_like_legacy_payload(loaded):
                return loaded
        return None

    @staticmethod
    def _load_json_dict(path: Path) -> dict[str, Any] | None:
        if not path.exists():
            return None
        try:
            with path.open("r", encoding="utf-8") as file:
                loaded = json.load(file)
            if isinstance(loaded, dict):
                return loaded
        except Exception:
            pass
        return None

    @staticmethod
    def _legacy_config_paths() -> list[Path]:
        candidates: list[Path] = []
        if getattr(sys, "frozen", False):
            candidates.append(Path(sys.executable).resolve().with_name("edc_site_adder_config.json"))

        module_dir = Path(__file__).resolve().parent
        candidates.append(module_dir / "edc_site_adder_config.json")
        candidates.append(module_dir.parent / "gui" / "widgets" / "edc_site_adder_config.json")

        deduped: list[Path] = []
        seen: set[Path] = set()
        for path in candidates:
            if path in seen:
                continue
            seen.add(path)
            deduped.append(path)
        return deduped
