"""Format conversion: CSV <-> XLSX, CSV to UTF-8 BOM, CSV quote removal."""
from __future__ import annotations

import csv
import io
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from openpyxl import Workbook
from openpyxl.utils.exceptions import IllegalCharacterError

from dataforge.core.errors import DataForgeError
from dataforge.core.progress import CancelToken, ProgressFn
from dataforge.core.result import Result
from dataforge.fileio.atomic import atomic_path
from dataforge.fileio.encoding import AmbiguousEncodingError, EncodingError
from dataforge.fileio.paths import plan_output
from dataforge.fileio.text_io import read_text, write_text
from dataforge.tools import sheet_split

logger = logging.getLogger(__name__)

_CANCEL_CHECK_ROWS = 5000
_SNIFF_DELIMITERS = ",\t;|"
_DELIMITER_NAMES = {"\t": "制表符", ";": "分号", "|": "竖线"}


class ConvertMode(str, Enum):
    CSV_TO_XLSX = "csv_to_xlsx"
    XLSX_TO_CSV = "xlsx_to_csv"
    CSV_TO_BOM = "csv_to_bom"
    CSV_UNQUOTE = "csv_unquote"


MODE_EXTENSIONS: dict[ConvertMode, tuple[str, ...]] = {
    ConvertMode.CSV_TO_XLSX: (".csv",),
    ConvertMode.XLSX_TO_CSV: sheet_split.SUPPORTED_EXTENSIONS,
    ConvertMode.CSV_TO_BOM: (".csv",),
    ConvertMode.CSV_UNQUOTE: (".csv",),
}


@dataclass
class FormatOptions:
    mode: ConvertMode
    output_dir: Path | None = None
    overwrite_source: bool = False
    all_sheets: bool = False
    encoding: str | None = None
    encodings: dict[str, str] = field(default_factory=dict)


def _csv_to_xlsx(
    text: str, src: Path, options: FormatOptions, result: Result, cancel: CancelToken
) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    for index, row in enumerate(csv.reader(io.StringIO(text, newline="")), 1):
        if index % _CANCEL_CHECK_ROWS == 0:
            cancel.raise_if_cancelled()
        try:
            ws.append(row)
        except IllegalCharacterError:
            result.fail(src, f"第 {index} 行含 Excel 不支持的控制字符")
            return
        for cell in ws[ws.max_row][: len(row)]:
            cell.data_type = "s"  # keep "=SUM(A1)" etc. as literal text, not a formula
            cell.number_format = "@"
    target = plan_output(src, new_name=f"{src.stem}.xlsx", output_dir=options.output_dir)
    with atomic_path(target) as tmp:
        wb.save(tmp)
    result.add_output(target)


def _csv_to_bom(text: str, src: Path, options: FormatOptions, result: Result) -> None:
    target = plan_output(
        src,
        new_name=f"{src.stem}_bom.csv",
        output_dir=options.output_dir,
        overwrite_source=options.overwrite_source,
    )
    write_text(text, target)
    result.add_output(target)


def _detect_delimiter(text: str) -> str:
    try:
        return csv.Sniffer().sniff(text[:1024], delimiters=_SNIFF_DELIMITERS).delimiter
    except csv.Error:
        return ","


def _format_field(value: str, delimiter: str) -> tuple[str, bool]:
    """Minimal-quote one field; returns (text, was_quoted)."""
    if any(d in value for d in _SNIFF_DELIMITERS) or"\r" in value or "\n" in value or value.startswith('"'):
        return '"' + value.replace('"', '""') + '"', True
    return value, False


def _csv_unquote(
    text: str, src: Path, options: FormatOptions, result: Result, cancel: CancelToken
) -> None:
    delimiter = _detect_delimiter(text)
    if delimiter != ",":
        result.warn(src, f"按「{_DELIMITER_NAMES[delimiter]}」分隔识别")
    quoted = 0
    lines: list[str] = []
    for index, row in enumerate(csv.reader(io.StringIO(text, newline=""), delimiter=delimiter), 1):
        if index % _CANCEL_CHECK_ROWS == 0:
            cancel.raise_if_cancelled()
        if row == [""]:
            lines.append('""')  # keep a one-empty-field row distinct from a blank line
            continue
        parts = []
        for value in row:
            piece, was_quoted = _format_field(value, delimiter)
            quoted += was_quoted
            parts.append(piece)
        lines.append(delimiter.join(parts))
    target = plan_output(
        src,
        new_name=f"{src.stem}_unquoted.csv",
        output_dir=options.output_dir,
        overwrite_source=options.overwrite_source,
    )
    write_text("".join(line + "\r\n" for line in lines), target)
    result.add_output(target)
    if quoted:
        result.warn(src, f"{quoted} 个字段含分隔符、换行或以引号开头，已保留引号")


def _convert_csv(
    src: Path, options: FormatOptions, result: Result, cancel: CancelToken
) -> None:
    forced = options.encodings.get(str(src), options.encoding)
    try:
        text, decision = read_text(src, forced)
    except AmbiguousEncodingError as exc:
        result.ask_encoding(src, exc.previews)
        return
    except EncodingError as exc:
        result.fail(src, str(exc))
        return
    if decision.note:
        result.warn(src, decision.note)

    mode = options.mode
    if mode is ConvertMode.CSV_TO_XLSX:
        _csv_to_xlsx(text, src, options, result, cancel)
    elif mode is ConvertMode.CSV_TO_BOM:
        if decision.encoding == "utf-8-sig":
            result.warn(src, "已是 UTF-8 BOM，未生成文件")
            return
        _csv_to_bom(text, src, options, result)
    else:
        _csv_unquote(text, src, options, result, cancel)


def run(
    files: list[Path], options: FormatOptions, progress: ProgressFn, cancel: CancelToken
) -> Result:
    if not files:
        raise DataForgeError("请先选择要转换的文件")
    result = Result()
    allowed = MODE_EXTENSIONS[options.mode]
    total = len(files)
    for index, src in enumerate(files, 1):
        progress(index, total, src.name)
        cancel.raise_if_cancelled()
        if src.suffix.lower() not in allowed:
            result.fail(src, "文件类型与所选模式不符")
            continue
        errors_before = len(result.errors)
        outputs_before = len(result.outputs)
        try:
            if options.mode is ConvertMode.XLSX_TO_CSV:
                sheet_split.export_workbook(
                    src,
                    all_sheets=options.all_sheets,
                    output_dir=options.output_dir,
                    result=result,
                    cancel=cancel,
                )
            else:
                _convert_csv(src, options, result, cancel)
        except PermissionError:
            result.fail(src, "无法写入输出文件（可能已被其他程序打开）")
        except Exception as exc:  # noqa: BLE001 - per-file isolation
            logger.exception("convert failed: %s", src)
            result.fail(src, f"转换失败：{exc}")
        if len(result.errors) == errors_before:
            result.count("files" if len(result.outputs) > outputs_before else "skipped")
    return result
