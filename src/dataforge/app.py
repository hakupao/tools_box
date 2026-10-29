"""Application entry point."""
from __future__ import annotations

import logging
import os
import sys

from PySide6.QtWidgets import QApplication

from dataforge.config.recent import RecentStore
from dataforge.config.store import ConfigStore
from dataforge.core.logs import setup_logging
from dataforge.ui.gc_guard import MainThreadGarbageCollector
from dataforge.ui.jobs import JobRunner, wait_for_orphans
from dataforge.ui.shell import MainWindow
from dataforge.ui.theme import apply_theme_mode, start_system_theme_listener

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    try:
        setup_logging()
    except OSError:
        logging.basicConfig(level=logging.INFO)
        logger.exception("File logging unavailable; logging to stderr")

    app = QApplication(sys.argv if argv is None else argv)
    gc_guard = MainThreadGarbageCollector(app)
    gc_guard.start()
    config = ConfigStore()
    apply_theme_mode(config.section("app").get("theme", "auto"))
    theme_watcher = start_system_theme_listener(app)  # daemon thread; dies with the process
    runner = JobRunner()
    recent = RecentStore(config)
    window = MainWindow(config, runner, recent)
    window.show()

    code = app.exec()
    # gc stays disabled through shutdown: a still-running worker must never trigger a
    # collection off the GUI thread. ``gc_guard`` stays referenced until main() returns.

    runner.shutdown()
    runner.dispose()
    if not wait_for_orphans(3000):
        logger.warning("Background job still running at exit; forcing exit")
        logging.shutdown()
        os._exit(code)
    return code
