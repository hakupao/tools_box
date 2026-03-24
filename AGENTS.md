# Agent Guide for This Repository

## Purpose
- This file is for coding agents working in `tools_box`.
- Prefer small, targeted changes that match existing patterns.
- Keep behavior stable unless the task explicitly asks for behavior changes.

## Project Snapshot
- Stack: Python desktop app (`PySide6` + `QFluentWidgets`) with pandas-based processing services.
- Entry point: `src/main.py`.
- UI shell and page registry: `src/gui/main_window.py`.
- Business logic: `src/utils/*_service.py`.
- Tests: `tests/` (`unittest` style, pytest-compatible).
- Current release baseline: `v2.0.1` (2026-03-24), with unified `spec_workflow_page.py` replacing separate DataSet/DataCleaner/Codelist pages.

## Environment Setup
- Python `3.11` is confirmed working here.
- Create and activate a venv (Windows):
```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```
- Run app in dev mode:
```bash
python src/main.py
```

## Build Commands
- Recommended onedir build:
```powershell
powershell -ExecutionPolicy Bypass -File .\packaging\scripts\build_onedir.ps1 -Clean
```
- Build installer (requires Inno Setup 6 / `ISCC.exe`):
```powershell
powershell -ExecutionPolicy Bypass -File .\packaging\scripts\build_installer.ps1 -Clean
```
- Measure startup baseline vs candidate:
```powershell
powershell -ExecutionPolicy Bypass -File .\packaging\scripts\measure_startup.ps1
```

## Test Commands
- Full suite with unittest discovery:
```bash
python -m unittest discover -s tests
```
- Full suite with pytest:
```bash
python -m pytest tests -q
```
- Single test file:
```bash
python -m unittest tests.test_data_masking_service
python -m pytest tests/test_data_masking_service.py -q
```
- Single test method (preferred quick validation command):
```bash
python -m unittest tests.test_data_masking_service.DataMaskingServicePattern1Tests.test_pattern1_default_infer_and_iso_output
python -m pytest tests/test_data_masking_service.py::DataMaskingServicePattern1Tests::test_pattern1_default_infer_and_iso_output -q
```

## Lint and Formatting
- No checked-in lint/format config exists (`pyproject.toml`, `setup.cfg`, `ruff.toml` not present).
- Project docs mention `black`, `flake8`, `isort`; they are optional and may need manual install.
- Install optional tools:
```bash
pip install black flake8 isort
```
- Suggested commands (`line-length = 100`):
```bash
python -m black src tests --line-length 100
python -m isort src tests
python -m flake8 src tests --max-line-length=100
```

## Architecture Boundaries
- Keep UI interaction/state wiring in `src/gui/widgets/*_page.py`.
- Keep data/business transformations in `src/utils/*_service.py`.
- Reuse `src/gui/qt_common.py` wrappers for dialogs and file pickers.

## Code Style Guidelines

### Imports
- Use order: stdlib, third-party, local imports; separate groups with one blank line.
- If used, keep `from __future__ import annotations` as the first import.
- Prefer absolute `src...` imports in UI modules; utility modules may use relative imports.

### Formatting
- Use 4-space indentation.
- Keep line length around 100 characters.
- Do not mass-reformat untouched legacy files; limit churn to edited regions.

### Types
- Add explicit type hints on new/changed public functions.
- In modernized modules, prefer built-in generics (`list[str]`, `dict[str, Any]`) and `|` unions.

### Naming
- Classes: `PascalCase`.
- Functions/methods/variables: `snake_case`.
- Constants: `UPPER_CASE`.
- Qt page classes use `<ToolName>Page`; services use `<ToolName>Service`.

### Data and Encoding
- Preserve existing CSV/Excel conventions:
  - Read with `dtype=str` and usually `na_filter=False`.
  - Write CSV with `encoding="utf-8-sig"`.
- Do not silently change delimiter/encoding behavior.

### Error Handling
- Match the local module pattern:
  - Some services return `(success: bool, message: str)`.
  - Newer services may raise `ValueError` for invalid input and return structured data otherwise.
- In UI pages, catch exceptions at action boundaries and show user-facing messages.

### UI and Interaction
- Prefer `qt_common.py` helper APIs over direct static `QFileDialog.get*` calls.
- Reuse `FileListWidget` for drag-and-drop file lists.
- Keep light-theme patterns consistent with existing pages and avoid UI freezes.

### Config Persistence
- Shared config helpers are in `src/utils/app_config.py`.
- Store service data under section keys (for example `CONFIG_SECTION` constants).
- Preserve unrelated config sections when saving.

### Tests
- Add tests under `tests/test_<feature>.py`.
- Follow current `unittest.TestCase` style for consistency.
- Use temp directories/files for IO-heavy tests.
- Assert on concrete outputs (files/content), not only success flags.

## Rule Files (Cursor / Copilot)
- Checked locations:
  - `.cursor/rules/`
  - `.cursorrules`
  - `.github/copilot-instructions.md`
- Result: none of these files currently exist in this repository.
- If these files are added later, treat them as higher-priority instructions.

## Agent Working Agreements
- Do not move business logic into UI handlers if it can live in a service.
- Do not introduce heavy dependencies without a clear reason.
- Prefer backward-compatible changes to file formats and config schema.
- Before finishing, run the most relevant targeted test.

## Quick Pre-Submit Checklist
- Touched code runs for the changed path.
- Relevant test(s) pass (single-test command is acceptable for small edits).
- Encoding-sensitive output behavior is unchanged unless intentional.
- New UI actions show actionable success/error feedback.
