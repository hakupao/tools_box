from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tests.dataforge import golden


class GoldenTests(unittest.TestCase):
    def test_width_convert_has_cases(self) -> None:
        self.assertIn("width_convert", golden.ADAPTERS)
        self.assertTrue(golden.discover("width_convert"))

    def test_date_convert_has_cases(self) -> None:
        self.assertIn("date_convert", golden.ADAPTERS)
        self.assertTrue(golden.discover("date_convert"))

    def test_sheet_split_has_cases(self) -> None:
        self.assertIn("sheet_split", golden.ADAPTERS)
        self.assertTrue(golden.discover("sheet_split"))

    def test_format_convert_has_cases(self) -> None:
        self.assertIn("format_convert", golden.ADAPTERS)
        self.assertEqual(len(golden.discover("format_convert")), 9)

    def test_field_extract_has_cases(self) -> None:
        self.assertIn("field_extract", golden.ADAPTERS)
        self.assertTrue(golden.discover("field_extract"))

    def test_field_extract_stale_summary_case_exists(self) -> None:
        names = {p.name for p in golden.discover("field_extract")}
        self.assertIn("stale_summary", names)

    def test_masking_has_cases(self) -> None:
        self.assertIn("masking", golden.ADAPTERS)
        names = [p.name for p in golden.discover("masking")]
        self.assertEqual(names, ["rule_chain_ambiguous", "sequential_basic"])

    def test_edc_has_cases(self) -> None:
        self.assertIn("edc", golden.ADAPTERS)
        names = [p.name for p in golden.discover("edc")]
        self.assertEqual(
            names,
            ["basic_three_rows", "esc_then_end", "failure_skip_then_redo", "limit_and_whitespace"],
        )

    def test_golden_samples(self) -> None:
        for tool_id, adapter in golden.ADAPTERS.items():
            for case in golden.discover(tool_id):
                with self.subTest(tool=tool_id, case=case.name):
                    params = json.loads((case / "params.json").read_text(encoding="utf-8"))
                    with tempfile.TemporaryDirectory() as tmp:
                        out = Path(tmp) / "out"
                        out.mkdir()
                        adapter(case / "input", out, params)
                        golden.assert_dirs_equal(self, case / "expected", out)


if __name__ == "__main__":
    unittest.main()
