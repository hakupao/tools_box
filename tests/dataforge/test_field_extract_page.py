from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests.dataforge.qt_helpers import qapp, wait_until

AMBIGUOUS = "テスト医師\n".encode("cp932")


class FieldExtractPageTests(unittest.TestCase):
    def setUp(self) -> None:
        from dataforge.ui.jobs import JobRunner

        qapp()
        self.runner = JobRunner()
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self) -> None:
        self.runner.shutdown()
        self.runner.dispose()
        self._tmp.cleanup()

    def _page(self):
        from dataforge.ui.pages.field_extract_page import FieldExtractPage
        from dataforge.ui.registry import get_tool

        return FieldExtractPage(get_tool("field_extract"), self.runner)

    def _summaries(self) -> list[Path]:
        return sorted(self.dir.glob("file_fields_summary*.csv"))

    def test_build_job_validation(self) -> None:
        page = self._page()
        with mock.patch("dataforge.ui.pages.field_extract_page.InfoBar") as bar:
            self.assertIsNone(page.build_job())
        bar.warning.assert_called_once()

    def test_state_roundtrip(self) -> None:
        page = self._page()
        self.assertEqual(page.header_spin.minimum(), 1)
        self.assertEqual(page.header_spin.maximum(), 1000)
        self.assertEqual(page.header_spin.value(), 1)
        state = {
            "folder": str(self.dir),
            "header_row": 3,
            "include_subfolders": True,
            "encoding": "gbk",
            "output_dir": str(self.dir),
        }
        self.assertEqual(page.restore_state(state), [])
        self.assertEqual(page.capture_state(), state)
        self.assertEqual(page.summary(), self.dir.name)
        gone = str(self.dir / "gone")
        self.assertEqual(page.restore_state({**state, "folder": gone}), [gone])
        self.assertIsNone(page.folder_picker.folder())

    def test_output_same_label(self) -> None:
        page = self._page()
        self.assertEqual(page.output_field.combo.itemText(0), "所选文件夹")

    def test_locking(self) -> None:
        page = self._page()
        page.set_inputs_locked(True)
        self.assertTrue(page.folder_picker.is_locked())
        self.assertFalse(page.header_spin.isEnabled())
        page.set_inputs_locked(False)
        self.assertFalse(page.folder_picker.is_locked())
        self.assertTrue(page.header_spin.isEnabled())

    def test_run_end_to_end(self) -> None:
        (self.dir / "a.csv").write_bytes(b"id,name\n1,x\n")
        page = self._page()
        page.folder_picker.set_folder(self.dir)
        with mock.patch("dataforge.ui.components.tool_page.InfoBar") as bar:
            page.run_bar.start_requested.emit()
            wait_until(lambda: bar.method_calls != [])
            wait_until(lambda: not self.runner.is_busy())
        self.assertEqual([p.name for p in self._summaries()], ["file_fields_summary.csv"])
        self.assertIn("file_fields_summary.csv", page.result_panel.page_text("result"))

    def test_retry_rewrites_single_summary(self) -> None:
        (self.dir / "a.csv").write_bytes(b"id\n")
        (self.dir / "amb.csv").write_bytes(AMBIGUOUS)
        (self.dir / "amb2.csv").write_bytes(AMBIGUOUS)
        page = self._page()
        page.folder_picker.set_folder(self.dir)
        answers = {str(self.dir / "amb.csv"): "cp932"}
        with mock.patch(
            "dataforge.ui.components.tool_page.ask_encodings", return_value=answers
        ), mock.patch("dataforge.ui.components.tool_page.InfoBar") as bar:
            page.run_bar.start_requested.emit()
            wait_until(lambda: bar.method_calls != [])
            wait_until(lambda: not self.runner.is_busy())
        files = self._summaries()
        self.assertEqual([p.name for p in files], ["file_fields_summary.csv"])
        with files[0].open(encoding="utf-8-sig", newline="") as fh:
            rows = list(csv.reader(fh))
        self.assertIn(["amb.csv", "テスト医師"], rows)
        self.assertIn(["a.csv", "id"], rows)
        self.assertIn("amb2.csv: 未选择编码，已跳过", page.result_panel.page_text("warnings"))


if __name__ == "__main__":
    unittest.main()
