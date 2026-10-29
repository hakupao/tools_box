"""Scan result view: status, per-file table and date-order choices."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import BodyLabel, ComboBox, PushButton, TableWidget

from dataforge.dates import SlashOrder
from dataforge.tools.masking.scan import ScanReport

_HEADERS = ("文件", "编码", "行数", "受试者", "有值字段数", "空字段数", "日期列")
_ORDER_CHOICES: tuple[tuple[str, SlashOrder | None], ...] = (
    ("请选择", None),
    ("日/月/年", SlashOrder.DAY_FIRST),
    ("月/日/年", SlashOrder.MONTH_FIRST),
)


class ScanResultView(QWidget):
    orders_changed = Signal()
    rescan_requested = Signal()
    export_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._report: ScanReport | None = None
        self._locked = False
        self._orders: list[tuple[tuple[str, str], str, ComboBox]] = []

        self.status_label = BodyLabel("", self)
        self.status_label.setWordWrap(True)
        self.table = TableWidget(self)
        self.table.setColumnCount(len(_HEADERS))
        self.table.setHorizontalHeaderLabels(list(_HEADERS))
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        self._orders_host = QWidget(self)
        self._orders_layout = QVBoxLayout(self._orders_host)
        self._orders_layout.setContentsMargins(0, 0, 0, 0)

        self.rescan_button = PushButton("重新扫描", self)
        self.export_button = PushButton("导出扫描报告…", self)
        buttons = QHBoxLayout()
        buttons.addWidget(self.rescan_button)
        buttons.addWidget(self.export_button)
        buttons.addStretch(1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.status_label)
        layout.addWidget(self.table)
        layout.addWidget(self._orders_host)
        layout.addLayout(buttons)

        self.rescan_button.clicked.connect(self.rescan_requested)
        self.export_button.clicked.connect(self.export_requested)
        self.show_report(None)

    # -- public API ------------------------------------------------------------------
    def show_report(self, report: ScanReport | None) -> None:
        self._report = report
        self._fill_status(report)
        self._fill_table(report)
        self._fill_orders(report)
        self._refresh_enabled()

    def report(self) -> ScanReport | None:
        return self._report

    def orders(self) -> dict[tuple[str, str], SlashOrder]:
        chosen: dict[tuple[str, str], SlashOrder] = {}
        for key, _, combo in self._orders:
            order = _ORDER_CHOICES[max(0, combo.currentIndex())][1]
            if order is not None:
                chosen[key] = order
        return chosen

    def order_combos(self) -> list[tuple[str, ComboBox]]:
        return [(label, combo) for _, label, combo in self._orders]

    def status_text(self) -> str:
        return self.status_label.text()

    def set_locked(self, locked: bool) -> None:
        self._locked = locked
        self._refresh_enabled()

    # -- internals -------------------------------------------------------------------
    def _refresh_enabled(self) -> None:
        free = not self._locked
        self.rescan_button.setEnabled(free)
        self.export_button.setEnabled(free and self._report is not None)
        for _, _, combo in self._orders:
            combo.setEnabled(free)

    def _fill_status(self, report: ScanReport | None) -> None:
        if report is None:
            text = "尚未扫描"
        elif report.processable:
            text = f"扫描通过：{len(report.files)} 个文件，DM 受试者 {len(report.subjects)} 个"
        else:
            text = '扫描未通过，请查看"警告"和结果区的错误'
        self.status_label.setText(text)

    def _fill_table(self, report: ScanReport | None) -> None:
        files = report.files if report is not None else []
        self.table.setRowCount(len(files))
        for row, f in enumerate(files):
            values = (
                f.file_name,
                f.encoding,
                str(f.row_count),
                str(f.unique_usubjid_count),
                str(len(f.non_empty_fields)),
                str(len(f.empty_fields)),
                "、".join(f.date_fields),
            )
            for col, value in enumerate(values):
                self.table.setItem(row, col, QTableWidgetItem(value))
        self.table.setVisible(bool(files))

    def _fill_orders(self, report: ScanReport | None) -> None:
        while self._orders_layout.count():
            item = self._orders_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._orders = []
        columns = report.ambiguous_columns if report is not None else []
        for column in columns:
            row = QWidget(self._orders_host)
            label = f"{column.file_name} · {column.column}（{column.ambiguous} 个无法判断）"
            combo = ComboBox(row)
            combo.addItems([text for text, _ in _ORDER_CHOICES])
            combo.currentIndexChanged.connect(self._on_order_changed)
            line = QHBoxLayout(row)
            line.setContentsMargins(0, 0, 0, 0)
            line.addWidget(BodyLabel(label, row), 1)
            line.addWidget(combo)
            self._orders_layout.addWidget(row)
            self._orders.append(((column.file_name, column.column), label, combo))
        self._orders_host.setVisible(bool(columns))

    def _on_order_changed(self, *_args: object) -> None:
        self.orders_changed.emit()
