"""The find and replace bar above the prompt box.

Searches are plain text, case-insensitive unless Match case is on, and look at the prompt box
only. The match the caret is on is the prompt box's own selection; every other match is
highlighted. Searching goes round from the end of the text to the start and back.
"""
from bisect import bisect_left

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QKeyEvent, QPalette, QTextCursor, QTextDocument
from PySide6.QtWidgets import (
    QCheckBox,
    QGridLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QToolButton,
    QWidget,
)

from mathdoer.interface.fonts import monospace_font
from mathdoer.interface.prompt_editor import PromptEditor
from mathdoer.interface.styling import text_box_palette, window_palette
from mathdoer.interface.theme import Theme
from mathdoer.utf16 import utf16_length

MATCH_LIMIT = 2000  # matches beyond this are neither counted nor highlighted
CLOSE_BUTTON_POINT_SIZE = 16
CLOSE_BUTTON_SIZE = 28  # pixels
ROW_SPACING = 4

PARAGRAPH_SEPARATOR = " "  # what a selection spanning lines contains instead of a line break


class _SearchField(QLineEdit):
    """A line of text where Enter, or Shift+Enter, asks for something rather than ending the edit."""

    enter_pressed = Signal(bool)  # True if Shift was held

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            modifiers = event.modifiers() & ~Qt.KeyboardModifier.KeypadModifier
            if modifiers in (Qt.KeyboardModifier.NoModifier, Qt.KeyboardModifier.ShiftModifier):
                self.enter_pressed.emit(modifiers == Qt.KeyboardModifier.ShiftModifier)
                event.accept()
            else:
                event.ignore()  # Ctrl+Enter runs the prompt; the window handles it
            return
        super().keyPressEvent(event)


class FindBar(QWidget):
    def __init__(self, editor: PromptEditor, theme: Theme, parent=None):
        super().__init__(parent)
        self._editor = editor
        self._match_starts: list[int] = []
        self._more_matches_than_the_limit = False
        self._status: str | None = None  # shown instead of the count, such as "Replaced 3"

        self.setAutoFillBackground(True)
        palette = window_palette(theme)
        palette.setColor(QPalette.ColorRole.Window, QColor(theme.panel_background))
        self.setPalette(palette)

        self.find_field = _SearchField()
        self.find_field.setPlaceholderText("Find")
        self.replace_field = _SearchField()
        self.replace_field.setPlaceholderText("Replace")
        for field in (self.find_field, self.replace_field):
            field.setFont(monospace_font())
        self.match_case_box = QCheckBox("Match case")
        self.counter_label = QLabel()
        self.counter_label.setMinimumWidth(self.counter_label.fontMetrics().horizontalAdvance(f"{MATCH_LIMIT}+ matches"))
        self.close_button = QToolButton()
        self.close_button.setText("×")
        self.close_button.setToolTip("Close (Esc)")
        self.close_button.setAutoRaise(True)
        self.replace_button = QPushButton("Replace")
        self.replace_all_button = QPushButton("Replace all")

        # Each child gets its palette explicitly: a widget does not reliably inherit one.
        field_palette = text_box_palette(palette, theme)
        field_style = (
            f"QLineEdit {{ border: 1px solid {theme.control_border}; padding: 2px 4px; "
            f"background: {theme.text_background}; color: {theme.default_text}; "
            f"placeholder-text-color: {theme.disabled_text}; "
            f"selection-background-color: {theme.selection_background}; "
            f"selection-color: {theme.selection_text}; }}"
            f"QLineEdit:focus {{ border: 1px solid {theme.default_text}; }}"
        )
        for field in (self.find_field, self.replace_field):
            field.setPalette(field_palette)
            field.setStyleSheet(field_style)
        close_font = self.close_button.font()
        close_font.setPointSize(CLOSE_BUTTON_POINT_SIZE)
        close_font.setBold(True)
        self.close_button.setFont(close_font)
        self.close_button.setFixedSize(CLOSE_BUTTON_SIZE, CLOSE_BUTTON_SIZE)
        for widget in (self.match_case_box, self.close_button, self.replace_button, self.replace_all_button):
            widget.setPalette(palette)
        self._normal_counter_palette = QPalette(palette)
        self._error_counter_palette = QPalette(palette)
        self._error_counter_palette.setColor(QPalette.ColorRole.WindowText, QColor(theme.error_text))

        # One grid, so the two fields share their left and right edges, and Replace all
        # ends under the close button.
        self._layout = QGridLayout(self)
        self._layout.setContentsMargins(6, 4, 6, 4)
        self._layout.setHorizontalSpacing(6)
        self._layout.setVerticalSpacing(ROW_SPACING)
        self._layout.addWidget(self.find_field, 0, 0)
        self._layout.addWidget(self.match_case_box, 0, 1)
        self._layout.addWidget(self.counter_label, 0, 2)
        self._layout.addWidget(self.close_button, 0, 3)
        self._layout.addWidget(self.replace_field, 1, 0)
        self._layout.addWidget(self.replace_button, 1, 1)
        self._layout.addWidget(self.replace_all_button, 1, 2, 1, 2)
        self._layout.setColumnStretch(0, 1)
        self._replace_widgets = (self.replace_field, self.replace_button, self.replace_all_button)
        self._set_replace_row_visible(False)
        self.hide()

        self.find_field.textChanged.connect(self._search_changed)
        self.match_case_box.toggled.connect(self._search_changed)
        self.find_field.enter_pressed.connect(lambda backwards: self._step(forward=not backwards))
        self.replace_field.enter_pressed.connect(lambda backwards: self.replace_current())
        self.replace_button.clicked.connect(self.replace_current)
        self.replace_all_button.clicked.connect(self.replace_all)
        self.close_button.clicked.connect(self.close_bar)
        editor.cursorPositionChanged.connect(self._selection_changed)
        editor.document().contentsChanged.connect(self._text_changed)

    # ------------------------------------------------------------ opening and closing

    def show_find(self) -> None:
        self._open(prefill=True, focus=True)

    def show_replace(self) -> None:
        self._set_replace_row_visible(True)
        self._open(prefill=True, focus=True)

    def _set_replace_row_visible(self, visible: bool) -> None:
        for widget in self._replace_widgets:
            widget.setVisible(visible)

    def step_from_shortcut(self, forward: bool) -> None:
        """F3 and Shift+F3: with no search yet, open the bar to type one; otherwise go to the
        next or previous match, bringing the bar back if it was closed but leaving the focus."""
        if not self.find_field.text():
            self._open(prefill=True, focus=True)
            return
        if self.isHidden():
            self._open(prefill=False, focus=False)
        self._step(forward)

    def close_bar(self) -> None:
        if self.isHidden():
            return
        self.hide()
        self._status = None
        self._editor.set_search_highlights([])
        self._editor.setFocus()

    def _open(self, prefill: bool, focus: bool) -> None:
        self.show()
        if prefill:
            selected = self._editor.textCursor().selectedText()
            if selected and PARAGRAPH_SEPARATOR not in selected:
                self.find_field.setText(selected)
        self._refresh_search_display()
        if focus:
            self.find_field.setFocus()
            self.find_field.selectAll()

    # ---------------------------------------------------------------------- finding

    def find_next(self) -> bool:
        return self._step(forward=True)

    def find_previous(self) -> bool:
        return self._step(forward=False)

    def _step(self, forward: bool) -> bool:
        text = self.find_field.text()
        if not text:
            return False
        self._status = None
        cursor = self._editor.textCursor()
        start = cursor.selectionEnd() if forward else cursor.selectionStart()
        found = self._find(text, start, forward)
        if found is None:
            self._render_counter()
            return False
        self._select(*found)
        return True

    def _find(self, text: str, start: int, forward: bool) -> tuple[int, int] | None:
        """The first match from the position in the direction, going round the text if need be."""
        document = self._editor.document()
        flags = self._flags() | (QTextDocument.FindFlag(0) if forward else QTextDocument.FindFlag.FindBackward)
        found = document.find(text, start, flags)
        if found.isNull():
            found = document.find(text, 0 if forward else document.characterCount() - 1, flags)
        if found.isNull():
            return None
        return found.selectionStart(), found.selectionEnd()

    def _select(self, start: int, end: int) -> None:
        cursor = QTextCursor(self._editor.document())
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
        self._editor.setTextCursor(cursor)
        self._editor.ensureCursorVisible()

    def _flags(self) -> QTextDocument.FindFlag:
        flags = QTextDocument.FindFlag(0)
        if self.match_case_box.isChecked():
            flags |= QTextDocument.FindFlag.FindCaseSensitively
        return flags

    # -------------------------------------------------------------------- replacing

    def replace_current(self) -> None:
        """Replace the selected match, if the selection is one, and go on to the next."""
        text = self.find_field.text()
        if not text:
            return
        cursor = self._editor.textCursor()
        if self._is_a_match(cursor):
            cursor.insertText(self.replace_field.text())
            self._editor.setTextCursor(cursor)
        self._step(forward=True)

    def replace_all(self) -> None:
        """Replace every match, as one step that undo takes back in one go."""
        text = self.find_field.text()
        if not text:
            return
        document = self._editor.document()
        flags = self._flags()
        matches = []
        found = document.find(text, 0, flags)
        while not found.isNull():
            matches.append((found.selectionStart(), found.selectionEnd()))
            found = document.find(text, found, flags)
        if not matches:
            return
        editing = QTextCursor(document)
        editing.beginEditBlock()
        for start, end in reversed(matches):  # from the end, so the earlier positions stay valid
            editing.setPosition(start)
            editing.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
            editing.insertText(self.replace_field.text())
        editing.endEditBlock()
        self._show_status(f"Replaced {len(matches)}")

    def _is_a_match(self, cursor: QTextCursor) -> bool:
        if not cursor.hasSelection():
            return False
        found = self._editor.document().find(self.find_field.text(), cursor.selectionStart(), self._flags())
        return (
            not found.isNull()
            and found.selectionStart() == cursor.selectionStart()
            and found.selectionEnd() == cursor.selectionEnd()
        )

    # ----------------------------------------------------- what the bar keeps showing

    def _search_changed(self) -> None:
        """The text searched for, or Match case, changed: go to the first match from the caret."""
        if self.isHidden():
            return
        text = self.find_field.text()
        if text:
            found = self._find(text, self._editor.textCursor().selectionStart(), forward=True)
            if found is not None:
                self._select(*found)
        self._refresh_search_display()

    def _text_changed(self) -> None:
        if not self.isHidden():
            self._refresh_search_display()

    def _selection_changed(self) -> None:
        if not self.isHidden():
            self._status = None
            self._render_counter()

    def _refresh_search_display(self) -> None:
        """Find all the matches again, highlight them and update the count."""
        text = self.find_field.text()
        starts = []
        if text:
            document = self._editor.document()
            flags = self._flags()
            found = document.find(text, 0, flags)
            while not found.isNull() and len(starts) <= MATCH_LIMIT:
                starts.append(found.selectionStart())
                found = document.find(text, found, flags)
        self._more_matches_than_the_limit = len(starts) > MATCH_LIMIT
        self._match_starts = starts[:MATCH_LIMIT]

        length = utf16_length(text)
        highlights = []
        for start in self._match_starts:
            cursor = QTextCursor(self._editor.document())
            cursor.setPosition(start)
            cursor.setPosition(start + length, QTextCursor.MoveMode.KeepAnchor)
            highlights.append(cursor)
        self._editor.set_search_highlights(highlights)
        self._render_counter()

    def _show_status(self, status: str) -> None:
        self._status = status
        self._render_counter()

    def _render_counter(self) -> None:
        text = self.find_field.text()
        self.counter_label.setPalette(self._normal_counter_palette)
        if self._status is not None:
            self.counter_label.setText(self._status)
        elif not text:
            self.counter_label.setText("")
        elif not self._match_starts:
            self.counter_label.setPalette(self._error_counter_palette)
            self.counter_label.setText("No matches")
        else:
            count = f"{len(self._match_starts)}{'+' if self._more_matches_than_the_limit else ''}"
            index = self._index_of_selected_match(text)
            if index is not None:
                self.counter_label.setText(f"{index + 1} of {count}")
            else:
                noun = "match" if count == "1" else "matches"
                self.counter_label.setText(f"{count} {noun}")

    def _index_of_selected_match(self, text: str) -> int | None:
        cursor = self._editor.textCursor()
        index = bisect_left(self._match_starts, cursor.selectionStart())
        if (
            index < len(self._match_starts)
            and self._match_starts[index] == cursor.selectionStart()
            and cursor.selectionEnd() == cursor.selectionStart() + utf16_length(text)
        ):
            return index
        return None
