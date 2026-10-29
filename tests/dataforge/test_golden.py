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
