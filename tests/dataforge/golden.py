"""Golden-sample discovery, tool adapters and output comparison.

Layout: tests/golden/<tool_id>/<case>/{params.json, input/, expected/}
"""
from __future__ import annotations

import shutil
import tempfile
import unittest
from collections.abc import Callable
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

from dataforge.core.progress import CancelToken, no_progress

GOLDEN_ROOT = Path("tests/golden")
_REPO_ROOT = Path(__file__).resolve().parents[2]


def discover(tool_id: str) -> list[Path]:
    root = _REPO_ROOT / GOLDEN_ROOT / tool_id
    if not root.is_dir():
        return []
    return sorted(p for p in root.iterdir() if p.is_dir() and (p / "params.json").is_file())


def _run_width_convert(input_dir: Path, output_dir: Path, params: dict[str, Any]) -> None:
    from dataforge.tools.width_convert import SUPPORTED_EXTENSIONS, WidthOptions, run

    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "input"
        shutil.copytree(input_dir, work)
        files = sorted(p for p in work.iterdir() if p.suffix.lower() in SUPPORTED_EXTENSIONS)
        options = WidthOptions(output_dir=output_dir)
        result = run(files, options, no_progress, CancelToken())
        if result.errors:
            raise AssertionError(f"tool reported errors: {result.errors}")


def _run_date_convert(input_dir: Path, output_dir: Path, params: dict[str, Any]) -> None:
    from dataforge.tools.date_convert import convert_text

    text = (input_dir / "input.txt").read_bytes().decode("utf-8")
    (output_dir / "output.txt").write_bytes(convert_text(text).encode("utf-8"))


def _run_sheet_split(input_dir: Path, output_dir: Path, params: dict[str, Any]) -> None:
    from dataforge.tools.sheet_split import SUPPORTED_EXTENSIONS, SplitOptions, run

    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "input"
        shutil.copytree(input_dir, work)
        files = sorted(p for p in work.iterdir() if p.suffix.lower() in SUPPORTED_EXTENSIONS)
        result = run(files, SplitOptions(output_dir=output_dir), no_progress, CancelToken())
        if result.errors:
            raise AssertionError(f"tool reported errors: {result.errors}")


def _run_format_convert(input_dir: Path, output_dir: Path, params: dict[str, Any]) -> None:
    from dataforge.tools.format_convert import MODE_EXTENSIONS, ConvertMode, FormatOptions, run

    mode = ConvertMode(params["mode"])
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "input"
        shutil.copytree(input_dir, work)
        files = sorted(p for p in work.iterdir() if p.suffix.lower() in MODE_EXTENSIONS[mode])
        options = FormatOptions(
            mode=mode, output_dir=output_dir, all_sheets=params.get("all_sheets", False)
        )
        result = run(files, options, no_progress, CancelToken())
        if result.errors:
            raise AssertionError(f"tool reported errors: {result.errors}")


ADAPTERS: dict[str, Callable[[Path, Path, dict], None]] = {
    "width_convert": _run_width_convert,
    "date_convert": _run_date_convert,
    "sheet_split": _run_sheet_split,
    "format_convert": _run_format_convert,
}


def _list_files(root: Path) -> list[str]:
    return sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file())


def _dump_sheet(ws) -> dict[tuple[int, int], tuple[Any, str]]:
    cells: dict[tuple[int, int], tuple[Any, str]] = {}
    for row in ws.iter_rows():
        for c in row:
            cells[(c.row, c.column)] = (c.value, c.number_format)
    return cells


def _assert_xlsx_equal(test: unittest.TestCase, expected: Path, actual: Path, name: str) -> None:
    wb_e, wb_a = load_workbook(expected), load_workbook(actual)
    test.assertEqual(wb_e.sheetnames, wb_a.sheetnames, f"{name}: sheet names")
    for sheet in wb_e.sheetnames:
        ws_e, ws_a = wb_e[sheet], wb_a[sheet]
        rows = max(ws_e.max_row, ws_a.max_row)
        cols = max(ws_e.max_column, ws_a.max_column)
        for r in range(1, rows + 1):
            for c in range(1, cols + 1):
                ce, ca = ws_e.cell(r, c), ws_a.cell(r, c)
                where = f"{name}!{sheet}!{ce.coordinate}"
                test.assertEqual(ce.value, ca.value, f"{where}: value")
                test.assertEqual(ce.number_format, ca.number_format, f"{where}: number_format")
        test.assertEqual(
            sorted(str(m) for m in ws_e.merged_cells.ranges),
            sorted(str(m) for m in ws_a.merged_cells.ranges),
            f"{name}!{sheet}: merged ranges",
        )


def assert_dirs_equal(test: unittest.TestCase, expected: Path, actual: Path) -> None:
    names_e, names_a = _list_files(expected), _list_files(actual)
    test.assertEqual(names_e, names_a, "file name sets differ")
    for name in names_e:
        path_e, path_a = expected / name, actual / name
        suffix = path_e.suffix.lower()
        if suffix in (".csv", ".txt"):
            test.assertEqual(path_e.read_bytes(), path_a.read_bytes(), f"{name}: bytes differ")
        elif suffix in (".xlsx", ".xlsm"):
            _assert_xlsx_equal(test, path_e, path_a, name)
        else:
            test.fail(f"unsupported file type in golden sample: {name}")
