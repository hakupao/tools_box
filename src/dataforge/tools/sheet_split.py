"""Split Excel workbooks into one CSV per sheet (also used by XLSX -> CSV conversion)."""
from __future__ import annotations

import logging
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, datetime, time
from pathlib import Path

from openpyxl import load_workbook

from dataforge.core.errors import DataForgeError
from dataforge.core.progress import CancelToken, ProgressFn
from dataforge.core.result import Result
from dataforge.fileio.paths import plan_output
from dataforge.fileio.text_io import write_csv_rows

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = (".xlsx", ".xlsm")

_INVALID_CHARS_PATTERN = re.compile(r'[<>:"/\\|?*]')
_CONTROL_CHARS_PATTERN = re.compile(r"[\x00-\x1f]")
RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    "COM1",
    "COM2",
    "COM3",
    "COM4",
    "COM5",
    "COM6",
    "COM7",
    "COM8",
    "COM9",
    "LPT1",
    "LPT2",
    "LPT3",
    "LPT4",
    "LPT5",
    "LPT6",
    "LPT7",
    "LPT8",
    "LPT9",
}


@dataclass
class SplitOptions:
    output_dir: Path | None = None


def sanitize_sheet_name(name: str) -> str:
    sanitized = _INVALID_CHARS_PATTERN.sub("_", name)
    sanitized = _CONTROL_CHARS_PATTERN.sub("_", sanitized)
    sanitized = sanitized.rstrip(" .")

    if sanitized in {"", ".", ".."}:
        sanitized = "Sheet"

    if sanitized.upper() in RESERVED_NAMES:
        sanitized = f"{sanitized}_"

    return sanitized


def _make_unique_name(name: str, used_names: set[str]) -> str:
    if name not in used_names:
        used_names.add(name)
        return name

    counter = 1
    while True:
        candidate = f"{name}_{counter}"
        if candidate not in used_names:
            used_names.add(candidate)
            return candidate
        counter += 1


def _read_sheet_as_strings(rows: Iterable[Iterable[object]]) -> list[list[str]]:
    output_rows: list[list[str]] = []
    max_nonempty_col = -1

    for row in rows:
        string_row = [_cell_to_string(cell) for cell in row]
        for idx in range(len(string_row) - 1, -1, -1):
            if string_row[idx] != "":
                if idx > max_nonempty_col:
                    max_nonempty_col = idx
                break
        output_rows.append(string_row)

    if max_nonempty_col >= 0:
        output_rows = [row[: max_nonempty_col + 1] for row in output_rows]

    while output_rows and all(cell == "" for cell in output_rows[-1]):
        output_rows.pop()

    return output_rows


def sheet_rows(ws) -> list[list[str]]:
    """All rows of a worksheet as strings, without trailing blank rows/columns."""
    return _read_sheet_as_strings(ws.iter_rows())


def _cell_to_string(cell: object) -> str:
    if cell is None:
        return ""

    value = getattr(cell, "value", cell)
    if value is None:
        return ""

    if getattr(cell, "is_date", False) and isinstance(value, (datetime, date)):
        number_format = getattr(cell, "number_format", "")
        return _format_excel_date(value, number_format)

    return str(value)


def _format_excel_date(value: object, number_format: str) -> str:
    fmt = (number_format or "").lower()
    fmt = fmt.split(";")[0]
    fmt = re.sub(r"\[[^\]]*\]", "", fmt)
    fmt = re.sub(r'"[^"]*"', "", fmt)

    if "h" in fmt:
        date_part, time_part = fmt.split("h", 1)
        time_part = "h" + time_part
    else:
        date_part, time_part = fmt, ""

    date_tokens = _extract_date_tokens(date_part)
    sep = _detect_date_separator(date_part)
    date_str = _render_date_tokens(value, date_tokens, sep)

    include_time = _should_include_time(value, time_part)
    if not include_time:
        return date_str

    time_str = _render_time(value, time_part)
    return f"{date_str} {time_str}"


def _extract_date_tokens(date_part: str) -> Sequence[str]:
    tokens: list[str] = []
    i = 0
    while i < len(date_part):
        ch = date_part[i]
        if ch in {"y", "m", "d"}:
            j = i + 1
            while j < len(date_part) and date_part[j] == ch:
                j += 1
            tokens.append(date_part[i:j])
            i = j
        else:
            i += 1
    return tokens


def _detect_date_separator(date_part: str) -> str:
    if "/" in date_part:
        return "/"
    if "-" in date_part:
        return "-"
    if "." in date_part:
        return "."
    return "-"


def _render_date_tokens(value: object, tokens: Sequence[str], sep: str) -> str:
    if not isinstance(value, (datetime, date)):
        return str(value)

    year = value.year
    month = value.month
    day = value.day

    if not tokens:
        return f"{year:04d}{sep}{month:02d}{sep}{day:02d}"

    parts: list[str] = []
    for token in tokens:
        if token.startswith("y"):
            if len(token) <= 2:
                parts.append(f"{year % 100:02d}")
            else:
                parts.append(f"{year:04d}")
        elif token.startswith("m"):
            if len(token) >= 2:
                parts.append(f"{month:02d}")
            else:
                parts.append(str(month))
        elif token.startswith("d"):
            if len(token) >= 2:
                parts.append(f"{day:02d}")
            else:
                parts.append(str(day))

    return sep.join(parts)


def _should_include_time(value: object, time_part: str) -> bool:
    if not isinstance(value, datetime):
        return False
    if value.time() != time(0, 0, 0):
        return True
    return bool(time_part and ("h" in time_part or "s" in time_part))


def _render_time(value: datetime, time_part: str) -> str:
    include_seconds = "s" in time_part
    return value.strftime("%H:%M:%S" if include_seconds else "%H:%M")


def export_workbook(
    src: Path,
    *,
    all_sheets: bool,
    output_dir: Path | None,
    result: Result,
    cancel: CancelToken,
) -> None:
    """Write sheets of ``src`` as CSV files; first sheet only unless ``all_sheets``."""
    try:
        workbook = load_workbook(src, read_only=True, data_only=True)
    except PermissionError:
        result.fail(src, "无法读取文件（可能已在 Excel 中打开）")
        return
    except Exception as exc:  # noqa: BLE001 - per-file isolation
        result.fail(src, f"读取失败：{exc}")
        return

    try:
        sheet_names = list(workbook.sheetnames)
        if not all_sheets:
            sheet_names = sheet_names[:1]
        used_names: set[str] = set()
        for sheet_name in sheet_names:
            cancel.raise_if_cancelled()
            try:
                if all_sheets:
                    safe_name = _make_unique_name(sanitize_sheet_name(sheet_name), used_names)
                    new_name = f"{src.stem}_{safe_name}.csv"
                else:
                    new_name = f"{src.stem}.csv"
                rows = sheet_rows(workbook[sheet_name])
                target = plan_output(src, new_name=new_name, output_dir=output_dir)
                write_csv_rows(rows, target)
            except Exception as exc:  # noqa: BLE001 - continue with next sheet
                result.fail(src, f"{sheet_name}: {exc}")
                continue
            result.add_output(target)
            result.count("sheets")
    finally:
        workbook.close()


def run(
    files: list[Path], options: SplitOptions, progress: ProgressFn, cancel: CancelToken
) -> Result:
    if not files:
        raise DataForgeError("请先选择要拆分的 Excel 文件")
    result = Result()
    total = len(files)
    for index, src in enumerate(files, 1):
        progress(index, total, src.name)
        cancel.raise_if_cancelled()
        errors_before = len(result.errors)
        export_workbook(
            src, all_sheets=True, output_dir=options.output_dir, result=result, cancel=cancel
        )
        if len(result.errors) == errors_before:
            result.count("files")
    return result
