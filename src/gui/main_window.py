from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    CardWidget,
    FluentIcon as FIF,
    FluentWindow,
    NavigationItemPosition,
    PrimaryPushButton,
    SubtitleLabel,
    TitleLabel,
)

from src.version import VERSION
from .widgets.codelist_processor import CodelistProcessorPage
from .widgets.csv_quote_remover import CsvQuoteRemoverPage
from .widgets.data_cleaner import DataCleanerPage
from .widgets.data_masking import DataMaskingPage
from .widgets.date_converter import DateConverterPage
from .widgets.dead_link_checker import DeadLinkCheckerPage
from .widgets.edc_site_adder import EdcSiteAdderPage
from .widgets.file_field_extractor import FileFieldExtractorPage
from .widgets.file_format_converter import FileFormatConverterPage
from .widgets.fullwidth_halfwidth_converter import FullwidthHalfwidthConverterPage
from .widgets.xlsx_file_restructuring import FileRestructurePage
from .widgets.xlsx_sheet_splitter import XlsxSheetSplitterPage


TOOL_CATEGORIES = [
    {
        "name": "文件处理",
        "description": "文件格式、结构和内容处理工具",
        "tools": [
            {
                "id": "file_format",
                "name": "文件格式转换",
                "icon": "🔄",
                "desc": "支持 CSV、Excel、SAS 等多种格式互转",
            },
            {
                "id": "xlsx_sheet_splitter",
                "name": "工作表拆分",
                "icon": "📄",
                "desc": "将 Excel 工作表拆分为多个 CSV",
            },
            {
                "id": "file_restructure",
                "name": "生成 Data Set",
                "icon": "📊",
                "desc": "快速生成标准化数据集结构",
            },
            {
                "id": "file_field_extractor",
                "name": "获取文件字段",
                "icon": "📋",
                "desc": "提取文件中的字段信息列表",
            },
            {
                "id": "dead_link_checker",
                "name": "死链检测",
                "icon": "🔗",
                "desc": "检测文件或网页中的无效链接",
            },
        ],
    },
    {
        "name": "数据处理",
        "description": "数据清洗、转换和处理工具",
        "tools": [
            {
                "id": "data_cleaner",
                "name": "数据清洗",
                "icon": "🧹",
                "desc": "清理数据中的异常值和空白",
            },
            {
                "id": "data_masking",
                "name": "数据模糊化",
                "icon": "🔒",
                "desc": "对敏感数据进行脱敏处理",
            },
            {
                "id": "codelist_processor",
                "name": "Codelist 处理",
                "icon": "📝",
                "desc": "处理和管理代码列表数据",
            },
            {
                "id": "edc_site_adder",
                "name": "EDC 施设添加",
                "icon": "🏥",
                "desc": "EDC 系统施设信息批量添加",
            },
        ],
    },
    {
        "name": "格式转换",
        "description": "文本和格式快速转换工具",
        "tools": [
            {
                "id": "date_converter",
                "name": "日期转换",
                "icon": "📅",
                "desc": "多种日期格式智能转换",
            },
            {
                "id": "fullwidth_halfwidth",
                "name": "全角转半角",
                "icon": "🔡",
                "desc": "全角半角字符快速转换",
            },
            {
                "id": "csv_quote_remover",
                "name": "CSV 引号去除",
                "icon": "✂️",
                "desc": "批量去除 CSV 文件中的引号",
            },
        ],
    },
]


class ToolCard(CardWidget):
    def __init__(self, tool: dict, open_callback: Callable[[str], None], parent=None) -> None:
        super().__init__(parent)
        self.tool_id = tool["id"]
        self.setObjectName(f"card_{self.tool_id}")
        self.setMinimumWidth(240)
        self.setMaximumWidth(320)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        icon_label = TitleLabel(tool["icon"])
        icon_label.setAlignment(Qt.AlignLeft)

        name_label = BodyLabel(tool["name"])
        name_label.setWordWrap(True)

        desc_label = CaptionLabel(tool["desc"])
        desc_label.setWordWrap(True)
        desc_label.setTextColor(QColor("#7A8190"), QColor("#7A8190"))

        open_btn = PrimaryPushButton("打开工具")
        open_btn.clicked.connect(lambda: open_callback(self.tool_id))

        layout.addWidget(icon_label)
        layout.addWidget(name_label)
        layout.addWidget(desc_label)
        layout.addStretch(1)
        layout.addWidget(open_btn)


class HomePage(QWidget):
    def __init__(self, categories: list[dict], open_callback: Callable[[str], None], parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("home")
        self.setStyleSheet(
            """
            QWidget#home { background: #F5F6F8; }
            QScrollArea { background: transparent; }
            QScrollArea > QWidget > QWidget { background: #F5F6F8; }
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        scroll.setWidget(container)

        content_layout = QVBoxLayout(container)
        content_layout.setContentsMargins(36, 30, 36, 30)
        content_layout.setSpacing(28)

        header_frame = QFrame()
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(20)

        title_block = QVBoxLayout()
        title = TitleLabel("工具箱")
        subtitle = SubtitleLabel(f"实用工具集合  •  v{VERSION}  •  Win11 Fluent UI")
        subtitle.setWordWrap(True)
        title_block.addWidget(title)
        title_block.addWidget(subtitle)
        title_block.addStretch(1)

        header_layout.addLayout(title_block, stretch=1)

        content_layout.addWidget(header_frame)

        for category in categories:
            section = QFrame()
            section_layout = QVBoxLayout(section)
            section_layout.setContentsMargins(0, 0, 0, 0)
            section_layout.setSpacing(12)

            name_label = TitleLabel(category["name"])
            desc_label = CaptionLabel(category["description"])
            desc_label.setTextColor(QColor("#7A8190"), QColor("#7A8190"))

            grid = QGridLayout()
            grid.setHorizontalSpacing(16)
            grid.setVerticalSpacing(16)

            for idx, tool in enumerate(category["tools"]):
                row = idx // 3
                col = idx % 3
                card = ToolCard(tool, open_callback)
                grid.addWidget(card, row, col)

            section_layout.addWidget(name_label)
            section_layout.addWidget(desc_label)
            section_layout.addLayout(grid)
            content_layout.addWidget(section)

        content_layout.addStretch(1)
        layout.addWidget(scroll)


class MainWindow(FluentWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("工具箱")
        self.resize(1280, 860)
        self.setMinimumSize(1160, 760)
        try:
            self.setMicaEffectEnabled(False)
        except Exception:
            pass
        self.navigationInterface.panel.setExpandWidth(220)
        self.navigationInterface.panel.setMinimumExpandWidth(900)
        self.navigationInterface.panel.expand(False)

        self.tool_pages: dict[str, QWidget] = {}

        self.home_interface = HomePage(TOOL_CATEGORIES, self.open_tool)
        self.addSubInterface(self.home_interface, FIF.HOME, "主页")

        self._register_tool_page("date_converter", DateConverterPage(self), FIF.CALENDAR, "日期转换")
        self._register_tool_page("file_format", FileFormatConverterPage(self), FIF.SYNC, "文件格式转换")
        self._register_tool_page("file_restructure", FileRestructurePage(self), FIF.DOCUMENT, "生成 Data Set")
        self._register_tool_page("file_field_extractor", FileFieldExtractorPage(self), FIF.LIBRARY, "获取文件字段")
        self._register_tool_page("dead_link_checker", DeadLinkCheckerPage(self), FIF.LINK, "死链检测")
        self._register_tool_page("data_cleaner", DataCleanerPage(self), FIF.BROOM, "数据清洗")
        self._register_tool_page("codelist_processor", CodelistProcessorPage(self), FIF.DICTIONARY, "Codelist 处理")
        self._register_tool_page("data_masking", DataMaskingPage(self), FIF.FINGERPRINT, "数据模糊化")
        self._register_tool_page("edc_site_adder", EdcSiteAdderPage(self), FIF.ROBOT, "EDC 施设添加")
        self._register_tool_page("fullwidth_halfwidth", FullwidthHalfwidthConverterPage(self), FIF.FONT, "全角转半角")
        self._register_tool_page("csv_quote_remover", CsvQuoteRemoverPage(self), FIF.CUT, "CSV 引号去除")
        self._register_tool_page("xlsx_sheet_splitter", XlsxSheetSplitterPage(self), FIF.CLIPPING_TOOL, "工作表拆分")

        self.switch_to(self.home_interface)

    def _register_tool_page(self, tool_id: str, page: QWidget, icon, title: str) -> None:
        self.tool_pages[tool_id] = page
        self.addSubInterface(page, icon, title, position=NavigationItemPosition.TOP)

    def switch_to(self, widget: QWidget) -> None:
        self.stackedWidget.setCurrentWidget(widget)
        self.navigationInterface.setCurrentItem(widget.objectName())

    def open_tool(self, tool_id: str) -> None:
        page = self.tool_pages.get(tool_id)
        if page is None:
            return
        self.switch_to(page)
