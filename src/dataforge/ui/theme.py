from __future__ import annotations

import logging
import threading
from collections.abc import Callable

import darkdetect
from PySide6.QtCore import QObject, Qt, Signal, Slot
from qfluentwidgets import Theme, qconfig, setTheme

logger = logging.getLogger(__name__)

THEME_MODES: dict[str, Theme] = {"auto": Theme.AUTO, "light": Theme.LIGHT, "dark": Theme.DARK}


def apply_theme_mode(mode: str) -> Theme:
    theme = THEME_MODES.get(mode, Theme.AUTO)
    setTheme(theme)
    return theme


class _ThemeBridge(QObject):
    """Main-thread receiver for the watcher's cross-thread notification.

    Re-reads the system theme and refreshes style sheets on the GUI thread.
    """

    @Slot()
    def on_system_theme_changed(self) -> None:
        if qconfig.themeMode.value == Theme.AUTO:
            # setTheme(AUTO) alone is a no-op while the mode is unchanged; the property
            # setter re-reads the system theme, then setTheme refreshes the style sheets.
            qconfig.theme = Theme.AUTO
            setTheme(Theme.AUTO, lazy=True)


class SystemThemeWatcher(QObject):
    """Follows the OS theme via a daemon thread running ``darkdetect.listener``.

    The listener blocks forever and has no stop flag, so the thread is a daemon that dies with
    the process. Its callback only emits a signal; ``setTheme`` runs on the GUI thread.
    """

    _changed = Signal()

    def __init__(
        self,
        parent: QObject,
        watch: Callable[[Callable[[str], None]], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self._watch = watch if watch is not None else darkdetect.listener
        self._bridge = _ThemeBridge(self)
        self._changed.connect(
            self._bridge.on_system_theme_changed, Qt.ConnectionType.QueuedConnection
        )
        self._thread = threading.Thread(target=self._run, daemon=True, name="dataforge-theme-watch")

    def start(self) -> None:
        self._thread.start()

    def _on_system_theme(self, _value: str) -> None:
        self._changed.emit()

    def _run(self) -> None:
        try:
            self._watch(self._on_system_theme)
        except Exception:
            logger.exception("System theme watcher stopped")


def start_system_theme_listener(
    parent: QObject, watch: Callable[[Callable[[str], None]], None] | None = None
) -> SystemThemeWatcher:
    watcher = SystemThemeWatcher(parent, watch)
    watcher.start()
    return watcher
