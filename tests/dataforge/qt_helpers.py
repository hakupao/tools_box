from __future__ import annotations

import time
from collections.abc import Callable

from PySide6.QtCore import QCoreApplication, QThread
from PySide6.QtWidgets import QApplication


def qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def wait_until(predicate: Callable[[], bool], timeout_ms: int = 5000) -> None:
    qapp()
    deadline = time.monotonic() + timeout_ms / 1000
    while not predicate():
        if time.monotonic() > deadline:
            raise AssertionError(f"condition not met within {timeout_ms} ms")
        QCoreApplication.processEvents()
        QThread.msleep(10)


def drain_deleted(*objs) -> None:
    """deleteLater() every object, then run the deferred deletes deterministically."""
    from PySide6.QtCore import QEvent

    for obj in objs:
        obj.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete.value)
    QCoreApplication.processEvents()
