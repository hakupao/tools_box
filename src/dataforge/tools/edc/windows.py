"""Target window discovery and activation (pywin32, no UI imports)."""
from __future__ import annotations

import os
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import PureWindowsPath

import win32api
import win32con
import win32gui
import win32process

from dataforge.core.errors import DataForgeError

_PROCESS_QUERY_AND_READ = 0x0410  # PROCESS_QUERY_INFORMATION | PROCESS_VM_READ
_GA_ROOT = 2
_SW_RESTORE = 9


@dataclass(frozen=True)
class WindowInfo:
    hwnd: int
    title: str
    process: str


def find_target(target: WindowInfo, candidates: Sequence[WindowInfo]) -> WindowInfo | None:
    proc = target.process.lower()
    same_proc = [c for c in candidates if c.process.lower() == proc]
    for c in same_proc:
        if c.hwnd == target.hwnd:
            return c
    for c in same_proc:
        if c.title == target.title:
            return c
    if len(same_proc) == 1:
        return same_proc[0]
    return None


def _pid_of(hwnd: int) -> int:
    return win32process.GetWindowThreadProcessId(hwnd)[1]


def _process_name_for_pid(pid: int) -> str:
    try:
        handle = win32api.OpenProcess(_PROCESS_QUERY_AND_READ, False, pid)
    except Exception:
        return ""
    try:
        return PureWindowsPath(win32process.GetModuleFileNameEx(handle, 0)).name.lower()
    except Exception:
        return ""
    finally:
        try:
            win32api.CloseHandle(handle)
        except Exception:
            pass


def process_name(hwnd: int) -> str:
    try:
        return _process_name_for_pid(_pid_of(hwnd))
    except Exception:
        return ""


def list_windows(exclude_pid: int | None = None) -> list[WindowInfo]:
    skip = os.getpid() if exclude_pid is None else exclude_pid
    result: list[WindowInfo] = []

    def _visit(hwnd: int, _extra: object) -> bool:
        try:
            if not win32gui.IsWindowVisible(hwnd):
                return True
            title = win32gui.GetWindowText(hwnd)
            if not title:
                return True
            pid = _pid_of(hwnd)
            if pid == skip:
                return True
            result.append(WindowInfo(hwnd, title, _process_name_for_pid(pid)))
        except Exception:
            pass
        return True

    try:
        win32gui.EnumWindows(_visit, None)
    except Exception:
        pass
    return result


def window_at(x: int, y: int) -> WindowInfo | None:
    try:
        hwnd = win32gui.WindowFromPoint((int(x), int(y)))
        if not hwnd:
            return None
        root = win32gui.GetAncestor(hwnd, _GA_ROOT) or hwnd
        pid = _pid_of(root)
        if pid == os.getpid():
            return None
        return WindowInfo(root, win32gui.GetWindowText(root), _process_name_for_pid(pid))
    except Exception:
        return None


def activate_window(hwnd: int) -> None:
    if not hwnd or not win32gui.IsWindow(hwnd):
        raise DataForgeError("目标窗口已关闭")
    try:
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, _SW_RESTORE)
        for attempt in range(2):
            try:
                win32gui.SetForegroundWindow(hwnd)
                return
            except Exception:
                if attempt == 0:
                    win32api.keybd_event(win32con.VK_MENU, 0, 0, 0)
                    win32api.keybd_event(win32con.VK_MENU, 0, 2, 0)
    except Exception:
        pass
    raise DataForgeError("无法激活目标窗口")
