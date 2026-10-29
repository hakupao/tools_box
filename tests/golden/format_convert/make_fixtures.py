"""Regenerate the format_convert golden samples from hand-written literals.

Run from the repo root:
    .venv/Scripts/python.exe tests/golden/format_convert/make_fixtures.py

Inputs and expected outputs are written here by hand; the tool under test is never called.
"""
from __future__ import annotations

import json
from pathlib import Path

from openpyxl import Workbook

ROOT = Path(__file__).resolve().parent
BOM = b"\xef\xbb\xbf"


def _write_case(
    name: str, params: dict, inputs: dict[str, bytes], expect_outputs: bool = True
) -> Path:
    case = ROOT / name
    (case / "input").mkdir(parents=True, exist_ok=True)
    (case / "params.json").write_bytes((json.dumps(params) + "\n").encode("utf-8"))
    if expect_outputs:
        (case / "expected").mkdir(parents=True, exist_ok=True)
    for fname, data in inputs.items():
        (case / "input" / fname).write_bytes(data)
    return case


def csv_to_xlsx() -> None:
    case = _write_case(
        "csv_to_xlsx",
        {"mode": "csv_to_xlsx"},
        {"data.csv": b'id,note\r\n007,"x\ny",extra\r\n2\r\n=SUM(A1),+1\r\n'},
    )
    wb = Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    for coord, value in {
        "A1": "id",
        "B1": "note",
        "A2": "007",
        "B2": "x\ny",
        "C2": "extra",
        "A3": "2",
        "A4": "=SUM(A1)",
        "B4": "+1",
    }.items():
        ws[coord] = value
        ws[coord].data_type = "s"
        ws[coord].number_format = "@"
    wb.save(case / "expected" / "data.xlsx")


def xlsx_to_csv_all() -> None:
    case = _write_case("xlsx_to_csv_all", {"mode": "xlsx_to_csv", "all_sheets": True}, {})
    wb = Workbook()
    ws = wb.active
    ws.title = "S1"
    ws["A1"], ws["B1"], ws["A2"], ws["B2"] = "a", "b", 1, "x,y"
    ws2 = wb.create_sheet("S2")
    ws2["A1"] = "only"
    wb.save(case / "input" / "book.xlsx")
    (case / "expected" / "book_S1.csv").write_bytes(BOM + b'a,b\r\n1,"x,y"\r\n')
    (case / "expected" / "book_S2.csv").write_bytes(BOM + b"only\r\n")


def csv_to_bom_gbk() -> None:
    case = _write_case(
        "csv_to_bom_gbk",
        {"mode": "csv_to_bom"},
        {"people.csv": "姓名,年龄\r\n张伟,30\n".encode("gbk")},
    )
    (case / "expected" / "people_bom.csv").write_bytes(
        BOM + "姓名,年龄\r\n张伟,30\n".encode("utf-8")
    )


def csv_unquote() -> None:
    case = _write_case(
        "csv_unquote",
        {"mode": "csv_unquote"},
        {"q.csv": b'"a","  b ","c""d"\r\n"x,y","1"\r\n'},
    )
    (case / "expected" / "q_unquoted.csv").write_bytes(BOM + b'a,  b ,c"d\r\n"x,y",1\r\n')


def xlsx_to_csv_first() -> None:
    case = _write_case("xlsx_to_csv_first", {"mode": "xlsx_to_csv"}, {})
    wb = Workbook()
    ws = wb.active
    ws.title = "S1"
    ws["A1"], ws["B1"], ws["A2"], ws["B2"] = "a", "b", 1, "x,y"
    wb.create_sheet("S2")["A1"] = "ignored"
    wb.save(case / "input" / "book.xlsx")
    (case / "expected" / "book.csv").write_bytes(BOM + b'a,b\r\n1,"x,y"\r\n')


def csv_unquote_semicolon() -> None:
    case = _write_case(
        "csv_unquote_semicolon",
        {"mode": "csv_unquote"},
        {"s.csv": b'"a";"b,c";"d"\r\n"1";"2";"3"\r\n'},
    )
    (case / "expected" / "s_unquoted.csv").write_bytes(BOM + b'a;"b,c";d\r\n1;2;3\r\n')


def csv_to_bom_already() -> None:
    _write_case(
        "csv_to_bom_already",
        {"mode": "csv_to_bom"},
        {"has_bom.csv": BOM + b"id,name\r\n1,x\r\n"},
        expect_outputs=False,
    )


def csv_to_bom_ambiguous_chosen() -> None:
    text = "テスト医師\r\n"
    case = _write_case(
        "csv_to_bom_ambiguous_chosen",
        {"mode": "csv_to_bom", "encodings": {"amb.csv": "cp932"}},
        {"amb.csv": text.encode("cp932")},
    )
    (case / "expected" / "amb_bom.csv").write_bytes(BOM + text.encode("utf-8"))


def overwrite_source() -> None:
    case = _write_case(
        "overwrite_source",
        {"mode": "csv_to_bom", "overwrite_source": True},
        {"plain.csv": b"id,name\r\n1,x\r\n"},
    )
    (case / "expected" / "plain.csv").write_bytes(BOM + b"id,name\r\n1,x\r\n")


def main() -> None:
    csv_to_xlsx()
    xlsx_to_csv_all()
    csv_to_bom_gbk()
    csv_unquote()
    xlsx_to_csv_first()
    csv_unquote_semicolon()
    csv_to_bom_already()
    csv_to_bom_ambiguous_chosen()
    overwrite_source()


if __name__ == "__main__":
    main()
