"""Capture the README screenshots into docs/images/readme/.

Run on the real desktop (not offscreen: Chinese text needs the system font renderer):

    .venv\\Scripts\\python scripts\\capture_screenshots.py

A temporary config file is used, so the author's own settings and recent list never appear.
The window opens for a few seconds and closes by itself.
"""
from __future__ import annotations

import os
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs" / "images" / "readme"
OLD_IMAGES = (
    "home-overview.png",
    "file-format-converter.png",
    "data-masking-workflow.png",
    "edc-site-adder.png",
)
WINDOW_SIZE = (1200, 760)
SETTLE_MS = 300

_tmp_dir = tempfile.TemporaryDirectory(prefix="dataforge_shots_")
# Must be set before ConfigStore is created; it then never touches the real config.
os.environ["DATAFORGE_STUDIO_CONFIG_PATH"] = str(
    Path(_tmp_dir.name) / "dataforge_studio_config.json"
)
if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
    sys.exit("Run on the real desktop: QT_QPA_PLATFORM=offscreen is set.")
sys.path.insert(0, str(ROOT / "src"))

from PySide6.QtCore import QLocale, QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402
from qfluentwidgets import FluentTranslator  # noqa: E402

from dataforge.config.recent import RecentStore  # noqa: E402
from dataforge.config.store import ConfigStore  # noqa: E402
from dataforge.ui.jobs import JobRunner  # noqa: E402
from dataforge.ui.shell import MainWindow  # noqa: E402
from dataforge.ui.theme import apply_theme_mode  # noqa: E402


def main() -> int:
    app = QApplication(sys.argv)
    translator = FluentTranslator(QLocale("zh_CN"))
    app.installTranslator(translator)
    config = ConfigStore()
    runner = JobRunner()
    window = MainWindow(config, runner, RecentStore(config))
    # Mica leaves the window background transparent, and grab() would then save a see-through
    # image (dark text on nothing). Without Mica the window paints its own theme background.
    window.setMicaEffectEnabled(False)
    window.resize(*WINDOW_SIZE)
    window.show()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    def home() -> None:
        window.switchTo(window.home)

    shots: list[tuple[str, str, Callable[[], None]]] = [
        ("home-light.png", "light", home),
        ("home-dark.png", "dark", home),
        ("format-convert.png", "light", lambda: window.open_tool("format_convert")),
        ("masking-dark.png", "dark", lambda: window.open_tool("masking")),
        ("edc.png", "light", lambda: window.open_tool("edc")),
    ]
    saved: list[Path] = []

    def step(index: int) -> None:
        if index >= len(shots):
            app.quit()
            return
        name, theme, show = shots[index]
        apply_theme_mode(theme)
        show()
        QTimer.singleShot(SETTLE_MS, lambda: capture(index, name))

    def capture(index: int, name: str) -> None:
        path = OUT_DIR / name
        if not window.grab().save(str(path), "PNG"):
            raise RuntimeError(f"could not save {path}")
        saved.append(path)
        step(index + 1)

    QTimer.singleShot(SETTLE_MS, lambda: step(0))
    app.exec()
    runner.shutdown()
    runner.dispose()

    for path in saved:
        sys.stdout.write(f"saved {path.relative_to(ROOT)}\n")
    for name in OLD_IMAGES:
        old = OUT_DIR / name
        if old.exists():
            old.unlink()
            sys.stdout.write(f"removed {old.relative_to(ROOT)}\n")
    _tmp_dir.cleanup()
    return 0 if len(saved) == len(shots) else 1


if __name__ == "__main__":
    sys.exit(main())
