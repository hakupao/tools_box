from __future__ import annotations

import importlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from dataforge import app
from dataforge.selfcheck import self_check
from dataforge.ui.resources import app_icon_path


class SelfCheckTests(unittest.TestCase):
    def test_self_check_passes_in_dev(self) -> None:
        # Imports pyautogui/keyboard/mouse: run in a subprocess so the test process stays clean.
        code = (
            "from dataforge.selfcheck import self_check; "
            "failures = self_check(); "
            "import sys; sys.stdout.write(repr(failures)); "
            "sys.exit(1 if failures else 0)"
        )
        result = subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True, timeout=120
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        # qfluentwidgets may print a "Tips" banner first; the result is the last line.
        self.assertEqual(result.stdout.strip().splitlines()[-1], "[]")

    def test_self_check_reports_failure(self) -> None:
        real_import = importlib.import_module
        loaded: list[str] = []

        def fake_import(name: str, package: str | None = None):
            loaded.append(name)
            if name == "pyautogui":
                raise ImportError("boom")
            if name in {"keyboard", "mouse", "pyperclip", "dataforge.tools.edc.live"}:
                return None  # keep input-hook libraries out of the test process
            return real_import(name, package)

        with mock.patch("importlib.import_module", side_effect=fake_import):
            failures = self_check()
        self.assertEqual(failures, ["pyautogui: boom"])
        self.assertIn("openpyxl", loaded)
        self.assertIn("win32com.client", loaded)
        self.assertIn("dataforge.ui.pages.edc.page", loaded)

    def test_app_icon_path_dev(self) -> None:
        path = app_icon_path()
        self.assertIsNotNone(path)
        self.assertTrue(path.is_file())
        self.assertEqual(path.name, "favicon.ico")

    def _run_main_self_check(self, failures: list[str]) -> tuple[int, str]:
        with (
            tempfile.TemporaryDirectory() as tmp,
            mock.patch.object(app, "setup_logging"),
            mock.patch.object(app, "default_log_dir", return_value=Path(tmp)),
            mock.patch.object(app, "self_check", return_value=failures),
            mock.patch.object(app, "QApplication") as qapp,
            mock.patch.object(app, "MainWindow") as window,
        ):
            code = app.main(["x", "--self-check"])
            text = (Path(tmp) / "self_check.txt").read_text(encoding="utf-8")
        qapp.assert_not_called()
        window.assert_not_called()
        return code, text

    def test_main_self_check_ok(self) -> None:
        code, text = self._run_main_self_check([])
        self.assertEqual(code, 0)
        self.assertEqual(text.strip(), "OK")

    def test_main_self_check_failure(self) -> None:
        with self.assertLogs("dataforge.app", level="ERROR"):
            code, text = self._run_main_self_check(["pyautogui: boom", "mouse: bad"])
        self.assertEqual(code, 1)
        self.assertEqual(text.splitlines(), ["pyautogui: boom", "mouse: bad"])

    def test_main_self_check_result_file_unwritable(self) -> None:
        with (
            tempfile.TemporaryDirectory() as tmp,
            mock.patch.object(app, "setup_logging"),
            mock.patch.object(app, "default_log_dir", return_value=Path(tmp)),
            mock.patch.object(app, "self_check", return_value=[]),
            mock.patch.object(Path, "write_text", side_effect=OSError("disk full")),
            self.assertLogs("dataforge.app", level="ERROR"),
        ):
            code = app.main(["x", "--self-check"])
        self.assertEqual(code, 1)

    def test_main_self_check_log_dir_unavailable(self) -> None:
        with (
            mock.patch.object(app, "setup_logging"),
            mock.patch.object(app, "default_log_dir", side_effect=OSError("denied")),
            mock.patch.object(app, "self_check", return_value=[]),
            self.assertLogs("dataforge.app", level="ERROR"),
        ):
            code = app.main(["x", "--self-check"])
        self.assertEqual(code, 1)

    def test_main_sets_window_icon(self) -> None:
        with (
            mock.patch.object(app, "setup_logging"),
            mock.patch.object(app, "QApplication") as qapp,
            mock.patch.object(app, "QIcon") as qicon,
            mock.patch.object(app, "MainThreadGarbageCollector"),
            mock.patch.object(app, "ConfigStore"),
            mock.patch.object(app, "apply_theme_mode"),
            mock.patch.object(app, "start_system_theme_listener"),
            mock.patch.object(app, "JobRunner"),
            mock.patch.object(app, "RecentStore"),
            mock.patch.object(app, "MainWindow"),
            mock.patch.object(app, "wait_for_orphans", return_value=True),
        ):
            qapp.return_value.exec.return_value = 0
            app.main(["x"])
        qicon.assert_called_once_with(str(app_icon_path()))
        qapp.return_value.setWindowIcon.assert_called_once_with(qicon.return_value)


if __name__ == "__main__":
    unittest.main()
