from __future__ import annotations

import threading
import unittest
from types import SimpleNamespace

from PySide6.QtCore import QThread

from dataforge.ui.pages.edc.hooks import EscHook, MouseClickHook
from tests.dataforge.edc_fakes import FakeKeyboardBackend, FakeMouseBackend
from tests.dataforge.qt_helpers import qapp, wait_until


class EscHookTests(unittest.TestCase):
    def setUp(self) -> None:
        qapp()

    def test_esc_hook_register_once_and_unhook_own_handle(self) -> None:
        backend = FakeKeyboardBackend()
        hook = EscHook(backend)
        hook.start()
        hook.start()
        self.assertEqual(backend.registered, ["esc"])
        self.assertTrue(hook.is_active())
        hook.stop()
        self.assertEqual(len(backend.unhooked), 1)
        self.assertFalse(hook.is_active())
        hook.stop()
        self.assertEqual(len(backend.unhooked), 1)
        self.assertFalse(hasattr(backend, "unhook_all"))

    def test_esc_callback_from_thread_reaches_main(self) -> None:
        backend = FakeKeyboardBackend()
        hook = EscHook(backend)
        seen: list[bool] = []
        hook.pressed.connect(lambda: seen.append(QThread.currentThread() is qapp().thread()))
        hook.start()
        thread = threading.Thread(target=lambda: backend.callback(object()))
        thread.start()
        thread.join()
        wait_until(lambda: bool(seen))
        self.assertEqual(seen, [True])
        hook.stop()


class MouseClickHookTests(unittest.TestCase):
    def setUp(self) -> None:
        qapp()

    def test_mouse_hook_filters_events(self) -> None:
        backend = FakeMouseBackend((10, 20))
        hook = MouseClickHook(backend)
        got: list[tuple[int, int]] = []
        hook.clicked.connect(lambda x, y: got.append((x, y)))
        hook.start()
        hook.start()
        self.assertEqual(len(backend.hooked), 1)
        backend.callback(SimpleNamespace(event_type="up", button="left"))
        backend.callback(SimpleNamespace(event_type="down", button="right"))
        backend.callback(SimpleNamespace(x=1))  # e.g. a MoveEvent
        qapp().processEvents()
        self.assertEqual(got, [])
        backend.callback(SimpleNamespace(event_type="down", button="left"))
        wait_until(lambda: bool(got))
        self.assertEqual(got, [(10, 20)])
        hook.stop()
        hook.stop()
        self.assertEqual(len(backend.unhooked), 1)
        self.assertFalse(hook.is_active())


if __name__ == "__main__":
    unittest.main()
