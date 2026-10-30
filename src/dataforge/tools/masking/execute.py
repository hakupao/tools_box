"""Masking execution: rewrite the scanned CSV files into a new masked_output folder."""
from __future__ import annotations

import os
import re
import shutil
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from dataforge.core.errors import DataForgeError
from dataforge.core.progress import CancelToken, ProgressFn
from dataforge.core.result import Result
from dataforge.dates import DateOutcome, SlashOrder, mask_date
from dataforge.fileio.text_io import write_csv_rows
from dataforge.tools.masking.profile import MaskingProfile, RuleStep
from dataforge.tools.masking.scan import (
    MAPPING_FILE,
    AmbiguousColumn,
    FileScan,
    ScanReport,
    export_report,
)
from dataforge.tools.masking.table import find_column, is_blank, read_table

REPORT_FILE = "pattern1_scan_report.json"
FOLDER_PREFIX = "masked_output_"
_AGE_RE = re.compile(r"^[+-]?\d+(\.\d+)?$")


def _non_negative_int(raw: Any) -> int:
    try:
        return max(0, int(raw))
    except (TypeError, ValueError):
        return 0


def _apply_rule_chain(value: str, steps: Sequence[RuleStep]) -> str:
    result = value
    for step in steps:
        op = step.op.strip().lower()
        if op == "remove_prefix":
            result = result[_non_negative_int(step.value):]
        elif op == "remove_suffix":
            count = _non_negative_int(step.value)
            if count > 0:
                result = result[:-count] if count < len(result) else ""
        elif op == "prepend":
            result = f"{step.value}{result}"
        elif op == "append":
            result = f"{result}{step.value}"
    return result


def transform_subject_id(subject: str, profile: MaskingProfile, index: int) -> str:
    if profile.usubjid_mode == "rule_chain":
        return _apply_rule_chain(subject, profile.rule_chain_steps)
    width = max(1, profile.sequential_width)
    return f"{profile.sequential_prefix}{profile.sequential_start + index:0{width}d}"


def build_mapping(subjects: Sequence[str], profile: MaskingProfile) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for index, old in enumerate(subjects):
        new = transform_subject_id(old, profile, index)
        if not new.strip():
            raise DataForgeError(f"新 USUBJID 为空（原 ID：{old}）")
        mapping[old] = new
    seen: set[str] = set()
    duplicates: list[str] = []
    for new in mapping.values():
        if new in seen and new not in duplicates:
            duplicates.append(new)
        seen.add(new)
    if duplicates:
        raise DataForgeError(f"新 USUBJID 重复：{', '.join(duplicates[:10])}")
    return mapping


def shift_age(text: str, years: int) -> str:
    if is_blank(text):
        return text
    stripped = text.strip()
    if not _AGE_RE.match(stripped):
        return text
    value = Decimal(stripped)
    shifted = value + years
    if shifted < 0:
        shifted = Decimal(0).quantize(value)
    return format(shifted, "f")


@dataclass
class MaskOptions:
    profile: MaskingProfile
    output_parent: Path | None = None
    date_orders: dict[tuple[str, str], SlashOrder] = field(default_factory=dict)
    now: datetime | None = None  # tests only: fixes the folder time stamp


def missing_orders(
    report: ScanReport, date_orders: Mapping[tuple[str, str], SlashOrder]
) -> list[AmbiguousColumn]:
    return [c for c in report.ambiguous_columns if (c.file_name, c.column) not in date_orders]


def _dm_scan(report: ScanReport) -> FileScan | None:
    return next((f for f in report.files if f.file_name == report.dm_file), None)


def _has_values(dm: FileScan | None, column: str) -> bool:
    """Whether ``column`` (case-insensitive) had a non-blank value in DM at scan time."""
    if dm is None:
        return False
    return find_column(dm.non_empty_fields, column) is not None


def describe_plan(
    report: ScanReport,
    profile: MaskingProfile,
    date_orders: Mapping[tuple[str, str], SlashOrder],
    output_parent: Path | None,
) -> list[str]:
    subjects = report.subjects
    k = min(profile.subject_limit, len(subjects))
    lines = [f"受试者：保留 DM 排序后的前 {k} 个（共 {len(subjects)} 个），其他受试者的行全部删除"]
    if profile.usubjid_mode == "rule_chain":
        first = report.dm_first_usubjid or ""
        lines.append(f"USUBJID：规则链，例如 {first} → {transform_subject_id(first, profile, 0)}")
    else:
        first_id = transform_subject_id("", profile, 0)
        last_id = transform_subject_id("", profile, max(k, 1) - 1)
        lines.append(f"USUBJID：顺序编号 {first_id} … {last_id}")
    lines.append("SUBJID 列将被清空" if profile.include_subjid else "SUBJID 列保持不变")
    lines.append(f"STUDYID：全部改为 {profile.studyid_value}")
    date_columns = sum(len(f.date_fields) for f in report.files)
    lines.append(f"日期：{date_columns} 个日期列偏移 {profile.date_shift_years:+d} 年，时间部分保留")
    dm = _dm_scan(report)
    if profile.doctor_replace_enabled:
        doctors = [name for name in profile.doctor_fields if _has_values(dm, name)]
        if not any(name.strip() for name in profile.doctor_fields):
            lines.append("DM：未指定医生字段，不替换")
        elif doctors:
            lines.append(f"DM：{'、'.join(doctors)} 改为 {profile.doctor_value}")
    if profile.site_replace_enabled:
        if not profile.site_field.strip():
            lines.append("DM：未指定施设字段，不替换")
        elif _has_values(dm, profile.site_field):
            lines.append(f"DM：{profile.site_field} 改为 {profile.site_value}")
    if _has_values(dm, profile.age_field):
        lines.append(f"DM：{profile.age_field} 偏移 {profile.age_shift_years:+d} 岁")
    missing = len(missing_orders(report, date_orders))
    if missing:
        lines.append(f"还有 {missing} 个日期列需要选择 日/月 顺序")
    where = str(output_parent) if output_parent is not None else "DM.csv 所在文件夹"
    lines.append(f"输出：{where} 下新建 {FOLDER_PREFIX}<时间> 文件夹")
    return lines


def _folder_name(parent: Path, now: datetime) -> str:
    base = f"{FOLDER_PREFIX}{now:%Y%m%d_%H%M%S}"
    name, suffix = base, 1
    while (parent / name).exists():
        name = f"{base}_{suffix}"
        suffix += 1
    return name


def _find_columns(header: Sequence[str], name: str) -> list[int]:
    """Indexes of every column equal to ``name`` ignoring case (spaces are not stripped)."""
    target = name.lower()
    return [index for index, column in enumerate(header) if column.lower() == target]


def _set_cells(
    rows: list[list[str]], indexes: Sequence[int], value: str, only_non_blank: bool
) -> None:
    for row in rows:
        for index in indexes:
            if not only_non_blank or not is_blank(row[index]):
                row[index] = value


class StaleScanError(DataForgeError):
    """A scanned file changed or vanished after the scan; the report must be redone."""


def _write_output(rows: Sequence[Sequence[str]], target: Path) -> None:
    try:
        write_csv_rows(rows, target)
    except OSError as exc:
        raise DataForgeError(f"无法写入输出文件 {target.name}（{exc}）") from exc


class _Run:
    def __init__(self, report: ScanReport, options: MaskOptions, result: Result) -> None:
        self.report = report
        self.options = options
        self.profile = options.profile
        self.result = result
        self.dm = _dm_scan(report)

    def mask_file(self, fs: FileScan, mapping: Mapping[str, str], folder: Path) -> Path:
        p = self.profile
        try:
            table = read_table(fs.path, fs.encoding)
        except (DataForgeError, OSError) as exc:  # EncodingError is a DataForgeError
            raise StaleScanError(f"{fs.file_name}：读取失败，请重新扫描（{exc}）") from exc
        header = table.header
        uids = _find_columns(header, "USUBJID")
        if not uids:
            raise StaleScanError(f"{fs.file_name}：读取失败，请重新扫描（缺少 USUBJID 列）")
        if len(uids) > 1:
            raise DataForgeError(f"{fs.file_name}：USUBJID 列重复")
        uid = uids[0]
        rows = [r for r in table.rows if r[uid].strip() in mapping]
        for row in rows:
            row[uid] = mapping[row[uid].strip()]

        if p.include_subjid:
            _set_cells(rows, _find_columns(header, "SUBJID"), "", only_non_blank=False)
        _set_cells(rows, _find_columns(header, "STUDYID"), p.studyid_value, only_non_blank=False)

        date_fields = set(fs.date_fields)
        for col, column in enumerate(header):
            if column not in date_fields:
                continue
            order = self.options.date_orders.get((fs.file_name, column))
            unparsed = 0
            for row in rows:
                row[col], outcome = mask_date(row[col], p.date_shift_years, order)
                if outcome is DateOutcome.SHIFTED:
                    self.result.count("dates_shifted")
                elif outcome is DateOutcome.FILLED:
                    self.result.count("dates_shifted")
                    self.result.count("dates_filled")
                elif outcome is DateOutcome.UNPARSED:
                    unparsed += 1
            if unparsed:
                self.result.count("dates_unparsed", unparsed)
                self.result.warn(
                    fs.file_name, f"{column} 列有 {unparsed} 个值无法识别为日期，已保持原样"
                )

        if fs.file_name == self.report.dm_file:
            self._dm_overrides(header, rows)

        target = folder / fs.file_name
        _write_output([header, *rows], target)
        self.result.count("rows", len(rows))
        return target

    def _dm_columns(self, header: list[str], name: str) -> list[int]:
        """Every column named ``name``, provided one of them had values in DM at scan time."""
        return _find_columns(header, name) if _has_values(self.dm, name) else []

    def _dm_overrides(self, header: list[str], rows: list[list[str]]) -> None:
        p = self.profile
        if p.doctor_replace_enabled:
            for name in p.doctor_fields:
                cols = self._dm_columns(header, name)
                _set_cells(rows, cols, p.doctor_value, only_non_blank=True)
        if p.site_replace_enabled:
            cols = self._dm_columns(header, p.site_field)
            _set_cells(rows, cols, p.site_value, only_non_blank=True)
        for col in self._dm_columns(header, p.age_field):
            for row in rows:
                row[col] = shift_age(row[col], p.age_shift_years)


def _folder_error(exc: OSError) -> DataForgeError:
    return DataForgeError(f"无法创建输出文件夹（{exc}）")


def run(
    report: ScanReport, options: MaskOptions, progress: ProgressFn, cancel: CancelToken
) -> Result:
    profile = options.profile
    if not report.processable:
        raise DataForgeError("扫描未通过，无法执行")
    missing = missing_orders(report, options.date_orders)
    if missing:
        raise DataForgeError(f"请先为 {len(missing)} 个日期列选择 日/月 顺序")
    if profile.subject_limit < 1:
        raise DataForgeError("输出受试者数必须大于 0")

    subjects = report.subjects[: profile.subject_limit]
    mapping = build_mapping(subjects, profile)

    dm = _dm_scan(report)
    if options.output_parent is not None:
        parent = options.output_parent
    elif dm is not None:
        parent = dm.path.parent
    else:  # processable reports always have a DM entry
        raise DataForgeError("扫描未通过，无法执行")
    try:
        parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise _folder_error(exc) from exc
    name = _folder_name(parent, options.now or datetime.now())
    final = parent / name

    result = Result()
    for key in ("files", "subjects", "rows", "dates_shifted", "dates_filled", "dates_unparsed"):
        result.stats[key] = 0
    work = _Run(report, options, result)
    try:
        tmp = Path(tempfile.mkdtemp(prefix=f".{name}.", suffix=".tmp", dir=parent))
    except OSError as exc:
        raise _folder_error(exc) from exc
    try:
        written: list[str] = []
        total = len(report.files)
        for index, fs in enumerate(report.files, 1):
            progress(index, total, fs.file_name)
            cancel.raise_if_cancelled()
            written.append(work.mask_file(fs, mapping, tmp).name)
            result.count("files")
        cancel.raise_if_cancelled()
        _write_output(
            [["OLD_USUBJID", "NEW_USUBJID"], *([old, mapping[old]] for old in subjects)],
            tmp / MAPPING_FILE,
        )
        try:
            export_report(report, tmp / REPORT_FILE, options.date_orders)
        except OSError as exc:
            raise DataForgeError(f"无法写入输出文件 {REPORT_FILE}（{exc}）") from exc
        try:
            os.rename(tmp, final)
        except OSError as exc:
            raise _folder_error(exc) from exc
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise

    result.outputs = [final / n for n in (*written, MAPPING_FILE, REPORT_FILE)]
    result.count("subjects", len(subjects))
    result.data = final
    return result
