from __future__ import annotations

import csv
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests.dataforge.qt_helpers import drain_deleted, qapp, wait_until

AMBIGUOUS = "テスト医師\n".encode("cp932")


class FieldExtractPageTests(unittest.TestCase):
    def setUp(self) -> None:
        from dataforge.ui.jobs import JobRunner

        qapp()
        self.runner = JobRunner()
        self._pages: list = []
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self) -> None:
        wait_until(lambda: not self.runner.is_busy())
        self.runner.shutdown()
        self.runner.dispose()
        drain_deleted(*self._pages, self.runner)
        self._tmp.cleanup()

    def _page(self):
        from dataforge.ui.pages.field_extract_page import FieldExtractPage
        from dataforge.ui.registry import get_tool

        page = FieldExtractPage(get_tool("field_extract"), self.runner)
        self._pages.append(page)
        return page

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

    def _first_run(self, page, **opts):
        from dataforge.core.progress import CancelToken, no_progress
        from dataforge.tools import field_extract

        first = field_extract.run(
            self.dir, field_extract.FieldOptions(**opts), no_progress, CancelToken()
        )
        page._carry = first
        return first

    def _retry(self, page, token=None):
        from dataforge.core.progress import CancelToken, no_progress

        job = page.build_retry_job({str(self.dir / "amb.csv"): "cp932"})
        return job(no_progress, token or CancelToken())

    def _setup_amb(self, page, out_dir=None):
        (self.dir / "a.csv").write_bytes(b"id\n")
        (self.dir / "amb.csv").write_bytes(AMBIGUOUS)
        page.folder_picker.set_folder(self.dir)
        if out_dir is not None:
            page.output_field.set_output_dir(out_dir)
        return self._first_run(page, output_dir=out_dir)

    def test_retry_replaces_original_summary_name(self) -> None:
        page = self._page()
        first = self._setup_amb(page)
        result = self._retry(page)
        self.assertEqual(result.outputs, first.outputs)
        self.assertEqual([p.name for p in self._summaries()], ["file_fields_summary.csv"])
        with first.outputs[0].open(encoding="utf-8-sig", newline="") as fh:
            self.assertIn(["amb.csv", "テスト医師"], list(csv.reader(fh)))

    def test_retry_with_custom_output_dir(self) -> None:
        page = self._page()
        out = self.dir / "out"
        first = self._setup_amb(page, out)
        result = self._retry(page)
        self.assertEqual(result.outputs, first.outputs)
        self.assertEqual(sorted(p.name for p in out.iterdir()), ["file_fields_summary.csv"])

    def test_retry_replace_failure_keeps_both(self) -> None:
        page = self._page()
        first = self._setup_amb(page)
        real = os.replace

        def flaky(src, dst):
            if Path(dst).name == "file_fields_summary.csv":
                raise PermissionError("open in Excel")
            return real(src, dst)

        with mock.patch("dataforge.ui.pages.field_extract_page.os.replace", flaky):
            result = self._retry(page)
        self.assertEqual([p.name for p in self._summaries()],
                         ["file_fields_summary.csv", "file_fields_summary_1.csv"])
        self.assertEqual(result.outputs, [self.dir / "file_fields_summary_1.csv"])
        self.assertTrue(any("无法覆盖原汇总" in w.message for w in result.warnings))
        self.assertEqual(first.outputs, [self.dir / "file_fields_summary.csv"])

    def test_cancelled_retry_leaves_original(self) -> None:
        from dataforge.core.errors import Cancelled
        from dataforge.core.progress import CancelToken

        page = self._page()
        first = self._setup_amb(page)
        before = first.outputs[0].read_bytes()
        token = CancelToken()
        token.cancel()
        with self.assertRaises(Cancelled):
            self._retry(page, token)
        self.assertEqual(first.outputs[0].read_bytes(), before)
        self.assertEqual([p.name for p in self._summaries()], ["file_fields_summary.csv"])

    def test_retry_does_not_duplicate_notes(self) -> None:
        page = self._page()
        (self.dir / "g.csv").write_bytes("姓名\n".encode("gbk"))
        first = self._setup_amb(page)
        notes = [w for w in first.warnings if "g.csv" in w.path]
        self.assertTrue(notes)
        result = self._retry(page)
        self.assertEqual([w for w in result.warnings if "g.csv" in w.path], notes)


if __name__ == "__main__":
    unittest.main()
