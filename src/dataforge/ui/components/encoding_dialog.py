"""Dialog for resolving ambiguous file encodings, plus the batch asking loop."""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtWidgets import QButtonGroup, QWidget
from qfluentwidgets import CheckBox, MessageBoxBase, PlainTextEdit, RadioButton, StrongBodyLabel

from dataforge.core.result import EncodingQuestion
from dataforge.fileio.encoding import ENCODING_LABELS


_last_choice: str | None = None


def reset_encoding_memory() -> None:
    global _last_choice
    _last_choice = None


class EncodingChoiceDialog(MessageBoxBase):
    def __init__(
        self, parent: QWidget, question: EncodingQuestion, default: str | None = None
    ) -> None:
        super().__init__(parent)
        self.yesButton.setText("确定")
        self.cancelButton.setText("取消")
        self.viewLayout.addWidget(StrongBodyLabel("选择编码", self))
        self.viewLayout.addWidget(StrongBodyLabel(Path(question.path).name, self))
        self._group = QButtonGroup(self)
        self._radios: dict[str, RadioButton] = {}
        for enc, preview in question.previews.items():
            radio = RadioButton(ENCODING_LABELS.get(enc, enc), self)
            self._group.addButton(radio)
            self._radios[enc] = radio
            edit = PlainTextEdit(self)
            edit.setReadOnly(True)
            edit.setPlainText(preview)
            self.viewLayout.addWidget(radio)
            self.viewLayout.addWidget(edit)
        if self._radios:
            preselect = default if default in self._radios else next(iter(self._radios))
            self._radios[preselect].setChecked(True)
        self._rest = CheckBox("本批其余文件也用此编码", self)
        self.viewLayout.addWidget(self._rest)

    def chosen(self) -> str:
        for enc, radio in self._radios.items():
            if radio.isChecked():
                return enc
        return next(iter(self._radios), "")

    def apply_to_rest(self) -> bool:
        return self._rest.isChecked()


def _dispose(dialog: object) -> None:
    delete = getattr(dialog, "deleteLater", None)
    if delete is not None:
        delete()


def ask_encodings(
    parent: QWidget,
    questions: list[EncodingQuestion],
    dialog_factory: Callable[[QWidget, EncodingQuestion, str | None], object] = EncodingChoiceDialog,
) -> dict[str, str]:
    """Ask for each question's encoding; stop at the first cancel and return answers so far."""
    global _last_choice
    answers: dict[str, str] = {}
    sticky: str | None = None
    for question in questions:
        if sticky is not None and sticky in question.previews:
            answers[question.path] = sticky
            continue
        dialog = dialog_factory(parent, question, _last_choice)
        try:
            accepted = dialog.exec()
            chosen = dialog.chosen() if accepted else None
            rest = bool(accepted) and dialog.apply_to_rest()
        finally:
            _dispose(dialog)
        if not accepted:
            break
        answers[question.path] = chosen
        _last_choice = chosen
        if rest:
            sticky = chosen
    return answers
