import tempfile
import unittest
from pathlib import Path

from dataforge.core.errors import Cancelled
from dataforge.fileio.atomic import atomic_path
from dataforge.fileio.text_io import read_text, write_csv_rows, write_text


class TextIoTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)

    def test_read_text_keeps_crlf(self):
        p = self.dir / "a.txt"
        p.write_bytes(b"a\r\nb\r\n")
        text, decision = read_text(p)
        self.assertEqual(text, "a\r\nb\r\n")
        self.assertEqual(decision.encoding, "utf-8")

    def test_read_text_forced_encoding(self):
        p = self.dir / "a.txt"
        p.write_bytes("张伟".encode("gbk"))
        self.assertEqual(read_text(p, "gbk")[0], "张伟")

    def test_write_csv_rows_bom_and_crlf(self):
        p = self.dir / "o.csv"
        write_csv_rows([["a", "b,c"], ["1", ""]], p)
        self.assertEqual(p.read_bytes(), b'\xef\xbb\xbfa,"b,c"\r\n1,\r\n')

    def test_write_text_bom(self):
        p = self.dir / "o.txt"
        write_text("a\r\nb", p)
        self.assertEqual(p.read_bytes(), b"\xef\xbb\xbfa\r\nb")

    def test_atomic_path_cleans_up_on_error(self):
        t = self.dir / "x.csv"
        with self.assertRaises(RuntimeError):
            with atomic_path(t) as tmp:
                tmp.write_text("half")
                raise RuntimeError("boom")
        self.assertFalse(t.exists())
        self.assertEqual(list(self.dir.iterdir()), [])

    def test_atomic_path_cleans_up_on_cancelled(self):
        t = self.dir / "x.csv"
        with self.assertRaises(Cancelled):
            with atomic_path(t) as tmp:
                tmp.write_text("half")
                raise Cancelled()
        self.assertFalse(t.exists())
        self.assertEqual(list(self.dir.iterdir()), [])

    def test_atomic_path_success_keeps_suffix(self):
        t = self.dir / "x.csv"
        with atomic_path(t) as tmp:
            self.assertEqual(tmp.suffix, ".csv")
            self.assertEqual(tmp.parent, t.parent)
            tmp.write_text("ok")
        self.assertEqual(t.read_text(), "ok")
        self.assertEqual(list(self.dir.iterdir()), [t])
