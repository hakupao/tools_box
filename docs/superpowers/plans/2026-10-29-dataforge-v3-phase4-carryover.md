# DataForge v3 · 阶段 4 裁定与遗留项

Source: SDD ledger for docs/superpowers/plans/2026-10-30-dataforge-v3-phase4-edc.md. Phase 5 plan must start from the 'Final: parked' and 'Phase-5 notes' lines.

Ruling R1: fake keyboard/mouse backends go into tests/dataforge/edc_fakes.py (created in T3, extended in T5) so T6/T7 can reuse them — plan says "reuse Task 5 fake backend" without a location — cost if wrong: none.
Ruling R2: T7 may add an optional `on_call: Callable[[str], None] | None` hook to FakePorts (called before each recorded action) for blocking/ESC tests; trace format unchanged — cost if wrong: none.
Task 1: minor (deferred): shutdown follow-up test may assert before queued busy_changed slot runs; mapping/report write OSError wrap untested; in-function imports in new tests; orders-kept test doesn't spy orders_changed.
Task 1: complete (commits dc1449f..77187b2, review clean)
Ruling: T2 smoke tests use a native win32 probe window instead of a QWidget — test suite runs Qt offscreen (tests/dataforge/__init__.py) so QWidgets have no HWND — cost if wrong: none.
Task 2: minor (deferred): stray blank line in test imports; activate_window outer except hides cause (no `from exc`); no success-path test for activate_window/window_at; probe window_at test could flake under another topmost window; config imports pywin32 via WindowInfo.
Task 2: complete (commits 77187b2..ca6166c, review clean)
Task 3: minor (deferred): fake "DataForgeError" exc is a synthetic class; pre-count runs before first cancel check; ESC during last row's step 11 → next segment stops on an empty cell and SKIP would record a blank row (doc or treat as empty); test _row_actions mirrors config; extra stats on segment Result.
Task 3: complete (commits ca6166c..0639743, review clean)
Task 4: minor (deferred): LiveExcel._app may outlive CoUninitialize if a traceback holds it (add close()); com_error on Selection access gives raw COM text; subprocess import test relies on inherited path.
Task 4: complete (commits 0639743..0651640, review clean)
Task 5: minor (deferred → carried to T7 dispatch): keep_log flag leaks if submit refused (T7 must reset on failed submit); queued ESC/click after stop() (T7 guard with running/is_active); get_position exception on hook thread uncaught; mouse test not cross-thread; no test that other tool's start keeps flag.
Task 5: complete (commits 0651640..c0beb0e, review clean)
Ruling: test_overlay_has_no_stylesheet skips qfluentwidgets widgets (they install their own theme QSS; the brief mandates Fluent buttons) and asserts our overlay/QLabel have none — plan test was unsatisfiable as written — cost if wrong: none.
Task 6: fix round 1 dispatched (FIX_BASE 6a1b649; includes picker selectedItems + button order assertion)
Task 6: fix round 1/5 (3 addressed, 0 open — start-delay hook leak, picker selectedItems, button order; commits 6a1b649..df3c6a0)
Task 6: minor (deferred): _start_mouse isVisible on deleted widget edge; picker selectedItems change has no dedicated test; no dpr-1.5 overlay ignore test; replay marker lifecycle undocumented.
Task 6: complete (commits c0beb0e..df3c6a0, review clean)
Ruling: ToolPage.submit_job clears the keep-log separator when runner.submit is refused (T7 scope) — closes T5's flag-leak minor at the source — cost if wrong: none.
Task 7: minor (deferred): second replay may drop/leak markers (no WA_DeleteOnClose); refused continuation leaves session without summary; esc stop after id guard (equivalent); controls briefly enabled between segments.
Task 7: complete (commits df3c6a0..4c5e93c, review clean)
Final review: dispatched over dc1449f..4c5e93c (a9047a8680200f821 opus); suite x3 running
Final review: ready with fixes — I1 run can start during recording (two ESC hooks → keyboard.unhook KeyError, leaked hook); I2 ESC during last row step 11 → stop on empty cell, SKIP records blank row; I3 stop dialog may sit behind browser + showNormal un-maximizes. Minors M1 ESC closes StopDialog as END; M2 COM proxies via traceback after CoUninitialize; M3 REDO row vanishes if continuation fails; M4 LL hooks persist for process life; M5 elevated browser process name "".
Ruling: one fix wave covers I1, I2 (+doc sentence), I3 (plan said showNormal; only restore if minimized, foreground via activate_window, restore pre-recording state), M1 (StopDialog ignores Escape — ESC is the stop key, a double press would silently END) — cheap and all hit acceptance step 5 — cost if wrong: none. M2, M3 parked; M4, M5 go to carry-over doc as known limitations.
Final fix wave: 2e3e55c (I1 I2 I3 M1) — 499 passed
Final re-review: I1 I2 I3 M1 all addressed, no new Crit/Imp. Residual minors: _restore_maximized stale if user un-maximizes during recording; real SetForegroundWindow unverified (manual acceptance); escape test overrides done().
Final: parked — M2 COM proxies via traceback after CoUninitialize; M3 REDO row vanishes from summary if continuation fails; all ledger minors per final triage — Ruling: minor, carry — cost if wrong: edge-case UX only.

Phase-5 notes: packaging must collect mouse._winmouse, the keyboard Windows backend (keyboard._winkeyboard), win32com/pythoncom/pywintypes, win32gui/win32process/win32api; keyboard and mouse install WH_KEYBOARD_LL/WH_MOUSE_LL hooks on first use and keep them for the process lifetime (handlers are run-scoped, OS hooks are not) — known limitation; an elevated browser yields process name "" (GetModuleFileNameEx needs PROCESS_VM_READ across integrity levels) so find_target rule 3 could match another unreadable process — consider QueryFullProcessImageName; v2 EDC code (src/gui/widgets/edc_*.py, src/utils/edc_site_adder_*.py) and v2 dependency pygetwindow are deleted in phase 5; the ESC hook does not swallow the key (same as v2).
Verification (controller, after final fix wave 2e3e55c): 499 passed, 97 subtests x2 (78.3 s, 65.0 s); a third run was stopped by the system for low memory, not a test failure; banned-pattern grep empty.
