from __future__ import annotations

from PySide6.QtCore import QObject
from qfluentwidgets import SystemThemeListener, Theme, setTheme

THEME_MODES: dict[str, Theme] = {"auto": Theme.AUTO, "light": Theme.LIGHT, "dark": Theme.DARK}


def apply_theme_mode(mode: str) -> Theme:
    theme = THEME_MODES.get(mode, Theme.AUTO)
    setTheme(theme)
    return theme


def start_system_theme_listener(parent: QObject) -> SystemThemeListener:
    listener = SystemThemeListener(parent)
    listener.start()
    return listener
