"""Sectioned JSON config store with atomic saves and corrupt-file backup."""
from __future__ import annotations

import copy
import json
import logging
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from platformdirs import user_config_dir

logger = logging.getLogger(__name__)

ENV_CONFIG_PATH = "DATAFORGE_STUDIO_CONFIG_PATH"
ENV_LEGACY_CONFIG_PATH = "TOOLS_BOX_CONFIG_PATH"


def default_config_path() -> Path:
    for var in (ENV_CONFIG_PATH, ENV_LEGACY_CONFIG_PATH):
        value = os.environ.get(var)
        if value:
            return Path(value).expanduser()
    base = user_config_dir("dataforge_studio", appauthor=False, roaming=False)
    return Path(base) / "dataforge_studio_config.json"


def legacy_config_path() -> Path:
    base = user_config_dir("tools_box", appauthor=False, roaming=False)
    return Path(base) / "tools_box_config.json"


class ConfigStore:
    def __init__(self, path: Path | None = None, legacy_path: Path | None = None) -> None:
        if path is None:
            self.path = default_config_path()
            self._legacy: Path | None = legacy_path or legacy_config_path()
        else:
            self.path = Path(path)
            self._legacy = legacy_path

    def section(self, name: str) -> dict[str, Any]:
        try:
            value = self._load().get(name)
        except OSError:
            logger.exception("Could not read config %s", self.path)
            return {}
        return copy.deepcopy(value) if isinstance(value, dict) else {}

    def update_section(self, name: str, data: dict[str, Any]) -> bool:
        tmp_name: str | None = None
        try:
            config = self._load()
            config[name] = data
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp_name = tempfile.mkstemp(
                dir=self.path.parent, prefix=self.path.name + ".", suffix=".tmp"
            )
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            os.replace(tmp_name, self.path)
            return True
        except Exception:
            logger.exception("Failed to save config section %r to %s", name, self.path)
            if tmp_name:
                try:
                    os.unlink(tmp_name)
                except OSError:
                    pass
            return False

    def _load(self) -> dict[str, Any]:
        """Load config; raises OSError if an existing file cannot be read."""
        source = self.path
        if not source.exists():
            if self._legacy is not None and self._legacy.exists():
                source = self._legacy
            else:
                return {}
        try:
            data = json.loads(source.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {}
        except ValueError:  # JSONDecodeError and UnicodeDecodeError
            logger.warning("Corrupt config file: %s", source)
            self._backup_corrupt(source)
            return {}
        # other OSError propagates: a read failure is not corruption
        if not isinstance(data, dict):
            logger.warning("Config top level is not an object: %s", source)
            self._backup_corrupt(source)
            return {}
        return data

    def _backup_corrupt(self, source: Path) -> None:
        if source != self.path:
            return  # never modify the legacy file
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = source.with_name(f"{source.name}.corrupt-{stamp}.bak")
        try:
            os.replace(source, backup)
        except OSError:
            logger.exception("Could not back up corrupt config %s", source)
