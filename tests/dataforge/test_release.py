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


    def test_version_consistent(self):
        import dataforge

        self.assertEqual(dataforge.__version__, "3.0.0")
        text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), "3.0.0")
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn("## [3.0.0]", changelog)

    def test_spec_has_no_removed_imports(self):
        spec = (ROOT / "packaging/pyinstaller/tools_box_onedir.spec").read_text(encoding="utf-8")
        # Names may appear only in the ``excludes=[...]`` list (e.g. pandas is excluded).
        spec = re.sub(r"excludes=\[.*?\]", "", spec, flags=re.DOTALL)
        for banned in ("tkinterdnd2", "pygetwindow", "requests", "bs4", "pandas", "src/main.py"):
            self.assertNotIn(banned, spec)

    def test_docs_not_stale(self):
        self.maxDiff = None
        stale = ("src/main.py", "src/utils", "src/gui", "tkinterdnd2", "pandas", "processEvents")
        exempt = ("禁止", "不用", "不得", "不再", "移除")
        paths = [ROOT / "README.md", ROOT / "AGENTS.md", ROOT / "packaging/README.md"]
        paths += sorted((ROOT / "docs").glob("*.md"))
        hits = []
        for path in paths:
            lines = path.read_text(encoding="utf-8").splitlines()
            for lineno, line in enumerate(lines, 1):
                if any(word in line for word in exempt):
                    continue
                for term in stale:
                    if term in line:
                        hits.append(f"{path.relative_to(ROOT)}:{lineno}: {term}")
        self.assertEqual(hits, [])

    def test_installer_keeps_side_files(self):
        text = (ROOT / "packaging/installer/tools_box.iss").read_text(encoding="utf-8")
        match = re.search(r"^\[InstallDelete\]\s*$(.*?)(?=^\[|\Z)", text, re.MULTILINE | re.DOTALL)
        self.assertIsNotNone(match)
        section = match.group(1)
        self.assertNotIn(r"{app}\*", section)
        self.assertIn(r"{app}\_internal", section)


if __name__ == "__main__":
    unittest.main()
