"""Home page: recent runs and a compact grid of all tools."""
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    CardWidget,
    FlowLayout,
    IconWidget,
    SmoothScrollArea,
    StrongBodyLabel,
    SubtitleLabel,
    TitleLabel,
)

from dataforge import __version__
from dataforge.config.recent import RecentEntry, RecentStore
from dataforge.ui.registry import ToolSpec

_ICON_SIZE = 24


def format_recent_time(timestamp: str, now: datetime) -> str:
    """`今天 HH:MM` / `昨天` / `YYYY-MM-DD`; unparsable input is returned unchanged."""
    try:
        moment = datetime.fromisoformat(timestamp)
    except ValueError:
        return timestamp
    if moment.date() == now.date():
        return f"今天 {moment:%H:%M}"
    if moment.date() == (now - timedelta(days=1)).date():
        return "昨天"
    return f"{moment:%Y-%m-%d}"


class HomePage(QWidget):
    def __init__(
        self,
        tools: tuple[ToolSpec, ...],
        recent: RecentStore,
        open_tool: Callable[[str, dict | None], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._tools = tools
        self._by_id = {t.id: t for t in tools}
        self._recent = recent
        self._open_tool = open_tool
        self._recent_cards: list[CardWidget] = []
        self._tool_cards: list[CardWidget] = []
        self._empty_label: CaptionLabel | None = None

        scroll = SmoothScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.enableTransparentBackground()  # before setWidget: keeps cards opaque
        body = QWidget()
        scroll.setWidget(body)
        # setWidget() turns autoFill on, which paints the light palette under dark-theme text.
        body.setAutoFillBackground(False)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        col = QVBoxLayout(body)
        col.setContentsMargins(24, 24, 24, 24)
        col.setSpacing(12)
        col.addWidget(TitleLabel("DataForge Studio", body))
        col.addWidget(CaptionLabel(f"v{__version__}", body))

        col.addSpacing(12)
        col.addWidget(SubtitleLabel("最近使用", body))
        self._recent_box = QVBoxLayout()
        self._recent_box.setSpacing(8)
        col.addLayout(self._recent_box)

        col.addSpacing(12)
        col.addWidget(SubtitleLabel("全部工具", body))
        grid_host = QWidget(body)
        grid = FlowLayout(grid_host, needAni=False)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)
        for spec in tools:
            card = self._make_tool_card(spec, grid_host)
            self._tool_cards.append(card)
            grid.addWidget(card)
        col.addWidget(grid_host)
        col.addStretch(1)

        self.refresh()

    def visible_recent(self) -> list[RecentEntry]:
        return [e for e in self._recent.entries() if e.tool_id in self._by_id]

    def recent_cards(self) -> list[CardWidget]:
        return list(self._recent_cards)

    def tool_cards(self) -> list[CardWidget]:
        return list(self._tool_cards)

    def refresh(self) -> None:
        for card in self._recent_cards:
            self._recent_box.removeWidget(card)
            card.deleteLater()
        self._recent_cards.clear()
        if self._empty_label is not None:
            self._recent_box.removeWidget(self._empty_label)
            self._empty_label.deleteLater()
            self._empty_label = None

        entries = self.visible_recent()
        if not entries:
            self._empty_label = CaptionLabel("还没有使用记录", self)
            self._recent_box.addWidget(self._empty_label)
            return
        now = datetime.now()
        for entry in entries:
            card = self._make_recent_card(entry, now)
            self._recent_cards.append(card)
            self._recent_box.addWidget(card)

    def _make_recent_card(self, entry: RecentEntry, now: datetime) -> CardWidget:
        spec = self._by_id[entry.tool_id]
        card = CardWidget(self)
        row = QHBoxLayout(card)
        row.setContentsMargins(16, 10, 16, 10)
        icon = IconWidget(spec.icon, card)
        icon.setFixedSize(_ICON_SIZE, _ICON_SIZE)
        row.addWidget(icon)
        text = QVBoxLayout()
        text.setSpacing(2)
        text.addWidget(StrongBodyLabel(spec.name, card))
        summary = BodyLabel(entry.summary, card)
        summary.setWordWrap(True)
        text.addWidget(summary)
        row.addLayout(text, 1)
        row.addWidget(
            CaptionLabel(format_recent_time(entry.timestamp, now), card),
            0,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )
        card.clicked.connect(
            lambda _=False, tid=entry.tool_id, st=entry.state: self._open_tool(tid, st)
        )
        return card

    def _make_tool_card(self, spec: ToolSpec, parent: QWidget) -> CardWidget:
        card = CardWidget(parent)
        row = QHBoxLayout(card)
        row.setContentsMargins(16, 10, 16, 10)
        icon = IconWidget(spec.icon, card)
        icon.setFixedSize(_ICON_SIZE, _ICON_SIZE)
        row.addWidget(icon)
        text = QVBoxLayout()
        text.setSpacing(2)
        text.addWidget(StrongBodyLabel(spec.name, card))
        text.addWidget(CaptionLabel(spec.description, card))
        row.addLayout(text, 1)
        card.clicked.connect(lambda _=False, tid=spec.id: self._open_tool(tid, None))
        return card
