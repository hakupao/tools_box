import logging
import tempfile
import unittest
from pathlib import Path

from dataforge.core.logs import default_log_dir, setup_logging


class LogsTests(unittest.TestCase):
    def test_default_log_dir_is_path(self):
        self.assertIsInstance(default_log_dir(), Path)

    def test_setup_logging_writes_file(self):
        root = logging.getLogger("dataforge")
        old_level = root.level
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            try:
                path = setup_logging(tmp)
                setup_logging(tmp)
                logging.getLogger("dataforge.x").info("hello")
                for h in root.handlers:
                    h.flush()
                self.assertEqual(path, tmp / "dataforge.log")
                self.assertTrue(path.exists())
                self.assertEqual(path.read_text(encoding="utf-8").count("hello"), 1)
            finally:
                for h in list(root.handlers):
                    root.removeHandler(h)
                    h.close()
                root.setLevel(old_level)


if __name__ == "__main__":
    unittest.main()
