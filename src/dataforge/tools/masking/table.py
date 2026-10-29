"""CSV table reading shared by the masking scan and execution."""
from __future__ import annotations

import csv
import io
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from dataforge.core.errors import DataForgeError
from dataforge.fileio.text_io import read_text


def is_blank(value: str) -> bool:
    return not value.strip() or value.strip().lower() == "nan"


def find_column(header: Sequence[str], name: str) -> int | None:
    """Index of the first column equal to ``name`` ignoring case (spaces are not stripped)."""
    target = name.lower()
    for index, column in enumerate(header):
        if column.lower() == target:
            return index
    return None


@dataclass
class Table:
    header: list[str]
    rows: list[list[str]]
    encoding: str
    note: str | None


def read_table(path: Path, encoding: str | None) -> Table:
    text, decision = read_text(path, encoding)
    reader = csv.reader(io.StringIO(text, newline=""))
    header: list[str] | None = None
    rows: list[list[str]] = []
    for row in reader:
        if not row:
            continue
        if header is None:
            header = row
            continue
        if len(row) > len(header):
            raise DataForgeError(f"第 {reader.line_num} 行字段数多于表头")
        rows.append(row + [""] * (len(header) - len(row)))
    if header is None:
        raise DataForgeError("文件为空")
    return Table(header, rows, decision.encoding, decision.note)
