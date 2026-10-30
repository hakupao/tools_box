import unittest

import win32api
import win32con
import win32gui

from dataforge.core.errors import DataForgeError

from dataforge.tools.edc.windows import (
    WindowInfo,
    activate_window,
    find_target,
    list_windows,
    process_name,
    window_at,
)


class FindTargetTests(unittest.TestCase):
    def test_find_target_rules(self):
        target = WindowInfo(10, "EDC - Chrome", "chrome.exe")
        same = WindowInfo(10, "renamed", "Chrome.EXE")
        other = WindowInfo(11, "notepad", "notepad.exe")
        self.assertIs(find_target(target, [other, same]), same)

        # stale hwnd, same title
        t1 = WindowInfo(99, "EDC - Chrome", "chrome.exe")
        a = WindowInfo(1, "x", "chrome.exe")
        b = WindowInfo(2, "EDC - Chrome", "chrome.exe")
        self.assertIs(find_target(t1, [a, b, other]), b)

        # the only same-process window
        self.assertIs(find_target(t1, [a, other]), a)

        # two same-process windows, no title match
        self.assertIsNone(find_target(t1, [a, WindowInfo(3, "y", "chrome.exe"), other]))

        # case-insensitive process
        self.assertIs(find_target(t1, [WindowInfo(5, "z", "CHROME.exe")]).hwnd, 5)

        # same hwnd, different process: not a hit
        self.assertIsNone(find_target(target, [WindowInfo(10, "EDC - Chrome", "edge.exe")]))
        self.assertIsNone(find_target(target, []))


class EmptyProcessTests(unittest.TestCase):
    def test_find_target_empty_process(self):
        target = WindowInfo(10, "EDC", "")
        self.assertIsNone(find_target(target, [WindowInfo(11, "EDC", "")]))
        self.assertIsNone(find_target(target, [WindowInfo(11, "EDC", "chrome.exe")]))
        same = WindowInfo(10, "other", "")
        self.assertIs(find_target(target, [WindowInfo(11, "EDC", ""), same]), same)


class ActivateTests(unittest.TestCase):
    def test_invalid_hwnd_raises(self):
        with self.assertRaises(DataForgeError) as ctx:
            activate_window(0x7FFFFFF)
        self.assertEqual(str(ctx.exception), "目标窗口已关闭")


class WindowSmokeTests(unittest.TestCase):
    """Uses a real native window: the suite runs Qt offscreen, which has no HWNDs."""

    def setUp(self):
        wc = win32gui.WNDCLASS()
        wc.lpszClassName = f"EdcProbe{id(self)}"
        wc.hInstance = win32api.GetModuleHandle(None)
        wc.lpfnWndProc = {}
        atom = win32gui.RegisterClass(wc)
        self.addCleanup(win32gui.UnregisterClass, atom, wc.hInstance)
        self.hwnd = win32gui.CreateWindowEx(
            win32con.WS_EX_TOPMOST,
            atom,
            "edc-probe",
            win32con.WS_OVERLAPPEDWINDOW | win32con.WS_VISIBLE,
            100,
            100,
            300,
            200,
            0,
            0,
            wc.hInstance,
            None,
        )
        self.addCleanup(win32gui.DestroyWindow, self.hwnd)
        win32gui.PumpWaitingMessages()

    def test_list_windows_smoke(self):
        found = [i for i in list_windows(exclude_pid=-1) if i.title == "edc-probe"]
        self.assertTrue(found)
        self.assertEqual(found[0].hwnd, self.hwnd)
        self.assertTrue(found[0].process.startswith("python"))
        self.assertTrue(found[0].process.endswith(".exe"))
        self.assertFalse(any(i.title == "edc-probe" for i in list_windows()))
        self.assertEqual(process_name(self.hwnd), found[0].process)
        self.assertEqual(process_name(0), "")

    def test_process_name_own_process(self):
        self.assertTrue(process_name(self.hwnd).startswith("python"))

    def test_window_at_own_window_is_none(self):
        left, top, right, bottom = win32gui.GetWindowRect(self.hwnd)
        self.assertIsNone(window_at((left + right) // 2, (top + bottom) // 2))
