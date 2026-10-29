"""Confirmation dialogs with explicit Chinese button texts."""
from __future__ import annotations

from qfluentwidgets import MessageBox


def use_chinese_buttons(box: MessageBox) -> MessageBox:
    box.yesButton.setText("确定")
    box.cancelButton.setText("取消")
    return box
