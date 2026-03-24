from __future__ import annotations

import copy
import json
import sys
import time
from pathlib import Path
from typing import Any, Callable

from .app_config import get_app_config_path, load_app_config, save_app_config


LogCallback = Callable[[str], None]

CLICK_STEP_KEYS = ("新建", "查找", "搜索框", "搜索", "选择", "ok", "确认")


class EdcSiteAdderService:
    CONFIG_SECTION = "edc_site_adder"

    DEFAULT_CONFIG: dict[str, Any] = {
        "max_loops": 100,
        "retry_count": 1,
        "step_delay": 0.3,
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
        self.default_config = copy.deepcopy(self.DEFAULT_CONFIG)
        self._using_default_config_path = config_path is None
        self.config_path = Path(config_path) if config_path else self._default_config_path()
        self.config: dict[str, Any] = copy.deepcopy(self.default_config)
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

    def _merge_with_defaults(self, loaded_config: object) -> dict:
        merged_config = copy.deepcopy(self.default_config)
        if not isinstance(loaded_config, dict):
            return merged_config

        for int_key in ("max_loops", "retry_count"):
            value = loaded_config.get(int_key)
            if isinstance(value, int) and value > 0:
                merged_config[int_key] = value

        step_delay = loaded_config.get("step_delay")
        if isinstance(step_delay, (int, float)) and step_delay > 0:
            merged_config["step_delay"] = float(step_delay)

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
