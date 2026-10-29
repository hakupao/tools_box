"""Rotating file logging setup."""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

import platformdirs

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def default_log_dir() -> Path:
    return Path(platformdirs.user_log_dir("dataforge_studio", appauthor=False))


def setup_logging(log_dir: Path | None = None, level: int = logging.INFO) -> Path:
    """Attach a rotating file handler to the ``dataforge`` logger (idempotent)."""
    directory = Path(log_dir) if log_dir is not None else default_log_dir()
    directory.mkdir(parents=True, exist_ok=True)
    log_path = directory / "dataforge.log"

    logger = logging.getLogger("dataforge")
    logger.setLevel(level)
    target = str(log_path.resolve())
    for handler in logger.handlers:
        if (
            isinstance(handler, RotatingFileHandler)
            and Path(handler.baseFilename).resolve() == Path(target)
        ):
            return log_path

    handler = RotatingFileHandler(
        log_path, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(handler)
    return log_path
