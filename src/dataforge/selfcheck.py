"""Import self-check for packaged builds (``DataForgeStudio.exe --self-check``).

No Qt import at module level: page modules are only imported inside ``self_check``.
"""
from __future__ import annotations

import importlib

EXTRA_MODULES = (
    "dataforge.tools.edc.live",
    "pyautogui",
    "pyperclip",
    "keyboard",
    "mouse",
    "win32com.client",
    "pythoncom",
    "win32gui",
    "win32process",
    "openpyxl",
)


def _modules() -> list[str]:
    from dataforge.ui.registry import TOOLS

    pages = [spec.page.split(":", 1)[0] for spec in TOOLS]
    return pages + list(EXTRA_MODULES)


def self_check() -> list[str]:
    """Import every lazily loaded module; return ``"<module>: <error>"`` per failure."""
    failures: list[str] = []
    for name in _modules():
        try:
            importlib.import_module(name)
        except Exception as exc:  # noqa: BLE001 - report every import failure
            failures.append(f"{name}: {exc}")
    return failures
