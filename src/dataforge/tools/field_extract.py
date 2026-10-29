"""Field extraction: list the header fields of every CSV/Excel file in a folder."""
from __future__ import annotations

import csv
import io
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

from openpyxl import load_workbook

from dataforge.core.errors import DataForgeError
from dataforge.core.progress import CancelToken, ProgressFn
from dataforge.core.result import Result
from dataforge.fileio.encoding import AmbiguousEncodingError, EncodingError
from dataforge.fileio.paths import iter_input_files, plan_output
from dataforge.fileio.text_io import read_text, write_csv_rows

logger = logging.getLogger(__name__)

SUMMARY_NAME = "file_fields_summary.csv"
SUPPORTED_EXTENSIONS = (".csv", ".xlsx", ".xlsm")
_SUMMARY_PATTERN = re.compile(r"^file_fields_summary(_\d+)?\.csv$", re.IGNORECASE)


@dataclass
class FieldOptions:
    header_row: int = 1
    include_subfolders: bool = False
    output_dir: Path | None = None
    encoding: str | None = None
    encodings: dict[str, str] = field(default_factory=dict)


def _csv_fields(src: Path, options: FieldOptions, result: Result) -> list[str] | None:
    """Header fields of a CSV; ``None`` when the file was questioned or failed."""
    forced = options.encodings.get(str(src), options.encoding)
    try:
        text, decision = read_text(src, forced)
    except AmbiguousEncodingError as exc:
        result.ask_encoding(src, exc.previews)
        return None
    except EncodingError as exc:
        result.fail(src, str(exc))
        return []
    if decision.note:
        result.warn(src, decision.note)
    for index, row in enumerate(csv.reader(io.StringIO(text, newline="")), 1):
        if index == options.header_row:
            return list(row)
    return []


def _excel_fields(src: Path, options: FieldOptions, result: Result) -> list[str]:
    try:
        wb = load_workbook(src, read_only=True, data_only=True)
    except PermissionError:
        result.fail(src, "无法读取文件（可能已在 Excel 中打开）")
        return []
    except Exception as exc:  # noqa: BLE001 - unreadable workbook
        result.fail(src, f"读取失败：{exc}")
        return []
    fields: list[str] = []
    try:
        for ws in wb.worksheets:
            rows = ws.iter_rows(
                min_row=options.header_row, max_row=options.header_row, values_only=True
            )
            header = next(rows, None)
            if header is None:
                continue
            values = ["" if v is None else str(v) for v in header]
            while values and values[-1] == "":
                values.pop()
            fields.extend(f"{ws.title}: {v}" for v in values)
    except Exception as exc:  # noqa: BLE001 - corrupt sheet data
        result.fail(src, f"读取失败：{exc}")
        return []
    finally:
        wb.close()
    return fields


def run(folder: Path, options: FieldOptions, progress: ProgressFn, cancel: CancelToken) -> Result:
    folder = Path(folder)
    if not folder.is_dir():
        raise DataForgeError("请选择有效的文件夹")
    if options.header_row < 1:
        raise DataForgeError("列名行号必须大于等于 1")
    files = [
        f
        for f in iter_input_files(
            [folder], SUPPORTED_EXTENSIONS, recursive=options.include_subfolders
        )
        if not _SUMMARY_PATTERN.match(f.name)
    ]
    if not files:
        raise DataForgeError("该文件夹中没有 CSV 或 Excel 文件")

    result = Result()
    rows: list[list[str]] = [["文件名", "字段名"]]
    total = len(files)
    for index, src in enumerate(files, 1):
        rel = src.relative_to(folder).as_posix()
        progress(index, total, rel)
        cancel.raise_if_cancelled()
        errors_before = len(result.errors)
        questions_before = len(result.encoding_questions)
        try:
            if src.suffix.lower() == ".csv":
                fields = _csv_fields(src, options, result)
            else:
                fields = _excel_fields(src, options, result)
        except PermissionError:
            result.fail(src, "无法读取文件（可能已被其他程序占用）")
            fields = []
        except Exception as exc:  # noqa: BLE001 - per-file isolation
            logger.exception("field extract failed: %s", src)
            result.fail(src, f"读取失败：{exc}")
            fields = []
        if len(result.encoding_questions) > questions_before:
            continue
        failed = len(result.errors) > errors_before
        if not failed:
            result.count("files")
            result.count("fields", len(fields or []))
        if fields:
            rows.extend([rel, name] for name in fields)
        else:
            rows.append([rel, ""])

    summary = plan_output(
        folder / SUMMARY_NAME, new_name=SUMMARY_NAME, output_dir=options.output_dir
    )
    write_csv_rows(rows, summary)
    result.add_output(summary)
    return result
