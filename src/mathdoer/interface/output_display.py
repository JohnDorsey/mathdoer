"""The read-only output box."""
from collections.abc import Iterable

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import QFrame, QPlainTextEdit

from mathdoer.interface.fonts import monospace_font
from mathdoer.interface.styling import text_box_palette
from mathdoer.interface.theme import Theme
from mathdoer.output_text import utf16_length

PARAGRAPH_SEPARATORS = ("\n", " ")


def truncation_notice(discarded_character_count: int) -> str:
    return f"[output truncated: the oldest {discarded_character_count} characters were discarded]"


class OutputDisplay(QPlainTextEdit):
    """Shows a run's output.

    The document is, in order: a truncation notice (once text has been discarded), the
    output, and a progress line while a run is going. Positions are Qt's: UTF-16 units.
    """

    def __init__(self, theme: Theme, parent=None):
        super().__init__(parent)
        self._notice = ""
        self._notice_length = 0
        self._progress_length = 0
        self._default_format = self._text_format(theme.default_text)
        self._error_format = self._text_format(theme.error_text)
        self._notice_format = self._text_format(theme.notice_text)

        self.setReadOnly(True)
        self.setUndoRedoEnabled(False)
        self.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setFont(monospace_font())
        self.setPalette(text_box_palette(self.palette(), theme))

    @staticmethod
    def _text_format(color: str) -> QTextCharFormat:
        text_format = QTextCharFormat()
        text_format.setForeground(QColor(color))
        return text_format

    def clear_output(self) -> None:
        self.clear()
        self._notice = ""
        self._notice_length = 0
        self._progress_length = 0

    def apply_changes(
        self,
        segments: Iterable[tuple[str, bool]] = (),
        discarded_text: str = "",
        discarded_character_count: int = 0,
        progress_text: str | None = None,
    ) -> None:
        """Add output, then drop the text discarded from the beginning, then show the
        notice for the total discarded so far and the progress line, if any."""
        following = self._is_at_bottom()
        cursor = QTextCursor(self.document())
        cursor.beginEditBlock()
        self._remove_progress(cursor)
        for text, is_error in segments:
            self._insert_at_end(cursor, text, self._error_format if is_error else self._default_format)
        if discarded_text:
            self._remove_from_start_of_output(cursor, utf16_length(discarded_text))
        if discarded_character_count:
            self._show_notice(cursor, truncation_notice(discarded_character_count) + "\n")
        if progress_text is not None:
            self._insert_progress(cursor, progress_text)
        cursor.endEditBlock()
        if following:
            self._scroll_to_bottom()

    def output_text(self) -> str:
        """Everything shown except the progress line."""
        text = self.toPlainText()
        return text[: len(text) - self._progress_length]

    def append_marker(self, text: str) -> None:
        """Add a status line such as [cancelled], replacing the progress line."""
        following = self._is_at_bottom()
        cursor = QTextCursor(self.document())
        cursor.beginEditBlock()
        self._remove_progress(cursor)
        self._insert_at_end(cursor, self._line_break_if_needed() + text, self._notice_format)
        cursor.endEditBlock()
        if following:
            self._scroll_to_bottom()

    def _end_position(self) -> int:
        return self.document().characterCount() - 1

    def _line_break_if_needed(self) -> str:
        end = self._end_position()
        if end <= self._notice_length:
            return ""
        return "" if self.document().characterAt(end - 1) in PARAGRAPH_SEPARATORS else "\n"

    def _insert_at_end(self, cursor: QTextCursor, text: str, text_format: QTextCharFormat) -> None:
        cursor.setPosition(self._end_position())
        cursor.insertText(text, text_format)

    def _remove_progress(self, cursor: QTextCursor) -> None:
        if self._progress_length:
            end = self._end_position()
            cursor.setPosition(end - self._progress_length)
            cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
            cursor.removeSelectedText()
            self._progress_length = 0

    def _insert_progress(self, cursor: QTextCursor, text: str) -> None:
        text = self._line_break_if_needed() + text
        self._insert_at_end(cursor, text, self._default_format)
        self._progress_length = utf16_length(text)

    def _remove_from_start_of_output(self, cursor: QTextCursor, length: int) -> None:
        cursor.setPosition(self._notice_length)
        cursor.setPosition(self._notice_length + length, QTextCursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()

    def _show_notice(self, cursor: QTextCursor, notice: str) -> None:
        if notice == self._notice:
            return
        self._notice = notice
        cursor.setPosition(0)
        cursor.setPosition(self._notice_length, QTextCursor.MoveMode.KeepAnchor)
        cursor.insertText(notice, self._notice_format)
        self._notice_length = utf16_length(notice)

    def _is_at_bottom(self) -> bool:
        scroll_bar = self.verticalScrollBar()
        return scroll_bar.value() >= scroll_bar.maximum() - 1

    def _scroll_to_bottom(self) -> None:
        scroll_bar = self.verticalScrollBar()
        scroll_bar.setValue(scroll_bar.maximum())
