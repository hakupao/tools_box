import subprocess
import sys
import unittest
from types import SimpleNamespace
from unittest import mock

import pywintypes

from dataforge.core.errors import DataForgeError
from dataforge.tools.edc.live import LiveExcel, LiveWindow, open_live_ports
from dataforge.tools.edc.loop import CellRef
from dataforge.tools.edc.windows import WindowInfo


class ImportTests(unittest.TestCase):
    def test_import_is_light(self):
        code = (
            "import sys, dataforge.tools.edc.live\n"
            "assert 'pyautogui' not in sys.modules\n"
            "assert 'pyperclip' not in sys.modules\n"
        )
        proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)


class OpenLivePortsTests(unittest.TestCase):
    def test_no_excel_message(self):
        err = pywintypes.com_error(-2147221021, "Operation unavailable", None, None)
        with mock.patch("pythoncom.CoInitialize") as init, mock.patch(
            "pythoncom.CoUninitialize"
        ) as uninit, mock.patch("win32com.client.GetActiveObject", side_effect=err):
            with self.assertRaises(DataForgeError) as ctx:
                with open_live_ports():
                    pass
        self.assertEqual(
            str(ctx.exception),
            "未检测到正在运行的 Excel，请先打开 Excel 并选中第一个站点所在的单元格",
        )
        init.assert_called_once()
        uninit.assert_called_once()

    def test_uninitialize_on_body_error(self):
        with mock.patch("pythoncom.CoInitialize"), mock.patch(
            "pythoncom.CoUninitialize"
        ) as uninit, mock.patch("win32com.client.GetActiveObject", return_value=object()):
            with self.assertRaises(RuntimeError):
                with open_live_ports():
                    raise RuntimeError("boom")
        uninit.assert_called_once()

    def test_close_before_uninitialize(self):
        order: list[str] = []
        original_close = LiveExcel.close

        def close(self_):
            order.append("close")
            original_close(self_)

        with mock.patch("pythoncom.CoInitialize"), mock.patch(
            "pythoncom.CoUninitialize", side_effect=lambda: order.append("uninit")
        ), mock.patch("win32com.client.GetActiveObject", return_value=object()), \
                mock.patch.object(LiveExcel, "close", close):
            with open_live_ports():
                pass
        self.assertEqual(order, ["close", "uninit"])

    def test_close_releases_app(self):
        excel = LiveExcel(object())
        excel.close()
        self.assertIsNone(excel._app)

    def test_ports_wired(self):
        with mock.patch("pythoncom.CoInitialize"), mock.patch("pythoncom.CoUninitialize"), \
                mock.patch("win32com.client.GetActiveObject", return_value=object()):
            with open_live_ports() as ports:
                self.assertIsInstance(ports.excel, LiveExcel)
                self.assertIsInstance(ports.window, LiveWindow)
                self.assertTrue(callable(ports.sleep))


class LiveWindowTests(unittest.TestCase):
    def test_live_window_missing(self):
        target = WindowInfo(1, "EDC", "chrome.exe")
        with mock.patch("dataforge.tools.edc.live.list_windows", return_value=[]):
            with self.assertRaises(DataForgeError) as ctx:
                LiveWindow().activate(target)
        self.assertEqual(str(ctx.exception), "找不到目标窗口：EDC（chrome.exe）")

    def test_live_window_activates_match(self):
        target = WindowInfo(1, "EDC", "chrome.exe")
        found = WindowInfo(77, "EDC", "chrome.exe")
        with mock.patch("dataforge.tools.edc.live.list_windows", return_value=[found]), \
                mock.patch("dataforge.tools.edc.live.activate_window") as act:
            LiveWindow().activate(target)
        act.assert_called_once_with(77)


def _fake_xl(selection):
    calls: list[str] = []
    cells = SimpleNamespace(
        Text=" v ", Select=lambda: calls.append("select")
    )
    sheet = SimpleNamespace(
        Activate=lambda: calls.append("sheet"), Cells=lambda r, c: cells
    )
    wb = SimpleNamespace(
        Activate=lambda: calls.append("wb"),
        Worksheets=lambda name: sheet,
    )
    xl = SimpleNamespace(
        Selection=selection,
        Workbooks=lambda name: wb,
        ActiveWindow=SimpleNamespace(Activate=lambda: calls.append("window")),
    )
    return xl, calls


class LiveExcelTests(unittest.TestCase):
    def test_live_excel_selection(self):
        sheet = SimpleNamespace(Name="Sheet1", Parent=SimpleNamespace(Name="book.xlsx"))
        cell = SimpleNamespace(Worksheet=sheet, Row=5, Column=3)
        xl, _ = _fake_xl(SimpleNamespace(Cells=lambda i: cell))
        self.assertEqual(LiveExcel(xl).selection(), CellRef("book.xlsx", "Sheet1", 5, 3))

    def test_selection_missing(self):
        for sel in (None, SimpleNamespace()):
            xl, _ = _fake_xl(sel)
            with self.assertRaises(DataForgeError) as ctx:
                LiveExcel(xl).selection()
            self.assertEqual(str(ctx.exception), "请先在 Excel 中选中第一个站点所在的单元格")

    def test_text_and_focus(self):
        xl, calls = _fake_xl(None)
        ex = LiveExcel(xl)
        ref = CellRef("b", "s", 2, 1)
        self.assertEqual(ex.text(ref), " v ")
        ex.focus(ref)
        self.assertEqual(calls, ["wb", "sheet", "window", "select"])


if __name__ == "__main__":
    unittest.main()
