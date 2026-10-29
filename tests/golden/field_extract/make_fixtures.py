"""Regenerate the field_extract golden samples from hand-written literals.

Run from the repo root:
    .venv/Scripts/python.exe tests/golden/field_extract/make_fixtures.py

Inputs and expected outputs are written here by hand; the tool under test is never called.
"""
from __future__ import annotations

import json
from pathlib import Path

from openpyxl import Workbook

ROOT = Path(__file__).resolve().parent
BOM = b"\xef\xbb\xbf"


def basic() -> None:
    case = ROOT / "basic"
    (case / "input" / "sub").mkdir(parents=True, exist_ok=True)
    (case / "expected").mkdir(parents=True, exist_ok=True)
    params = {"header_row": 1, "include_subfolders": True}
    (case / "params.json").write_bytes((json.dumps(params) + "\n").encode("utf-8"))
    (case / "input" / "a.csv").write_bytes(b"id,name,id,\r\n1,2,3,4\r\n")
    wb = Workbook()
    ws = wb.active
    ws.title = "S1"
    ws["A1"], ws["B1"] = "x", "y"
    wb.create_sheet("S2")["A1"] = "z"
    wb.save(case / "input" / "b.xlsx")
    (case / "input" / "sub" / "c.csv").write_bytes("姓名,年龄\r\n".encode("gbk"))
    (case / "input" / "sub" / "empty.csv").write_bytes(b"")
    (case / "expected" / "file_fields_summary.csv").write_bytes(
        BOM
        + "文件名,字段名\r\n".encode("utf-8")
        + b'a.csv,id\r\na.csv,name\r\na.csv,id\r\na.csv,\r\n'
        + b"b.xlsx,S1: x\r\nb.xlsx,S1: y\r\nb.xlsx,S2: z\r\n"
        + "sub/c.csv,姓名\r\nsub/c.csv,年龄\r\n".encode("utf-8")
        + b"sub/empty.csv,\r\n"
    )


def main() -> None:
    basic()


if __name__ == "__main__":
    main()
