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

    def test_cancelled_survives_except_exception(self):
        self.assertFalse(issubclass(Cancelled, Exception))
        t = CancelToken()
        t.cancel()
        processed = []

        def loop():
            for i in range(3):
                try:
                    t.raise_if_cancelled()
                    processed.append(i)
                except Exception:  # tool-style per-file guard
                    pass

        with self.assertRaises(Cancelled):
            loop()
        self.assertEqual(processed, [])

    def test_dataforge_error_is_value_error(self):
        self.assertTrue(issubclass(DataForgeError, ValueError))

    def test_no_progress_is_noop(self):
        self.assertIsNone(no_progress(1, 2, "x"))


class ResultEncodingTests(unittest.TestCase):
    def test_result_extend(self):
        from dataforge.core.result import EncodingQuestion

        a = Result()
        a.add_output(Path("1"))
        a.warn("w1", "m")
        a.count("n", 1)
        b = Result()
        b.add_output(Path("2"))
        b.fail("e", "m")
        b.ask_encoding("q.csv", {"gbk": "x"})
        b.count("n", 2)
        b.count("k")
        a.extend(b)
        self.assertEqual(a.outputs, [Path("1"), Path("2")])
        self.assertEqual(len(a.warnings), 1)
        self.assertEqual(a.errors, [FileIssue("e", "m")])
        self.assertEqual(a.encoding_questions, [EncodingQuestion("q.csv", {"gbk": "x"})])
        self.assertEqual(a.stats, {"n": 3, "k": 1})

    def test_ask_encoding_not_error(self):
        r = Result()
        r.ask_encoding(Path("q.csv"), {"cp932": "a", "gbk": "b"})
        self.assertTrue(r.ok)
        self.assertEqual(r.encoding_questions[0].path, "q.csv")


class ResultDataTests(unittest.TestCase):
    def test_result_data_not_extended(self):
        a = Result(data="keep")
        b = Result(data="other")
        a.extend(b)
        self.assertEqual(a.data, "keep")
        self.assertIsNone(Result().data)
