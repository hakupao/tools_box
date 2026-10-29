"""Regenerate the width_convert golden workbooks from hand-written literals.

Run from the repo root:
    .venv/Scripts/python.exe tests/golden/width_convert/make_fixtures.py

Expected values are written by hand here; the tool under test is never called.
"""
from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font

CASE = Path(__file__).resolve().parent / "basic"

# (sheet1 rows, sheet2 rows) as (input, expected) literal pairs.
# "FORMULA" cells are identical in both. Dates/numbers are real numerics (untouched).


def _build(path: Path, expected: bool) -> None:
    def v(src: str, dst: str) -> str:
        return dst if expected else src

    wb = Workbook()
    ws = wb.active
    ws.title = "患者"
    ws["A1"] = v("ＳＵＢＪＩＤ", "SUBJID")
    ws["B1"] = v("氏名（ＫＡＮＡ）", "氏名(KANA)")
    ws["C1"] = v("備考", "備考")
    for cell in ("A1", "B1", "C1"):
        ws[cell].font = Font(bold=True)
    ws["A2"] = v("ＡＢＣ１２３", "ABC123")
    ws["B2"] = v("テスト　医師ｱｲｳ", "テスト 医師ｱｲｳ")
    ws["C2"] = v("全角！＠＃", "全角!@#")
    ws["A3"] = v("００１", "001")
    ws["A3"].number_format = "@"
    ws["B3"] = "=LEN(A3)"
    ws["C3"] = 42
    ws["C3"].number_format = "0.00"
    ws["A4"] = v("合并１２", "合并12")
    ws.merge_cells("A4:C4")
    ws["A5"] = "plain ASCII"
    ws["B5"] = v("ｘ　ｙ", "x y")

    ws2 = wb.create_sheet("Sheet２")  # sheet names are never converted
    ws2["A1"] = v("ＮＯ．", "NO.")
    ws2["B1"] = v("ひらがな　カタカナ", "ひらがな カタカナ")
    ws2["A2"] = v("（１）", "(1)")
    ws2["B2"] = '=A2&"x"'
    ws2["A3"] = v("～ｚ", "~z")
    ws2.merge_cells("A3:B3")
    wb.save(path)


def main() -> None:
    (CASE / "input").mkdir(parents=True, exist_ok=True)
    (CASE / "expected").mkdir(parents=True, exist_ok=True)
    _build(CASE / "input" / "sample.xlsx", expected=False)
    _build(CASE / "expected" / "sample_halfwidth.xlsx", expected=True)
    (CASE / "params.json").write_text("{}\n", encoding="utf-8")


if __name__ == "__main__":
    main()
