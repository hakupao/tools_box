import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SELF = Path(__file__).resolve()
V2_IMPORT = re.compile(r"\bsrc\.(gui|utils)\b|^\s*from utils\b", re.MULTILINE)


class ReleaseTests(unittest.TestCase):
    def test_no_v2_tree(self):
        for rel in ("src/gui", "src/utils", "src/main.py", "src/version.py"):
            self.assertFalse((ROOT / rel).exists(), rel)
        hits = []
        for base in ("src", "tests"):
            for path in (ROOT / base).rglob("*.py"):
                if path.resolve() == SELF or ".venv" in path.parts:
                    continue
                if V2_IMPORT.search(path.read_text(encoding="utf-8")):
                    hits.append(str(path.relative_to(ROOT)))
        self.assertEqual(hits, [])

    def test_requirements(self):
        text = (ROOT / "requirements.txt").read_text(encoding="utf-8").lower()
        names = {
            re.split(r"[<>=!~\s\[;]", line, maxsplit=1)[0]
            for line in text.splitlines()
            if line.strip() and not line.startswith("#")
        }
        for banned in (
            "pygetwindow",
            "pyqtgraph",
            "tkinterdnd2",
            "requests",
            "beautifulsoup4",
            "pandas",
            "numpy",
        ):
            self.assertNotIn(banned, names)
        self.assertIn("mouse==0.7.1", text.split())
        self.assertIn("darkdetect", names)


if __name__ == "__main__":
    unittest.main()
