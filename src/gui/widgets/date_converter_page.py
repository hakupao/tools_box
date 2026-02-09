from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import BodyLabel, PrimaryPushButton, PushButton, TextEdit, TitleLabel

from ...utils.date_utils import convert_to_iso8601
from ..qt_common import mono_font, show_info


class DateConverterPage(QWidget):
    def __init__(self, main_window) -> None:
        super().__init__()
        self.setObjectName("date_converter")
        self.main_window = main_window

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(16)

        header_layout = QHBoxLayout()
        title = TitleLabel("日期格式转换")
        desc = BodyLabel("多种日期格式智能转换，支持批量处理")
        desc.setTextColor("#6B7280", "#6B7280")

        header_left = QVBoxLayout()
        header_left.addWidget(title)
        header_left.addWidget(desc)
        header_left.addStretch(1)

        back_btn = PushButton("返回主页")
        back_btn.clicked.connect(lambda: self.main_window.switch_to(self.main_window.home_interface))

        header_layout.addLayout(header_left, stretch=1)
        header_layout.addWidget(back_btn, alignment=Qt.AlignRight | Qt.AlignTop)
        layout.addLayout(header_layout)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(16)

        self.input_text = TextEdit()
        self.input_text.setPlaceholderText("请输入日期内容，每行一个")
        self.input_text.setFont(mono_font(10))

        self.output_text = TextEdit()
        self.output_text.setPlaceholderText("转换结果将在此显示")
        self.output_text.setReadOnly(True)
        self.output_text.setFont(mono_font(10))

        content_layout.addWidget(self.input_text, stretch=1)
        content_layout.addWidget(self.output_text, stretch=1)

        action_layout = QHBoxLayout()
        action_layout.addStretch(1)
        convert_btn = PrimaryPushButton("转换")
        convert_btn.clicked.connect(self.convert_dates)
        copy_btn = PushButton("复制全部")
        copy_btn.clicked.connect(self.copy_all)
        action_layout.addWidget(convert_btn)
        action_layout.addWidget(copy_btn)

        layout.addLayout(content_layout)
        layout.addLayout(action_layout)
        layout.addStretch(1)

    def convert_dates(self) -> None:
        input_text = self.input_text.toPlainText()
        lines = input_text.splitlines()
        result = [convert_to_iso8601(line.strip()) for line in lines]
        self.output_text.setPlainText("\n".join(result))

    def copy_all(self) -> None:
        result = self.output_text.toPlainText().strip()
        if not result:
            show_info(self, "提示", "没有可复制的内容")
            return
        QApplication.clipboard().setText(result)
        show_info(self, "完成", "已复制到剪贴板")
