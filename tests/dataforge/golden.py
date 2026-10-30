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


def _map_encodings(encodings: dict[str, str], work: Path) -> dict[str, str]:
    """``encodings`` keys are input-relative paths; the tools key on the copied absolute path."""
    return {str(work / rel): enc for rel, enc in encodings.items()}


def _run_format_convert(input_dir: Path, output_dir: Path, params: dict[str, Any]) -> None:
    from dataforge.tools.format_convert import MODE_EXTENSIONS, ConvertMode, FormatOptions, run

    mode = ConvertMode(params["mode"])
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "input"
        shutil.copytree(input_dir, work)
        files = sorted(p for p in work.iterdir() if p.suffix.lower() in MODE_EXTENSIONS[mode])
        options = FormatOptions(
            mode=mode,
            output_dir=output_dir,
            overwrite_source=params.get("overwrite_source", False),
            all_sheets=params.get("all_sheets", False),
            encoding=params.get("encoding"),
            encodings=_map_encodings(params.get("encodings", {}), work),
        )
        result = run(files, options, no_progress, CancelToken())
        if result.errors:
            raise AssertionError(f"tool reported errors: {result.errors}")
        if options.overwrite_source:  # outputs are the rewritten inputs: collect them for diffing
            for out in result.outputs:
                shutil.copy2(out, output_dir / out.relative_to(work))


def _run_field_extract(input_dir: Path, output_dir: Path, params: dict[str, Any]) -> None:
    from dataforge.tools.field_extract import FieldOptions, run

    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "input"
        shutil.copytree(input_dir, work)
        options = FieldOptions(
            header_row=params.get("header_row", 1),
            include_subfolders=params.get("include_subfolders", False),
            output_dir=output_dir,
            encoding=params.get("encoding"),
            encodings=_map_encodings(params.get("encodings", {}), work),
        )
        result = run(work, options, no_progress, CancelToken())
        if result.errors:
            raise AssertionError(f"tool reported errors: {result.errors}")


def _run_masking(input_dir: Path, output_dir: Path, params: dict[str, Any]) -> None:
    from datetime import datetime

    from dataforge.dates import SlashOrder
    from dataforge.tools.masking.execute import MaskOptions, run
    from dataforge.tools.masking.profile import MaskingProfile
    from dataforge.tools.masking.scan import ScanSettings, scan

    profile = MaskingProfile.from_dict(params.get("profile", {}))
    orders = {}
    for key, value in params.get("date_orders", {}).items():
        file_name, column = key.split(":", 1)  # file names cannot contain ":"
        orders[(file_name, column)] = SlashOrder(value)
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "input"
        shutil.copytree(input_dir, work)
        files = sorted(p for p in work.iterdir() if p.suffix.lower() == ".csv")
        encodings = _map_encodings(params.get("encodings", {}), work)
        settings = ScanSettings.from_profile(profile)
        scanned = scan(files, settings, None, encodings, no_progress, CancelToken())
        if scanned.errors:
            raise AssertionError(f"scan reported errors: {scanned.errors}")
        parent = Path(tmp) / "out"
        options = MaskOptions(
            profile=profile,
            output_parent=parent,
            date_orders=orders,
            now=datetime(2026, 1, 2, 3, 4, 5),
        )
        result = run(scanned.data, options, no_progress, CancelToken())
        folders = [p.name for p in parent.iterdir()]
        if folders != ["masked_output_20260102_030405"]:
            raise AssertionError(f"unexpected output folders: {folders}")
        for out in result.outputs:
            shutil.copy2(out, output_dir / out.name)


def _run_edc(input_dir: Path, output_dir: Path, params: dict[str, Any]) -> None:
    """Drive run_segment + EdcSession with FakePorts and write the action trace."""
    import threading

    from dataforge.tools.edc.config import EdcConfig
    from dataforge.tools.edc.loop import (
        CellRef,
        EdcSession,
        Segment,
        StopChoice,
        StopFlag,
        run_segment,
    )
    from dataforge.tools.edc.windows import WindowInfo
    from tests.dataforge.edc_fakes import FakePorts

    fake = FakePorts(
        {int(row): text for row, text in params["cells"].items()},
        params["start_row"],
        fail=params.get("fail"),
        esc_after=params.get("esc_after"),
    )
    config = EdcConfig(
        max_loops=params["max_loops"],
        step_delay=params["step_delay"],
        target_window=WindowInfo(1, "EDC", "chrome.exe"),
    )
    choices = iter(params.get("choices", []))

    def segment(start: CellRef | None, end_row: int | None, stop: StopFlag) -> Segment:
        result = run_segment(config, fake.ports(), start, end_row, stop, no_progress, CancelToken())
        return result.data

    seg = segment(None, None, fake.stop_flag())  # esc_after only applies to the first segment
    session = EdcSession.begin(seg)
    while seg.stop is not None:
        choice = next(choices, "end")
        stop = seg.stop
        fake.trace.append(
            f"== stop {stop.cell.address()} step {stop.step}: {stop.reason} -> {choice}"
        )
        nxt = session.resolve(stop, StopChoice(choice))
        if nxt is None:
            break
        seg = segment(nxt, session.end_row, threading.Event())
        session.absorb(seg)

    lines = list(fake.trace)
    lines += [f"succeeded {d.cell.address()} {d.value}" for d in session.done]
    lines += [f"skipped {s.cell.address()} step {s.step}" for s in session.skipped]
    lines += [f"failed {s.cell.address()} step {s.step}" for s in session.failed]
    (output_dir / "trace.txt").write_bytes(("\n".join(lines) + "\n").encode("utf-8"))


ADAPTERS: dict[str, Callable[[Path, Path, dict], None]] = {
    "width_convert": _run_width_convert,
    "date_convert": _run_date_convert,
    "sheet_split": _run_sheet_split,
    "format_convert": _run_format_convert,
    "field_extract": _run_field_extract,
    "masking": _run_masking,
    "edc": _run_edc,
}


def _list_files(root: Path) -> list[str]:
    if not root.is_dir():  # an absent expected/ means "no output files"
        return []
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
                test.assertEqual(ce.data_type, ca.data_type, f"{where}: data_type")
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
        if suffix in (".csv", ".txt", ".json"):
            test.assertEqual(path_e.read_bytes(), path_a.read_bytes(), f"{name}: bytes differ")
        elif suffix in (".xlsx", ".xlsm"):
            _assert_xlsx_equal(test, path_e, path_a, name)
        else:
            test.fail(f"unsupported file type in golden sample: {name}")
