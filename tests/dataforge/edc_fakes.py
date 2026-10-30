"""Shared fakes for the EDC site adder tests (loop ports; later phases add hook backends).

``FakePorts.trace`` records every port call as one line; the golden traces depend on this
exact format:

    excel.selection -> A2      excel.text A3      excel.focus A4
    clipboard.copy SITE-1      window.activate
    screen.click 241 212       screen.paste       sleep 0.3
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from dataforge.tools.edc.loop import CellRef, EdcPorts
from dataforge.tools.edc.windows import WindowInfo

WORKBOOK = "Book1"
SHEET = "Sheet1"
COLUMN = 1


class _Excel:
    def __init__(self, owner: FakePorts) -> None:
        self._owner = owner

    def selection(self) -> CellRef:
        cell = CellRef(WORKBOOK, SHEET, self._owner.start_row, COLUMN)
        self._owner._record("excel.selection", f"excel.selection -> {cell.address()}")
        return cell

    def text(self, cell: CellRef) -> str:
        self._owner._record("excel.text", f"excel.text {cell.address()}")
        return self._owner.cells.get(cell.row, "")

    def focus(self, cell: CellRef) -> None:
        self._owner._record("excel.focus", f"excel.focus {cell.address()}")


class _Screen:
    def __init__(self, owner: FakePorts) -> None:
        self._owner = owner

    def click(self, x: int, y: int) -> None:
        self._owner._record("screen.click", f"screen.click {x} {y}")

    def paste(self) -> None:
        self._owner._record("screen.paste", "screen.paste")


class _Clipboard:
    def __init__(self, owner: FakePorts) -> None:
        self._owner = owner

    def copy(self, text: str) -> None:
        self._owner._record("clipboard.copy", f"clipboard.copy {text}")


class _Window:
    def __init__(self, owner: FakePorts) -> None:
        self._owner = owner

    def activate(self, target: WindowInfo) -> None:
        self._owner._record("window.activate", "window.activate")


class _TraceStop:
    """Stop flag that turns on once the trace holds ``esc_after`` lines (never if None)."""

    def __init__(self, owner: FakePorts) -> None:
        self._owner = owner

    def is_set(self) -> bool:
        limit = self._owner.esc_after
        return limit is not None and len(self._owner.trace) >= limit


class FakePorts:
    """In-memory Excel column A of ``Book1``/``Sheet1`` plus recording screen/clipboard/window.

    ``fail`` entries ``{"call", "nth", "message", "exc"}`` each raise on the nth (1-based) call
    of that action, counted over the whole life of this object (so across segments). The call
    is recorded in the trace before it raises. ``exc`` is a class name (a same-named Exception
    subclass is created on the fly) or None for ``RuntimeError``.
    """

    def __init__(
        self,
        cells: dict[int, str],
        start_row: int,
        fail: list[dict[str, Any]] | None = None,
        esc_after: int | None = None,
        on_call: Callable[[str], None] | None = None,
    ) -> None:
        self.cells = dict(cells)
        self.start_row = start_row
        self.fail = list(fail or [])
        self.esc_after = esc_after
        self.on_call = on_call  # called with the action name before each recorded call
        self.trace: list[str] = []
        self._counts: dict[str, int] = {}
        self._ports = EdcPorts(
            excel=_Excel(self),
            screen=_Screen(self),
            clipboard=_Clipboard(self),
            window=_Window(self),
            sleep=self._sleep,
        )

    def ports(self) -> EdcPorts:
        return self._ports

    def stop_flag(self) -> _TraceStop:
        return _TraceStop(self)

    def _sleep(self, seconds: float) -> None:
        self._record("sleep", f"sleep {format(seconds, 'g')}")

    def _record(self, call: str, line: str) -> None:
        if self.on_call is not None:
            self.on_call(call)
        self.trace.append(line)
        n = self._counts.get(call, 0) + 1
        self._counts[call] = n
        for entry in self.fail:
            if entry["call"] == call and entry["nth"] == n:
                message = entry.get("message", "")
                name = entry.get("exc")
                exc_type = type(name, (Exception,), {}) if name else RuntimeError
                raise exc_type(message)


class FakeKeyboardBackend:
    """Records on_press_key/unhook and keeps the callback; deliberately no unhook_all."""

    def __init__(self) -> None:
        self.registered: list[str] = []
        self.unhooked: list[Any] = []
        self.callback: Any = None

    def on_press_key(self, key: str, callback: Any) -> object:
        self.registered.append(key)
        self.callback = callback
        return object()

    def unhook(self, handle: Any) -> None:
        self.unhooked.append(handle)


class FakeMouseBackend:
    """Records hook/unhook and keeps the callback; get_position is configurable."""

    def __init__(self, position: tuple[int, int] = (10, 20)) -> None:
        self.position = position
        self.hooked: list[Any] = []
        self.unhooked: list[Any] = []
        self.callback: Any = None

    def hook(self, callback: Any) -> Any:
        self.hooked.append(callback)
        self.callback = callback
        return callback

    def unhook(self, handle: Any) -> None:
        self.unhooked.append(handle)

    def get_position(self) -> tuple[int, int]:
        return self.position
