"""EDC site adder settings with v2 config coercion rules."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dataforge.config.legacy import legacy_file_candidates, load_section_with_legacy
from dataforge.config.store import ConfigStore
from dataforge.tools.edc.windows import WindowInfo

CONFIG_SECTION = "edc_site_adder"
LEGACY_FILE_NAME = "edc_site_adder_config.json"
LEGACY_KEYS = frozenset({"max_loops", "click_positions"})
STEP_KEYS = ("新建", "查找", "搜索框", "搜索", "选择", "ok", "确认")
DEFAULT_POSITIONS: dict[str, tuple[int, int]] = {
    "新建": (241, 212),
    "查找": (1137, 460),
    "搜索框": (817, 409),
    "搜索": (1040, 406),
    "选择": (699, 471),
    "ok": (1121, 758),
    "确认": (1038, 728),
}
MAX_LOOPS_RANGE = (1, 9999)
STEP_DELAY_RANGE = (0.1, 5.0)


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _parse_window(raw: Any) -> WindowInfo | None:
    if not isinstance(raw, dict):
        return None
    hwnd, title, process = raw.get("hwnd"), raw.get("title"), raw.get("process")
    if _is_int(hwnd) and isinstance(title, str) and isinstance(process, str):
        return WindowInfo(hwnd, title, process)
    return None


@dataclass
class EdcConfig:
    max_loops: int = 100
    step_delay: float = 0.3
    click_positions: dict[str, tuple[int, int]] = field(
        default_factory=lambda: dict(DEFAULT_POSITIONS)
    )
    target_window: WindowInfo | None = None

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> EdcConfig:
        cfg = cls()

        loops = raw.get("max_loops")
        if _is_int(loops) and MAX_LOOPS_RANGE[0] <= loops <= MAX_LOOPS_RANGE[1]:
            cfg.max_loops = loops

        delay = raw.get("step_delay")
        if _is_number(delay) and STEP_DELAY_RANGE[0] <= delay <= STEP_DELAY_RANGE[1]:
            cfg.step_delay = float(delay)

        positions = raw.get("click_positions")
        if isinstance(positions, dict):
            for key in STEP_KEYS:
                pos = positions.get(key)
                if isinstance(pos, dict) and _is_int(pos.get("x")) and _is_int(pos.get("y")):
                    cfg.click_positions[key] = (pos["x"], pos["y"])

        cfg.target_window = _parse_window(raw.get("target_window"))
        return cfg

    def to_dict(self) -> dict[str, Any]:
        window = self.target_window
        return {
            "max_loops": self.max_loops,
            "step_delay": self.step_delay,
            "click_positions": {k: {"x": x, "y": y} for k, (x, y) in self.click_positions.items()},
            "target_window": (
                {"hwnd": window.hwnd, "title": window.title, "process": window.process}
                if window
                else None
            ),
        }


def legacy_files() -> list[Path]:
    return legacy_file_candidates(
        LEGACY_FILE_NAME, Path(__file__).resolve().parents[3] / "gui" / "widgets"
    )


def load_config(store: ConfigStore, legacy: Sequence[Path] = ()) -> EdcConfig:
    raw = load_section_with_legacy(store, CONFIG_SECTION, LEGACY_KEYS, legacy)
    return EdcConfig.from_dict(raw)


def save_config(store: ConfigStore, config: EdcConfig) -> bool:
    return store.update_section(CONFIG_SECTION, config.to_dict())
