"""Real Excel / screen / clipboard / window ports for the EDC site adder.

Backend module: only stdlib and ``dataforge`` at import time; COM and GUI-automation
libraries are imported lazily so importing this module stays cheap.
"""
from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from dataforge.core.errors import DataForgeError
from dataforge.tools.edc.loop import CellRef, EdcPorts
from dataforge.tools.edc.windows import WindowInfo, activate_window, find_target, list_windows

NO_EXCEL_MESSAGE = "未检测到正在运行的 Excel，请先打开 Excel 并选中第一个站点所在的单元格"
NO_SELECTION_MESSAGE = "请先在 Excel 中选中第一个站点所在的单元格"


class LiveExcel:
    def __init__(self, app: Any) -> None:
        self._app: Any = app

    def selection(self) -> CellRef:
        selection = getattr(self._app, "Selection", None)
        cells = getattr(selection, "Cells", None) if selection is not None else None
        if cells is None:
            raise DataForgeError(NO_SELECTION_MESSAGE)
        cell = cells(1)
        sheet = cell.Worksheet
        return CellRef(
            workbook=sheet.Parent.Name, sheet=sheet.Name, row=cell.Row, column=cell.Column
        )

    def _sheet(self, cell: CellRef) -> tuple[Any, Any]:
        workbook = self._app.Workbooks(cell.workbook)
        return workbook, workbook.Worksheets(cell.sheet)

    def text(self, cell: CellRef) -> str:
        _, sheet = self._sheet(cell)
        return sheet.Cells(cell.row, cell.column).Text

    def focus(self, cell: CellRef) -> None:
        workbook, sheet = self._sheet(cell)
        workbook.Activate()
        sheet.Activate()
        self._app.ActiveWindow.Activate()
        sheet.Cells(cell.row, cell.column).Select()


class LiveScreen:
    def click(self, x: int, y: int) -> None:
        import pyautogui

        pyautogui.click(x, y)

    def paste(self) -> None:
        import pyautogui

        pyautogui.hotkey("ctrl", "v")


class LiveClipboard:
    def copy(self, text: str) -> None:
        import pyperclip

        pyperclip.copy(text)


class LiveWindow:
    def activate(self, target: WindowInfo) -> None:
        match = find_target(target, list_windows())
        if match is None:
            raise DataForgeError(f"找不到目标窗口：{target.title}（{target.process}）")
        activate_window(match.hwnd)


@contextmanager
def open_live_ports() -> Iterator[EdcPorts]:
    import pythoncom
    import pywintypes
    import win32com.client

    pythoncom.CoInitialize()
    app: Any = None
    ports: EdcPorts | None = None
    try:
        try:
            app = win32com.client.GetActiveObject("Excel.Application")
        except pywintypes.com_error as exc:
            raise DataForgeError(NO_EXCEL_MESSAGE) from exc
        ports = EdcPorts(
            excel=LiveExcel(app),
            screen=LiveScreen(),
            clipboard=LiveClipboard(),
            window=LiveWindow(),
            sleep=time.sleep,
        )
        yield ports
    finally:
        if ports is not None:
            ports.excel = None  # type: ignore[assignment]
        ports = None
        app = None
        pythoncom.CoUninitialize()
