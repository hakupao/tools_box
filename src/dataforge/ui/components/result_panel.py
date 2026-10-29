"""Tabbed result / warnings / log panel with a collapsible summary."""
from __future__ import annotations

from PySide6.QtWidgets import QStackedWidget, QVBoxLayout, QWidget
from qfluentwidgets import PlainTextEdit, SegmentedWidget, TransparentPushButton

from dataforge.core.result import Result

_KEYS = ("result", "warnings", "log")


def _issue_line(path: str, message: str) -> str:
    return f"{path}: {message}" if path else message


class ResultPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._outputs = 0
        self._issues = 0
        self._summary = TransparentPushButton(self)
        self._tabs = SegmentedWidget(self)
        self._stack = QStackedWidget(self)
        self._edits: dict[str, PlainTextEdit] = {}
        for key, text in zip(_KEYS, ("结果", "警告", "日志")):
            edit = PlainTextEdit(self)
            edit.setReadOnly(True)
            self._edits[key] = edit
            self._stack.addWidget(edit)
            self._tabs.addItem(key, text, onClick=lambda k=key: self._select(k))
        self._tabs.setCurrentItem("result")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._summary)
        layout.addWidget(self._tabs)
        layout.addWidget(self._stack, 1)
        self._summary.clicked.connect(lambda: self.set_collapsed(False))
        self._summary.setVisible(False)
        self._refresh_labels()

    def _select(self, key: str) -> None:
        self._stack.setCurrentWidget(self._edits[key])
        self._tabs.setCurrentItem(key)

    def _refresh_labels(self) -> None:
        self._tabs.items["result"].setText(f"结果 ({self._outputs})")
        self._tabs.items["warnings"].setText(f"警告 ({self._issues})")
        self._summary.setText(self.summary_text())

    def show_result(self, result: Result) -> None:
        lines = [str(p) for p in result.outputs]
        if result.stats:
            lines.append("")
            lines.extend(f"{k}: {v}" for k, v in result.stats.items())
        self._edits["result"].setPlainText("\n".join(lines))
        issues = [
            *(_issue_line(i.path, i.message) for i in result.warnings),
            *(_issue_line(i.path, i.message) for i in result.errors),
            *(f"{q.path}: 需要选择编码" for q in result.encoding_questions),
        ]
        self._edits["warnings"].setPlainText("\n".join(issues))
        self._outputs = len(result.outputs)
        self._issues = len(issues)
        self._refresh_labels()

    def append_log(self, line: str) -> None:
        self._edits["log"].appendPlainText(line)

    def clear(self) -> None:
        for edit in self._edits.values():
            edit.clear()
        self._outputs = 0
        self._issues = 0
        self._refresh_labels()

    def tab_text(self, key: str) -> str:
        """Label of a tab: 'result', 'warnings' or 'log'."""
        return self._tabs.items[key].text()

    def page_text(self, key: str) -> str:
        return self._edits[key].toPlainText()

    def is_collapsed(self) -> bool:
        return self._stack.isHidden()

    def summary_button(self) -> TransparentPushButton:
        return self._summary

    def summary_text(self) -> str:
        return f"{self._outputs} 个输出 · {self._issues} 个问题"

    def set_collapsed(self, collapsed: bool) -> None:
        self._summary.setVisible(collapsed)
        self._tabs.setVisible(not collapsed)
        self._stack.setVisible(not collapsed)
