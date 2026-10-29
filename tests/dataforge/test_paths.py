import tempfile
import unittest
from pathlib import Path

from dataforge.fileio.paths import iter_input_files, plan_output


class PlanOutputTests(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.addCleanup(self._td.cleanup)
        self.tmp = Path(self._td.name)
        self.src = self.tmp / "a.xlsx"
        self.src.write_bytes(b"")

    def test_new_name_next_to_source(self):
        out = plan_output(self.src, new_name="a_halfwidth.xlsx")
        self.assertEqual(out, self.tmp / "a_halfwidth.xlsx")

    def test_conflict_appends_counter(self):
        (self.tmp / "a_halfwidth.xlsx").write_bytes(b"")
        (self.tmp / "a_halfwidth_1.xlsx").write_bytes(b"")
        out = plan_output(self.src, new_name="a_halfwidth.xlsx")
        self.assertEqual(out, self.tmp / "a_halfwidth_2.xlsx")

    def test_output_dir_created(self):
        d = self.tmp / "out" / "sub"
        out = plan_output(self.src, new_name="a_halfwidth.xlsx", output_dir=d)
        self.assertEqual(out, d / "a_halfwidth.xlsx")
        self.assertTrue(d.is_dir())

    def test_overwrite_returns_source(self):
        out = plan_output(self.src, new_name="x.xlsx", overwrite_source=True)
        self.assertEqual(out, self.src)


class IterInputFilesTests(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.addCleanup(self._td.cleanup)
        self.tmp = Path(self._td.name)
        for name in ("b.xlsx", "A.XLSX", "~$b.xlsx", "note.txt"):
            (self.tmp / name).write_bytes(b"")
        (self.tmp / "sub").mkdir()
        (self.tmp / "sub" / "c.xlsx").write_bytes(b"")

    def test_iter_skips_lock_files_and_filters_ext(self):
        got = iter_input_files([self.tmp], (".xlsx",))
        self.assertEqual(got, [self.tmp / "A.XLSX", self.tmp / "b.xlsx"])
        got = iter_input_files([self.tmp], (".xlsx",), recursive=True)
        self.assertEqual(
            got, [self.tmp / "A.XLSX", self.tmp / "b.xlsx", self.tmp / "sub" / "c.xlsx"]
        )

    def test_iter_skips_atomic_temp_files(self):
        (self.tmp / ".b.123.abcd1234.tmp.xlsx").write_bytes(b"")
        (self.tmp / ".hidden.xlsx").write_bytes(b"")
        got = iter_input_files([self.tmp], (".xlsx",))
        self.assertEqual(
            got, [self.tmp / ".hidden.xlsx", self.tmp / "A.XLSX", self.tmp / "b.xlsx"]
        )

    def test_iter_dedupes(self):
        f = self.tmp / "b.xlsx"
        got = iter_input_files([f, f, self.tmp], (".xlsx",))
        self.assertEqual(got, [f, self.tmp / "A.XLSX"])

    def test_iter_skips_missing(self):
        self.assertEqual(iter_input_files([self.tmp / "nope.xlsx"], (".xlsx",)), [])


if __name__ == "__main__":
    unittest.main()
