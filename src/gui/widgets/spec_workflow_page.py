from __future__ import annotations

import os
from dataclasses import dataclass, field

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QFrame, QHBoxLayout, QScrollArea, QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    ComboBox,
    PrimaryPushButton,
    ProgressBar,
    PushButton,
    SegmentedWidget,
    TitleLabel,
)

from ...utils.codelist_service import CodelistService
from ...utils.data_cleaner_service import DataCleanerService
from ...utils.xlsx_restructure_service import XlsxRestructureService
from ..qt_common import (
    FileListWidget,
    select_existing_directory,
    select_open_file,
    select_open_files,
    show_error,
    show_info,
    show_warning,
)


MODE_DATASET = "dataset"
MODE_CLEANER = "cleaner"
MODE_CODELIST = "codelist"

MODE_META = {
    MODE_DATASET: {
        "name": "生成 Data Set",
        "rule_label": "仕样书（Patients）",
        "mode_hint": "输入 XLSX，按仕样书 Patients 映射并生成标准 CSV",
        "input_hint": "支持拖拽或批量导入 .xlsx 文件",
        "select_file_text": "选择 XLSX 文件",
        "select_folder_text": "选择 XLSX 文件夹",
        "select_dialog_title": "选择 Excel 文件",
        "folder_dialog_title": "选择包含 Excel 文件的文件夹",
        "file_filter": "Excel 文件 (*.xlsx)",
        "exts": [".xlsx"],
        "run_text": "开始生成",
        "tooltip": "仅支持 .xlsx 输入",
    },
    MODE_CLEANER: {
        "name": "数据清洗",
        "rule_label": "仕样书（Patients/Process/Files）",
        "mode_hint": "输入 CSV，按仕样书执行筛选、字段保留和清洗",
        "input_hint": "支持拖拽或批量导入 .csv 文件",
        "select_file_text": "选择 CSV 文件",
        "select_folder_text": "选择 CSV 文件夹",
        "select_dialog_title": "选择 CSV 文件",
        "folder_dialog_title": "选择包含 CSV 文件的文件夹",
        "file_filter": "CSV 文件 (*.csv)",
        "exts": [".csv"],
        "run_text": "开始清洗",
        "tooltip": "仅支持 .csv 输入",
    },
    MODE_CODELIST: {
        "name": "Codelist 处理",
        "rule_label": "仕样书（Process/CodeList/Files）",
        "mode_hint": "输入 CSV，按仕样书 CodeList 规则映射并标准化日期",
        "input_hint": "支持拖拽或批量导入 .csv 文件",
        "select_file_text": "选择 CSV 文件",
        "select_folder_text": "选择 CSV 文件夹",
        "select_dialog_title": "选择 CSV 文件",
        "folder_dialog_title": "选择包含 CSV 文件的文件夹",
        "file_filter": "CSV 文件 (*.csv)",
        "exts": [".csv"],
        "run_text": "开始处理",
        "tooltip": "仅支持 .csv 输入",
    },
}


@dataclass
class ModeState:
    files: list[str] = field(default_factory=list)
    output_path: str | None = None
    rule_file: str | None = None
    study_id: str = "CIRCULATE"
    patients_mapping: dict | None = None


class SpecWorkflowPage(QWidget):
    def __init__(self, main_window) -> None:
        super().__init__()
        self.setObjectName("spec_workflow")
        self.main_window = main_window

        self.cleaner_service = DataCleanerService()
        self.codelist_service = CodelistService()

        self.mode_states: dict[str, ModeState] = {
            MODE_DATASET: ModeState(),
            MODE_CLEANER: ModeState(),
            MODE_CODELIST: ModeState(),
        }
        self.current_mode = MODE_DATASET
        self.output_path: str | None = None

        self._build_ui()
        self._apply_mode(self.current_mode, first_load=True)

    def _build_ui(self) -> None:
        self.setStyleSheet(
            """
            QWidget#spec_workflow {
                background: #F5F6F8;
            }
            QWidget#specScrollContent,
            QScrollArea#specScrollArea,
            QScrollArea#specScrollArea > QWidget > QWidget,
            QScrollArea#specScrollArea QWidget#qt_scrollarea_viewport {
                background: #F5F6F8;
                border: none;
            }
            QFrame#specCard {
                background: #FFFFFF;
                border: 1px solid #E3E8EF;
                border-radius: 12px;
            }
            QLabel#specSectionTitle {
                color: #0F172A;
                font-size: 14px;
                font-weight: 700;
            }
            QLabel#specMuted {
                color: #6B7280;
                font-size: 12px;
            }
            QWidget#spec_workflow QScrollBar:vertical {
                background: transparent;
                width: 10px;
                margin: 6px 3px 6px 0;
            }
            QWidget#spec_workflow QScrollBar::handle:vertical {
                background: #C7D3E3;
                min-height: 52px;
                border-radius: 5px;
            }
            QWidget#spec_workflow QScrollBar::handle:vertical:hover {
                background: #A9BCD6;
            }
            QWidget#spec_workflow QScrollBar::handle:vertical:pressed {
                background: #92ABC9;
            }
            QWidget#spec_workflow QScrollBar::add-line:vertical,
            QWidget#spec_workflow QScrollBar::sub-line:vertical {
                height: 0px;
                border: none;
                background: transparent;
            }
            QWidget#spec_workflow QScrollBar::add-page:vertical,
            QWidget#spec_workflow QScrollBar::sub-page:vertical {
                background: transparent;
            }
            QWidget#spec_workflow QScrollBar:horizontal {
                background: transparent;
                height: 10px;
                margin: 0 6px 3px 6px;
            }
            QWidget#spec_workflow QScrollBar::handle:horizontal {
                background: #C7D3E3;
                min-width: 52px;
                border-radius: 5px;
            }
            QWidget#spec_workflow QScrollBar::handle:horizontal:hover {
                background: #A9BCD6;
            }
            QWidget#spec_workflow QScrollBar::handle:horizontal:pressed {
                background: #92ABC9;
            }
            QWidget#spec_workflow QScrollBar::add-line:horizontal,
            QWidget#spec_workflow QScrollBar::sub-line:horizontal {
                width: 0px;
                border: none;
                background: transparent;
            }
            QWidget#spec_workflow QScrollBar::add-page:horizontal,
            QWidget#spec_workflow QScrollBar::sub-page:horizontal {
                background: transparent;
            }
            """
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.scroll = QScrollArea(self)
        self.scroll.setObjectName("specScrollArea")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)

        content_wrap = QWidget()
        content_wrap.setObjectName("specScrollContent")
        self.scroll.setWidget(content_wrap)

        content_layout = QVBoxLayout(content_wrap)
        content_layout.setContentsMargins(32, 24, 32, 24)
        content_layout.setSpacing(14)

        header = QHBoxLayout()
        header_left = QVBoxLayout()
        title = TitleLabel("仕样书工作流")
        subtitle = CaptionLabel("统一入口：生成 Data Set / 数据清洗 / Codelist 处理")
        subtitle.setObjectName("specMuted")
        header_left.addWidget(title)
        header_left.addWidget(subtitle)
        header_left.addStretch(1)

        back_btn = PushButton("返回主页")
        back_btn.clicked.connect(lambda: self.main_window.switch_to(self.main_window.home_interface))

        header.addLayout(header_left, stretch=1)
        header.addWidget(back_btn, alignment=Qt.AlignRight | Qt.AlignTop)
        content_layout.addLayout(header)

        mode_row = QHBoxLayout()
        mode_row.setSpacing(10)
        mode_label = BodyLabel("处理模式")
        self.mode_segment = SegmentedWidget()
        self.mode_segment.addItem(
            MODE_DATASET,
            MODE_META[MODE_DATASET]["name"],
            onClick=lambda: self._switch_mode(MODE_DATASET),
        )
        self.mode_segment.addItem(
            MODE_CLEANER,
            MODE_META[MODE_CLEANER]["name"],
            onClick=lambda: self._switch_mode(MODE_CLEANER),
        )
        self.mode_segment.addItem(
            MODE_CODELIST,
            MODE_META[MODE_CODELIST]["name"],
            onClick=lambda: self._switch_mode(MODE_CODELIST),
        )
        self.mode_segment.setCurrentItem(MODE_DATASET)

        self.mode_hint = CaptionLabel("")
        self.mode_hint.setObjectName("specMuted")
        self.mode_hint.setWordWrap(True)

        mode_row.addWidget(mode_label)
        mode_row.addWidget(self.mode_segment)
        mode_row.addWidget(self.mode_hint, stretch=1)
        content_layout.addLayout(mode_row)

        rule_card, rule_layout = self._create_card(
            "步骤 1 · 上传仕样书",
            "三种模式统一使用仕样书驱动，切换模式时会自动记住各自的配置",
        )
        rule_row = QHBoxLayout()
        self.rule_label = BodyLabel("仕样书")
        self.rule_note = CaptionLabel("未加载仕样书")
        self.rule_note.setObjectName("specMuted")
        upload_rule_btn = PushButton("上传仕样书")
        upload_rule_btn.clicked.connect(self.select_rule_file)

        rule_row.addWidget(self.rule_label)
        rule_row.addWidget(self.rule_note, stretch=1)
        rule_row.addWidget(upload_rule_btn)
        rule_layout.addLayout(rule_row)
        content_layout.addWidget(rule_card)

        input_card, input_layout = self._create_card(
            "步骤 2 · 选择输入文件",
            "统一拖拽导入文件；不同模式会自动限制允许的文件后缀",
        )
        action_row = QHBoxLayout()
        self.select_file_btn = PushButton("选择文件")
        self.select_file_btn.clicked.connect(self.select_file)
        self.select_folder_btn = PushButton("选择文件夹")
        self.select_folder_btn.clicked.connect(self.select_folder)
        clear_btn = PushButton("清空列表")
        clear_btn.clicked.connect(self.clear_file_list)

        action_row.addWidget(self.select_file_btn)
        action_row.addWidget(self.select_folder_btn)
        action_row.addWidget(clear_btn)
        action_row.addStretch(1)
        input_layout.addLayout(action_row)

        self.input_hint = CaptionLabel("")
        self.input_hint.setObjectName("specMuted")
        input_layout.addWidget(self.input_hint)

        self.file_list = FileListWidget(allowed_exts=[".xlsx"])
        self.file_list.setMinimumHeight(220)
        input_layout.addWidget(self.file_list)
        content_layout.addWidget(input_card)

        run_card, run_layout = self._create_card("步骤 3 · 输出与执行", "设置输出目录并启动批处理")
        output_row = QHBoxLayout()
        output_label = BodyLabel("输出路径")
        self.output_note = CaptionLabel("默认输出到原文件所在目录")
        self.output_note.setObjectName("specMuted")
        select_output_btn = PushButton("选择输出路径")
        select_output_btn.clicked.connect(self.select_output_path)

        output_row.addWidget(output_label)
        output_row.addWidget(self.output_note, stretch=1)
        output_row.addWidget(select_output_btn)
        run_layout.addLayout(output_row)

        self.study_row = QWidget()
        study_row_layout = QHBoxLayout(self.study_row)
        study_row_layout.setContentsMargins(0, 0, 0, 0)
        study_row_layout.setSpacing(8)
        study_label = BodyLabel("STUDYID")
        self.study_combo = ComboBox()
        self.study_combo.addItems(["CIRCULATE", "MONSTAR"])
        self.study_combo.currentTextChanged.connect(self._on_study_changed)
        study_row_layout.addWidget(study_label)
        study_row_layout.addWidget(self.study_combo)
        study_row_layout.addStretch(1)
        run_layout.addWidget(self.study_row)

        self.progress_bar = ProgressBar()
        self.progress_bar.setValue(0)
        self.progress_label = CaptionLabel("")
        self.progress_label.setObjectName("specMuted")

        run_layout.addWidget(self.progress_bar)
        run_layout.addWidget(self.progress_label)

        self.run_btn = PrimaryPushButton("开始处理")
        self.run_btn.clicked.connect(self.run_workflow)
        run_layout.addWidget(self.run_btn, alignment=Qt.AlignLeft)

        self.status_label = CaptionLabel("")
        self.status_label.setObjectName("specMuted")
        run_layout.addWidget(self.status_label)

        content_layout.addWidget(run_card)
        content_layout.addStretch(1)
        root.addWidget(self.scroll, stretch=1)

    def _create_card(self, title: str, description: str) -> tuple[QFrame, QVBoxLayout]:
        card = QFrame()
        card.setObjectName("specCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)
        title_label = BodyLabel(title)
        title_label.setObjectName("specSectionTitle")
        desc_label = CaptionLabel(description)
        desc_label.setObjectName("specMuted")
        desc_label.setWordWrap(True)
        layout.addWidget(title_label)
        layout.addWidget(desc_label)
        return card, layout

    def _switch_mode(self, mode_key: str) -> None:
        if mode_key == self.current_mode:
            return
        self._store_mode_state(self.current_mode)
        self.current_mode = mode_key
        self._apply_mode(mode_key)

    def _store_mode_state(self, mode_key: str) -> None:
        state = self.mode_states[mode_key]
        state.files = self.file_list.paths()
        state.output_path = self.output_path
        if mode_key == MODE_DATASET:
            state.study_id = self.study_combo.currentText()

    def _apply_mode(self, mode_key: str, first_load: bool = False) -> None:
        state = self.mode_states[mode_key]
        meta = MODE_META[mode_key]

        self.mode_segment.setCurrentItem(mode_key)
        self.mode_hint.setText(meta["mode_hint"])
        self.rule_label.setText(meta["rule_label"])
        self.input_hint.setText(meta["input_hint"])
        self.select_file_btn.setText(meta["select_file_text"])
        self.select_folder_btn.setText(meta["select_folder_text"])
        self.run_btn.setText(meta["run_text"])

        self.file_list.set_allowed_exts(meta["exts"])
        self.file_list.clear()
        if state.files:
            self.file_list.add_paths(state.files)
            self.file_list.filter_by_exts(meta["exts"])
        self.file_list.setToolTip(meta["tooltip"])

        self.output_path = state.output_path
        self._refresh_output_note()
        self._refresh_rule_note()

        self.study_row.setVisible(mode_key == MODE_DATASET)
        if mode_key == MODE_DATASET:
            index = self.study_combo.findText(state.study_id)
            if index >= 0:
                self.study_combo.setCurrentIndex(index)

        if first_load:
            self.status_label.setText("请先上传仕样书并选择输入文件。")
        else:
            self.status_label.setText(f"已切换到“{meta['name']}”模式")
        self.progress_bar.setValue(0)
        self.progress_label.setText("")

    def _refresh_output_note(self) -> None:
        if self.output_path:
            self.output_note.setText(f"输出到: {self.output_path}")
        else:
            self.output_note.setText("默认输出到原文件所在目录")

    def _refresh_rule_note(self) -> None:
        state = self.mode_states[self.current_mode]
        if state.rule_file:
            self.rule_note.setText(f"已加载: {os.path.basename(state.rule_file)}")
        else:
            self.rule_note.setText("未加载仕样书")

    def _on_study_changed(self, value: str) -> None:
        self.mode_states[MODE_DATASET].study_id = value

    def select_rule_file(self) -> None:
        file_path, _ = select_open_file(self, "选择仕样书文件", "", "Excel 文件 (*.xlsx)")
        if not file_path:
            return

        try:
            if self.current_mode == MODE_DATASET:
                mapping = XlsxRestructureService.read_patients_mapping(file_path)
                state = self.mode_states[MODE_DATASET]
                state.rule_file = file_path
                state.patients_mapping = mapping
                self.status_label.setText(f"已加载 Patients 映射: {os.path.basename(file_path)}")
            elif self.current_mode == MODE_CLEANER:
                self.cleaner_service.select_rule_file(file_path)
                state = self.mode_states[MODE_CLEANER]
                state.rule_file = file_path
                self.status_label.setText(f"已加载清洗规则: {os.path.basename(file_path)}")
            else:
                self.codelist_service.select_codelist_file(file_path)
                state = self.mode_states[MODE_CODELIST]
                state.rule_file = file_path
                self.status_label.setText(f"已加载 Codelist 规则: {os.path.basename(file_path)}")

            self._refresh_rule_note()
        except Exception as exc:  # pylint: disable=broad-except
            show_error(self, "错误", f"加载仕样书失败: {exc}")

    def select_file(self) -> None:
        meta = MODE_META[self.current_mode]
        files, _ = select_open_files(self, meta["select_dialog_title"], "", meta["file_filter"])
        if files:
            self.file_list.add_paths(files)

    def select_folder(self) -> None:
        meta = MODE_META[self.current_mode]
        folder = select_existing_directory(self, meta["folder_dialog_title"])
        if folder:
            self.file_list.add_paths([folder])

    def select_output_path(self) -> None:
        folder = select_existing_directory(self, "选择输出文件夹")
        if folder:
            self.output_path = folder
            self.mode_states[self.current_mode].output_path = folder
            self._refresh_output_note()

    def clear_file_list(self) -> None:
        self.file_list.clear()
        self.mode_states[self.current_mode].files = []
        self.status_label.setText("已清空当前模式输入列表")

    def update_progress(self, current: int, total: int, current_file: str) -> None:
        if total <= 0:
            return
        progress = int((current / total) * 100)
        self.progress_bar.setValue(progress)
        self.progress_label.setText(f"正在处理: {current_file} ({current}/{total}) | {progress}%")
        QApplication.processEvents()

    def _ensure_rule_loaded(self) -> bool:
        state = self.mode_states[self.current_mode]
        if state.rule_file:
            return True
        show_warning(self, "警告", "请先上传仕样书文件！")
        return False

    def _show_batch_result(self, success_count: int, total: int, error_files: list[str], action: str) -> None:
        if error_files:
            error_msg = "\n".join(error_files)
            show_warning(
                self,
                f"{action}完成",
                f"成功 {success_count}/{total} 个文件\n\n失败列表:\n{error_msg}",
            )
            self.status_label.setText(f"{action}完成：成功 {success_count}/{total}，有失败项")
        else:
            show_info(self, f"{action}完成", f"成功处理所有 {total} 个文件！")
            self.status_label.setText(f"{action}完成：成功 {success_count}/{total}")

        self.progress_bar.setValue(0)
        self.progress_label.setText("")

    def run_workflow(self) -> None:
        files = self.file_list.paths()
        if not files:
            show_warning(self, "警告", "请先选择要处理的文件！")
            return

        if not self._ensure_rule_loaded():
            return

        self.run_btn.setEnabled(False)
        try:
            if self.current_mode == MODE_DATASET:
                self._run_dataset(files)
            elif self.current_mode == MODE_CLEANER:
                self._run_cleaner(files)
            else:
                self._run_codelist(files)
        except Exception as exc:  # pylint: disable=broad-except
            show_error(self, "错误", f"处理过程中发生错误：{exc}")
            self.status_label.setText("处理失败")
        finally:
            self.run_btn.setEnabled(True)

    def _run_dataset(self, files: list[str]) -> None:
        state = self.mode_states[MODE_DATASET]
        total = len(files)
        success_count = 0
        error_files: list[str] = []
        study_id = self.study_combo.currentText().strip() or "CIRCULATE"
        state.study_id = study_id
        mapping = state.patients_mapping

        for index, file_path in enumerate(files, 1):
            self.update_progress(index, total, os.path.basename(file_path))
            try:
                success, message = XlsxRestructureService.file_restructure(
                    file_path,
                    self.output_path,
                    study_id,
                    mapping,
                )
                if success:
                    success_count += 1
                else:
                    error_files.append(f"{file_path} (错误: {message})")
            except Exception as exc:  # pylint: disable=broad-except
                error_files.append(f"{file_path} (错误: {exc})")

        self._show_batch_result(success_count, total, error_files, "生成")

    def _run_cleaner(self, files: list[str]) -> None:
        state = self.mode_states[MODE_CLEANER]
        if not getattr(self.cleaner_service, "rule_file", None) and state.rule_file:
            self.cleaner_service.select_rule_file(state.rule_file)

        total = len(files)
        success_count = 0
        error_files: list[str] = []
        for index, file_path in enumerate(files, 1):
            self.update_progress(index, total, os.path.basename(file_path))
            success = self.cleaner_service.clean_csv_file(file_path, self.output_path)
            if success:
                success_count += 1
            else:
                error_files.append(file_path)

        self._show_batch_result(success_count, total, error_files, "清洗")

    def _run_codelist(self, files: list[str]) -> None:
        state = self.mode_states[MODE_CODELIST]
        if not getattr(self.codelist_service, "codelist_file", None) and state.rule_file:
            self.codelist_service.select_codelist_file(state.rule_file)

        total = len(files)
        success_count = 0
        error_files: list[str] = []
        for index, file_path in enumerate(files, 1):
            self.update_progress(index, total, os.path.basename(file_path))
            try:
                success = self.codelist_service.process_csv_file(file_path, self.output_path)
                if success:
                    success_count += 1
                else:
                    error_files.append(file_path)
            except Exception as exc:  # pylint: disable=broad-except
                error_files.append(f"{file_path} (错误: {exc})")

        self._show_batch_result(success_count, total, error_files, "处理")
