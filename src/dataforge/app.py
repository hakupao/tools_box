"""Application entry point."""
from __future__ import annotations

import logging
import os
import sys

from PySide6.QtCore import QLocale
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication
from qfluentwidgets import FluentTranslator

from dataforge.config.recent import RecentStore
from dataforge.config.store import ConfigStore
from dataforge.core.logs import default_log_dir, setup_logging
from dataforge.selfcheck import self_check
from dataforge.ui.gc_guard import MainThreadGarbageCollector
from dataforge.ui.jobs import JobRunner, wait_for_orphans
from dataforge.ui.resources import app_icon_path
from dataforge.ui.shell import MainWindow
from dataforge.ui.theme import apply_theme_mode, start_system_theme_listener

logger = logging.getLogger(__name__)

SELF_CHECK_FLAG = "--self-check"


def run_self_check() -> int:
    """Import-check the bundle and write ``self_check.txt`` to the log dir (no window)."""
    failures = self_check()
    for failure in failures:
        logger.error("Self-check failed: %s", failure)
    text = "\n".join(failures) if failures else "OK"
    try:
        log_dir = default_log_dir()
        log_dir.mkdir(parents=True, exist_ok=True)
        (log_dir / "self_check.txt").write_text(text + "\n", encoding="utf-8")
    except OSError:
        # A windowed exe has no console: report via the exit code instead of crashing.
        logger.exception("Could not write self_check.txt")
        return 1
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    try:
        setup_logging()
    except OSError:
        logging.basicConfig(level=logging.INFO)
        logger.exception("File logging unavailable; logging to stderr")

    args = sys.argv if argv is None else argv
    if SELF_CHECK_FLAG in args:
        return run_self_check()

    app = QApplication(args)
    icon_path = app_icon_path()
    if icon_path is not None:
        app.setWindowIcon(QIcon(str(icon_path)))
    translator = FluentTranslator(QLocale("zh_CN"))  # Chinese button texts in fluent dialogs
    app.installTranslator(translator)  # ``translator`` stays referenced until main() returns
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
