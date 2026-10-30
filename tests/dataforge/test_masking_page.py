from __future__ import annotations

import csv
import io
import json
import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from tests.dataforge.qt_helpers import drain_deleted, qapp, wait_until

PAGE = "dataforge.ui.pages.masking.page"

DM_TEXT = (
    "USUBJID,SUBJID,STUDYID,INVNAM,SITEID,AGE,DMDTC\n"
    "S1,S1,OLD,Doctor-A,Site-01,45,2024-05-01\n"
    "S2,S2,OLD,Doctor-B,Site-02,30,2024-05-02\n"
)
AE_TEXT = (
    "USUBJID,SUBJID,STUDYID,AESTDTC\n"
    "S1,S1,OLD,2024-06-15\n"
    "S2,S2,OLD,2024-07-01\n"
)
AE_AMBIGUOUS_TEXT = (
    "USUBJID,AESTDTC\n"
    "S1,03/04/2024\n"
    "S2,05/06/2024\n"
)


def _rows(path: Path) -> list[dict[str, str]]:
    text = path.read_bytes().decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(text, newline="")))


class MaskingPageTests(unittest.TestCase):
    def setUp(self) -> None:
        from dataforge.config.store import ConfigStore
        from dataforge.ui.jobs import JobRunner

        qapp()
        self.runner = JobRunner()
        self._pages: list = []
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.cfg_path = self.dir / "config.json"
        self.config = ConfigStore(self.cfg_path)
        self.out = self.dir / "out"
        legacy = mock.patch(f"{PAGE}.legacy_file_candidates", return_value=[])
        legacy.start()
        self.addCleanup(legacy.stop)
        self.bar = mock.patch(f"{PAGE}.InfoBar").start()
        self.tool_bar = mock.patch("dataforge.ui.components.tool_page.InfoBar").start()
        self.addCleanup(mock.patch.stopall)

    def tearDown(self) -> None:
        wait_until(lambda: not self.runner.is_busy())
        self.runner.shutdown()
        self.runner.dispose()
        for page in self._pages:
            page.close()
        drain_deleted(*self._pages, self.runner)
        self._tmp.cleanup()

    # -- helpers -------------------------------------------------------------
    def _page(self):
        from dataforge.ui.pages.masking.page import MaskingPage
        from dataforge.ui.registry import get_tool

        page = MaskingPage(get_tool("masking"), self.runner, config=self.config)
        page.output_field.set_output_dir(self.out)
        self._pages.append(page)
        return page

    def _write(self, name: str, text: str, encoding: str = "utf-8-sig") -> Path:
        path = self.dir / name
        path.write_bytes(text.encode(encoding))
        return path

    def _text(self, page) -> str:
        return page.run_bar.primary_button().text()

    def _click_and_wait(self, page, until) -> None:
        page.run_bar.start_requested.emit()
        wait_until(until)
        wait_until(lambda: not self.runner.is_busy())

    def _scan(self, page) -> None:
        self._click_and_wait(page, lambda: page._report is not None)

    def _outputs(self) -> list[Path]:
        return sorted(self.out.glob("masked_output_*")) if self.out.exists() else []

    def _warning_titles(self) -> list[str]:
        return [c.args[0] for c in self.bar.warning.call_args_list]

    # -- tests ---------------------------------------------------------------
    def test_registered_in_business_group(self) -> None:
        from qfluentwidgets import FluentIcon

        from dataforge.ui.registry import ToolGroup, get_tool, load_page_class

        spec = get_tool("masking")
        self.assertIs(spec.group, ToolGroup.BUSINESS)
        self.assertIs(spec.icon, FluentIcon.HIDE)
        self.assertEqual(spec.name, "数据模糊化")
        self.assertEqual(spec.description, "SDTM Pattern1：扫描 → 配置 → 执行")
        cls = load_page_class(spec)
        self.assertEqual(cls.__name__, "MaskingPage")
        self.assertTrue(cls.USES_CONFIG)

    def test_build_job_requires_files(self) -> None:
        page = self._page()
        self.assertIsNone(page.build_job())
        self.bar.warning.assert_called_once()
        self.assertEqual(self.bar.warning.call_args.args[:2], ("请先添加文件", "请先添加 SDTM CSV 文件"))

    def test_scan_then_execute(self) -> None:
        dm = self._write("DM.csv", DM_TEXT)
        ae = self._write("AE.csv", AE_TEXT)
        page = self._page()
        succeeded: list = []
        page.run_succeeded.connect(lambda s, st: succeeded.append((s, st)))
        self.assertEqual(page.view.status_text(), "尚未扫描")
        self.assertEqual(page.summary_lines(), ["扫描通过后显示"])
        page.file_input.set_files([dm, ae])
        self.assertEqual(self._text(page), "开始扫描")
        self.assertEqual(page.current_job_kind(), "scan")

        self._scan(page)
        self.assertEqual(self._text(page), "开始处理")
        self.assertEqual(page.current_job_kind(), "run")
        self.assertIn("SUBJID 列将被清空", page.summary_lines())
        self.assertEqual(page.view.status_text(), "扫描通过：2 个文件，DM 受试者 2 个")
        self.assertEqual(page.view.table.rowCount(), 2)
        self.assertEqual(page.profile_form.preview_text(), "DM 首条 USUBJID：S1 → TEST0001")
        self.assertEqual(succeeded, [])
        self.assertEqual(self.bar.success.call_args.args[0], "扫描通过")

        self._click_and_wait(page, lambda: succeeded != [])
        folders = self._outputs()
        self.assertEqual(len(folders), 1)
        dm_rows = _rows(folders[0] / "DM.csv")
        self.assertEqual([r["USUBJID"] for r in dm_rows], ["TEST0001", "TEST0002"])
        self.assertEqual([r["SUBJID"] for r in dm_rows], ["", ""])
        self.assertEqual(len(succeeded), 1)
        summary, state = succeeded[0]
        self.assertEqual(summary, "2 个 CSV")
        self.assertEqual(state["files"], [str(dm), str(ae)])
        self.assertEqual(state["output_dir"], str(self.out))
        saved = json.loads(self.cfg_path.read_text(encoding="utf-8"))
        self.assertIn("data_masking_pattern1", saved)
        self.assertEqual(self._text(page), "开始处理")

    def test_file_change_invalidates_scan(self) -> None:
        dm = self._write("DM.csv", DM_TEXT)
        ae = self._write("AE.csv", AE_TEXT)
        extra = self._write("LB.csv", AE_TEXT)
        page = self._page()
        page.file_input.set_files([dm, ae])
        self._scan(page)
        self.assertEqual(self._text(page), "开始处理")
        page.file_input.add_paths([extra])
        self.assertEqual(self._text(page), "开始扫描")
        self.assertIsNone(page._report)
        self.assertEqual(page.view.status_text(), "尚未扫描")
        self.assertEqual(page.summary_lines(), ["扫描通过后显示"])

    def test_scan_setting_change_invalidates_scan(self) -> None:
        dm = self._write("DM.csv", DM_TEXT)
        page = self._page()
        page.file_input.set_files([dm])
        self._scan(page)
        self.assertEqual(self._text(page), "开始处理")
        page.profile_form.sample_spin.setValue(300)
        self.assertEqual(self._text(page), "开始扫描")
        self._scan(page)
        page.encoding_field.set_encoding("cp932")
        self.assertEqual(self._text(page), "开始扫描")

    def test_other_profile_change_keeps_scan(self) -> None:
        dm = self._write("DM.csv", DM_TEXT)
        page = self._page()
        page.file_input.set_files([dm])
        self._scan(page)
        page.profile_form.studyid_edit.setText("NEW-STUDY")
        self.assertEqual(self._text(page), "开始处理")
        self.assertIn("STUDYID：全部改为 NEW-STUDY", page.summary_lines())
        page.profile_form.prefix_edit.setText("ABC")
        self.assertEqual(page.profile_form.preview_text(), "DM 首条 USUBJID：S1 → ABC0001")

    def test_modified_file_requires_rescan(self) -> None:
        dm = self._write("DM.csv", DM_TEXT)
        ae = self._write("AE.csv", AE_TEXT)
        page = self._page()
        page.file_input.set_files([dm, ae])
        self._scan(page)
        st = ae.stat()
        os.utime(ae, ns=(st.st_atime_ns, st.st_mtime_ns + 5_000_000_000))
        with mock.patch.object(page.runner, "submit", wraps=page.runner.submit) as submit:
            page.run_bar.start_requested.emit()
        submit.assert_not_called()
        self.assertEqual(self._warning_titles(), ["需要重新扫描"])
        self.assertEqual(self.bar.warning.call_args.args[1], "文件或扫描设置已变化，请重新扫描")
        self.assertEqual(self._text(page), "开始扫描")
        self.assertIsNone(page._report)
        self.assertEqual(self._outputs(), [])

    def test_ambiguous_order_required(self) -> None:
        from dataforge.dates import SlashOrder

        dm = self._write("DM.csv", DM_TEXT)
        ae = self._write("AE.csv", AE_AMBIGUOUS_TEXT)
        page = self._page()
        page.file_input.set_files([dm, ae])
        self._scan(page)
        self.assertEqual(len(page.view.order_combos()), 1)
        label, combo = page.view.order_combos()[0]
        self.assertEqual(label, "AE.csv · AESTDTC（2 个无法判断）")
        self.assertEqual(
            [combo.itemText(i) for i in range(combo.count())], ["请选择", "日/月/年", "月/日/年"]
        )
        self.assertIn("还有 1 个日期列需要选择 日/月 顺序", page.summary_lines())

        page.run_bar.start_requested.emit()
        self.assertFalse(self.runner.is_busy())
        self.assertEqual(self._warning_titles(), ["请选择日期顺序"])
        self.assertEqual(
            self.bar.warning.call_args.args[1], "还有 1 个日期列需要选择 日/月 顺序"
        )

        combo.setCurrentIndex(1)
        self.assertEqual(page.view.orders(), {("AE.csv", "AESTDTC"): SlashOrder.DAY_FIRST})
        self.assertNotIn("还有 1 个日期列需要选择 日/月 顺序", page.summary_lines())
        self._click_and_wait(page, lambda: self._outputs() != [])
        ae_rows = _rows(self._outputs()[0] / "AE.csv")
        self.assertEqual(ae_rows[0]["AESTDTC"], "2022-04-03")

    def test_encoding_question_triggers_full_rescan(self) -> None:
        dm = self._write("DM.csv", DM_TEXT)
        ae = self._write("AE.csv", "USUBJID,AETERM\nS1,テスト医師\n", encoding="cp932")
        page = self._page()
        page.file_input.set_files([dm, ae])
        with mock.patch(f"{PAGE}.ask_encodings", return_value={str(ae): "cp932"}) as ask:
            page.run_bar.start_requested.emit()
            wait_until(lambda: self._text(page) == "开始处理")
            wait_until(lambda: not self.runner.is_busy())
        ask.assert_called_once()
        report = page._report
        self.assertTrue(report.processable)
        by_name = {f.file_name: f for f in report.files}
        self.assertEqual(by_name["AE.csv"].encoding, "cp932")
        self.assertEqual(page._encodings, {str(ae): "cp932"})

    def test_execute_after_encoding_rescan_when_runner_already_idle(self) -> None:
        dm = self._write("DM.csv", DM_TEXT)
        ae = self._write("AE.csv", "USUBJID,AETERM\nS1,テスト医師\n", encoding="cp932")
        page = self._page()
        page.file_input.set_files([dm, ae])

        def ask(parent, questions):
            # Like the modal dialog's nested event loop: the scan worker is released
            # meanwhile, so the rescan takes submit_job_when_idle()'s immediate branch.
            wait_until(lambda: not self.runner.is_busy())
            return {str(ae): "cp932"}

        with mock.patch(f"{PAGE}.ask_encodings", side_effect=ask) as asked:
            page.run_bar.start_requested.emit()
            wait_until(lambda: self._text(page) == "开始处理")
            wait_until(lambda: not self.runner.is_busy())
        asked.assert_called_once()
        succeeded: list = []
        page.run_succeeded.connect(lambda s, st: succeeded.append(s))
        self._click_and_wait(page, lambda: succeeded != [])
        folders = self._outputs()
        self.assertEqual(len(folders), 1)
        rows = _rows(folders[0] / "AE.csv")
        self.assertEqual([(r["USUBJID"], r["AETERM"]) for r in rows], [("TEST0001", "テスト医師")])

    def test_execute_failure_asking_for_rescan_discards_report(self) -> None:
        from dataforge.core.errors import DataForgeError
        from dataforge.tools.masking.execute import StaleScanError

        dm = self._write("DM.csv", DM_TEXT)
        ae = self._write("AE.csv", AE_TEXT)
        page = self._page()
        page.file_input.set_files([dm, ae])
        self._scan(page)
        self.assertEqual(self._text(page), "开始处理")

        other = DataForgeError("无法创建输出文件夹（x）")
        with mock.patch(f"{PAGE}.execute.run", side_effect=other):
            page.run_bar.start_requested.emit()
            wait_until(lambda: self.tool_bar.error.called)
            wait_until(lambda: not self.runner.is_busy())
        self.assertIsNotNone(page._report)
        self.assertEqual(self._text(page), "开始处理")

        self.tool_bar.error.reset_mock()
        stale = StaleScanError("AE.csv：读取失败，请重新扫描（x）")
        with mock.patch(f"{PAGE}.execute.run", side_effect=stale):
            page.run_bar.start_requested.emit()
            wait_until(lambda: self.tool_bar.error.called)
            wait_until(lambda: not self.runner.is_busy())
        self.assertEqual(self.tool_bar.error.call_args.args[1], str(stale))
        self.assertIsNone(page._report)
        self.assertEqual(self._text(page), "开始扫描")
        self.assertEqual(page.summary_lines(), ["扫描通过后显示"])

    def test_stale_detected_by_type(self) -> None:
        from dataforge.tools.masking.execute import StaleScanError

        dm = self._write("DM.csv", DM_TEXT)
        ae = self._write("AE.csv", AE_TEXT)
        page = self._page()
        page.file_input.set_files([dm, ae])
        self._scan(page)
        self.assertEqual(self._text(page), "开始处理")
        with mock.patch(f"{PAGE}.execute.run", side_effect=StaleScanError("x")):
            page.run_bar.start_requested.emit()
            wait_until(lambda: self.tool_bar.error.called)
            wait_until(lambda: not self.runner.is_busy())
        self.assertIsNone(page._report)
        self.assertEqual(self._text(page), "开始扫描")

    def test_restore_defaults_feedback(self) -> None:
        page = self._page()
        page.restore_defaults_button.click()
        self.bar.success.assert_called_once()
        self.assertEqual(self.bar.success.call_args.args[:2], ("已恢复默认值", "下次执行时保存"))

    def test_orders_kept_on_rescan(self) -> None:
        from dataforge.dates import SlashOrder

        dm = self._write("DM.csv", DM_TEXT)
        ae = self._write("AE.csv", AE_AMBIGUOUS_TEXT)
        page = self._page()
        page.file_input.set_files([dm, ae])
        self._scan(page)
        page.view.order_combos()[0][1].setCurrentIndex(1)
        first = page._report
        page.view.rescan_button.click()
        wait_until(lambda: page._report is not first and page._report is not None)
        wait_until(lambda: not self.runner.is_busy())
        self.assertEqual(page.view.orders(), {("AE.csv", "AESTDTC"): SlashOrder.DAY_FIRST})
        self.assertNotIn("还有 1 个日期列需要选择 日/月 顺序", page.summary_lines())

    def test_encoding_question_unanswered_keeps_report(self) -> None:
        dm = self._write("DM.csv", DM_TEXT)
        ae = self._write("AE.csv", "USUBJID,AETERM\nS1,テスト医師\n", encoding="cp932")
        page = self._page()
        page.file_input.set_files([dm, ae])
        with mock.patch(f"{PAGE}.ask_encodings", return_value={}) as ask:
            self._scan(page)
        ask.assert_called_once()
        self.assertFalse(page._report.processable)
        self.assertEqual(self._text(page), "开始扫描")
        self.assertIn("扫描未通过", page.view.status_text())

    def test_encodings_pruned_on_file_change(self) -> None:
        dm = self._write("DM.csv", DM_TEXT)
        ae = self._write("AE.csv", AE_TEXT)
        page = self._page()
        page.file_input.set_files([dm, ae])
        page._encodings = {str(dm): "cp932", str(ae): "cp932"}
        page.file_input.set_files([dm])
        self.assertEqual(page._encodings, {str(dm): "cp932"})

    def test_v2_section_loaded(self) -> None:
        from dataforge.config.store import ConfigStore

        self.cfg_path.write_text(
            json.dumps(
                {
                    "data_masking_pattern1": {
                        "include_subjid": False,
                        "subject_sort": "x",
                        "subject_limit": 7,
                    }
                }
            ),
            encoding="utf-8",
        )
        self.config = ConfigStore(self.cfg_path)
        page = self._page()
        self.assertFalse(page.profile_form.subjid_box.isChecked())
        self.assertEqual(page.profile_form.limit_spin.value(), 7)
        self.assertEqual(page.profile_form.profile().subject_limit, 7)

    def test_rule_chain_rows_toggle(self) -> None:
        page = self._page()
        form = page.profile_form
        seq = (form.prefix_edit, form.width_spin, form.start_spin)
        rule = (form.remove_prefix_spin, form.remove_suffix_spin, form.prepend_edit,
                form.append_edit)
        self.assertTrue(all(not w.isHidden() for w in seq))
        self.assertTrue(all(w.isHidden() for w in rule))
        form.mode_combo.setCurrentIndex(1)
        self.assertTrue(all(w.isHidden() for w in seq))
        self.assertTrue(all(not w.isHidden() for w in rule))
        profile = form.profile()
        self.assertEqual(profile.usubjid_mode, "rule_chain")
        self.assertEqual(
            [(s.op, s.value) for s in profile.rule_chain_steps],
            [("remove_prefix", 4), ("remove_suffix", 0), ("prepend", "SKLT"), ("append", "")],
        )
        form.set_preview_source("ABC-001")
        self.assertEqual(form.preview_text(), "DM 首条 USUBJID：ABC-001 → SKLT001")
        form.set_preview_source(None)
        self.assertEqual(form.preview_text(), "扫描后显示示例")

    def test_rule_chain_reads_first_step_of_each_op(self) -> None:
        from dataforge.tools.masking.profile import MaskingProfile, RuleStep

        page = self._page()
        form = page.profile_form
        form.set_profile(
            MaskingProfile(
                usubjid_mode="rule_chain",
                rule_chain_steps=[
                    RuleStep("prepend", "P"),
                    RuleStep("remove_prefix", "2"),
                    RuleStep("prepend", "Q"),
                ],
            )
        )
        self.assertEqual(form.mode_combo.currentIndex(), 1)
        self.assertEqual(form.remove_prefix_spin.value(), 2)
        self.assertEqual(form.remove_suffix_spin.value(), 0)
        self.assertEqual(form.prepend_edit.text(), "P")
        self.assertEqual(form.append_edit.text(), "")
        self.assertEqual(
            [(s.op, s.value) for s in form.profile().rule_chain_steps],
            [("remove_prefix", 2), ("remove_suffix", 0), ("prepend", "P"), ("append", "")],
        )

    def test_age_follows_date_shift(self) -> None:
        page = self._page()
        form = page.profile_form
        self.assertTrue(form.age_same_box.isChecked())  # defaults are equal (-2, -2)
        self.assertFalse(form.age_spin.isEnabled())
        form.date_spin.setValue(5)
        self.assertEqual(form.age_spin.value(), 5)
        self.assertEqual(form.profile().age_shift_years, 5)
        form.age_same_box.setChecked(False)
        self.assertTrue(form.age_spin.isEnabled())
        form.age_spin.setValue(-1)
        form.date_spin.setValue(3)
        self.assertEqual(form.profile().age_shift_years, -1)

    def test_age_unchecked_when_loaded_values_differ(self) -> None:
        from dataforge.tools.masking.profile import MaskingProfile

        page = self._page()
        form = page.profile_form
        form.set_profile(MaskingProfile(date_shift_years=-2, age_shift_years=-3))
        self.assertFalse(form.age_same_box.isChecked())
        self.assertTrue(form.age_spin.isEnabled())

    def test_custom_field_names_gate(self) -> None:
        page = self._page()
        form = page.profile_form
        fields = (form.doctor_fields_edit, form.site_field_edit, form.age_field_edit)
        self.assertTrue(all(not w.isEnabled() for w in fields))
        form.custom_fields_box.setChecked(True)
        self.assertTrue(all(w.isEnabled() for w in fields))
        form.doctor_fields_edit.setText("INVNAM, ICINVNAM ,")
        self.assertEqual(form.profile().doctor_fields, ["INVNAM", "ICINVNAM"])

    def test_restore_defaults(self) -> None:
        page = self._page()
        form = page.profile_form
        form.studyid_edit.setText("X")
        form.limit_spin.setValue(3)
        page.restore_defaults_button.click()
        self.assertEqual(form.studyid_edit.text(), "[UAT]CIRCULATE")
        self.assertEqual(form.limit_spin.value(), 100)

    def test_ranges(self) -> None:
        page = self._page()
        form = page.profile_form
        checks = [
            (form.limit_spin, 1, 100000),
            (form.width_spin, 1, 10),
            (form.start_spin, 0, 999999),
            (form.remove_prefix_spin, 0, 100),
            (form.remove_suffix_spin, 0, 100),
            (form.date_spin, -100, 100),
            (form.age_spin, -100, 100),
            (form.sample_spin, 10, 20000),
            (form.min_non_empty_spin, 1, 10000),
        ]
        for spin, low, high in checks:
            self.assertEqual((spin.minimum(), spin.maximum()), (low, high))
        self.assertEqual((form.ratio_spin.minimum(), form.ratio_spin.maximum()), (0.0, 1.0))
        self.assertAlmostEqual(form.ratio_spin.singleStep(), 0.05)
        self.assertEqual(
            [form.mode_combo.itemText(i) for i in range(form.mode_combo.count())],
            ["顺序编号", "规则链"],
        )
        self.assertEqual(page.output_field.combo.itemText(0), "DM.csv 所在文件夹")

    def test_state_roundtrip(self) -> None:
        dm = self._write("DM.csv", DM_TEXT)
        page = self._page()
        gone = str(self.dir / "gone.csv")
        state = {"files": [str(dm), gone], "encoding": "cp932", "output_dir": str(self.out)}
        self.assertEqual(page.restore_state(state), [gone])
        self.assertEqual(
            page.capture_state(),
            {"files": [str(dm)], "encoding": "cp932", "output_dir": str(self.out)},
        )
        self.assertEqual(page.summary(), "1 个 CSV")
        self.assertIsNone(page._report)
        self.assertEqual(self._text(page), "开始扫描")

    def test_export_report(self) -> None:
        dm = self._write("DM.csv", DM_TEXT)
        page = self._page()
        self.assertFalse(page.view.export_button.isEnabled())
        page.file_input.set_files([dm])
        self._scan(page)
        self.assertTrue(page.view.export_button.isEnabled())
        target = self.dir / "report.json"
        with mock.patch(
            f"{PAGE}.QFileDialog.getSaveFileName", return_value=(str(target), "JSON (*.json)")
        ) as dialog:
            page.view.export_button.click()
        self.assertEqual(dialog.call_args.args[3], "JSON (*.json);;CSV (*.csv)")
        data = json.loads(target.read_text(encoding="utf-8"))
        self.assertEqual(data["subjects"], ["S1", "S2"])
        bad = self.dir / "missing_dir" / "x" / "report.json"
        with mock.patch(f"{PAGE}.export_report", side_effect=OSError("boom")), mock.patch(
            f"{PAGE}.QFileDialog.getSaveFileName", return_value=(str(bad), "JSON (*.json)")
        ):
            page.view.export_button.click()
        self.bar.error.assert_called_once()

    def test_rescan_button(self) -> None:
        dm = self._write("DM.csv", DM_TEXT)
        page = self._page()
        page.file_input.set_files([dm])
        self._scan(page)
        first = page._report
        page.view.rescan_button.click()
        wait_until(lambda: page._report is not first and page._report is not None)
        wait_until(lambda: not self.runner.is_busy())
        self.assertTrue(page._report.processable)

    def test_locked_while_running(self) -> None:
        from dataforge.tools.masking import scan as scan_module

        dm = self._write("DM.csv", DM_TEXT)
        page = self._page()
        page.file_input.set_files([dm])
        gate = threading.Event()
        self.addCleanup(gate.set)

        def gated_scan(*args, **kwargs):
            gate.wait(5)
            return scan_module.scan(*args, **kwargs)

        with mock.patch(f"{PAGE}.scan", side_effect=gated_scan):
            page.run_bar.start_requested.emit()
            wait_until(lambda: self.runner.is_busy())
            wait_until(lambda: page.file_input.is_locked())
            form = page.profile_form
            for widget in (form.limit_spin, form.studyid_edit, form.date_spin,
                           form.sample_spin, form.custom_fields_box, page.encoding_field,
                           page.output_field, page.view.rescan_button,
                           page.restore_defaults_button):
                self.assertFalse(widget.isEnabled(), widget)
            gate.set()
            wait_until(lambda: page._report is not None)
            wait_until(lambda: not self.runner.is_busy())
        self.assertFalse(page.file_input.is_locked())
        self.assertTrue(page.profile_form.limit_spin.isEnabled())
        self.assertTrue(page.view.rescan_button.isEnabled())
        self.assertFalse(page.profile_form.age_spin.isEnabled())  # still follows date shift
        self.assertFalse(page.profile_form.doctor_fields_edit.isEnabled())
        self.assertEqual(self._text(page), "开始处理")

    def test_narrow_mode_compacts_forms(self) -> None:
        from dataforge.ui.layout import LayoutMode

        page = self._page()
        form = page.profile_form
        page.apply_layout_mode(LayoutMode.NARROW)
        for responsive in (form.id_form, form.dm_form, form.scan_form):
            self.assertTrue(responsive.is_compact())
        page.apply_layout_mode(LayoutMode.WIDE)
        self.assertFalse(form.id_form.is_compact())


if __name__ == "__main__":
    unittest.main()
