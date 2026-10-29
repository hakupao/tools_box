"""Regenerate the sheet_split golden sample from hand-written literals.

Run from the repo root:
    .venv/Scripts/python.exe tests/golden/sheet_split/make_fixtures.py

Expected CSV bytes are written by hand here; the tool under test is never called.
Excel itself forbids / \\ ? * [ ] : in sheet names, so the illegal-character case
uses the characters Excel allows but file names do not: < > " |
"""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from openpyxl import Workbook

CASE = Path(__file__).resolve().parent / "basic"
BOM = b"\xef\xbb\xbf"


def _build_input(path: Path) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "数据"
    ws["A1"] = "日期"
    ws["B1"] = "时间"
    ws["C1"] = "数量"
    ws["A2"] = date(2020, 3, 4)
    ws["A2"].number_format = "yyyy/mm/dd"
    ws["B2"] = datetime(2020, 3, 4, 10, 5)
    ws["B2"].number_format = "yyyy-mm-dd hh:mm"
    ws["C2"] = 12
    ws["A3"] = date(2021, 12, 1)
    ws["A3"].number_format = "yy.m.d"
    ws["B3"] = datetime(2021, 12, 1, 0, 0)
    ws["B3"].number_format = "yyyy-mm-dd"
    ws["C3"] = 1.5
    ws["A4"] = "含,逗号"
    ws["B4"] = 'say "hi"'
    # Empty-valued cells in the trailing row/column: must be trimmed from the output.
    ws["D5"] = None
    ws["A6"] = None

    ws2 = wb.create_sheet("a<b")
    ws2["A1"] = "x"
    ws2["B1"] = "y"

    ws3 = wb.create_sheet("a|b")
    ws3["A1"] = "dup"

    wb.create_sheet("CON")  # reserved name, empty sheet
    wb.save(path)


EXPECTED = {
    "book_数据.csv": BOM
    + "日期,时间,数量\r\n".encode("utf-8")
    + b"2020/03/04,2020-03-04 10:05,12\r\n"
    + b"21.12.1,2021-12-01,1.5\r\n"
    + '"含,逗号","say ""hi""",\r\n'.encode("utf-8"),
    "book_a_b.csv": BOM + b"x,y\r\n",
    "book_a_b_1.csv": BOM + b"dup\r\n",
    "book_CON_.csv": BOM,
}


def main() -> None:
    (CASE / "input").mkdir(parents=True, exist_ok=True)
    (CASE / "expected").mkdir(parents=True, exist_ok=True)
    (CASE / "params.json").write_bytes(b"{}\n")
    _build_input(CASE / "input" / "book.xlsx")
    for name, data in EXPECTED.items():
        (CASE / "expected" / name).write_bytes(data)


if __name__ == "__main__":
    main()
