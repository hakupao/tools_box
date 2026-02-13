from __future__ import annotations

import json

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QPlainTextEdit,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    CheckBox,
    ComboBox,
    DoubleSpinBox,
    LineEdit,
    PrimaryPushButton,
    ProgressBar,
    PushButton,
    SegmentedWidget,
    SpinBox,
    TitleLabel,
)

from ...utils.data_masking_service import DataMaskingService, Pattern1Profile, RuleStep
from ..qt_common import FileListWidget, show_error, show_info, show_warning


class NoWheelSpinBox(SpinBox):
    def wheelEvent(self, event) -> None:  # noqa: N802
        event.ignore()


class NoWheelDoubleSpinBox(DoubleSpinBox):
    def wheelEvent(self, event) -> None:  # noqa: N802
        event.ignore()


class NoWheelComboBox(ComboBox):
    def wheelEvent(self, event) -> None:  # noqa: N802
        event.ignore()


class DataMaskingPage(QWidget):
    FORM_LABEL_WIDTH = 150
    FORM_FIELD_WIDTH = 220

    def __init__(self, main_window) -> None:
        super().__init__()
        self.setObjectName("data_masking")
        self.setAcceptDrops(True)
        self.main_window = main_window

        self.output_path: str | None = None
        self.processor = DataMaskingService()
        self.scan_report = None
        self.scan_signature: str | None = None
        self._loading_profile = False

        self._build_ui()
        self._bind_profile_inputs()
        self._load_profile_to_ui(self.processor.profile)
        self._update_usubjid_mode()

    def _build_ui(self) -> None:
        self.setStyleSheet(
            """
            QWidget#data_masking {
                background: #F5F6F8;
            }
            QWidget#dmScrollContent,
            QWidget#dmPattern1Page,
            QWidget#dmPattern2Page,
            QStackedWidget#dmPatternStack {
                background: #F5F6F8;
                border: none;
            }
            QStackedWidget#dmModeStack {
                background: transparent;
                border: none;
            }
            QScrollArea#dmScrollArea,
            QScrollArea#dmScrollArea > QWidget > QWidget,
            QScrollArea#dmScrollArea QWidget#qt_scrollarea_viewport {
                background: #F5F6F8;
                border: none;
            }
            QWidget#data_masking QScrollBar:vertical {
                background: transparent;
                width: 10px;
                margin: 6px 3px 6px 0;
            }
            QWidget#data_masking QScrollBar::handle:vertical {
                background: #C7D3E3;
                min-height: 52px;
                border-radius: 5px;
            }
            QWidget#data_masking QScrollBar::handle:vertical:hover {
                background: #A9BCD6;
            }
            QWidget#data_masking QScrollBar::handle:vertical:pressed {
                background: #92ABC9;
            }
            QWidget#data_masking QScrollBar::add-line:vertical,
            QWidget#data_masking QScrollBar::sub-line:vertical {
                height: 0px;
                border: none;
                background: transparent;
            }
            QWidget#data_masking QScrollBar::add-page:vertical,
            QWidget#data_masking QScrollBar::sub-page:vertical {
                background: transparent;
            }
            QWidget#data_masking QScrollBar:horizontal {
                background: transparent;
                height: 10px;
                margin: 0 6px 3px 6px;
            }
            QWidget#data_masking QScrollBar::handle:horizontal {
                background: #C7D3E3;
                min-width: 52px;
                border-radius: 5px;
            }
            QWidget#data_masking QScrollBar::handle:horizontal:hover {
                background: #A9BCD6;
            }
            QWidget#data_masking QScrollBar::handle:horizontal:pressed {
                background: #92ABC9;
            }
            QWidget#data_masking QScrollBar::add-line:horizontal,
            QWidget#data_masking QScrollBar::sub-line:horizontal {
                width: 0px;
                border: none;
                background: transparent;
            }
            QWidget#data_masking QScrollBar::add-page:horizontal,
            QWidget#data_masking QScrollBar::sub-page:horizontal {
                background: transparent;
            }
            QFrame#dmCard {
                background: #FFFFFF;
                border: 1px solid #E3E8EF;
                border-radius: 12px;
            }
            QFrame#dmSubCard {
                background: #F8FAFC;
                border: 1px solid #E8EDF4;
                border-radius: 10px;
            }
            QFrame#dmCard QLabel,
            QFrame#dmSubCard QLabel {
                color: #334155;
            }
            QLabel#dmSectionTitle {
                color: #0F172A;
                font-size: 15px;
                font-weight: 700;
            }
            QLabel#dmFormLabel {
                color: #1E293B;
                font-size: 13px;
                font-weight: 600;
            }
            QLabel#dmSubFormLabel {
                color: #1E293B;
                font-size: 13px;
                font-weight: 600;
            }
            QLabel#dmMuted {
                color: #6B7280;
                font-size: 12px;
            }
            QLabel#dmFieldHint {
                color: #64748B;
                font-size: 12px;
            }
            QLabel#dmAlertNote {
                color: #DC2626;
                font-size: 12px;
                font-weight: 600;
            }
            QLabel#dmSubtle {
                color: #475569;
                font-size: 12px;
                font-weight: 600;
            }
            QLabel#dmAccent {
                color: #0E7490;
                font-size: 12px;
                font-weight: 600;
            }
            QLabel#dmRequired {
                color: #DC2626;
                font-size: 12px;
                font-weight: 700;
            }
            QPlainTextEdit {
                background: #FBFCFE;
                border: 1px solid #E3E8EF;
                border-radius: 8px;
                padding: 8px;
                color: #1F2937;
            }
            QFrame#dmSubCard QLineEdit:disabled,
            QFrame#dmSubCard QAbstractSpinBox:disabled,
            QFrame#dmSubCard QComboBox:disabled {
                background: #EEF2F7;
                color: #94A3B8;
                border: 1px solid #D8E0EA;
            }
            QFrame#dmSubCard QLineEdit,
            QFrame#dmSubCard QAbstractSpinBox,
            QFrame#dmSubCard QComboBox {
                min-height: 34px;
            }
            """
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(32, 24, 32, 24)
        root.setSpacing(14)

        header = QHBoxLayout()
        header_left = QVBoxLayout()

        title = TitleLabel("数据模糊化工具")
        subtitle = CaptionLabel("Pattern1（SDTM）可配置脱敏；Pattern2（EDC）暂未开放执行")
        subtitle.setObjectName("dmMuted")

        header_left.addWidget(title)
        header_left.addWidget(subtitle)
        header_left.addStretch(1)

        back_btn = PushButton("返回主页")
        back_btn.clicked.connect(lambda: self.main_window.switch_to(self.main_window.home_interface))

        header.addLayout(header_left, stretch=1)
        header.addWidget(back_btn, alignment=Qt.AlignRight | Qt.AlignTop)
        root.addLayout(header)

        mode_row = QHBoxLayout()
        mode_row.setSpacing(10)

        mode_label = BodyLabel("处理模式")
        self.mode_segment = SegmentedWidget()
        self.mode_segment.addItem("pattern1", "Pattern1 · SDTM", onClick=lambda: self._switch_pattern("pattern1"))
        self.mode_segment.addItem("pattern2", "Pattern2 · EDC", onClick=lambda: self._switch_pattern("pattern2"))
        self.mode_segment.setCurrentItem("pattern1")

        flow_tip = CaptionLabel("步骤：1 输入 -> 2 扫描 -> 3 配置 -> 4 执行 -> 5 预览输出")
        flow_tip.setObjectName("dmSubtle")

        mode_row.addWidget(mode_label)
        mode_row.addWidget(self.mode_segment)
        mode_row.addWidget(flow_tip)
        mode_row.addStretch(1)
        root.addLayout(mode_row)

        self.pattern_stack = QStackedWidget()
        self.pattern_stack.setObjectName("dmPatternStack")
        self.pattern1_page = QWidget()
        self.pattern1_page.setObjectName("dmPattern1Page")
        self.pattern2_page = QWidget()
        self.pattern2_page.setObjectName("dmPattern2Page")

        self.pattern_stack.addWidget(self.pattern1_page)
        self.pattern_stack.addWidget(self.pattern2_page)

        self._build_pattern1_page()
        self._build_pattern2_page()

        content_wrap = QWidget()
        content_wrap.setObjectName("dmScrollContent")
        content_layout = QVBoxLayout(content_wrap)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        content_layout.addWidget(self.pattern_stack)
        content_layout.addStretch(1)

        self.scroll = QScrollArea(self)
        self.scroll.setObjectName("dmScrollArea")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setWidget(content_wrap)

        root.addWidget(self.scroll, stretch=1)

    def _build_pattern1_page(self) -> None:
        layout = QVBoxLayout(self.pattern1_page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        step1_card, step1_layout = self._create_card("步骤 1 · 输入文件 / 文件夹", "先选择数据源，再选择输出目录（可选）")

        source_actions = QHBoxLayout()
        select_file_btn = PushButton("选择文件")
        select_file_btn.clicked.connect(self.select_file)
        select_folder_btn = PushButton("选择文件夹")
        select_folder_btn.clicked.connect(self.select_folder)
        clear_btn = PushButton("清空列表")
        clear_btn.clicked.connect(self.clear_file_list)

        source_actions.addWidget(select_file_btn)
        source_actions.addWidget(select_folder_btn)
        source_actions.addWidget(clear_btn)
        source_actions.addStretch(1)
        step1_layout.addLayout(source_actions)

        drop_tip = CaptionLabel("支持拖拽文件或文件夹到下方列表，自动识别并加载 CSV")
        drop_tip.setObjectName("dmMuted")
        step1_layout.addWidget(drop_tip)

        self.file_list = FileListWidget(allowed_exts=[".csv"])
        self.file_list.setMinimumHeight(140)
        self.file_list.setToolTip("可拖拽文件或文件夹到此区域导入")
        step1_layout.addWidget(self.file_list)

        output_row = QHBoxLayout()
        output_label = BodyLabel("输出路径")
        self.output_note = CaptionLabel("默认输出到自动创建的 masked_output_时间戳 目录")
        self.output_note.setObjectName("dmMuted")
        self.output_note.setWordWrap(True)
        select_output_btn = PushButton("选择输出路径")
        select_output_btn.clicked.connect(self.select_output_path)

        output_row.addWidget(output_label)
        output_row.addWidget(self.output_note, stretch=1)
        output_row.addWidget(select_output_btn)
        step1_layout.addLayout(output_row)

        layout.addWidget(step1_card)

        step2_card, step2_layout = self._create_card("步骤 2 · 扫描", "扫描文件结构、USUBJID统计和日期字段识别结果")

        scan_action_row = QHBoxLayout()
        self.scan_btn = PrimaryPushButton("开始扫描")
        self.scan_btn.clicked.connect(self.scan_files)

        self.export_scan_btn = PushButton("导出扫描报告")
        self.export_scan_btn.setEnabled(False)
        self.export_scan_btn.clicked.connect(self.export_scan_report)

        scan_action_row.addWidget(self.scan_btn)
        scan_action_row.addWidget(self.export_scan_btn)
        scan_action_row.addStretch(1)
        step2_layout.addLayout(scan_action_row)

        self.scan_status_hint = CaptionLabel("请先完成扫描，再进入配置和执行")
        self.scan_status_hint.setObjectName("dmMuted")
        step2_layout.addWidget(self.scan_status_hint)

        self.scan_preview = QPlainTextEdit()
        self.scan_preview.setReadOnly(True)
        self.scan_preview.setMinimumHeight(180)
        self.scan_preview.setPlaceholderText("点击“开始扫描”后显示结构与字段汇总")
        step2_layout.addWidget(self.scan_preview)

        layout.addWidget(step2_card)

        step3_card, step3_layout = self._create_card(
            "步骤 3 · 根据扫描结果进行配置",
            "请先扫描查看结果，再按需调整配置；仅扫描参数变更时需要重新扫描",
        )

        global_box = QFrame()
        global_box.setObjectName("dmSubCard")
        global_layout = QVBoxLayout(global_box)
        global_layout.setContentsMargins(12, 10, 12, 10)
        global_layout.setSpacing(8)
        global_title = BodyLabel("全局设置")
        global_title.setObjectName("dmSectionTitle")
        global_layout.addWidget(global_title)

        global_form = QFormLayout()
        self._style_form_layout(global_form)

        self.studyid_edit = LineEdit()
        global_form.addRow(
            self._form_label("STUDYID 固定值"),
            self._input_with_note(
                self.studyid_edit,
                "统一替换所有文件的 STUDYID",
                required=True,
                note_object_name="dmAlertNote",
            ),
        )

        self.subject_limit_spin = NoWheelSpinBox()
        self.subject_limit_spin.setRange(1, 100000)
        global_form.addRow(
            self._form_label("输出病例数 (前N)"),
            self._input_with_note(
                self.subject_limit_spin,
                "执行阶段按 DM 前 N 个病例输出",
                required=True,
                note_object_name="dmAlertNote",
            ),
        )

        self.date_shift_spin = NoWheelSpinBox()
        self.date_shift_spin.setRange(-100, 100)
        self.date_shift_spin.valueChanged.connect(self._on_date_shift_changed)
        global_form.addRow(
            self._form_label("日期偏移 (年)"),
            self._input_with_note(
                self.date_shift_spin,
                "日期字段统一偏移年数（可为负）",
                required=True,
                note_object_name="dmAlertNote",
            ),
        )
        global_layout.addLayout(global_form)
        step3_layout.addWidget(global_box)

        id_box = QFrame()
        id_box.setObjectName("dmSubCard")
        id_layout = QVBoxLayout(id_box)
        id_layout.setContentsMargins(12, 10, 12, 10)
        id_layout.setSpacing(8)
        id_title = BodyLabel("ID 脱敏设置")
        id_title.setObjectName("dmSectionTitle")
        id_layout.addWidget(id_title)

        id_form = QFormLayout()
        self._style_form_layout(id_form)

        self.usubjid_mode_combo = NoWheelComboBox()
        self.usubjid_mode_combo.addItem("顺序重编", userData="sequential")
        self.usubjid_mode_combo.addItem("规则链", userData="rule_chain")
        self.usubjid_mode_combo.currentIndexChanged.connect(self._update_usubjid_mode)
        id_form.addRow(
            self._form_label("USUBJID 脱敏模式"),
            self._input_with_note(self.usubjid_mode_combo, "选择 ID 脱敏策略"),
        )

        self.include_subjid_checkbox = CheckBox("同步处理 SUBJID 字段")
        id_form.addRow(self._form_label("ID 处理范围"), self._checkbox_field(self.include_subjid_checkbox))
        id_layout.addLayout(id_form)

        self.seq_mode_box = QFrame()
        self.seq_mode_box.setObjectName("dmSubCard")
        self.seq_mode_box.setMinimumHeight(150)
        seq_layout = QFormLayout(self.seq_mode_box)
        self._style_form_layout(seq_layout)
        # Keep x-axis alignment unchanged; add vertical breathing room from sub-card edges.
        seq_layout.setContentsMargins(0, 10, 0, 10)

        self.seq_prefix_edit = LineEdit()
        self.seq_width_spin = NoWheelSpinBox()
        self.seq_width_spin.setRange(1, 10)
        self.seq_start_spin = NoWheelSpinBox()
        self.seq_start_spin.setRange(0, 999999)

        seq_layout.addRow(self._form_label("顺序前缀", submodule=True), self._input_with_note(self.seq_prefix_edit, "例如 TEST"))
        seq_layout.addRow(
            self._form_label("补零位数", submodule=True),
            self._input_with_note(self.seq_width_spin, "例如 4 表示 TEST0001"),
        )
        seq_layout.addRow(self._form_label("起始号", submodule=True), self._input_with_note(self.seq_start_spin, "第一例序号"))

        self.rule_mode_box = QFrame()
        self.rule_mode_box.setObjectName("dmSubCard")
        self.rule_mode_box.setMinimumHeight(170)
        rule_layout = QFormLayout(self.rule_mode_box)
        self._style_form_layout(rule_layout)
        # Keep x-axis alignment unchanged; add vertical breathing room from sub-card edges.
        rule_layout.setContentsMargins(0, 10, 0, 10)

        self.rule_remove_prefix_spin = NoWheelSpinBox()
        self.rule_remove_prefix_spin.setRange(0, 100)
        self.rule_remove_suffix_spin = NoWheelSpinBox()
        self.rule_remove_suffix_spin.setRange(0, 100)
        self.rule_prepend_edit = LineEdit()
        self.rule_append_edit = LineEdit()

        rule_layout.addRow(
            self._form_label("删前N位", submodule=True),
            self._input_with_note(self.rule_remove_prefix_spin, "从左侧裁剪字符数"),
        )
        rule_layout.addRow(
            self._form_label("删后N位", submodule=True),
            self._input_with_note(self.rule_remove_suffix_spin, "从右侧裁剪字符数"),
        )
        rule_layout.addRow(
            self._form_label("前插入", submodule=True),
            self._input_with_note(self.rule_prepend_edit, "在 ID 前追加文本"),
        )
        rule_layout.addRow(
            self._form_label("后插入", submodule=True),
            self._input_with_note(self.rule_append_edit, "在 ID 后追加文本"),
        )

        self.usubjid_mode_stack = QStackedWidget()
        self.usubjid_mode_stack.setObjectName("dmModeStack")
        self.usubjid_mode_stack.addWidget(self.seq_mode_box)
        self.usubjid_mode_stack.addWidget(self.rule_mode_box)
        id_layout.addWidget(self.usubjid_mode_stack)

        self.usubjid_source_hint = CaptionLabel("DM 首条 USUBJID：请先扫描")
        self.usubjid_source_hint.setObjectName("dmSubtle")
        self.usubjid_preview_hint = CaptionLabel("规则预览：请先扫描并配置规则")
        self.usubjid_preview_hint.setObjectName("dmAccent")
        self.usubjid_preview_hint.setWordWrap(True)
        id_layout.addWidget(self.usubjid_source_hint)
        id_layout.addWidget(self.usubjid_preview_hint)
        step3_layout.addWidget(id_box)

        dm_box = QFrame()
        dm_box.setObjectName("dmSubCard")
        dm_layout = QVBoxLayout(dm_box)
        dm_layout.setContentsMargins(12, 10, 12, 10)
        dm_layout.setSpacing(8)
        dm_header = QHBoxLayout()
        dm_title = BodyLabel("DM 专属设置")
        dm_title.setObjectName("dmSectionTitle")
        self.dm_custom_checkbox = CheckBox("自定义字段名")
        dm_header.addWidget(dm_title)
        dm_header.addStretch(1)
        dm_header.addWidget(self.dm_custom_checkbox)
        dm_layout.addLayout(dm_header)

        dm_form = QFormLayout()
        self._style_form_layout(dm_form)

        self.doctor_fields_edit = LineEdit()
        self.doctor_fields_edit.setPlaceholderText("例如: INVNAM,ICINVNAM")
        dm_form.addRow(
            self._form_label("人名字段"),
            self._input_with_note(self.doctor_fields_edit, "多个字段用逗号分隔"),
        )

        self.doctor_value_edit = LineEdit()
        dm_form.addRow(
            self._form_label("人名替换值"),
            self._input_with_note(self.doctor_value_edit, "仅替换原本有值的单元格"),
        )

        self.site_field_edit = LineEdit()
        dm_form.addRow(self._form_label("施设字段"), self._input_with_note(self.site_field_edit, "默认 SITEID"))

        self.site_value_edit = LineEdit()
        dm_form.addRow(
            self._form_label("施设替换值"),
            self._input_with_note(self.site_value_edit, "仅替换原本有值的单元格"),
        )

        self.age_field_edit = LineEdit()
        dm_form.addRow(self._form_label("年龄字段"), self._input_with_note(self.age_field_edit, "默认 AGE"))

        self.link_age_checkbox = CheckBox("年龄偏移联动日期")
        self.link_age_checkbox.stateChanged.connect(self._on_link_age_changed)
        dm_form.addRow(
            self._form_label("偏移联动"),
            self._checkbox_field(self.link_age_checkbox, "勾选后年龄偏移跟随日期偏移"),
        )

        self.age_shift_spin = NoWheelSpinBox()
        self.age_shift_spin.setRange(-100, 100)
        dm_form.addRow(
            self._form_label("年龄偏移 (年)"),
            self._input_with_note(self.age_shift_spin, "仅对非空年龄值生效"),
        )
        dm_layout.addLayout(dm_form)
        step3_layout.addWidget(dm_box)

        self.toggle_advanced_btn = PushButton("显示扫描参数")
        self.toggle_advanced_btn.clicked.connect(self._toggle_advanced)
        step3_layout.addWidget(self.toggle_advanced_btn, alignment=Qt.AlignLeft)

        self.advanced_box = QFrame()
        self.advanced_box.setObjectName("dmSubCard")
        self.advanced_box.setVisible(False)
        self.advanced_box.setMinimumHeight(260)

        advanced_form = QFormLayout(self.advanced_box)
        self._style_form_layout(advanced_form)

        self.date_sample_spin = NoWheelSpinBox()
        self.date_sample_spin.setRange(10, 20000)
        advanced_form.addRow(
            self._form_label("日期识别抽样数"),
            self._input_with_note(self.date_sample_spin, "每列最多抽样行数"),
        )

        self.date_min_non_empty_spin = NoWheelSpinBox()
        self.date_min_non_empty_spin.setRange(1, 10000)
        advanced_form.addRow(
            self._form_label("日期识别最少非空值"),
            self._input_with_note(self.date_min_non_empty_spin, "低于该值时按严格匹配"),
        )

        self.date_ratio_spin = NoWheelDoubleSpinBox()
        self.date_ratio_spin.setRange(0.0, 1.0)
        self.date_ratio_spin.setSingleStep(0.05)
        self.date_ratio_spin.setDecimals(2)
        advanced_form.addRow(
            self._form_label("日期识别命中阈值"),
            self._input_with_note(self.date_ratio_spin, "建议 0.7~1.0"),
        )

        step3_layout.addWidget(self.advanced_box)

        config_action_row = QHBoxLayout()
        self.save_profile_btn = PrimaryPushButton("保存配置（必做）")
        self.save_profile_btn.clicked.connect(self.save_profile)
        self.reset_profile_btn = PushButton("重置默认")
        self.reset_profile_btn.clicked.connect(self.reset_profile)
        save_hint = CaptionLabel("修改后请先保存，再执行扫描/处理")
        save_hint.setObjectName("dmRequired")
        config_action_row.addWidget(self.save_profile_btn)
        config_action_row.addWidget(save_hint)
        config_action_row.addWidget(self.reset_profile_btn)
        config_action_row.addStretch(1)
        step3_layout.addLayout(config_action_row)

        self.dm_custom_checkbox.stateChanged.connect(self._on_dm_custom_toggle_changed)
        self.dm_custom_checkbox.setChecked(False)
        self._set_dm_custom_fields_enabled(False)

        layout.addWidget(step3_card)

        step4_card, step4_layout = self._create_card("步骤 4 · 执行", "扫描通过且配置确认后执行")

        execute_row = QHBoxLayout()
        self.process_btn = PrimaryPushButton("开始处理")
        self.process_btn.setEnabled(False)
        self.process_btn.clicked.connect(self.process_files)
        execute_row.addWidget(self.process_btn)
        execute_row.addStretch(1)
        step4_layout.addLayout(execute_row)

        self.progress_bar = ProgressBar()
        self.progress_bar.setValue(0)
        self.progress_label = CaptionLabel("")
        self.progress_label.setObjectName("dmMuted")
        self.status_label = CaptionLabel("")
        self.status_label.setObjectName("dmMuted")

        step4_layout.addWidget(self.progress_bar)
        step4_layout.addWidget(self.progress_label)
        step4_layout.addWidget(self.status_label)

        layout.addWidget(step4_card)

        step5_card, step5_layout = self._create_card("步骤 5 · 预览和输出", "查看执行结果、输出目录和产物信息")

        run_title = BodyLabel("执行结果预览")
        run_title.setObjectName("dmSectionTitle")
        self.run_preview = QPlainTextEdit()
        self.run_preview.setReadOnly(True)
        self.run_preview.setMinimumHeight(120)
        self.run_preview.setPlaceholderText("点击“开始处理”后显示输出目录、映射文件等信息")

        step5_layout.addWidget(run_title)
        step5_layout.addWidget(self.run_preview)

        layout.addWidget(step5_card)
        layout.addStretch(1)

    def _build_pattern2_page(self) -> None:
        layout = QVBoxLayout(self.pattern2_page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        card, card_layout = self._create_card("Pattern2 - EDC 数据", "该模式暂未开放执行")

        desc = QPlainTextEdit()
        desc.setReadOnly(True)
        desc.setMinimumHeight(180)
        desc.setPlainText(
            "Pattern2（EDC）将在后续版本提供：\n"
            "1. EDC 结构识别与字段映射\n"
            "2. 规则模板与配置复用\n"
            "3. 与 Pattern1 一致的扫描/报告能力\n\n"
            "当前请切换到 Pattern1 处理 SDTM 标准格式数据。"
        )
        card_layout.addWidget(desc)

        layout.addWidget(card)
        layout.addStretch(1)

    def _create_card(self, title: str, subtitle: str | None = None) -> tuple[QFrame, QVBoxLayout]:
        card = QFrame()
        card.setObjectName("dmCard")

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 12, 14, 12)
        card_layout.setSpacing(10)

        title_label = BodyLabel(title)
        title_label.setObjectName("dmSectionTitle")
        card_layout.addWidget(title_label)

        if subtitle:
            subtitle_label = CaptionLabel(subtitle)
            subtitle_label.setObjectName("dmMuted")
            subtitle_label.setWordWrap(True)
            card_layout.addWidget(subtitle_label)

        return card, card_layout

    def _style_form_layout(self, form: QFormLayout) -> None:
        form.setSpacing(8)
        form.setContentsMargins(0, 0, 0, 0)
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        form.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(8)

    def _form_label(self, text: str, *, submodule: bool = False) -> BodyLabel:
        label = BodyLabel(text)
        label.setObjectName("dmSubFormLabel" if submodule else "dmFormLabel")
        label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        label.setMinimumHeight(34)
        label.setMinimumWidth(self.FORM_LABEL_WIDTH)
        label.setMaximumWidth(self.FORM_LABEL_WIDTH)
        if submodule:
            label.setIndent(8)
        return label

    def _input_with_note(
        self,
        widget: QWidget,
        note: str,
        *,
        required: bool = False,
        width: int | None = None,
        note_object_name: str = "dmFieldHint",
    ) -> QWidget:
        input_width = width if width is not None else self.FORM_FIELD_WIDTH
        if hasattr(widget, "setMaximumWidth"):
            widget.setMinimumWidth(input_width)
            widget.setMaximumWidth(input_width)

        container = QWidget()
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        row.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        container.setMinimumHeight(34)

        row.addWidget(widget, 0, Qt.AlignLeft | Qt.AlignVCenter)

        note_label = CaptionLabel(note)
        note_label.setObjectName(note_object_name)
        note_label.setWordWrap(False)
        note_label.setMaximumHeight(20)
        if note_object_name == "dmAlertNote":
            note_label.setTextColor("#DC2626", "#DC2626")
            note_label.setStyleSheet("color: #DC2626;")
        row.addWidget(note_label, 1, Qt.AlignLeft | Qt.AlignVCenter)

        if required:
            required_label = CaptionLabel("必填")
            required_label.setObjectName("dmRequired")
            required_label.setTextColor("#DC2626", "#DC2626")
            required_label.setStyleSheet("color: #DC2626;")
            row.addWidget(required_label, 0, Qt.AlignRight | Qt.AlignVCenter)

        return container

    def _checkbox_field(self, checkbox: CheckBox, note: str | None = None) -> QWidget:
        checkbox.setMinimumHeight(34)

        container = QWidget()
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        row.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        container.setMinimumHeight(34)

        # Use a fixed-width slot so the note starts at the same x as text-input rows.
        field_slot = QWidget()
        field_slot.setMinimumWidth(self.FORM_FIELD_WIDTH)
        field_slot.setMaximumWidth(self.FORM_FIELD_WIDTH)
        field_slot_layout = QHBoxLayout(field_slot)
        field_slot_layout.setContentsMargins(0, 0, 0, 0)
        field_slot_layout.setSpacing(0)
        field_slot_layout.addWidget(checkbox, 0, Qt.AlignLeft | Qt.AlignVCenter)
        field_slot_layout.addStretch(1)

        row.addWidget(field_slot, 0, Qt.AlignLeft | Qt.AlignVCenter)
        if note:
            note_label = CaptionLabel(note)
            note_label.setObjectName("dmFieldHint")
            note_label.setWordWrap(False)
            note_label.setMaximumHeight(20)
            row.addWidget(note_label, 1, Qt.AlignLeft | Qt.AlignVCenter)
        else:
            row.addStretch(1)

        return container

    def _bind_profile_inputs(self) -> None:
        runtime_widgets = [
            self.studyid_edit,
            self.subject_limit_spin,
            self.usubjid_mode_combo,
            self.seq_prefix_edit,
            self.seq_width_spin,
            self.seq_start_spin,
            self.rule_remove_prefix_spin,
            self.rule_remove_suffix_spin,
            self.rule_prepend_edit,
            self.rule_append_edit,
            self.date_shift_spin,
            self.link_age_checkbox,
            self.age_shift_spin,
            self.doctor_fields_edit,
            self.doctor_value_edit,
            self.site_field_edit,
            self.site_value_edit,
            self.age_field_edit,
            self.dm_custom_checkbox,
            self.include_subjid_checkbox,
        ]

        scan_widgets = [
            self.date_sample_spin,
            self.date_min_non_empty_spin,
            self.date_ratio_spin,
        ]

        for widget in runtime_widgets:
            self._connect_change_signal(widget, self._on_runtime_profile_changed)

        for widget in scan_widgets:
            self._connect_change_signal(widget, self._on_scan_config_changed)

        self.file_list.filesAdded.connect(lambda _files: self._invalidate_scan())

    def _connect_change_signal(self, widget, callback) -> None:
        if hasattr(widget, "textChanged"):
            widget.textChanged.connect(callback)
        if hasattr(widget, "valueChanged"):
            widget.valueChanged.connect(callback)
        if hasattr(widget, "currentIndexChanged"):
            widget.currentIndexChanged.connect(callback)
        if hasattr(widget, "stateChanged"):
            widget.stateChanged.connect(callback)

    def _switch_pattern(self, route_key: str) -> None:
        if route_key == "pattern2":
            self.pattern_stack.setCurrentWidget(self.pattern2_page)
        else:
            self.pattern_stack.setCurrentWidget(self.pattern1_page)

    def _toggle_advanced(self) -> None:
        visible = not self.advanced_box.isVisible()
        self.advanced_box.setVisible(visible)
        self.toggle_advanced_btn.setText("隐藏扫描参数" if visible else "显示扫描参数")

    def _on_runtime_profile_changed(self, *_args) -> None:
        if self._loading_profile:
            return
        self._update_usubjid_preview()

    def _on_scan_config_changed(self, *_args) -> None:
        if self._loading_profile:
            return
        self._invalidate_scan()

    def _on_dm_custom_toggle_changed(self, *_args) -> None:
        enabled = self.dm_custom_checkbox.isChecked()
        self._set_dm_custom_fields_enabled(enabled)
        if not self._loading_profile:
            self._on_runtime_profile_changed()

    def _set_dm_custom_fields_enabled(self, enabled: bool) -> None:
        dm_widgets = [
            self.doctor_fields_edit,
            self.doctor_value_edit,
            self.site_field_edit,
            self.site_value_edit,
            self.age_field_edit,
            self.link_age_checkbox,
        ]
        for widget in dm_widgets:
            widget.setEnabled(enabled)

        if not enabled:
            self.age_shift_spin.setEnabled(False)
            return
        self._on_link_age_changed()

    def _update_usubjid_mode(self) -> None:
        mode = self.usubjid_mode_combo.currentData()
        if mode == "sequential":
            self.usubjid_mode_stack.setCurrentWidget(self.seq_mode_box)
        else:
            self.usubjid_mode_stack.setCurrentWidget(self.rule_mode_box)
        self._update_usubjid_preview()

    def _update_usubjid_preview(self) -> None:
        source = self._resolve_preview_source_subject()
        if not source:
            self.usubjid_source_hint.setText("DM 首条 USUBJID：请先扫描")
            self.usubjid_preview_hint.setText("规则预览：请先扫描并配置规则")
            return

        profile = self._collect_profile_from_ui()
        preview_value = self._preview_subject_transform(source, profile)
        self.usubjid_source_hint.setText(f"DM 首条 USUBJID：{source}")
        self.usubjid_preview_hint.setText(f"规则预览：{source}  ->  {preview_value}")

    def _resolve_preview_source_subject(self) -> str | None:
        if self.scan_report is None:
            return None

        dm_first = getattr(self.scan_report, "dm_first_usubjid", None)
        if dm_first:
            return str(dm_first)

        if self.scan_report.selected_subjects:
            return str(self.scan_report.selected_subjects[0])
        return None

    def _preview_subject_transform(self, original: str, profile: Pattern1Profile) -> str:
        return self.processor.transform_subject_id(original, profile)

    def _add_source_paths(self, paths: list[str]) -> list[str]:
        added = self.file_list.add_paths(paths)
        if added:
            self.file_list.filesAdded.emit(added)
        return added

    def _on_date_shift_changed(self) -> None:
        if self.link_age_checkbox.isChecked():
            self.age_shift_spin.setValue(self.date_shift_spin.value())

    def _on_link_age_changed(self) -> None:
        if not self.dm_custom_checkbox.isChecked():
            self.age_shift_spin.setEnabled(False)
            return
        linked = self.link_age_checkbox.isChecked()
        self.age_shift_spin.setEnabled(not linked)
        if linked:
            self.age_shift_spin.setValue(self.date_shift_spin.value())

    def _load_profile_to_ui(self, profile: Pattern1Profile) -> None:
        self._loading_profile = True
        try:
            self.studyid_edit.setText(profile.studyid_value)
            self.subject_limit_spin.setValue(profile.subject_limit)

            mode_idx = self.usubjid_mode_combo.findData(profile.usubjid_mode)
            self.usubjid_mode_combo.setCurrentIndex(max(0, mode_idx))

            self.seq_prefix_edit.setText(profile.sequential_prefix)
            self.seq_width_spin.setValue(profile.sequential_width)
            self.seq_start_spin.setValue(profile.sequential_start)

            remove_prefix = 0
            remove_suffix = 0
            prepend = ""
            append = ""
            for step in profile.rule_chain_steps:
                if step.op == "remove_prefix":
                    try:
                        remove_prefix = int(step.value)
                    except (TypeError, ValueError):
                        remove_prefix = 0
                elif step.op == "remove_suffix":
                    try:
                        remove_suffix = int(step.value)
                    except (TypeError, ValueError):
                        remove_suffix = 0
                elif step.op == "prepend":
                    prepend = str(step.value)
                elif step.op == "append":
                    append = str(step.value)

            self.rule_remove_prefix_spin.setValue(remove_prefix)
            self.rule_remove_suffix_spin.setValue(remove_suffix)
            self.rule_prepend_edit.setText(prepend)
            self.rule_append_edit.setText(append)

            self.date_shift_spin.setValue(profile.date_shift_years)
            self.age_shift_spin.setValue(profile.age_shift_years)

            linked = profile.age_shift_years == profile.date_shift_years
            self.link_age_checkbox.setChecked(linked)

            self.date_sample_spin.setValue(profile.date_detect_sample_size)
            self.date_min_non_empty_spin.setValue(profile.date_detect_min_non_empty)
            self.date_ratio_spin.setValue(profile.date_detect_success_ratio)

            self.doctor_fields_edit.setText(",".join(profile.doctor_fields))
            self.doctor_value_edit.setText(profile.doctor_value)
            self.site_field_edit.setText(profile.site_field)
            self.site_value_edit.setText(profile.site_value)
            self.age_field_edit.setText(profile.age_field)
            self.include_subjid_checkbox.setChecked(profile.include_subjid)
            self.dm_custom_checkbox.setChecked(False)
            self._set_dm_custom_fields_enabled(False)
        finally:
            self._loading_profile = False
        self._update_usubjid_preview()

    def _collect_profile_from_ui(self) -> Pattern1Profile:
        age_shift = self.date_shift_spin.value() if self.link_age_checkbox.isChecked() else self.age_shift_spin.value()

        doctor_fields = [item.strip() for item in self.doctor_fields_edit.text().split(",") if item.strip()]
        if not doctor_fields:
            doctor_fields = ["INVNAM"]

        return Pattern1Profile(
            studyid_value=self.studyid_edit.text().strip() or "[UAT]CIRCULATE",
            subject_limit=self.subject_limit_spin.value(),
            subject_sort="string_asc",
            usubjid_mode=str(self.usubjid_mode_combo.currentData()),
            rule_chain_steps=[
                RuleStep("remove_prefix", self.rule_remove_prefix_spin.value()),
                RuleStep("remove_suffix", self.rule_remove_suffix_spin.value()),
                RuleStep("prepend", self.rule_prepend_edit.text()),
                RuleStep("append", self.rule_append_edit.text()),
            ],
            sequential_prefix=self.seq_prefix_edit.text().strip() or "TEST",
            sequential_width=self.seq_width_spin.value(),
            sequential_start=self.seq_start_spin.value(),
            date_shift_years=self.date_shift_spin.value(),
            age_shift_years=age_shift,
            date_detect_sample_size=self.date_sample_spin.value(),
            date_detect_min_non_empty=self.date_min_non_empty_spin.value(),
            date_detect_success_ratio=float(self.date_ratio_spin.value()),
            date_output_format="yyyy-mm-dd",
            partial_date_policy="auto_fill_first_day",
            doctor_fields=doctor_fields,
            doctor_value=self.doctor_value_edit.text() or "テスト医師",
            site_field=self.site_field_edit.text().strip() or "SITEID",
            site_value=self.site_value_edit.text() or "テスト施設",
            age_field=self.age_field_edit.text().strip() or "AGE",
            include_subjid=self.include_subjid_checkbox.isChecked(),
        )

    def _invalidate_scan(self) -> None:
        self.scan_report = None
        self.scan_signature = None
        self.export_scan_btn.setEnabled(False)
        self.process_btn.setEnabled(False)
        self.status_label.setText("文件或配置变更后，请重新扫描")
        self.scan_status_hint.setText("请先完成扫描，再进入配置和执行")
        self._update_usubjid_preview()

    def _build_scan_signature(self, files: list[str], profile: Pattern1Profile) -> str:
        payload = {
            "files": sorted(files),
            "scan_profile": {
                "date_detect_sample_size": profile.date_detect_sample_size,
                "date_detect_min_non_empty": profile.date_detect_min_non_empty,
                "date_detect_success_ratio": profile.date_detect_success_ratio,
            },
        }
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)

    def save_profile(self) -> None:
        profile = self._collect_profile_from_ui()
        saved = self.processor.save_profile(profile)
        if saved:
            self.status_label.setText("配置已保存")
            show_info(self, "成功", "配置已保存")
        else:
            show_error(self, "错误", "配置保存失败")

    def reset_profile(self) -> None:
        profile = self.processor.reset_profile()
        self._load_profile_to_ui(profile)
        self._update_usubjid_mode()
        self._invalidate_scan()
        show_info(self, "成功", "已恢复默认配置")

    def select_file(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, "选择 CSV 文件", "", "CSV 文件 (*.csv)")
        if files:
            self._add_source_paths(files)

    def select_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "选择包含 CSV 文件的文件夹")
        if folder:
            self._add_source_paths([folder])

    def select_output_path(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "选择输出文件夹")
        if folder:
            self.output_path = folder
            self.output_note.setText(f"输出到: {folder}")

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        if self.pattern_stack.currentWidget() is self.pattern1_page and event.mimeData().hasUrls():
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event) -> None:  # noqa: N802
        if self.pattern_stack.currentWidget() is self.pattern1_page and event.mimeData().hasUrls():
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event) -> None:  # noqa: N802
        if self.pattern_stack.currentWidget() is not self.pattern1_page or not event.mimeData().hasUrls():
            super().dropEvent(event)
            return

        paths = [url.toLocalFile() for url in event.mimeData().urls()]
        self._add_source_paths(paths)
        event.acceptProposedAction()

    def update_progress(self, current: int, total: int, current_file: str) -> None:
        if total <= 0:
            return
        progress = int((current / total) * 100)
        self.progress_bar.setValue(progress)
        self.progress_label.setText(f"正在处理: {current_file} ({current}/{total}) | {progress}%")
        QApplication.processEvents()

    def scan_files(self) -> None:
        files = self.file_list.paths()
        if not files:
            show_warning(self, "警告", "请先选择要扫描的 CSV 文件！")
            return

        profile = self._collect_profile_from_ui()
        self.processor.save_profile(profile)

        self.scan_btn.setEnabled(False)
        try:
            report = self.processor.scan_pattern1(files, profile)
            self.scan_preview.setPlainText(self.processor.format_scan_report(report))

            self.scan_report = report
            self.scan_signature = self._build_scan_signature(files, profile)
            self.export_scan_btn.setEnabled(True)
            self.process_btn.setEnabled(not report.errors and bool(report.selected_subjects))
            self._update_usubjid_preview()

            if report.errors:
                show_warning(self, "扫描结果", "扫描未通过:\n\n" + "\n".join(report.errors))
                self.scan_status_hint.setText("扫描未通过，请根据提示修正后重新扫描")
                self.status_label.setText("扫描失败，请修正后重试")
            else:
                output_count = min(len(report.selected_subjects), profile.subject_limit)
                self.scan_status_hint.setText(
                    f"扫描通过：DM病例 {len(report.selected_subjects)}，当前配置预计输出 {output_count}"
                )
                self.status_label.setText("扫描通过，可执行")
                show_info(
                    self,
                    "扫描完成",
                    f"扫描成功，DM病例数: {len(report.selected_subjects)}\n当前配置预计输出: {output_count}",
                )
        except Exception as exc:  # pylint: disable=broad-except
            show_error(self, "错误", f"扫描过程中发生错误：{exc}")
            self._invalidate_scan()
        finally:
            self.scan_btn.setEnabled(True)

    def export_scan_report(self) -> None:
        if self.scan_report is None:
            show_warning(self, "警告", "请先执行扫描")
            return

        target_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出扫描报告",
            "pattern1_scan_report.json",
            "JSON 文件 (*.json);;CSV 文件 (*.csv)",
        )
        if not target_path:
            return

        try:
            self.processor.export_scan_report(self.scan_report, target_path)
            show_info(self, "导出成功", f"扫描报告已导出到:\n{target_path}")
        except Exception as exc:  # pylint: disable=broad-except
            show_error(self, "错误", f"导出扫描报告失败：{exc}")

    def process_files(self) -> None:
        files = self.file_list.paths()
        if not files:
            show_warning(self, "警告", "请先选择要处理的 CSV 文件！")
            return

        if self.scan_report is None:
            show_warning(self, "警告", "请先扫描并确认结果")
            return

        if self.scan_report.errors:
            show_warning(self, "警告", "扫描存在错误，无法开始处理")
            return

        profile = self._collect_profile_from_ui()
        self.processor.save_profile(profile)

        current_signature = self._build_scan_signature(files, profile)
        if self.scan_signature != current_signature:
            show_warning(self, "警告", "文件列表或配置已变更，请先重新扫描")
            return

        self.process_btn.setEnabled(False)
        self.scan_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_label.setText("开始执行 Pattern1 脱敏...")

        try:
            result = self.processor.run_pattern1(
                files,
                output_dir=self.output_path,
                profile=profile,
                scan_report=self.scan_report,
                progress_callback=self.update_progress,
            )

            self.progress_bar.setValue(100)
            self.progress_label.setText("处理完成")

            preview = (
                f"成功处理 {len(result.output_files)} 个文件\n\n"
                f"输出目录: {result.output_dir}\n"
                f"映射文件: {result.mapping_file}\n"
                f"扫描报告: {result.scan_report_file}\n\n"
                f"日期标准化: {result.date_normalized_count}\n"
                f"日期自动补全: {result.date_auto_filled_count}\n"
                f"日期未解析保留: {result.date_unparsed_count}"
            )
            self.run_preview.setPlainText(preview)
            self.status_label.setText("处理完成")
            show_info(self, "处理完成", preview)
        except Exception as exc:  # pylint: disable=broad-except
            show_error(self, "错误", f"处理过程中发生错误：{exc}")
            self.status_label.setText("处理失败")
        finally:
            self.process_btn.setEnabled(True)
            self.scan_btn.setEnabled(True)

    def clear_file_list(self) -> None:
        self.file_list.clear()
        self.scan_preview.clear()
        self.run_preview.clear()
        self._invalidate_scan()
