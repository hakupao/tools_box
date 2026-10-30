from __future__ import annotations

import unittest
from pathlib import Path

import dataforge

PKG = Path(dataforge.__file__).parent
BACKEND_DIRS = ("core", "fileio", "config", "tools")


class PackageTests(unittest.TestCase):
    def test_version(self) -> None:
        self.assertEqual(dataforge.__version__, "3.0.0")

    def test_backend_has_no_qt_imports(self) -> None:
        files = [p for d in BACKEND_DIRS for p in (PKG / d).glob("**/*.py")]
        dates = PKG / "dates.py"
        if dates.exists():
            files.append(dates)
        for path in files:
            text = path.read_text(encoding="utf-8")
            for banned in ("PySide6", "qfluentwidgets"):
                self.assertNotIn(banned, text, f"{path} imports {banned}")


if __name__ == "__main__":
    unittest.main()
