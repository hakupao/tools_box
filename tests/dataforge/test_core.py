import unittest
from pathlib import Path

from dataforge.core.errors import Cancelled, DataForgeError
from dataforge.core.progress import CancelToken, no_progress
from dataforge.core.result import FileIssue, Result


class ResultTests(unittest.TestCase):
    def test_ok_false_after_fail(self):
        r = Result()
        r.fail("a.csv", "坏了")
        self.assertFalse(r.ok)
        self.assertEqual(r.errors, [FileIssue("a.csv", "坏了")])

    def test_ok_true_when_empty(self):
        self.assertTrue(Result().ok)

    def test_add_output(self):
        r = Result()
        r.add_output(Path("o.csv"))
        self.assertEqual(r.outputs, [Path("o.csv")])

    def test_count_accumulates(self):
        r = Result()
        r.count("cells")
        r.count("cells", 4)
        self.assertEqual(r.stats["cells"], 5)

    def test_paths_are_stringified_in_issues(self):
        r = Result()
        r.warn(Path("x/y.csv"), "w")
        self.assertEqual(r.warnings[0].path, str(Path("x/y.csv")))


class CancelTokenTests(unittest.TestCase):
    def test_raise_if_cancelled(self):
        t = CancelToken()
        t.raise_if_cancelled()
        t.cancel()
        self.assertTrue(t.cancelled)
        with self.assertRaises(Cancelled):
            t.raise_if_cancelled()

    def test_dataforge_error_is_value_error(self):
        self.assertTrue(issubclass(DataForgeError, ValueError))

    def test_no_progress_is_noop(self):
        self.assertIsNone(no_progress(1, 2, "x"))
