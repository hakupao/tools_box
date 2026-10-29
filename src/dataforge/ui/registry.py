from __future__ import annotations

import importlib
from dataclasses import dataclass
from enum import Enum

from qfluentwidgets import FluentIcon


class ToolGroup(Enum):
    FILES = "文件处理"
    BUSINESS = "业务"
    UTILS = "小工具"


@dataclass(frozen=True)
class ToolSpec:
    id: str
    name: str
    description: str
    group: ToolGroup
    icon: FluentIcon
    page: str  # "module.path:ClassName"


TOOLS: tuple[ToolSpec, ...] = (
    ToolSpec(
        id="sheet_split",
        name="工作表拆分",
        description="每个工作表导出为一个 CSV",
        group=ToolGroup.FILES,
        icon=FluentIcon.LAYOUT,
        page="dataforge.ui.pages.sheet_split_page:SheetSplitPage",
    ),
    ToolSpec(
        id="field_extract",
        name="获取字段",
        description="批量读取 CSV / Excel 表头并汇总",
        group=ToolGroup.FILES,
        icon=FluentIcon.SEARCH,
        page="dataforge.ui.pages.field_extract_page:FieldExtractPage",
    ),
    ToolSpec(
        id="date_convert",
        name="日期转换",
        description="文本中的日期转为 ISO 8601",
        group=ToolGroup.UTILS,
        icon=FluentIcon.CALENDAR,
        page="dataforge.ui.pages.date_convert_page:DateConvertPage",
    ),
    ToolSpec(
        id="width_convert",
        name="全角转半角",
        description="Excel 中的全角英数符号转半角",
        group=ToolGroup.UTILS,
        icon=FluentIcon.FONT,
        page="dataforge.ui.pages.width_convert_page:WidthConvertPage",
    ),
)


def get_tool(tool_id: str) -> ToolSpec:
    for spec in TOOLS:
        if spec.id == tool_id:
            return spec
    raise KeyError(tool_id)


def load_page_class(spec: ToolSpec) -> type:
    module_name, _, class_name = spec.page.partition(":")
    return getattr(importlib.import_module(module_name), class_name)
