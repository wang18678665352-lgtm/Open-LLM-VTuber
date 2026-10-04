"""深色控制台视图：按日志级别着色、限制最大行数、可选自动滚动。"""

from __future__ import annotations

from PySide6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import QPlainTextEdit

from ..core.text import level_of_line
from ..core.theme import PALETTE, mono_font_family


class ConsoleView(QPlainTextEdit):
    """只读控制台，按行着色，超过上限自动丢弃最早的行。"""

    MAX_BLOCKS = 6000

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("console")
        self.setReadOnly(True)
        self.setUndoRedoEnabled(False)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setMaximumBlockCount(self.MAX_BLOCKS)
        font = QFont(mono_font_family(), 10)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)

        self._formats: dict[str, QTextCharFormat] = {}
        mapping = {
            "text": PALETTE["console_fg"],
            "launcher": PALETTE["launcher"],
            "debug": PALETTE["debug"],
            "ok": PALETTE["ok"],
            "info": PALETTE["info"],
            "warn": PALETTE["warn"],
            "err": PALETTE["err"],
        }
        for key, color in mapping.items():
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(color))
            self._formats[key] = fmt

    # ------------------------------------------------------------------
    def append_text(self, text: str, autoscroll: bool = True) -> None:
        if not text:
            return
        scrollbar = self.verticalScrollBar()
        was_at_bottom = scrollbar.value() >= scrollbar.maximum() - 4

        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        for line in text.splitlines(keepends=True):
            cursor.insertText(line, self._formats[level_of_line(line)])
        self.setTextCursor(cursor)

        if autoscroll and (was_at_bottom or scrollbar.maximum() == 0):
            scrollbar.setValue(scrollbar.maximum())

    def clear_all(self) -> None:
        self.clear()
