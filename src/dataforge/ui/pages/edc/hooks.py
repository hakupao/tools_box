"""Run-scoped system hooks for the EDC site adder.

The keyboard/mouse libraries call back on their own thread, so the callbacks only emit
Qt signals; receivers are connected normally and run on the main thread (queued).
"""
from __future__ import annotations

from typing import Any

from PySide6.QtCore import QObject, Signal


class EscHook(QObject):
    pressed = Signal()

    def __init__(self, backend: Any = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._backend = backend
        self._handle: Any = None

    def start(self) -> None:
        if self._handle is not None:
            return
        if self._backend is None:
            import keyboard

            self._backend = keyboard
        self._handle = self._backend.on_press_key("esc", self._callback)

    def stop(self) -> None:
        if self._handle is None:
            return
        handle, self._handle = self._handle, None
        self._backend.unhook(handle)

    def is_active(self) -> bool:
        return self._handle is not None

    def _callback(self, event: Any) -> None:
        self.pressed.emit()


class MouseClickHook(QObject):
    clicked = Signal(int, int)  # physical pixels

    def __init__(self, backend: Any = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._backend = backend
        self._handle: Any = None

    def start(self) -> None:
        if self._handle is not None:
            return
        if self._backend is None:
            import mouse

            self._backend = mouse
        self._handle = self._backend.hook(self._callback)

    def stop(self) -> None:
        if self._handle is None:
            return
        handle, self._handle = self._handle, None
        self._backend.unhook(handle)

    def is_active(self) -> bool:
        return self._handle is not None

    def _callback(self, event: Any) -> None:
        if getattr(event, "event_type", None) != "down":
            return
        if getattr(event, "button", None) != "left":
            return
        x, y = self._backend.get_position()
        self.clicked.emit(int(x), int(y))
