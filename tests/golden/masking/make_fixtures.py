"""Regenerate the masking golden samples from hand-written literals.

Run from the repo root:
    .venv/Scripts/python.exe tests/golden/masking/make_fixtures.py

Inputs and expected outputs are written here by hand; the tool under test is never called.
All data is fictional. The expected scan report is a hand-written dict serialised with the
report format (json.dumps(..., ensure_ascii=False, indent=2) + "\\n", UTF-8 without BOM, LF).
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BOM = b"\xef\xbb\xbf"


def _write_case(name: str, params: dict, inputs: dict[str, bytes]) -> Path:
    case = ROOT / name
    if case.exists():
        shutil.rmtree(case)
    (case / "input").mkdir(parents=True)
    (case / "expected").mkdir(parents=True)
    text = json.dumps(params, ensure_ascii=False, indent=2) + "\n"
    (case / "params.json").write_bytes(text.encode("utf-8"))
    for fname, data in inputs.items():
        (case / "input" / fname).write_bytes(data)
    return case


def _expect(case: Path, files: dict[str, bytes], report: dict) -> None:
    for fname, data in files.items():
        (case / "expected" / fname).write_bytes(data)
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    (case / "expected" / "pattern1_scan_report.json").write_bytes(text.encode("utf-8"))


def sequential_basic() -> None:
    case = _write_case(
        "sequential_basic",
        {"profile": {"subject_limit": 2, "date_detect_min_non_empty": 1}},
        {
            # DM: rows not in sorted order; ICINVNAM is empty in every row
            "DM.csv": BOM
            + (
                "USUBJID,SUBJID,STUDYID,INVNAM,ICINVNAM,SITEID,AGE,BRTHDTC,RFSTDTC\r\n"
                "S3,003,STUDY-X,Dr Kato,,Site-C,61,1963,2024-03-01\r\n"
                "S1,001,STUDY-X,Dr Sato,,Site-A,45,1979-05,2024-01-10\r\n"
                "S2,002,STUDY-X,Dr Ito,,Site-B,30.5,1994-02-28,2024-02-29T09:15\r\n"
            ).encode("utf-8"),
            # AE: plain UTF-8 with LF; dropped rows (S3, blank USUBJID), a padded " S1 ",
            # a quoted field with comma and newline, and one unparseable date (UNKNOWN)
            "AE.csv": (
                "USUBJID,SUBJID,STUDYID,AESEQ,AETERM,AESTDTC,AEENDTC\n"
                "S1,001,STUDY-X,1,Headache,2024-06-15T13:30:00+09:00,2024-06-16\n"
                "S3,003,STUDY-X,1,Nausea,2024-07-01,2024-07-02\n"
                ",,STUDY-X,1,Orphan row,2024-08-01,2024-08-02\n"
                ' S1 ,001,STUDY-X,2,"Rash, mild\nsecond line",2024,2024-07\n'
                "S2,002,STUDY-X,1,Fatigue,2024-02-29,UNKNOWN\n"
                "S2,002,STUDY-X,2,Cough,2023-12-31 08:00,2024-01-05\n"
            ).encode("utf-8"),
        },
    )
    _expect(
        case,
        {
            "DM.csv": BOM
            + (
                "USUBJID,SUBJID,STUDYID,INVNAM,ICINVNAM,SITEID,AGE,BRTHDTC,RFSTDTC\r\n"
                "TEST0001,,[UAT]CIRCULATE,テスト医師,,テスト施設,43,1977-05-01,2022-01-10\r\n"
                "TEST0002,,[UAT]CIRCULATE,テスト医師,,テスト施設,28.5,1992-02-28,"
                "2022-02-28T09:15\r\n"
            ).encode("utf-8"),
            "AE.csv": BOM
            + (
                "USUBJID,SUBJID,STUDYID,AESEQ,AETERM,AESTDTC,AEENDTC\r\n"
                "TEST0001,,[UAT]CIRCULATE,1,Headache,2022-06-15T13:30:00+09:00,2022-06-16\r\n"
                'TEST0001,,[UAT]CIRCULATE,2,"Rash, mild\nsecond line",2022-01-01,2022-07-01\r\n'
                "TEST0002,,[UAT]CIRCULATE,1,Fatigue,2022-02-28,UNKNOWN\r\n"
                "TEST0002,,[UAT]CIRCULATE,2,Cough,2021-12-31 08:00,2022-01-05\r\n"
            ).encode("utf-8"),
            "usubjid_mapping.csv": BOM
            + b"OLD_USUBJID,NEW_USUBJID\r\nS1,TEST0001\r\nS2,TEST0002\r\n",
        },
        {
            "dm_file": "DM.csv",
            "dm_first_usubjid": "S3",
            "subject_count": 3,
            "subjects": ["S1", "S2", "S3"],
            "date_detect": {"sample_size": 200, "min_non_empty": 1, "ratio": 0.8},
            "files": [
                {
                    "file_name": "AE.csv",
                    "encoding": "utf-8",
                    "row_count": 6,
                    "unique_usubjid_count": 3,
                    "non_empty_fields": [
                        "USUBJID",
                        "SUBJID",
                        "STUDYID",
                        "AESEQ",
                        "AETERM",
                        "AESTDTC",
                        "AEENDTC",
                    ],
                    "empty_fields": [],
                    "date_fields": ["AESTDTC", "AEENDTC"],
                },
                {
                    "file_name": "DM.csv",
                    "encoding": "utf-8-sig",
                    "row_count": 3,
                    "unique_usubjid_count": 3,
                    "non_empty_fields": [
                        "USUBJID",
                        "SUBJID",
                        "STUDYID",
                        "INVNAM",
                        "SITEID",
                        "AGE",
                        "BRTHDTC",
                        "RFSTDTC",
                    ],
                    "empty_fields": ["ICINVNAM"],
                    "date_fields": ["BRTHDTC", "RFSTDTC"],
                },
            ],
            "ambiguous_date_columns": [],
            "errors": [],
            "warnings": [],
        },
    )


def rule_chain_ambiguous() -> None:
    case = _write_case(
        "rule_chain_ambiguous",
        {
            "profile": {
                "usubjid_mode": "rule_chain",
                "rule_chain_steps": [
                    {"op": "remove_prefix", "value": 4},
                    {"op": "prepend", "value": "SKLT"},
                ],
                "include_subjid": False,
                "doctor_replace_enabled": False,
                "date_detect_min_non_empty": 1,
            },
            "date_orders": {"AE.csv:AESTDTC": "dmy"},
        },
        {
            "DM.csv": BOM
            + (
                "USUBJID,SUBJID,STUDYID,INVNAM,SITEID,AGE,RFSTDTC\r\n"
                "CIRC0102,102,OLD,Dr Mori,Site-9,0,2025-01-15\r\n"
                "CIRC0101,101,OLD,Dr Abe,Site-8,1,2025-02-01T10:00:00Z\r\n"
            ).encode("utf-8"),
            # cp932, half-width katakana only; the odd-length "ﾊｷｹ" makes GBK fail,
            # so detection is unambiguous. 03/04/2024 is ambiguous, 25/12 day-first only,
            # 07/07 reads the same either way.
            "AE.csv": (
                "USUBJID,STUDYID,AETERM,AESTDTC\r\n"
                "CIRC0101,OLD,ｽﾞﾂｳ,03/04/2024\r\n"
                "CIRC0102,OLD,ﾊｷｹ,25/12/2024\r\n"
                "CIRC0101,OLD,ｾｷ,07/07/2024\r\n"
            ).encode("cp932"),
        },
    )
    _expect(
        case,
        {
            "DM.csv": BOM
            + (
                "USUBJID,SUBJID,STUDYID,INVNAM,SITEID,AGE,RFSTDTC\r\n"
                "SKLT0102,102,[UAT]CIRCULATE,Dr Mori,テスト施設,0,2023-01-15\r\n"
                "SKLT0101,101,[UAT]CIRCULATE,Dr Abe,テスト施設,0,2023-02-01T10:00:00Z\r\n"
            ).encode("utf-8"),
            "AE.csv": BOM
            + (
                "USUBJID,STUDYID,AETERM,AESTDTC\r\n"
                "SKLT0101,[UAT]CIRCULATE,ｽﾞﾂｳ,2022-04-03\r\n"
                "SKLT0102,[UAT]CIRCULATE,ﾊｷｹ,2022-12-25\r\n"
                "SKLT0101,[UAT]CIRCULATE,ｾｷ,2022-07-07\r\n"
            ).encode("utf-8"),
            "usubjid_mapping.csv": BOM
            + b"OLD_USUBJID,NEW_USUBJID\r\nCIRC0101,SKLT0101\r\nCIRC0102,SKLT0102\r\n",
        },
        {
            "dm_file": "DM.csv",
            "dm_first_usubjid": "CIRC0102",
            "subject_count": 2,
            "subjects": ["CIRC0101", "CIRC0102"],
            "date_detect": {"sample_size": 200, "min_non_empty": 1, "ratio": 0.8},
            "files": [
                {
                    "file_name": "AE.csv",
                    "encoding": "cp932",
                    "row_count": 3,
                    "unique_usubjid_count": 2,
                    "non_empty_fields": ["USUBJID", "STUDYID", "AETERM", "AESTDTC"],
                    "empty_fields": [],
                    "date_fields": ["AESTDTC"],
                },
                {
                    "file_name": "DM.csv",
                    "encoding": "utf-8-sig",
                    "row_count": 2,
                    "unique_usubjid_count": 2,
                    "non_empty_fields": [
                        "USUBJID",
                        "SUBJID",
                        "STUDYID",
                        "INVNAM",
                        "SITEID",
                        "AGE",
                        "RFSTDTC",
                    ],
                    "empty_fields": [],
                    "date_fields": ["RFSTDTC"],
                },
            ],
            "ambiguous_date_columns": [
                {
                    "file_name": "AE.csv",
                    "column": "AESTDTC",
                    "ambiguous": 1,
                    "day_first_only": 1,
                    "month_first_only": 0,
                    "order": "dmy",
                }
            ],
            "errors": [],
            "warnings": [
                "自动识别为 日文 (cp932)",
                "AESTDTC 列有 1 个日期无法判断是 日/月 还是 月/日，请选择顺序",
            ],
        },
    )


def main() -> None:
    sequential_basic()
    rule_chain_ambiguous()


if __name__ == "__main__":
    main()
