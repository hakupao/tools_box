from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from typing import Any, Callable, Optional

import pandas as pd


ProgressCallback = Optional[Callable[[int, int, str], None]]


@dataclass
class RuleStep:
    op: str
    value: Any

    @staticmethod
    def from_dict(raw: dict[str, Any]) -> "RuleStep":
        return RuleStep(op=str(raw.get("op", "")).strip(), value=raw.get("value", ""))


@dataclass
class Pattern1Profile:
    studyid_value: str = "[UAT]CIRCULATE"
    subject_limit: int = 100
    subject_sort: str = "string_asc"
    usubjid_mode: str = "sequential"  # sequential | rule_chain

    rule_chain_steps: list[RuleStep] = field(
        default_factory=lambda: [
            RuleStep("remove_prefix", 4),
            RuleStep("remove_suffix", 0),
            RuleStep("prepend", "SKLT"),
            RuleStep("append", ""),
        ]
    )

    sequential_prefix: str = "TEST"
    sequential_width: int = 4
    sequential_start: int = 1

    date_shift_years: int = -2
    age_shift_years: int = -2

    date_detect_sample_size: int = 200
    date_detect_min_non_empty: int = 20
    date_detect_success_ratio: float = 0.8

    date_output_format: str = "yyyy-mm-dd"
    partial_date_policy: str = "auto_fill_first_day"

    doctor_fields: list[str] = field(default_factory=lambda: ["INVNAM"])
    doctor_value: str = "テスト医師"
    site_field: str = "SITEID"
    site_value: str = "テスト施設"
    age_field: str = "AGE"

    include_subjid: bool = True

    @staticmethod
    def from_dict(raw: dict[str, Any]) -> "Pattern1Profile":
        profile = Pattern1Profile()

        for key in (
            "studyid_value",
            "subject_sort",
            "usubjid_mode",
            "sequential_prefix",
            "date_output_format",
            "partial_date_policy",
            "doctor_value",
            "site_field",
            "site_value",
            "age_field",
        ):
            if key in raw and raw[key] is not None:
                setattr(profile, key, str(raw[key]))

        for key in (
            "subject_limit",
            "sequential_width",
            "sequential_start",
            "date_shift_years",
            "age_shift_years",
            "date_detect_sample_size",
            "date_detect_min_non_empty",
        ):
            if key in raw and raw[key] is not None:
                try:
                    setattr(profile, key, int(raw[key]))
                except (TypeError, ValueError):
                    pass

        if "date_detect_success_ratio" in raw and raw["date_detect_success_ratio"] is not None:
            try:
                profile.date_detect_success_ratio = float(raw["date_detect_success_ratio"])
            except (TypeError, ValueError):
                pass

        if "doctor_fields" in raw and isinstance(raw["doctor_fields"], list):
            profile.doctor_fields = [str(x).strip() for x in raw["doctor_fields"] if str(x).strip()]

        if "include_subjid" in raw:
            profile.include_subjid = bool(raw["include_subjid"])

        if "rule_chain_steps" in raw and isinstance(raw["rule_chain_steps"], list):
            parsed_steps = []
            for step in raw["rule_chain_steps"]:
                if isinstance(step, dict):
                    parsed_steps.append(RuleStep.from_dict(step))
            if parsed_steps:
                profile.rule_chain_steps = parsed_steps

        return profile

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["rule_chain_steps"] = [asdict(step) for step in self.rule_chain_steps]
        return data


@dataclass
class FileScanSummary:
    file_path: str
    file_name: str
    row_count: int
    non_empty_fields: list[str]
    empty_fields: list[str]
    unique_usubjid_count: int
    date_fields: list[str]


@dataclass
class Pattern1ScanReport:
    dm_file_path: str | None
    dm_first_usubjid: str | None
    files_summary: list[FileScanSummary]
    date_fields_by_file: dict[str, list[str]]
    selected_subjects: list[str]
    global_summary: dict[str, Any]
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dm_file_path": self.dm_file_path,
            "dm_first_usubjid": self.dm_first_usubjid,
            "files_summary": [asdict(item) for item in self.files_summary],
            "date_fields_by_file": self.date_fields_by_file,
            "selected_subjects": self.selected_subjects,
            "global_summary": self.global_summary,
            "errors": self.errors,
            "warnings": self.warnings,
        }


@dataclass
class Pattern1RunResult:
    output_dir: str
    output_files: list[str]
    mapping_file: str
    scan_report_file: str
    date_normalized_count: int
    date_auto_filled_count: int
    date_unparsed_count: int
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class DataMaskingService:
    """SDTM Pattern1 数据脱敏处理器。"""

    def __init__(self, config_path: str | None = None):
        self.config_path = config_path or self._default_config_path()
        self.profile = self.load_profile()

    def _default_config_path(self) -> str:
        if getattr(sys, "frozen", False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_dir, "data_masking_pattern1_config.json")

    def load_profile(self) -> Pattern1Profile:
        if not os.path.exists(self.config_path):
            return Pattern1Profile()

        try:
            with open(self.config_path, "r", encoding="utf-8") as fp:
                raw = json.load(fp)
            if isinstance(raw, dict):
                return Pattern1Profile.from_dict(raw)
        except Exception:
            pass

        return Pattern1Profile()

    def save_profile(self, profile: Pattern1Profile | None = None) -> bool:
        if profile is not None:
            self.profile = profile

        try:
            parent_dir = os.path.dirname(self.config_path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as fp:
                json.dump(self.profile.to_dict(), fp, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False

    def reset_profile(self) -> Pattern1Profile:
        self.profile = Pattern1Profile()
        self.save_profile(self.profile)
        return self.profile

    def scan_pattern1(self, file_paths: list[str], profile: Pattern1Profile | None = None) -> Pattern1ScanReport:
        active_profile = profile or self.profile

        normalized_paths = self._normalize_file_paths(file_paths)
        errors: list[str] = []
        warnings: list[str] = []

        if not normalized_paths:
            errors.append("未选择任何可处理的 CSV 文件")
            return Pattern1ScanReport(
                dm_file_path=None,
                dm_first_usubjid=None,
                files_summary=[],
                date_fields_by_file={},
                selected_subjects=[],
                global_summary={"total_files": 0, "processable": False},
                errors=errors,
                warnings=warnings,
            )

        dfs: dict[str, pd.DataFrame] = {}
        files_summary: list[FileScanSummary] = []
        date_fields_by_file: dict[str, list[str]] = {}

        dm_candidates: list[str] = []

        for path in normalized_paths:
            try:
                df = pd.read_csv(path, dtype=str, na_filter=False)
            except Exception as exc:  # pylint: disable=broad-except
                errors.append(f"读取失败: {path} ({exc})")
                continue

            dfs[path] = df
            if os.path.basename(path).upper() == "DM.CSV":
                dm_candidates.append(path)

            usubjid_col = self._find_column(df, "USUBJID")
            if usubjid_col is None:
                errors.append(f"文件缺少 USUBJID 字段: {os.path.basename(path)}")
                unique_count = 0
            else:
                unique_count = len(set(self._collect_non_empty_values(df[usubjid_col])))

            non_empty_fields = [col for col in df.columns if self._column_has_non_empty(df[col])]
            empty_fields = [col for col in df.columns if col not in non_empty_fields]
            detected_date_fields = self._detect_date_fields(df, non_empty_fields, active_profile)
            date_fields_by_file[path] = detected_date_fields

            files_summary.append(
                FileScanSummary(
                    file_path=path,
                    file_name=os.path.basename(path),
                    row_count=len(df),
                    non_empty_fields=non_empty_fields,
                    empty_fields=empty_fields,
                    unique_usubjid_count=unique_count,
                    date_fields=detected_date_fields,
                )
            )

        dm_file_path: str | None = None
        dm_first_usubjid: str | None = None
        selected_subjects: list[str] = []

        if len(dm_candidates) != 1:
            errors.append("DM.csv 必须且只能存在 1 个")
        else:
            dm_file_path = dm_candidates[0]
            dm_df = dfs.get(dm_file_path)
            if dm_df is None:
                errors.append("DM.csv 读取失败")
            else:
                dm_usubjid_col = self._find_column(dm_df, "USUBJID")
                if dm_usubjid_col is None:
                    errors.append("DM.csv 缺少 USUBJID 字段")
                else:
                    dm_subjects_by_row = self._collect_non_empty_values(dm_df[dm_usubjid_col])
                    dm_subjects = sorted(set(dm_subjects_by_row))
                    if not dm_subjects:
                        errors.append("DM.csv 中不存在有效的 USUBJID 数据")
                    else:
                        dm_first_usubjid = dm_subjects_by_row[0]
                        # 扫描阶段始终展示原始全量DM病例，不受输出病例数限制。
                        selected_subjects = dm_subjects

        processable = len(errors) == 0 and bool(selected_subjects)

        global_summary = {
            "total_files": len(normalized_paths),
            "processable": processable,
            "dm_file_count": len(dm_candidates),
            "dm_subject_count": len(selected_subjects),
            "profile_subject_limit": active_profile.subject_limit,
        }

        return Pattern1ScanReport(
            dm_file_path=dm_file_path,
            dm_first_usubjid=dm_first_usubjid,
            files_summary=files_summary,
            date_fields_by_file=date_fields_by_file,
            selected_subjects=selected_subjects,
            global_summary=global_summary,
            errors=errors,
            warnings=warnings,
        )

    def run_pattern1(
        self,
        file_paths: list[str],
        output_dir: str | None = None,
        profile: Pattern1Profile | None = None,
        scan_report: Pattern1ScanReport | None = None,
        progress_callback: ProgressCallback = None,
    ) -> Pattern1RunResult:
        active_profile = profile or self.profile
        report = scan_report or self.scan_pattern1(file_paths, active_profile)

        if report.errors:
            raise ValueError("扫描未通过:\n" + "\n".join(report.errors))

        if report.dm_file_path is None:
            raise ValueError("缺少 DM.csv，无法执行 Pattern1")

        dm_subjects = report.selected_subjects
        if not dm_subjects:
            raise ValueError("扫描结果中不存在可用的 DM USUBJID")

        limit = max(0, int(active_profile.subject_limit))
        if limit <= 0:
            raise ValueError("输出病例数必须大于 0")

        run_subjects = dm_subjects[:limit]
        if not run_subjects:
            raise ValueError("根据输出病例数配置，未选择到可处理的 USUBJID")

        subject_mapping = self._build_subject_mapping(run_subjects, active_profile)
        subject_set = set(run_subjects)

        final_output_dir = output_dir or self._build_default_output_dir(report.dm_file_path)
        os.makedirs(final_output_dir, exist_ok=True)

        total = len(report.files_summary)
        output_files: list[str] = []

        date_normalized_count = 0
        date_auto_filled_count = 0
        date_unparsed_count = 0
        dm_non_empty_fields: set[str] | None = None
        for summary in report.files_summary:
            if summary.file_name.upper() == "DM.CSV":
                dm_non_empty_fields = {name.upper() for name in summary.non_empty_fields}
                break

        for index, summary in enumerate(report.files_summary, 1):
            if progress_callback:
                progress_callback(index, total, summary.file_name)

            df = pd.read_csv(summary.file_path, dtype=str, na_filter=False)
            usubjid_col = self._find_column(df, "USUBJID")
            if usubjid_col is None:
                raise ValueError(f"执行阶段发现缺少 USUBJID: {summary.file_name}")

            df = df[df[usubjid_col].isin(subject_set)]

            df[usubjid_col] = df[usubjid_col].apply(lambda x: subject_mapping.get(str(x), x) if str(x).strip() else x)

            if active_profile.include_subjid:
                subjid_col = self._find_column(df, "SUBJID")
                if subjid_col is not None:
                    df[subjid_col] = df[subjid_col].apply(
                        lambda x: subject_mapping.get(str(x), x) if str(x).strip() else x
                    )

            studyid_col = self._find_column(df, "STUDYID")
            if studyid_col is not None:
                df[studyid_col] = active_profile.studyid_value

            for col in report.date_fields_by_file.get(summary.file_path, []):
                if col not in df.columns:
                    continue

                normalized_values: list[str] = []
                for value in df[col].tolist():
                    normalized, normalized_ok, auto_filled = self._normalize_date_value(str(value), active_profile.date_shift_years)
                    normalized_values.append(normalized)
                    if normalized_ok:
                        date_normalized_count += 1
                    if auto_filled:
                        date_auto_filled_count += 1
                    if not normalized_ok and not self._is_blank(value):
                        date_unparsed_count += 1

                df[col] = normalized_values

            is_dm = summary.file_name.upper() == "DM.CSV"
            if is_dm:
                self._apply_dm_overrides(df, active_profile, dm_non_empty_fields)

            output_path = os.path.join(final_output_dir, summary.file_name)
            df.to_csv(output_path, index=False, encoding="utf-8-sig")
            output_files.append(output_path)

        mapping_file = os.path.join(final_output_dir, "usubjid_mapping.csv")
        mapping_df = pd.DataFrame(
            {
                "OLD_USUBJID": run_subjects,
                "NEW_USUBJID": [subject_mapping[item] for item in run_subjects],
            }
        )
        mapping_df.to_csv(mapping_file, index=False, encoding="utf-8-sig")

        scan_report_file = os.path.join(final_output_dir, "pattern1_scan_report.json")
        self.export_scan_report(report, scan_report_file)

        return Pattern1RunResult(
            output_dir=final_output_dir,
            output_files=output_files,
            mapping_file=mapping_file,
            scan_report_file=scan_report_file,
            date_normalized_count=date_normalized_count,
            date_auto_filled_count=date_auto_filled_count,
            date_unparsed_count=date_unparsed_count,
            warnings=[],
            errors=[],
        )

    def export_scan_report(self, report: Pattern1ScanReport, target_path: str) -> str:
        ext = os.path.splitext(target_path)[1].lower()
        parent_dir = os.path.dirname(target_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)

        if ext == ".csv":
            rows = []
            for item in report.files_summary:
                rows.append(
                    {
                        "file_name": item.file_name,
                        "row_count": item.row_count,
                        "unique_usubjid_count": item.unique_usubjid_count,
                        "non_empty_fields": "|".join(item.non_empty_fields),
                        "empty_fields": "|".join(item.empty_fields),
                        "date_fields": "|".join(item.date_fields),
                    }
                )
            pd.DataFrame(rows).to_csv(target_path, index=False, encoding="utf-8-sig")
            return target_path

        with open(target_path, "w", encoding="utf-8") as fp:
            json.dump(report.to_dict(), fp, ensure_ascii=False, indent=2)
        return target_path

    def format_scan_report(self, report: Pattern1ScanReport) -> str:
        lines = []
        lines.append("Pattern1 扫描结果")
        lines.append(f"- 可处理: {'是' if report.global_summary.get('processable') else '否'}")
        lines.append(f"- 文件总数: {report.global_summary.get('total_files', 0)}")
        lines.append(f"- DM.csv: {os.path.basename(report.dm_file_path) if report.dm_file_path else '未找到'}")
        lines.append(f"- DM病例数(全量): {len(report.selected_subjects)}")
        lines.append(f"- 配置输出病例数: {report.global_summary.get('profile_subject_limit', 0)}")
        lines.append(
            f"- DM首条USUBJID: {report.dm_first_usubjid if report.dm_first_usubjid else '未识别'}"
        )

        if report.errors:
            lines.append("- 错误:")
            for item in report.errors:
                lines.append(f"  - {item}")

        lines.append("")
        lines.append("文件明细:")
        for summary in report.files_summary:
            lines.append(f"- {summary.file_name}")
            lines.append(f"  - 行数: {summary.row_count}")
            lines.append(f"  - USUBJID去重: {summary.unique_usubjid_count}")
            lines.append(f"  - 有值字段: {','.join(summary.non_empty_fields) if summary.non_empty_fields else '无'}")
            lines.append(f"  - 空字段: {','.join(summary.empty_fields) if summary.empty_fields else '无'}")
            lines.append(f"  - 日期字段: {','.join(summary.date_fields) if summary.date_fields else '无'}")

        return "\n".join(lines)

    def _normalize_file_paths(self, file_paths: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for item in file_paths:
            if not item:
                continue
            if not os.path.isfile(item):
                continue
            if not item.lower().endswith(".csv"):
                continue
            if item in seen:
                continue
            seen.add(item)
            normalized.append(item)
        return normalized

    def _find_column(self, df: pd.DataFrame, target: str) -> str | None:
        for column in df.columns:
            if str(column).upper() == target.upper():
                return column
        return None

    def _column_has_non_empty(self, series: pd.Series) -> bool:
        return any(not self._is_blank(item) for item in series.tolist())

    def _collect_non_empty_values(self, series: pd.Series) -> list[str]:
        return [str(item).strip() for item in series.tolist() if not self._is_blank(item)]

    def _is_blank(self, value: Any) -> bool:
        if value is None:
            return True
        text = str(value).strip()
        return text == "" or text.lower() == "nan"

    def _detect_date_fields(
        self,
        df: pd.DataFrame,
        non_empty_fields: list[str],
        profile: Pattern1Profile,
    ) -> list[str]:
        date_fields: list[str] = []

        sample_size = max(1, int(profile.date_detect_sample_size))
        min_non_empty = max(1, int(profile.date_detect_min_non_empty))
        threshold = max(0.0, min(1.0, float(profile.date_detect_success_ratio)))

        for column in non_empty_fields:
            values = [str(item).strip() for item in df[column].tolist() if not self._is_blank(item)]
            if not values:
                continue

            sampled_values = values[:sample_size]
            non_empty_count = len(sampled_values)
            if non_empty_count == 0:
                continue

            date_like_count = 0
            for item in sampled_values:
                parsed, _auto_filled = self._parse_date_value(item)
                if parsed is not None:
                    date_like_count += 1

            # Small samples are still evaluated, but require full match to avoid false positives.
            effective_threshold = threshold if non_empty_count >= min_non_empty else 1.0
            if (date_like_count / non_empty_count) >= effective_threshold:
                date_fields.append(column)

        return date_fields

    def _parse_date_value(self, value: str) -> tuple[date | None, bool]:
        text = value.strip()
        if not text:
            return None, False

        if text.endswith("Z"):
            text = text[:-1]

        iso_datetime = re.match(r"^(\d{4}-\d{1,2}-\d{1,2})[T ]\d{1,2}:\d{1,2}(:\d{1,2})?", text)
        if iso_datetime:
            text = iso_datetime.group(1)

        m = re.match(r"^(\d{4})[-/](\d{1,2})[-/](\d{1,2})$", text)
        if m:
            return self._safe_date(int(m.group(1)), int(m.group(2)), int(m.group(3))), False

        m = re.match(r"^(\d{4})[-/](\d{1,2})$", text)
        if m:
            return self._safe_date(int(m.group(1)), int(m.group(2)), 1), True

        m = re.match(r"^(\d{4})$", text)
        if m:
            return self._safe_date(int(m.group(1)), 1, 1), True

        m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", text)
        if m:
            first = int(m.group(1))
            second = int(m.group(2))
            year = int(m.group(3))

            parsed_ddmm = self._safe_date(year, second, first)
            if parsed_ddmm is not None:
                return parsed_ddmm, False

            parsed_mmdd = self._safe_date(year, first, second)
            if parsed_mmdd is not None:
                return parsed_mmdd, False

        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S"):
            try:
                parsed_dt = datetime.strptime(text, fmt)
                return parsed_dt.date(), False
            except ValueError:
                continue

        return None, False

    def _safe_date(self, year: int, month: int, day: int) -> date | None:
        try:
            return date(year, month, day)
        except ValueError:
            return None

    def _shift_year(self, target: date, offset: int) -> date:
        if offset == 0:
            return target

        new_year = target.year + offset
        new_day = target.day
        while new_day >= 1:
            try:
                return date(new_year, target.month, new_day)
            except ValueError:
                new_day -= 1

        return target

    def _normalize_date_value(self, value: str, year_offset: int) -> tuple[str, bool, bool]:
        parsed, auto_filled = self._parse_date_value(value)
        if parsed is None:
            return value, False, False

        shifted = self._shift_year(parsed, year_offset)
        return shifted.strftime("%Y-%m-%d"), True, auto_filled

    def transform_subject_id(self, subject: str, profile: Pattern1Profile, index: int = 0) -> str:
        original = str(subject)
        if profile.usubjid_mode == "rule_chain":
            return self._apply_rule_chain(original, profile.rule_chain_steps)

        width = max(1, int(profile.sequential_width))
        start = int(profile.sequential_start)
        seq_index = max(0, int(index))
        return f"{profile.sequential_prefix}{start + seq_index:0{width}d}"

    def _build_subject_mapping(self, subjects: list[str], profile: Pattern1Profile) -> dict[str, str]:
        mapping = {
            subject: self.transform_subject_id(subject, profile, index)
            for index, subject in enumerate(subjects)
        }

        duplicates = self._find_duplicates(list(mapping.values()))
        if duplicates:
            dup_text = ", ".join(duplicates[:10])
            raise ValueError(f"USUBJID 映射冲突，以下新ID重复: {dup_text}")

        return mapping

    def _to_non_negative_int(self, raw_value: Any) -> int:
        try:
            return max(0, int(raw_value))
        except (TypeError, ValueError):
            return 0

    def _apply_rule_chain(self, value: str, steps: list[RuleStep]) -> str:
        result = str(value)
        for step in steps:
            op = step.op.strip().lower()
            raw_value = step.value

            if op == "remove_prefix":
                count = self._to_non_negative_int(raw_value)
                result = result[count:]
            elif op == "remove_suffix":
                count = self._to_non_negative_int(raw_value)
                if count > 0:
                    result = result[:-count] if count < len(result) else ""
            elif op == "prepend":
                result = f"{str(raw_value)}{result}"
            elif op == "append":
                result = f"{result}{str(raw_value)}"

        return result

    def _find_duplicates(self, values: list[str]) -> list[str]:
        seen: set[str] = set()
        duplicates: list[str] = []
        for item in values:
            if item in seen and item not in duplicates:
                duplicates.append(item)
            seen.add(item)
        return duplicates

    def _apply_dm_overrides(
        self,
        df: pd.DataFrame,
        profile: Pattern1Profile,
        dm_non_empty_fields: set[str] | None = None,
    ) -> None:
        for doctor_field in profile.doctor_fields:
            column = self._resolve_dm_column(df, doctor_field, dm_non_empty_fields)
            if column is None:
                continue
            df[column] = df[column].apply(
                lambda x: profile.doctor_value if not self._is_blank(x) else x
            )

        site_column = self._resolve_dm_column(df, profile.site_field, dm_non_empty_fields)
        if site_column is not None:
            df[site_column] = df[site_column].apply(
                lambda x: profile.site_value if not self._is_blank(x) else x
            )

        age_column = self._resolve_dm_column(df, profile.age_field, dm_non_empty_fields)
        if age_column is not None:
            df[age_column] = df[age_column].apply(
                lambda x: self._shift_age(x, profile.age_shift_years)
            )

    def _resolve_dm_column(
        self,
        df: pd.DataFrame,
        field_name: str,
        dm_non_empty_fields: set[str] | None,
    ) -> str | None:
        if dm_non_empty_fields is not None and field_name.upper() not in dm_non_empty_fields:
            return None
        return self._find_column(df, field_name)

    def _shift_age(self, value: Any, offset: int) -> Any:
        if self._is_blank(value):
            return value
        text = str(value).strip()

        try:
            num = float(text)
            shifted = max(0.0, num + offset)
            if float(int(num)) == num and float(int(shifted)) == shifted:
                return str(int(shifted))
            return str(shifted)
        except (TypeError, ValueError):
            return value

    def _build_default_output_dir(self, dm_file_path: str) -> str:
        base_dir = os.path.dirname(dm_file_path) if dm_file_path else os.getcwd()
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        candidate = os.path.join(base_dir, f"masked_output_{stamp}")

        suffix = 1
        final_path = candidate
        while os.path.exists(final_path):
            final_path = f"{candidate}_{suffix}"
            suffix += 1

        return final_path
