"""Masking scan: read the selected CSV files and report what can be masked."""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dataforge.core.errors import DataForgeError
from dataforge.core.progress import CancelToken, ProgressFn
from dataforge.core.result import Result
from dataforge.dates import SlashKind, SlashOrder, is_date_like, slash_kind
from dataforge.fileio.atomic import atomic_path
from dataforge.fileio.encoding import AmbiguousEncodingError, EncodingError
from dataforge.fileio.text_io import write_csv_rows
from dataforge.tools.masking.profile import MaskingProfile
from dataforge.tools.masking.table import find_column, is_blank, read_table

_USUBJID = "USUBJID"
_DM_NAME = "DM.CSV"


@dataclass(frozen=True)
class ScanSettings:
    sample_size: int = 200
    min_non_empty: int = 20
    ratio: float = 0.8

    @classmethod
    def from_profile(cls, p: MaskingProfile) -> ScanSettings:
        return cls(
            p.date_detect_sample_size, p.date_detect_min_non_empty, p.date_detect_success_ratio
        )


@dataclass
class FileScan:
    path: Path
    file_name: str
    encoding: str
    row_count: int
    unique_usubjid_count: int
    non_empty_fields: list[str]
    empty_fields: list[str]
    date_fields: list[str]


@dataclass
class AmbiguousColumn:
    file_name: str
    column: str
    ambiguous: int
    day_first_only: int
    month_first_only: int


@dataclass
class ScanReport:
    files: list[FileScan]
    dm_file: str | None
    dm_first_usubjid: str | None
    subjects: list[str]
    ambiguous_columns: list[AmbiguousColumn]
    settings: ScanSettings
    errors: list[str]
    warnings: list[str]
    signature: str

    @property
    def processable(self) -> bool:
        return not self.errors and bool(self.subjects)

    def to_dict(
        self, date_orders: Mapping[tuple[str, str], SlashOrder] | None = None
    ) -> dict[str, Any]:
        orders = date_orders or {}

        def order_of(column: AmbiguousColumn) -> str | None:
            order = orders.get((column.file_name, column.column))
            return order.value if order is not None else None

        return {
            "dm_file": self.dm_file,
            "dm_first_usubjid": self.dm_first_usubjid,
            "subject_count": len(self.subjects),
            "subjects": list(self.subjects),
            "date_detect": {
                "sample_size": self.settings.sample_size,
                "min_non_empty": self.settings.min_non_empty,
                "ratio": self.settings.ratio,
            },
            "files": [
                {
                    "file_name": f.file_name,
                    "encoding": f.encoding,
                    "row_count": f.row_count,
                    "unique_usubjid_count": f.unique_usubjid_count,
                    "non_empty_fields": list(f.non_empty_fields),
                    "empty_fields": list(f.empty_fields),
                    "date_fields": list(f.date_fields),
                }
                for f in self.files
            ],
            "ambiguous_date_columns": [
                {
                    "file_name": c.file_name,
                    "column": c.column,
                    "ambiguous": c.ambiguous,
                    "day_first_only": c.day_first_only,
                    "month_first_only": c.month_first_only,
                    "order": order_of(c),
                }
                for c in self.ambiguous_columns
            ],
            "errors": list(self.errors),
            "warnings": list(self.warnings),
        }


def _stat(path: Path) -> tuple[int, int]:
    try:
        st = path.stat()
    except OSError:
        return -1, -1
    return st.st_size, st.st_mtime_ns


def scan_signature(
    paths: Sequence[Path],
    settings: ScanSettings,
    encoding: str | None,
    encodings: Mapping[str, str],
) -> str:
    files = sorted((str(p), *_stat(p)) for p in paths)
    payload = {
        "files": files,
        "settings": [settings.sample_size, settings.min_non_empty, settings.ratio],
        "encoding": encoding,
        "encodings": sorted(encodings.items()),
    }
    text = json.dumps(payload, ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _is_date_column(values: list[str], settings: ScanSettings) -> bool:
    sample = values[: max(1, settings.sample_size)]
    if not sample:
        return False
    if len(sample) < max(1, settings.min_non_empty):
        threshold = 1.0
    else:
        threshold = min(1.0, max(0.0, settings.ratio))
    hits = sum(1 for v in sample if is_date_like(v))
    return hits / len(sample) >= threshold


def scan(
    paths: Sequence[Path],
    settings: ScanSettings,
    encoding: str | None,
    encodings: Mapping[str, str],
    progress: ProgressFn,
    cancel: CancelToken,
) -> Result:
    result = Result()
    errors: list[str] = []
    warnings: list[str] = []

    def error(name: str, message: str) -> None:
        errors.append(message)
        result.fail(name, message)

    def warning(name: str, message: str) -> None:
        warnings.append(message)
        result.warn(name, message)

    files: list[Path] = []
    seen: set[Path] = set()
    for path in paths:
        if path.suffix.lower() == ".csv" and path.is_file() and path not in seen:
            seen.add(path)
            files.append(path)

    report = ScanReport(
        files=[],
        dm_file=None,
        dm_first_usubjid=None,
        subjects=[],
        ambiguous_columns=[],
        settings=settings,
        errors=errors,
        warnings=warnings,
        signature=scan_signature(files, settings, encoding, encodings),
    )
    result.data = report

    if not files:
        error("", "未选择任何 CSV 文件")
        return result

    names_seen: dict[str, str] = {}
    reported_dupes: set[str] = set()
    for path in files:
        key = path.name.lower()
        if key not in names_seen:
            names_seen[key] = path.name
        elif key not in reported_dupes:
            reported_dupes.add(key)
            error("", f"文件名重复：{names_seen[key]}（输出时会互相覆盖）")

    dm_scan: FileScan | None = None
    dm_ids_in_order: list[str] = []
    total = len(files)
    for index, path in enumerate(files, 1):
        progress(index, total, path.name)
        cancel.raise_if_cancelled()
        name = path.name
        try:
            table = read_table(path, encodings.get(str(path), encoding))
        except AmbiguousEncodingError as exc:
            result.ask_encoding(path, exc.previews)
            error(name, f"未确定编码：{name}")
            continue
        except (EncodingError, DataForgeError) as exc:
            error(name, f"{name}：{exc}")
            continue
        except PermissionError:
            error(name, f"{name}：无法读取文件（可能已在 Excel 中打开）")
            continue
        except OSError as exc:
            error(name, f"{name}：读取失败（{exc}）")
            continue
        if table.note:
            warning(name, table.note)
        uid_index = find_column(table.header, _USUBJID)
        if uid_index is None:
            error(name, f"文件缺少 USUBJID 列：{name}")
            continue

        ids = [r[uid_index].strip() for r in table.rows]
        ids = [v for v in ids if not is_blank(v)]
        non_empty: list[str] = []
        empty: list[str] = []
        dates: list[str] = []
        for col, column in enumerate(table.header):
            values = [r[col].strip() for r in table.rows if not is_blank(r[col])]
            if not values:
                empty.append(column)
                continue
            non_empty.append(column)
            if not _is_date_column(values, settings):
                continue
            dates.append(column)
            kinds = [slash_kind(v) for v in values]
            amb = kinds.count(SlashKind.AMBIGUOUS)
            dfo = kinds.count(SlashKind.DAY_FIRST_ONLY)
            mfo = kinds.count(SlashKind.MONTH_FIRST_ONLY)
            if amb:
                report.ambiguous_columns.append(AmbiguousColumn(name, column, amb, dfo, mfo))
                warning(name, f"{column} 列有 {amb} 个日期无法判断是 日/月 还是 月/日，请选择顺序")
            if dfo and mfo:
                warning(name, f"{column} 列同时有只能按 日/月 和只能按 月/日 解读的日期，请检查数据")

        file_scan = FileScan(
            path, name, table.encoding, len(table.rows), len(set(ids)), non_empty, empty, dates
        )
        report.files.append(file_scan)
        if name.upper() == _DM_NAME:
            dm_scan = file_scan
            dm_ids_in_order = ids

    if sum(1 for p in files if p.name.upper() == _DM_NAME) != 1:
        error("", "DM.csv 必须且只能有 1 个")
    elif dm_scan is not None:
        report.dm_file = dm_scan.file_name
        report.subjects = sorted(set(dm_ids_in_order))
        if report.subjects:
            report.dm_first_usubjid = dm_ids_in_order[0]
        else:
            error(dm_scan.file_name, "DM.csv 中没有有效的 USUBJID")

    result.count("files", len(report.files))
    result.count("subjects", len(report.subjects))
    return result


def export_report(report: ScanReport, target: Path) -> Path:
    if target.suffix.lower() == ".csv":
        rows = [
            [
                "file_name",
                "row_count",
                "unique_usubjid_count",
                "non_empty_fields",
                "empty_fields",
                "date_fields",
            ]
        ]
        for f in report.files:
            rows.append(
                [
                    f.file_name,
                    str(f.row_count),
                    str(f.unique_usubjid_count),
                    "|".join(f.non_empty_fields),
                    "|".join(f.empty_fields),
                    "|".join(f.date_fields),
                ]
            )
        write_csv_rows(rows, target)
    else:
        text = json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n"
        with atomic_path(target) as tmp:
            with open(tmp, "w", encoding="utf-8", newline="\n") as f:
                f.write(text)
    return target
