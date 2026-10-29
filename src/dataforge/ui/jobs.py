"""Global single background job runner.

Threading model: every :class:`_Worker` (a ``QThread`` subclass) lives in the main
thread; its signals are emitted from the worker thread and connected to
:class:`JobRunner` slots with ``Qt.QueuedConnection``, so all runner state changes
happen in the main thread. Job code only ever emits signals; it never touches widgets.
Job functions must not create QObjects or call ``gc.collect()`` (garbage collection
happens only in the main thread, via ``MainThreadGarbageCollector``).
"""
from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from typing import Any

import time

from PySide6.QtCore import QObject, QThread, Qt, Signal, Slot

from dataforge.core.errors import Cancelled, DataForgeError
from dataforge.core.progress import CancelToken, ProgressFn
from dataforge.core.result import Result

logger = logging.getLogger(__name__)

JobFn = Callable[[ProgressFn, CancelToken], Result]

_QUEUED = Qt.ConnectionType.QueuedConnection


class _Worker(QThread):
    progress = Signal(int, int, str)
    outcome = Signal(str, str, object)  # tool_id, kind ("ok"|"cancelled"|"failed"), payload

    def __init__(self, tool_id: str, fn: JobFn, token: CancelToken, parent: QObject | None = None):
        super().__init__(parent)
        self.tool_id = tool_id
        self._fn = fn
        self.token = token

    def run(self) -> None:
        try:
            result = self._fn(self.progress.emit, self.token)
        except Cancelled:
            self.outcome.emit(self.tool_id, "cancelled", None)
        except DataForgeError as exc:
            self.outcome.emit(self.tool_id, "failed", str(exc))
        except Exception as exc:  # noqa: BLE001 - last line of defence for job code
            logger.exception("Unexpected error in job %s", self.tool_id)
            self.outcome.emit(self.tool_id, "failed", f"内部错误：{exc}")
        else:
            self.outcome.emit(self.tool_id, "ok", result)


_ORPHANS: set[_Worker] = set()
_ORPHANS_LOCK = threading.Lock()


class _OrphanReaper(QObject):
    """Main-thread object that drops finished orphan workers from the keep-alive set."""

    @Slot()
    def reap(self) -> None:
        worker = self.sender()
        if isinstance(worker, _Worker) and worker.isFinished():
            with _ORPHANS_LOCK:
                _ORPHANS.discard(worker)
            worker.deleteLater()


_reaper: _OrphanReaper | None = None


def _orphan(worker: _Worker) -> None:
    global _reaper
    if _reaper is None:
        _reaper = _OrphanReaper()
    with _ORPHANS_LOCK:
        _ORPHANS.add(worker)
    worker.finished.connect(_reaper.reap, _QUEUED)
    if worker.isFinished():  # finished between wait() timing out and connecting
        with _ORPHANS_LOCK:
            _ORPHANS.discard(worker)


def wait_for_orphans(timeout_ms: int) -> bool:
    """Wait for timed-out workers; True if none are still running."""
    with _ORPHANS_LOCK:
        workers = list(_ORPHANS)
    deadline = time.monotonic() + timeout_ms / 1000
    for w in workers:
        w.wait(max(0, int((deadline - time.monotonic()) * 1000)))
    with _ORPHANS_LOCK:
        for w in workers:
            if w.isFinished():
                _ORPHANS.discard(w)
        return not any(w.isRunning() for w in _ORPHANS)


class _LogBridge(QObject):
    message = Signal(str)


class _ForwardHandler(logging.Handler):
    """Logging handler callable from any thread; forwards via a Qt signal."""

    def __init__(self, bridge: _LogBridge, is_busy: Callable[[], bool]) -> None:
        super().__init__()
        self._bridge = bridge
        self._is_busy = is_busy
        self.setFormatter(logging.Formatter("%(levelname)s %(message)s"))

    def emit(self, record: logging.LogRecord) -> None:
        try:
            if self._is_busy():
                self._bridge.message.emit(self.format(record))
        except Exception:  # noqa: BLE001
            self.handleError(record)


class JobRunner(QObject):
    started = Signal(str)
    progress = Signal(int, int, str)
    log = Signal(str)
    finished = Signal(str, object)
    failed = Signal(str, str)
    cancelled = Signal(str)
    busy_changed = Signal(bool)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._worker: _Worker | None = None
        self._busy = False
        self._closing = False  # set by shutdown(); no new job may start afterwards
        self._tool: str | None = None
        self._bridge = _LogBridge(self)
        self._bridge.message.connect(self.log, _QUEUED)
        self._handler: logging.Handler | None = _ForwardHandler(self._bridge, lambda: self._busy)
        root = logging.getLogger("dataforge")
        if root.level == logging.NOTSET:
            root.setLevel(logging.INFO)
        root.addHandler(self._handler)

    # -- public API -------------------------------------------------------
    def is_busy(self) -> bool:
        return self._busy

    def current_tool(self) -> str | None:
        return self._tool

    def submit(self, tool_id: str, fn: JobFn) -> bool:
        """Start ``fn``; False if a job is running or the runner is shutting down."""
        if self._busy or self._closing:
            return False
        worker = _Worker(tool_id, fn, CancelToken())
        worker.progress.connect(self._on_progress, _QUEUED)
        worker.outcome.connect(self._on_outcome, _QUEUED)
        worker.finished.connect(self._on_thread_finished, _QUEUED)
        self._worker = worker
        self._tool = tool_id
        self._busy = True
        self.busy_changed.emit(True)
        self.started.emit(tool_id)
        worker.start()
        return True

    def cancel(self) -> None:
        if self._worker is not None:
            self._worker.token.cancel()

    def shutdown(self, timeout_ms: int = 5000) -> None:
        # First, so follow-up handlers woken by busy_changed(False) cannot start a job.
        self._closing = True
        worker = self._worker
        if worker is None:
            return
        worker.token.cancel()
        if worker.wait(timeout_ms):
            self._release(worker)
        else:
            logger.warning("Job %s did not stop within %d ms; orphaning it", worker.tool_id, timeout_ms)
            _orphan(worker)
            self._release(worker, delete=False)

    def dispose(self) -> None:
        """Remove the logging handler (idempotent)."""
        if self._handler is not None:
            logging.getLogger("dataforge").removeHandler(self._handler)
            self._handler = None

    # -- main-thread slots -------------------------------------------------
    def _is_current_sender(self) -> bool:
        sender = self.sender()
        return sender is not None and sender is self._worker

    @Slot(int, int, str)
    def _on_progress(self, current: int, total: int, label: str) -> None:
        if self._is_current_sender():
            self.progress.emit(current, total, label)

    @Slot(str, str, object)
    def _on_outcome(self, tool_id: str, kind: str, payload: Any) -> None:
        if not self._is_current_sender():
            return  # stale event from an earlier job
        if kind == "ok":
            self.finished.emit(tool_id, payload)
        elif kind == "cancelled":
            self.cancelled.emit(tool_id)
        else:
            self.failed.emit(tool_id, payload)

    @Slot()
    def _on_thread_finished(self) -> None:
        worker = self._worker
        # Ignore stale events from an earlier (released or orphaned) thread.
        if worker is not None and self._is_current_sender() and worker.isFinished():
            self._release(worker)

    def _release(self, worker: _Worker, delete: bool = True) -> None:
        if self._worker is not worker:
            return
        self._worker = None
        self._tool = None
        self._busy = False
        if delete:
            worker.deleteLater()
        self.busy_changed.emit(False)
