"""Masking profile editor: three ResponsiveForms placed in separate page cards."""
from __future__ import annotations

import re
from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QWidget
from qfluentwidgets import BodyLabel, CheckBox, ComboBox, DoubleSpinBox, LineEdit, SpinBox

from dataforge.tools.masking.execute import transform_subject_id
from dataforge.tools.masking.profile import MaskingProfile, RuleStep
from dataforge.ui.components.responsive_form import ResponsiveForm

_MODES = (("顺序编号", "sequential"), ("规则链", "rule_chain"))
_FIELD_SPLIT = re.compile(r"[,，]")


def _spin(parent: QWidget, low: int, high: int) -> SpinBox:
    spin = SpinBox(parent)
    spin.setRange(low, high)
    return spin


def _int_or_zero(value: Any) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _first_step(steps: list[RuleStep], op: str) -> RuleStep | None:
    return next((s for s in steps if s.op.strip().lower() == op), None)


class ProfileForm(QWidget):
    """Edits a MaskingProfile.

    The widget itself stays hidden: the page puts ``id_form``, ``dm_form`` and ``scan_form``
    into their own cards, while this object keeps the fields wired together.
    """

    changed = Signal()
    scan_settings_changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setVisible(False)
        self._locked = False
        self._loading = False
        self._preview_source: str | None = None

        # -- subjects and IDs ------------------------------------------------------
        self.id_form = ResponsiveForm(self)
        self.limit_spin = _spin(self.id_form, 1, 100000)
        self.studyid_edit = LineEdit(self.id_form)
        self.mode_combo = ComboBox(self.id_form)
        self.mode_combo.addItems([label for label, _ in _MODES])
        self.prefix_edit = LineEdit(self.id_form)
        self.width_spin = _spin(self.id_form, 1, 10)
        self.start_spin = _spin(self.id_form, 0, 999999)
        self.remove_prefix_spin = _spin(self.id_form, 0, 100)
        self.remove_suffix_spin = _spin(self.id_form, 0, 100)
        self.prepend_edit = LineEdit(self.id_form)
        self.append_edit = LineEdit(self.id_form)
        self.subjid_box = CheckBox("清空 SUBJID 列", self.id_form)
        self.preview_label = BodyLabel("", self.id_form)
        self.preview_label.setWordWrap(True)

        form = self.id_form
        form.add_row("输出受试者数", self.limit_spin, "按 USUBJID 排序后保留前 N 个受试者")
        form.add_row("STUDYID", self.studyid_edit)
        form.add_row("编号方式", self.mode_combo)
        form.add_row("前缀", self.prefix_edit)
        form.add_row("位数", self.width_spin)
        form.add_row("起始号", self.start_spin)
        form.add_row("去前 N 位", self.remove_prefix_spin)
        form.add_row("去后 N 位", self.remove_suffix_spin)
        form.add_row("前加", self.prepend_edit)
        form.add_row("后加", self.append_edit)
        form.add_row("SUBJID", self.subjid_box)
        form.add_row("示例", self.preview_label)

        # -- dates and DM ------------------------------------------------------------
        self.dm_form = ResponsiveForm(self)
        self.date_spin = _spin(self.dm_form, -100, 100)
        age_host = QWidget(self.dm_form)
        self.age_spin = _spin(age_host, -100, 100)
        self.age_same_box = CheckBox("与日期偏移相同", age_host)
        age_layout = QHBoxLayout(age_host)
        age_layout.setContentsMargins(0, 0, 0, 0)
        age_layout.addWidget(self.age_spin)
        age_layout.addWidget(self.age_same_box)
        age_layout.addStretch(1)
        self.doctor_box = CheckBox("替换医生字段", self.dm_form)
        self.doctor_value_edit = LineEdit(self.dm_form)
        self.site_box = CheckBox("替换施设字段", self.dm_form)
        self.site_value_edit = LineEdit(self.dm_form)
        self.custom_fields_box = CheckBox("自定义字段名", self.dm_form)
        self.doctor_fields_edit = LineEdit(self.dm_form)
        self.site_field_edit = LineEdit(self.dm_form)
        self.age_field_edit = LineEdit(self.dm_form)

        form = self.dm_form
        form.add_row("日期偏移（年）", self.date_spin, "所有日期列按年偏移，时间部分保留")
        form.add_row("年龄偏移（年）", age_host)
        form.add_row("替换医生字段", self.doctor_box)
        form.add_row("医生替换值", self.doctor_value_edit)
        form.add_row("替换施设字段", self.site_box)
        form.add_row("施设替换值", self.site_value_edit)
        form.add_row("自定义字段名", self.custom_fields_box)
        form.add_row("医生字段", self.doctor_fields_edit, "多个字段用逗号分隔")
        form.add_row("施设字段", self.site_field_edit)
        form.add_row("年龄字段", self.age_field_edit)

        # -- date detection (scan settings) ---------------------------------------------
        self.scan_form = ResponsiveForm(self)
        self.sample_spin = _spin(self.scan_form, 10, 20000)
        self.min_non_empty_spin = _spin(self.scan_form, 1, 10000)
        self.ratio_spin = DoubleSpinBox(self.scan_form)
        self.ratio_spin.setRange(0.0, 1.0)
        self.ratio_spin.setSingleStep(0.05)
        self.ratio_spin.setDecimals(2)
        form = self.scan_form
        form.add_row("抽样数", self.sample_spin, "每列取前 N 个非空值判断是否为日期列")
        form.add_row("最少非空值", self.min_non_empty_spin, "非空值少于此数时要求全部像日期")
        form.add_row("命中比例", self.ratio_spin)

        self.set_profile(MaskingProfile())

        for spin in (self.limit_spin, self.width_spin, self.start_spin,
                     self.remove_prefix_spin, self.remove_suffix_spin, self.age_spin):
            spin.valueChanged.connect(self._emit_changed)
        for edit in (self.studyid_edit, self.prefix_edit, self.prepend_edit, self.append_edit,
                     self.doctor_value_edit, self.site_value_edit, self.doctor_fields_edit,
                     self.site_field_edit, self.age_field_edit):
            edit.textChanged.connect(self._emit_changed)
        for box in (self.subjid_box, self.doctor_box, self.site_box, self.custom_fields_box,
                    self.age_same_box):
            box.toggled.connect(self._on_toggle)
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        self.date_spin.valueChanged.connect(self._on_date_changed)
        for spin in (self.sample_spin, self.min_non_empty_spin, self.ratio_spin):
            spin.valueChanged.connect(self._emit_scan_changed)

    # -- public API ------------------------------------------------------------------
    def set_profile(self, p: MaskingProfile) -> None:
        before = self._scan_values()
        self._loading = True
        try:
            self.limit_spin.setValue(p.subject_limit)
            self.studyid_edit.setText(p.studyid_value)
            modes = [mode for _, mode in _MODES]
            self.mode_combo.setCurrentIndex(modes.index(p.usubjid_mode)
                                            if p.usubjid_mode in modes else 0)
            self.prefix_edit.setText(p.sequential_prefix)
            self.width_spin.setValue(p.sequential_width)
            self.start_spin.setValue(p.sequential_start)
            steps = list(p.rule_chain_steps)
            step = _first_step(steps, "remove_prefix")
            self.remove_prefix_spin.setValue(_int_or_zero(step.value) if step else 0)
            step = _first_step(steps, "remove_suffix")
            self.remove_suffix_spin.setValue(_int_or_zero(step.value) if step else 0)
            step = _first_step(steps, "prepend")
            self.prepend_edit.setText(str(step.value) if step else "")
            step = _first_step(steps, "append")
            self.append_edit.setText(str(step.value) if step else "")
            self.subjid_box.setChecked(p.include_subjid)

            self.date_spin.setValue(p.date_shift_years)
            self.age_spin.setValue(p.age_shift_years)
            self.age_same_box.setChecked(p.date_shift_years == p.age_shift_years)
            self.doctor_box.setChecked(p.doctor_replace_enabled)
            self.doctor_value_edit.setText(p.doctor_value)
            self.site_box.setChecked(p.site_replace_enabled)
            self.site_value_edit.setText(p.site_value)
            self.custom_fields_box.setChecked(False)
            self.doctor_fields_edit.setText(", ".join(p.doctor_fields))
            self.site_field_edit.setText(p.site_field)
            self.age_field_edit.setText(p.age_field)

            self.sample_spin.setValue(p.date_detect_sample_size)
            self.min_non_empty_spin.setValue(p.date_detect_min_non_empty)
            self.ratio_spin.setValue(p.date_detect_success_ratio)
        finally:
            self._loading = False
        self._refresh_state()
        if before != self._scan_values():
            self.scan_settings_changed.emit()
        self.changed.emit()

    def profile(self) -> MaskingProfile:
        doctors = [f.strip() for f in _FIELD_SPLIT.split(self.doctor_fields_edit.text())]
        return MaskingProfile(
            studyid_value=self.studyid_edit.text(),
            subject_limit=self.limit_spin.value(),
            usubjid_mode=_MODES[max(0, self.mode_combo.currentIndex())][1],
            rule_chain_steps=[
                RuleStep("remove_prefix", self.remove_prefix_spin.value()),
                RuleStep("remove_suffix", self.remove_suffix_spin.value()),
                RuleStep("prepend", self.prepend_edit.text()),
                RuleStep("append", self.append_edit.text()),
            ],
            sequential_prefix=self.prefix_edit.text(),
            sequential_width=self.width_spin.value(),
            sequential_start=self.start_spin.value(),
            date_shift_years=self.date_spin.value(),
            age_shift_years=self.age_spin.value(),
            date_detect_sample_size=self.sample_spin.value(),
            date_detect_min_non_empty=self.min_non_empty_spin.value(),
            date_detect_success_ratio=round(self.ratio_spin.value(), 2),
            doctor_fields=[f for f in doctors if f],
            doctor_value=self.doctor_value_edit.text(),
            doctor_replace_enabled=self.doctor_box.isChecked(),
            site_field=self.site_field_edit.text().strip(),
            site_value=self.site_value_edit.text(),
            site_replace_enabled=self.site_box.isChecked(),
            age_field=self.age_field_edit.text().strip(),
            include_subjid=self.subjid_box.isChecked(),
        )

    def set_locked(self, locked: bool) -> None:
        self._locked = locked
        self._refresh_state()

    def set_preview_source(self, usubjid: str | None) -> None:
        self._preview_source = usubjid
        self._refresh_preview()

    def preview_text(self) -> str:
        return self.preview_label.text()

    # -- internals -------------------------------------------------------------------
    def _scan_values(self) -> tuple[int, int, float]:
        return (self.sample_spin.value(), self.min_non_empty_spin.value(),
                round(self.ratio_spin.value(), 2))

    def _refresh_state(self) -> None:
        """Row visibility and enabled state; every widget's enabled flag is set only here."""
        rule = self.mode_combo.currentIndex() == 1
        for widget in (self.prefix_edit, self.width_spin, self.start_spin):
            self.id_form.set_row_visible(widget, not rule)
        for widget in (self.remove_prefix_spin, self.remove_suffix_spin, self.prepend_edit,
                       self.append_edit):
            self.id_form.set_row_visible(widget, rule)

        free = not self._locked
        custom = self.custom_fields_box.isChecked()
        conditional = {
            self.age_spin: not self.age_same_box.isChecked(),
            self.doctor_value_edit: self.doctor_box.isChecked(),
            self.site_value_edit: self.site_box.isChecked(),
            self.doctor_fields_edit: custom,
            self.site_field_edit: custom,
            self.age_field_edit: custom,
        }
        plain = (self.limit_spin, self.studyid_edit, self.mode_combo, self.prefix_edit,
                 self.width_spin, self.start_spin, self.remove_prefix_spin,
                 self.remove_suffix_spin, self.prepend_edit, self.append_edit, self.subjid_box,
                 self.date_spin, self.age_same_box, self.doctor_box, self.site_box,
                 self.custom_fields_box, self.sample_spin, self.min_non_empty_spin,
                 self.ratio_spin)
        for widget in plain:
            widget.setEnabled(free)
        for widget, condition in conditional.items():
            widget.setEnabled(free and condition)
        self._refresh_preview()

    def _refresh_preview(self) -> None:
        source = self._preview_source
        if source is None:
            self.preview_label.setText("扫描后显示示例")
            return
        new = transform_subject_id(source, self.profile(), 0)
        self.preview_label.setText(f"DM 首条 USUBJID：{source} → {new}")

    def _emit_changed(self, *_args: object) -> None:
        if self._loading:
            return
        self._refresh_preview()
        self.changed.emit()

    def _emit_scan_changed(self, *_args: object) -> None:
        if self._loading:
            return
        self.scan_settings_changed.emit()
        self.changed.emit()

    def _on_toggle(self, *_args: object) -> None:
        if self._loading:
            return
        if self.age_same_box.isChecked() and self.age_spin.value() != self.date_spin.value():
            self.age_spin.setValue(self.date_spin.value())  # emits changed itself
        self._refresh_state()
        self.changed.emit()

    def _on_mode_changed(self, *_args: object) -> None:
        if self._loading:
            return
        self._refresh_state()
        self.changed.emit()

    def _on_date_changed(self, value: int) -> None:
        if self._loading:
            return
        if self.age_same_box.isChecked():
            self._loading = True
            try:
                self.age_spin.setValue(value)
            finally:
                self._loading = False
        self._emit_changed()
