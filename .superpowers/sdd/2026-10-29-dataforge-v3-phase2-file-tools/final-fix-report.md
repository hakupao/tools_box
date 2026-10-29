# Phase 2 final-review fixes

RED run (new tests added first, before any source change): 16 failed / 252 passed. GREEN: 279 passed (+47 subtests).

1. Encoding log: `read_text` logs `<name>: 编码 <enc>（自动识别|手动指定）`. Test: test_text_io.test_read_text_logs_encoding (assertLogs). RED: failed (no log); GREEN.
2. Already-BOM check: `EncodingDecision.had_bom` (from bytes); format_convert uses it. Tests: test_encoding.test_had_bom_flag, test_format_convert.test_forced_utf8_sig_on_plain_file_converts / test_bom_file_is_skipped_with_warning. RED: failed; GREEN.
3. BOM wins over forced gbk/cp932 -> `utf-8-sig` + note. Tests: test_encoding.test_forced_legacy_encoding_on_bom_file_is_overridden (gbk, cp932 subtests), test_format_convert.test_forced_gbk_on_bom_file_warns_and_skips. RED: failed; GREEN.
4. `FluentTranslator(QLocale("zh_CN"))` installed in app.main (reference kept until return); `use_chinese_buttons()` (ui/components/confirm.py) applied to the 3 MessageBox confirmations; EncodingChoiceDialog sets 确定/取消. Tests: test_app_main.test_fluent_translator_installed_and_kept_alive, test_components_phase2 dialog + confirm button-text tests. RED: failed; GREEN.
5. Stats: questioned files no longer counted skipped. Test: test_questioned_files_are_not_counted_as_skipped (first {files:1}, after extend {files:2}); old test_stats_files_and_skipped updated (skipped 2 -> 1, the ambiguous file is no longer counted). RED/GREEN.
6. Golden: format_convert xlsx_to_csv_first, csv_unquote_semicolon, csv_to_bom_already (no expected/ dir; `_list_files` treats absent dir as empty), csv_to_bom_ambiguous_chosen; field_extract stale_summary. Harness reads encoding / encodings (input-relative keys mapped to copied absolute paths) / overwrite_source (rewritten inputs copied to the output dir for diffing). README documents xlsx value+data_type+number_format, empty expected, and the params.json keys. make_fixtures extended (literals only). RED: ambiguous_chosen failed before the harness change; GREEN. test_golden count 4 -> 8.
7. ToolPage: failed/cancelled retry with carried outputs shows carried result and emits run_succeeded once with first-submit snapshot. Tests: test_cancelled_retry_..., test_failed_retry_... RED/GREEN.
8. ResultPanel omits "path: " when path is empty. Test: test_result_panel_omits_empty_path_prefix. RED/GREEN.
9. PermissionError reading source -> "无法读取文件（可能已被其他程序打开）"; write message unchanged. Test: test_read_permission_error_message (+ existing write test). RED/GREEN.
10. iter_input_files skips names starting with "." containing ".tmp". Test: test_paths.test_iter_skips_atomic_temp_files. RED/GREEN.
11. field_extract.md retry wording updated (also README encoding rules, format_convert.md notes).
12. conftest: session-scoped autouse fixture disables gc (restores prior state at end), per-test gc.collect kept; test_gc_guard restores prior gc state via cleanup (closure keeps guard alive so its QTimer is not deleted early).

Full suite (`python -m pytest tests -q`): run1 279 passed 45.6s; run2 279 passed 50.5s; run3 see below.
run3 279 passed 70.2s (all under 180 s).
