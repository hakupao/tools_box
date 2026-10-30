"""Regenerate the EDC site adder golden traces from hand-written literals.

Run from the repo root:
    .venv/Scripts/python.exe tests/golden/edc/make_fixtures.py

The tool under test is never imported or called. Each case is a params.json for the golden
adapter (FakePorts drives run_segment + EdcSession) and the expected action trace
(expected/trace.txt, UTF-8 without BOM, LF, one action per line; format in
docs/tools/edc_site_adder.md). Click positions are the default recorded positions; the
target window is fixed by the adapter. There are no input files, so there is no input/ dir.
All data is fictional.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Default positions, in click order: 新建, 查找, 搜索框, 搜索, 选择, ok, 确认
CLICKS = [
    "screen.click 241 212",
    "screen.click 1137 460",
    "screen.click 817 409",
    "screen.click 1040 406",
    "screen.click 699 471",
    "screen.click 1121 758",
    "screen.click 1038 728",
]
SEARCH_BOX = 2  # index of 搜索框 in CLICKS: followed by a short wait and a paste


def _clicks(delay: str, upto: int = len(CLICKS)) -> list[str]:
    """Lines for the first ``upto`` click steps, each finished with ``sleep <delay>``."""
    lines: list[str] = []
    for i, click in enumerate(CLICKS[:upto]):
        lines.append(click)
        if i == SEARCH_BOX:
            lines += ["sleep 0.05", "screen.paste"]
        lines.append(f"sleep {delay}")
    return lines


def _row(row: int, value: str, delay: str) -> list[str]:
    """A fully successful row: read, copy, activate, 7 clicks, focus next row."""
    return (
        [f"excel.text A{row}", f"clipboard.copy {value}", "sleep 0.1", "window.activate",
         "sleep 0.1"]
        + _clicks(delay)
        + [f"excel.focus A{row + 1}", "sleep 0.1"]
    )


def _write_case(name: str, params: dict, trace: list[str]) -> None:
    case = ROOT / name
    if case.exists():
        shutil.rmtree(case)
    (case / "expected").mkdir(parents=True)
    text = json.dumps(params, ensure_ascii=False, indent=2) + "\n"
    (case / "params.json").write_bytes(text.encode("utf-8"))
    (case / "expected" / "trace.txt").write_bytes(("\n".join(trace) + "\n").encode("utf-8"))


def basic_three_rows() -> None:
    # A2-A4 filled, A5 empty: the pre-count reads A2..A5, then three rows, then A5 ends it
    _write_case(
        "basic_three_rows",
        {
            "cells": {"2": "SITE-1", "3": "SITE-2", "4": "SITE-3"},
            "start_row": 2,
            "max_loops": 100,
            "step_delay": 0.3,
            "fail": None,
            "esc_after": None,
            "choices": [],
        },
        ["excel.selection -> A2", "excel.text A2", "excel.text A3", "excel.text A4",
         "excel.text A5"]
        + _row(2, "SITE-1", "0.3")
        + _row(3, "SITE-2", "0.3")
        + _row(4, "SITE-3", "0.3")
        + ["excel.text A5",
           "succeeded A2 SITE-1", "succeeded A3 SITE-2", "succeeded A4 SITE-3"],
    )


def limit_and_whitespace() -> None:
    # max_loops 2 from A2: rows A2 and A3 only (end row 4, never read); " SITE-2 " is trimmed
    _write_case(
        "limit_and_whitespace",
        {
            "cells": {"2": "SITE-1", "3": " SITE-2 ", "4": "SITE-3"},
            "start_row": 2,
            "max_loops": 2,
            "step_delay": 0.5,
            "fail": None,
            "esc_after": None,
            "choices": [],
        },
        ["excel.selection -> A2", "excel.text A2", "excel.text A3"]
        + _row(2, "SITE-1", "0.5")
        + _row(3, "SITE-2", "0.5")
        + ["succeeded A2 SITE-1", "succeeded A3 SITE-2"],
    )


def failure_skip_then_redo() -> None:
    # Start A1. Row A2: its 5th click (【选择】, step 8) is click #12 overall -> fails, skip.
    # Row A3: window activation #3 fails (step 3) -> redo; activation #4 succeeds.
    # Every segment re-counts rows from its own start.
    _write_case(
        "failure_skip_then_redo",
        {
            "cells": {"1": "SITE-1", "2": "SITE-2", "3": "SITE-3"},
            "start_row": 1,
            "max_loops": 100,
            "step_delay": 0.3,
            "fail": [
                {"call": "screen.click", "nth": 12, "message": "boom", "exc": None},
                {
                    "call": "window.activate",
                    "nth": 3,
                    "message": "找不到目标窗口：EDC（chrome.exe）",
                    "exc": "DataForgeError",
                },
            ],
            "esc_after": None,
            "choices": ["skip", "redo"],
        },
        ["excel.selection -> A1", "excel.text A1", "excel.text A2", "excel.text A3",
         "excel.text A4"]
        + _row(1, "SITE-1", "0.3")
        + ["excel.text A2", "clipboard.copy SITE-2", "sleep 0.1", "window.activate",
           "sleep 0.1"]
        + _clicks("0.3", upto=4)
        + ["screen.click 699 471",
           "== stop A2 step 8: boom -> skip",
           "excel.text A3", "excel.text A4",
           "excel.text A3", "clipboard.copy SITE-3", "sleep 0.1", "window.activate",
           "== stop A3 step 3: 找不到目标窗口：EDC（chrome.exe） -> redo",
           "excel.text A3", "excel.text A4"]
        + _row(3, "SITE-3", "0.3")
        + ["excel.text A4",
           "succeeded A1 SITE-1", "succeeded A3 SITE-3", "skipped A2 step 8"],
    )


def esc_then_end() -> None:
    # Trace lines before the click steps: selection, 3 count reads, text, copy, sleep,
    # activate, sleep = 9. esc_after 12 turns on after 【查找】 is clicked (line 12), so the
    # check before step 6 (【搜索框】) stops the row; choosing end records it as failed.
    _write_case(
        "esc_then_end",
        {
            "cells": {"2": "SITE-1", "3": "SITE-2"},
            "start_row": 2,
            "max_loops": 100,
            "step_delay": 0.3,
            "fail": None,
            "esc_after": 12,
            "choices": ["end"],
        },
        ["excel.selection -> A2", "excel.text A2", "excel.text A3", "excel.text A4",
         "excel.text A2", "clipboard.copy SITE-1", "sleep 0.1", "window.activate", "sleep 0.1"]
        + _clicks("0.3", upto=2)
        + ["== stop A2 step 6: 已按 ESC 停止 -> end", "failed A2 step 6"],
    )


def main() -> None:
    basic_three_rows()
    limit_and_whitespace()
    failure_skip_then_redo()
    esc_then_end()


if __name__ == "__main__":
    main()
