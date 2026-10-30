"""EDC site adder row loop: injectable ports, one run segment, and the whole-run session."""
from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Protocol

from dataforge.core.errors import DataForgeError
from dataforge.core.progress import CancelToken, ProgressFn
from dataforge.core.result import Result
from dataforge.tools.edc.config import STEP_KEYS, EdcConfig
from dataforge.tools.edc.windows import WindowInfo

logger = logging.getLogger(__name__)

STEP_NAMES: tuple[str, ...] = (
    "读取单元格",
    "复制到剪贴板",
    "激活目标窗口",
    "点击【新建】",
    "点击【查找】",
    "点击【搜索框】并粘贴",
    "点击【搜索】",
    "点击【选择】",
    "点击【ok】",
    "点击【确认】",
    "切回 Excel 并选中下一行",
)
_FIRST_CLICK_STEP = 4  # STEP_KEYS[i] is step _FIRST_CLICK_STEP + i
_PASTE_KEY = "搜索框"
_SHORT_WAIT = 0.1
_PASTE_WAIT = 0.05
ESC_REASON = "已按 ESC 停止"
FAILSAFE_REASON = "鼠标移到了屏幕角落，已触发安全停止"


@dataclass(frozen=True)
class CellRef:
    workbook: str
    sheet: str
    row: int
    column: int

    def address(self) -> str:
        letters = ""
        n = self.column
        while n > 0:
            n, rem = divmod(n - 1, 26)
            letters = chr(ord("A") + rem) + letters
        return f"{letters}{self.row}"

    def at_row(self, row: int) -> CellRef:
        return replace(self, row=row)


class ExcelPort(Protocol):
    def selection(self) -> CellRef: ...

    def text(self, cell: CellRef) -> str: ...

    def focus(self, cell: CellRef) -> None: ...


class ScreenPort(Protocol):
    def click(self, x: int, y: int) -> None: ...

    def paste(self) -> None: ...


class ClipboardPort(Protocol):
    def copy(self, text: str) -> None: ...


class WindowPort(Protocol):
    def activate(self, target: WindowInfo) -> None: ...


class StopFlag(Protocol):
    def is_set(self) -> bool: ...


@dataclass
class EdcPorts:
    excel: ExcelPort
    screen: ScreenPort
    clipboard: ClipboardPort
    window: WindowPort
    sleep: Callable[[float], None]


@dataclass(frozen=True)
class RowDone:
    cell: CellRef
    value: str


@dataclass(frozen=True)
class RowStop:
    cell: CellRef
    value: str
    step: int  # 1-based index into STEP_NAMES; 1 means nothing was done for this row
    reason: str
    by_user: bool

    @property
    def step_name(self) -> str:
        return STEP_NAMES[self.step - 1]


@dataclass
class Segment:
    start: CellRef
    end_row: int
    done: list[RowDone]
    stop: RowStop | None
    reached: str  # "empty" | "limit" | "stopped"


class _RowStopped(Exception):
    def __init__(self, stop: RowStop) -> None:
        super().__init__(stop.reason)
        self.stop = stop


def _reason(exc: BaseException) -> str:
    name = type(exc).__name__
    if name == "FailSafeException":
        return FAILSAFE_REASON
    return str(exc) or name


def _count_rows(excel: ExcelPort, start: CellRef, end_row: int) -> int:
    try:
        count = 0
        for row in range(start.row, end_row):
            if not excel.text(start.at_row(row)).strip():
                break
            count += 1
        return count
    except Exception:
        return end_row - start.row


def _process_row(
    config: EdcConfig,
    ports: EdcPorts,
    cell: CellRef,
    target: WindowInfo,
    index: int,
    total: int,
    stop: StopFlag,
    progress: ProgressFn,
    cancel: CancelToken,
) -> str:
    """Run the 11 steps for one row; return the value ("" = empty cell, nothing done)."""
    value = ""

    def step(number: int, action: Callable[[], None]) -> None:
        cancel.raise_if_cancelled()
        if stop.is_set():
            raise _RowStopped(RowStop(cell, value, number, ESC_REASON, True))
        try:
            action()
        except Exception as exc:
            raise _RowStopped(RowStop(cell, value, number, _reason(exc), False)) from exc

    # Step 1 reads before honouring ESC: an empty cell ends the segment even after an ESC
    # pressed during the previous row, and a non-empty stop carries the value.
    cancel.raise_if_cancelled()
    try:
        value = ports.excel.text(cell).strip()
    except Exception as exc:
        raise _RowStopped(RowStop(cell, value, 1, _reason(exc), False)) from exc
    if not value:
        return ""
    if stop.is_set():
        raise _RowStopped(RowStop(cell, value, 1, ESC_REASON, True))
    addr = cell.address()
    progress(index, total, f"Excel {addr}：{value}")
    logger.info("EDC 第 %d/%d 行 Excel %s：%s", index, total, addr, value)

    def copy() -> None:
        ports.clipboard.copy(value)
        ports.sleep(_SHORT_WAIT)

    def activate() -> None:
        ports.window.activate(target)
        ports.sleep(_SHORT_WAIT)

    step(2, copy)
    step(3, activate)
    for offset, key in enumerate(STEP_KEYS):
        x, y = config.click_positions[key]

        def click(x: int = x, y: int = y, key: str = key) -> None:
            ports.screen.click(x, y)
            if key == _PASTE_KEY:
                ports.sleep(_PASTE_WAIT)
                ports.screen.paste()
            ports.sleep(config.step_delay)

        step(_FIRST_CLICK_STEP + offset, click)

    def focus_next() -> None:
        ports.excel.focus(cell.at_row(cell.row + 1))
        ports.sleep(_SHORT_WAIT)

    step(len(STEP_NAMES), focus_next)
    return value


def run_segment(
    config: EdcConfig,
    ports: EdcPorts,
    start: CellRef | None,
    end_row: int | None,
    stop: StopFlag,
    progress: ProgressFn,
    cancel: CancelToken,
) -> Result:
    """Process rows from ``start`` down until an empty cell, ``end_row`` or the first stop."""
    target = config.target_window
    if target is None:
        raise DataForgeError("未设置目标窗口")
    if start is None:
        try:
            start = ports.excel.selection()
        except DataForgeError:
            raise
        except Exception as exc:
            raise DataForgeError(f"无法读取 Excel 选中的单元格：{exc}") from exc
    if end_row is None:
        end_row = start.row + config.max_loops

    total = _count_rows(ports.excel, start, end_row)
    segment = Segment(start, end_row, [], None, "limit")
    for index, row in enumerate(range(start.row, end_row), start=1):
        cell = start.at_row(row)
        try:
            value = _process_row(
                config, ports, cell, target, index, total, stop, progress, cancel
            )
        except _RowStopped as stopped:
            segment.stop = stopped.stop
            segment.reached = "stopped"
            logger.info(
                "EDC 在 %s 第 %d 步停止：%s",
                cell.address(),
                stopped.stop.step,
                stopped.stop.reason,
            )
            break
        if not value:
            segment.reached = "empty"
            break
        segment.done.append(RowDone(cell, value))

    result = Result(data=segment)
    result.count("succeeded", len(segment.done))
    return result


class StopChoice(Enum):
    REDO = "redo"
    SKIP = "skip"
    END = "end"


@dataclass
class EdcSession:
    first: CellRef
    end_row: int
    done: list[RowDone] = field(default_factory=list)
    skipped: list[RowStop] = field(default_factory=list)
    failed: list[RowStop] = field(default_factory=list)

    @classmethod
    def begin(cls, segment: Segment) -> EdcSession:
        session = cls(segment.start, segment.end_row)
        session.absorb(segment)
        return session

    def absorb(self, segment: Segment) -> None:
        self.done.extend(segment.done)

    def resolve(self, stop: RowStop, choice: StopChoice) -> CellRef | None:
        """Apply the user's choice for a stopped row; return where the next segment starts."""
        if choice is StopChoice.REDO:
            return stop.cell
        if choice is StopChoice.SKIP:
            self.skipped.append(stop)
            next_cell = stop.cell.at_row(stop.cell.row + 1)
            return next_cell if next_cell.row < self.end_row else None
        if not (stop.by_user and stop.step == 1):  # an untouched row is not a failure
            self.failed.append(stop)
        return None

    def to_result(self) -> Result:
        result = Result(data=self)
        result.stats = {
            "succeeded": len(self.done),
            "skipped": len(self.skipped),
            "failed": len(self.failed),
        }
        for stop in self.skipped:
            result.warn(
                stop.cell.address(),
                f"已跳过（第 {stop.step} 步「{stop.step_name}」：{stop.reason}）",
            )
        for stop in self.failed:
            result.fail(
                stop.cell.address(),
                f"出错（第 {stop.step} 步「{stop.step_name}」：{stop.reason}）",
            )
        return result

    def done_lines(self) -> list[str]:
        return [f"{d.cell.address()} {d.value}" for d in self.done]
