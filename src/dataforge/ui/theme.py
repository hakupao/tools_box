from __future__ import annotations

from PySide6.QtCore import QObject, Qt, Slot
from qfluentwidgets import SystemThemeListener, Theme, qconfig, setTheme

THEME_MODES: dict[str, Theme] = {"auto": Theme.AUTO, "light": Theme.LIGHT, "dark": Theme.DARK}


def apply_theme_mode(mode: str) -> Theme:
    theme = THEME_MODES.get(mode, Theme.AUTO)
    setTheme(theme)
    return theme


class _ThemeBridge(QObject):
    """Main-thread receiver for the listener's cross-thread notification.

    qfluentwidgets 1.11.3's listener only switches ``qconfig.theme``; it never refreshes
    style sheets. Re-applying AUTO here does that, on the GUI thread.
    """

    @Slot()
    def on_system_theme_changed(self) -> None:
        if qconfig.themeMode.value == Theme.AUTO:
            setTheme(Theme.AUTO, lazy=True)


def start_system_theme_listener(parent: QObject) -> SystemThemeListener:
    listener = SystemThemeListener(parent)
    bridge = _ThemeBridge(parent)
    listener.systemThemeChanged.connect(
        bridge.on_system_theme_changed, Qt.ConnectionType.QueuedConnection
    )
    listener.start()
    return listener
