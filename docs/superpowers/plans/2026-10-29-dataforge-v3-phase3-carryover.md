# DataForge v3 · 阶段 3 裁定与遗留项

Source: SDD ledger for docs/superpowers/plans/2026-10-29-dataforge-v3-phase3-masking.md. Phase 4 plan must start from the 'Final: parked' and 'Phase-4 notes' lines.

Ruling P1: T5 extends assert_dirs_equal to byte-compare .json (and README comparison rules) — plan requires byte comparison of report JSON — cost if wrong: none.
Ruling P2: describe_plan line 1 k = min(subject_limit, len(subjects)) — matches execution rule 2 — cost if wrong: wording only.
Ruling: carry-over doc sentence fixed in docs/tools/format_convert.md (where it actually lived) instead of README — plan named wrong file — cost if wrong: none.
Task 1: minor (deferred): encoding_dialog factory annotation line >100 chars; uneven blank lines; mock.patch continuation formatting in test_tool_page.
Task 1: complete (commits bf734a3..e23665b, review clean)
Task 2: minor (deferred): _coerce_bool duplicated from v2 (intentional, v2 deleted in phase 5); overlapping candidate tests; root-level legacy returns whole root incl. other sections (from_dict filters).
Task 2: complete (commits e23665b..28bee44, review clean)
Ruling: tighten time suffix — after the date the remainder must fully match ^([T ]\d{1,2}:\d{1,2}(:\d{1,2}(\.\d+)?)?)?(Z|[+-]\d{2}:?\d{2})?$ else UNPARSED — verbatim kept suffix could carry real text/dates unshifted (privacy); v2 truncated instead — cost if wrong: odd-suffix values reported unparsed (warned, kept) instead of shifted.
Task 3: minor (deferred): slash dates with time ("25/03/2024 10:30") unparsed by design; duplicate slash parsing in parse_mask_date.
Ruling: date+timezone without time (2024-06-15+09:00) accepted as SHIFTED — follows the round-1 grammar (tz is not personal data) — cost if wrong: none.
Task 3: minor (deferred): \d matches non-ASCII digits (should be [0-9] for language-neutral port); time values not range-checked; slash_kind duplicates readings logic; test-loop special case for 9999.
Task 3: complete (commits 28bee44..28df38b, review clean)
Task 4: minor (deferred): files that fail to read / lack USUBJID have no FileScan row — Task 7 table shows them only via errors; test_basic_report overrides min_non_empty; DM count includes failed files (comment).
Task 4: minor (deferred): csv.Error test doesn't assert DM still scanned.
Task 4: complete (commits 28df38b..5058090, review clean)
Ruling: execute.run catches BaseException only to delete the temp folder and re-raises (same as atomic_path) — the "never catch BaseException" rule targets swallowing Cancelled — cost if wrong: none.
Ruling: export_report gains optional date_orders kwarg (scan.py outside task file list) — reuses one JSON writer per P1/plan — cost if wrong: none.
Ruling: promote privacy minors to fix round — (a) SUBJID/STUDYID/doctor/site/age apply to EVERY case-insensitively matching column, (b) duplicate USUBJID column → DataForgeError at execute, (c) masking.md warns mapping+report hold original IDs and must not be shared with masked domains, (d) README notes cleanup-and-reraise is the sanctioned BaseException exception — duplicate columns could leak doctor names — cost if wrong: none.
Task 5: minor (deferred): folder-name race raw OSError; parent mkdir outside try; test compares to_dict from code; golden adapter ignores warnings; describe_plan k=0 cosmetic.
Task 5: minor (deferred): core/errors.py Cancelled docstring still says "never catch BaseException" (conflicts with README exception).
Task 5: complete (commits 5058090..2750ba6, review clean)
Task 6: minor (deferred): aux started during pending run retry would drop carry (unreachable while locked); aux fail/cancel tests don't assert success InfoBar absent.
Task 6: complete (commits 2750ba6..ba6873f, review clean)
Ruling: automatic re-scan uses submit_job_when_idle instead of the plan's QTimer.singleShot — Task 6 showed the runner is still busy in the hook — cost if wrong: none.
Task 7: complete (commits ba6873f..f8bdcf2, review clean)
Final review: dispatched over bf734a3..f8bdcf2 (aa8d3d855e15ba23b opus)
Final review: ready with fixes — Important I1 reserved mapping name overwrite, I2 hour-only SDTM times leak; minors M1-M8; ledger minors all deferrable.
Ruling: one fix wave covers I1, I2, M1 (keep Unicode digits, document), M2, M3, M4, M5, M6, M8, add encoding-rescan-then-execute page test, JobRunner _closing guard — cheap and port/privacy relevant — cost if wrong: none. M7 (duplicate same-name ambiguous columns share one order key) stays deferred.
Final fix wave: 4987023 (11 items) — 401 passed x3
Final re-review: all 11 addressed, no new Crit/Imp. Residual minors: shutdown follow-up shows misleading InfoBar on exit; M8 substring detection; mask_file write OSError not wrapped.
Final: parked — M7 duplicate same-name ambiguous date columns share one order key (last choice wins); exit-time follow-up job shows misleading '已有任务正在运行' InfoBar; M8 rescan detection by message substring; execute write-side OSError not wrapped as DataForgeError; page duplicates scan()'s path filter (expose one select_files()); 恢复默认值 gives no feedback; date orders dropped on rescan — Ruling: minor, carry — cost if wrong: cosmetic/UX only.
Phase-4 notes: EDC reuses dataforge.config.legacy (load_section_with_legacy, legacy_file_candidates with extra dir src/gui/widgets) for edc_site_adder; use ToolPage.submit_job_when_idle for any follow-up job; JobRunner refuses submit after shutdown(); BaseException may be caught only to clean up and re-raise.
