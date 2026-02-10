from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from platformdirs import user_config_dir


APP_NAME = "tools_box"
APP_CONFIG_FILENAME = "tools_box_config.json"


def get_app_config_path() -> Path:
    env_path = os.getenv("TOOLS_BOX_CONFIG_PATH")
    if env_path:
        return Path(env_path).expanduser()

    config_dir = Path(user_config_dir(APP_NAME, appauthor=False, roaming=False))
    return config_dir / APP_CONFIG_FILENAME


def load_app_config(path: str | Path | None = None) -> dict[str, Any]:
    config_path = Path(path) if path is not None else get_app_config_path()
    if not config_path.exists():
        return {}

    try:
        with config_path.open("r", encoding="utf-8") as file:
            loaded = json.load(file)
        if isinstance(loaded, dict):
            return loaded
    except Exception:
        pass

    return {}


def save_app_config(payload: dict[str, Any], path: str | Path | None = None) -> bool:
    config_path = Path(path) if path is not None else get_app_config_path()
    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with config_path.open("w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False
