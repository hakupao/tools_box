# Phase 2 carry-over (rulings, parked findings, deferred minors)

Source: SDD ledger for docs/superpowers/plans/2026-10-29-dataforge-v3-phase2-file-tools.md. Phase 3 plan must start from the 'Final: parked' and 'Phase-3 notes' lines.

Ruling F: ToolPage (T6) gets class attribute `RETRY_MERGES: bool = True` and accessor `carried_result() -> Result | None`; when False the final result is the retry result only. FieldExtractPage (T7) sets False and, in build_retry_job, deletes `carried_result().outputs` (the first summary) before returning the full re-run job — cost if wrong: minor rework of retry API.
Ruling G: T8 updates T7's FILES-order test to [format_convert, sheet_split, field_extract] — cost if wrong: none.
Task 1: minor (deferred): watcher test racy/no-op assert; theme.py line 101 chars; late emit at interpreter shutdown only logged.
Task 1: minor (deferred): Theme(resolved) case-sensitive (darkdetect returns Dark/Light today); weak negative unchanged-theme test; relies on qconfig._cfg private.
Ruling: forced "utf-8" on BOM data resolves to "utf-8-sig" — protects header matching — cost if wrong: none.
Ruling: promote preview limits (split on \n, 200-char lines) into fix round — same function, protects dialog — cost if wrong: none.
Task 2: minor (deferred): no docstrings on writers; EncodingQuestion.previews mutable in frozen dataclass. Note for T4/T5 briefs: catch AmbiguousEncodingError before EncodingError.
Task 2: minor (deferred): README says "每行最多 200 字符" but clipped line shows 201 visible chars (… appended).
Ruling: a sheet that fails to read produces an error and no file (v2 wrote an empty CSV) — an empty file would look like a successful export of an empty sheet — cost if wrong: none.
Task 3: minor (deferred): no tests for Cancelled propagation/workbook close/failed-sheet continue; sheet_rows lacks type hint; date edge cases not in golden; wasted _n slot on failure.
Ruling: unquote quotes any field containing any candidate delimiter (, tab ; |) and warns the detected delimiter when not "," — lossless, robust to mis-sniff — cost if wrong: a few extra quotes.
Ruling: promote control-char error message and files/skipped stat semantics into the fix round — cheap and user-visible — cost if wrong: none.
Task 4: minor (deferred): `or"\r"` spacing / >100-char line in _format_field; test file formatting.
Task 5: minor (deferred): stats keys absent (not 0) when nothing read — UI must use .get; encodings keyed by str(src) built from folder — pages must key the same way.
Task 6: minor (deferred): build_retry_job returning None with answers drops questions silently; carried.warn("") renders leading colon; failed/cancelled retry records no recent entry; first-run log cleared on retry; no tests for retry fail/cancel/reject; whole OutputLocationField disabled (cosmetic); empty previews → answer ""; dialog buttons English (tr).
Ruling F amended: FieldExtractPage deletes the first summary INSIDE the retry job (after it starts), not in build_retry_job, and copies carried_result().warnings into the retry result — avoids losing the first summary if the retry never starts and keeps skip warnings — cost if wrong: none.
Ruling F amended again: retry never deletes first — run normally (new summary gets _1), then os.replace(new, old) after success; on OSError keep new + warning; cancel/failure leaves old untouched — cost if wrong: none (strictly safer).
Ruling: adopt product hardening — MainThreadGarbageCollector (gc.disable + 1 s main-thread QTimer, generation-aware, pyqtgraph pattern) started in app.main; conftest gc.collect after every test; deleteLater dialogs after exec — worker allocations make worker-thread GC inevitable, so GC must be pinned to the GUI thread — cost if wrong: slightly delayed garbage collection (≤1 s).
Ruling: never re-enable gc at exit (remove stop() from app.main) + defensive re-disable in check() — cost if wrong: none at process end.
Task 7: minor (deferred): test_app_main order assertion omits runner.shutdown; test_gc_guard restores gc to enabled unconditionally; older test files still leave pages to GC (conftest gc.collect covers).
Task 8: minor (deferred): restore_state drops mismatched-extension files silently; set_mode no lock guard; overwrite tick kept between BOM/unquote; hidden rows keep grid spacing.
Final review (750b897..778884d): With fixes — Important: detected encoding never logged (§6.2); forced "UTF-8 (BOM)" falsely skips non-BOM files; forced GBK/cp932 on BOM file corrupts header; dialog buttons English; retry double-counts stats; golden gaps + harness ignores encoding params.
Ruling: BOM always wins over a forced legacy encoding (→ utf-8-sig, with a warning note) — the bytes prove UTF-8 — cost if wrong: none.
Ruling: atomic temp files skipped by iter_input_files (names starting "." containing ".tmp") instead of changing temp suffix — keeps openpyxl/keep_vba format by extension — cost if wrong: a user file literally named ".x.tmp.csv" is ignored.
Ruling: fold must-fix minors into the single wave: recent entry for cancelled/failed retry when carried outputs exist; carried.warn("") colon; read-side PermissionError message; field_extract doc retry wording; README xlsx comparison wording; session-level gc guard in tests.
Final fix wave: commits 778884d..b364262 — all 12 ADDRESSED (re-review, probes clean). 279 passed x3.
Final: parked — declined encodings counted in neither files nor skipped; doc says "由重新处理计数" — Ruling: minor, carry to phase 3 (masking reuses retry flow) — cost if wrong: slightly off stats.
Final: parked — field_extract CSV read PermissionError falls to generic message; temp-file skip rule also skips ".tmpdata.csv"; golden overwrite_source path unexercised; long confirm lines — Ruling: minor, carry.
Phase-3 notes: cp932 Japanese files are practically always ambiguous → consider remembering the last ambiguity answer per session; move run-then-swap retry into a ToolPage helper; document "no gc.collect / no QObjects in job code".
