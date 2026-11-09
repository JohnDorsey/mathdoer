"""The prompt box: a text box that edits code the way a code editor does."""
from collections.abc import Callable, Iterator, Sequence
from typing import NamedTuple

from PySide6.QtCore import QEvent, QRect, QSize, Qt
from PySide6.QtGui import QColor, QKeyEvent, QPainter, QPaintEvent, QResizeEvent, QTextBlock, QTextCursor, QTextDocument
from PySide6.QtWidgets import QTextEdit, QWidget

from mathdoer.bracket_matching import find_bracket_pair
from mathdoer.indentation_guides import guide_columns
from mathdoer.interface.syntax_highlighter import SyntaxHighlighter
from mathdoer.interface.text_box import TextBox
from mathdoer.interface.theme import Theme
from mathdoer.languages import Language
from mathdoer.line_editing import (
    Position,
    TextEdit,
    dedent,
    delete_lines,
    duplicate_lines,
    home_column,
    indent,
    insert_newline,
    move_lines,
    toggle_comment,
)
from mathdoer.utf16 import index_at_utf16_offset, utf16_length

Key = Qt.Key
Modifier = Qt.KeyboardModifier

GUTTER_PADDING = 8  # pixels on each side of the line numbers
MINIMUM_GUTTER_DIGITS = 3  # so the gutter does not change width until a thousand lines


class IndentationGuide(NamedTuple):
    """One guide: the line it is on, the column it stands in, and where it is in the viewport."""

    line: int
    column: int
    x: int
    top: int
    bottom: int


class _DocumentLines(Sequence[str]):
    """The lines of a text document, read from its blocks only as they are asked for."""

    def __init__(self, document: QTextDocument):
        self._document = document

    def __len__(self) -> int:
        return self._document.blockCount()

    def __getitem__(self, index):
        if isinstance(index, slice):
            return [self[position] for position in range(*index.indices(len(self)))]
        if index < 0:
            index += len(self)
        if not 0 <= index < len(self):
            raise IndexError(index)
        return self._document.findBlockByNumber(index).text()


class _LineNumberGutter(QWidget):
    """The strip to the left of the text that shows the line numbers. The editor paints it."""

    def __init__(self, editor: "PromptEditor"):
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self) -> QSize:
        return QSize(self._editor.gutter_width(), 0)

    def paintEvent(self, event: QPaintEvent) -> None:
        self._editor.paint_gutter(event)


class PromptEditor(TextBox):
    _ready = False  # set once everything the font-change handler uses exists

    def __init__(self, theme: Theme, language: Language, parent=None):
        super().__init__(theme, parent)
        self._theme = theme
        self._language = language
        self._rules = language.editing
        self._bracket_selections: list[QTextEdit.ExtraSelection] = []
        self.gutter = _LineNumberGutter(self)
        self._highlighter = SyntaxHighlighter(self.document(), language, theme)
        self.blockCountChanged.connect(self._update_gutter_width)
        self.updateRequest.connect(self._scroll_gutter)
        self.cursorPositionChanged.connect(self._update_bracket_highlight)
        self.textChanged.connect(self._update_bracket_highlight)
        self._ready = True
        self._font_changed()

    # ----------------------------------------------------------- bracket highlight

    def _update_bracket_highlight(self) -> None:
        position = self._position_of(self.textCursor().position())
        pair = find_bracket_pair(
            _DocumentLines(self.document()),
            position,
            self._rules,
            self._language.lex_line,
            state_before=self._lexer_state_before_line,
        )
        self._bracket_selections = []
        if pair is not None:
            for bracket in (pair.first, pair.second):
                start = self._qt_position_of(bracket)
                selection = QTextEdit.ExtraSelection()
                selection.format.setBackground(QColor(self._theme.matching_bracket_background))
                selection.cursor = QTextCursor(self.document())
                selection.cursor.setPosition(start)
                selection.cursor.setPosition(start + 1, QTextCursor.MoveMode.KeepAnchor)
                self._bracket_selections.append(selection)
        self._refresh_extra_selections()

    def _refresh_extra_selections(self) -> None:
        self.setExtraSelections(self._bracket_selections)

    def _lexer_state_before_line(self, index: int) -> int:
        """The state the highlighter left at the end of the line before, kept with that line."""
        if index == 0:
            return 0
        return max(self.document().findBlockByNumber(index - 1).userState(), 0)

    # ------------------------------------------------------------ line numbers

    def gutter_width(self) -> int:
        digits = max(MINIMUM_GUTTER_DIGITS, len(str(max(1, self.blockCount()))))
        return 2 * GUTTER_PADDING + digits * self.fontMetrics().horizontalAdvance("9")

    def visible_line_numbers(self) -> list[int]:
        return [block.blockNumber() + 1 for block, _, _ in self._visible_blocks()]

    def paint_gutter(self, event: QPaintEvent) -> None:
        painter = QPainter(self.gutter)
        painter.fillRect(event.rect(), QColor(self._theme.line_number_background))
        painter.setPen(QColor(self._theme.line_number_text))
        painter.setFont(self.font())
        alignment = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        for block, top, bottom in self._visible_blocks():
            if bottom < event.rect().top() or top > event.rect().bottom():
                continue
            painter.drawText(
                0, top, self.gutter.width() - GUTTER_PADDING, self._first_row_height(block),
                alignment, str(block.blockNumber() + 1),
            )

    def _update_gutter_width(self) -> None:
        width = self.gutter_width()
        if self.viewportMargins().left() != width:
            self.setViewportMargins(width, 0, 0, 0)
        self._place_gutter()

    def _place_gutter(self) -> None:
        contents = self.contentsRect()
        self.gutter.setGeometry(QRect(contents.left(), contents.top(), self.gutter_width(), contents.height()))

    def _scroll_gutter(self, rect: QRect, scrolled_by: int) -> None:
        if scrolled_by:
            self.gutter.scroll(0, scrolled_by)
        else:
            self.gutter.update(0, rect.y(), self.gutter.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._update_gutter_width()

    # ------------------------------------------------------- indentation guides

    def visible_indentation_guides(self) -> list[IndentationGuide]:
        lines = _DocumentLines(self.document())
        space_width = self.fontMetrics().horizontalAdvance(" ")
        left = self.contentOffset().x() + self.document().documentMargin()
        guides = []
        for block, top, _ in self._visible_blocks():
            # On a wrapped line only the first row has the indentation; the rest start at the margin.
            bottom = top + self._first_row_height(block)
            for column in guide_columns(lines, block.blockNumber(), self._rules.indent_width):
                guides.append(
                    IndentationGuide(block.blockNumber(), column, round(left + column * space_width), top, bottom)
                )
        return guides

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)
        painter = QPainter(self.viewport())
        painter.setPen(QColor(self._theme.indentation_guide))
        for guide in self.visible_indentation_guides():
            painter.drawLine(guide.x, guide.top, guide.x, guide.bottom - 1)

    # ---------------------------------------------------------------- the blocks

    def _visible_blocks(self) -> Iterator[tuple[QTextBlock, int, int]]:
        """The blocks (lines) in view, each with the top and bottom of all its rows in the viewport."""
        block = self.firstVisibleBlock()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        viewport_height = self.viewport().height()
        while block.isValid() and top <= viewport_height:
            bottom = top + round(self.blockBoundingRect(block).height())
            if block.isVisible():
                yield block, top, bottom
            block = block.next()
            top = bottom

    def _first_row_height(self, block: QTextBlock) -> int:
        layout = block.layout()
        if layout is not None and layout.lineCount() > 0:
            return round(layout.lineAt(0).height())
        return round(self.blockBoundingRect(block).height())

    # ------------------------------------------------------------ size and font

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._place_gutter()

    def changeEvent(self, event: QEvent) -> None:
        super().changeEvent(event)
        if event.type() == QEvent.Type.FontChange and self._ready:
            self._font_changed()

    def _font_changed(self) -> None:
        self.setTabStopDistance(self._rules.indent_width * self.fontMetrics().horizontalAdvance(" "))
        self._update_gutter_width()

    # ------------------------------------------------------------------------ keys

    def keyPressEvent(self, event: QKeyEvent) -> None:
        key = event.key()
        modifiers = event.modifiers() & ~Modifier.KeypadModifier

        if key in (Key.Key_Return, Key.Key_Enter) and modifiers & Modifier.ControlModifier:
            event.ignore()  # Ctrl+Enter runs the prompt; the window handles it
            return

        command = self._command_for(key, modifiers)
        if command is not None:
            command()
            event.accept()
            return
        if key == Key.Key_Home and modifiers in (Modifier.NoModifier, Modifier.ShiftModifier):
            self._go_to_start_of_line(select=modifiers == Modifier.ShiftModifier)
            event.accept()
            return
        super().keyPressEvent(event)

    def _command_for(self, key: int, modifiers: Modifier) -> Callable[[], None] | None:
        rules = self._rules
        if modifiers == Modifier.NoModifier and key == Key.Key_Tab:
            return lambda: self._apply_command(lambda lines, a, c: indent(lines, a, c, rules))
        if key == Key.Key_Backtab or (key == Key.Key_Tab and modifiers == Modifier.ShiftModifier):
            return lambda: self._apply_command(lambda lines, a, c: dedent(lines, a, c, rules))
        if key in (Key.Key_Return, Key.Key_Enter) and modifiers in (Modifier.NoModifier, Modifier.ShiftModifier):
            return lambda: self._apply_command(lambda lines, a, c: insert_newline(lines, a, c, rules))
        if key == Key.Key_Slash and modifiers == Modifier.ControlModifier:
            return lambda: self._apply_command(lambda lines, a, c: toggle_comment(lines, a, c, rules))
        if key == Key.Key_D and modifiers == Modifier.ControlModifier:
            return lambda: self._apply_command(duplicate_lines)
        if key == Key.Key_K and modifiers == Modifier.ControlModifier | Modifier.ShiftModifier:
            return lambda: self._apply_command(delete_lines)
        if key in (Key.Key_Up, Key.Key_Down) and modifiers == Modifier.AltModifier:
            direction = -1 if key == Key.Key_Up else 1
            return lambda: self._apply_command(lambda lines, a, c: move_lines(lines, a, c, direction))
        return None

    def _go_to_start_of_line(self, select: bool) -> None:
        cursor = self.textCursor()
        block = cursor.block()
        offset = cursor.position() - block.position()
        mode = QTextCursor.MoveMode.KeepAnchor if select else QTextCursor.MoveMode.MoveAnchor

        layout_line = block.layout().lineForTextPosition(offset) if block.layout() is not None else None
        if layout_line is not None and layout_line.isValid() and layout_line.lineNumber() > 0:
            cursor.movePosition(QTextCursor.MoveOperation.StartOfLine, mode)  # a wrapped line: its own start
        else:
            text = block.text()
            column = home_column(text, index_at_utf16_offset(text, offset))
            cursor.setPosition(block.position() + utf16_length(text[:column]), mode)
        self.setTextCursor(cursor)

    # -------------------------------------------------- applying editing commands

    def _apply_command(self, command: Callable[[Sequence[str], Position, Position], TextEdit | None]) -> None:
        cursor = self.textCursor()
        edit = command(
            _DocumentLines(self.document()),
            self._position_of(cursor.anchor()),
            self._position_of(cursor.position()),
        )
        if edit is not None:
            self._apply_edit(edit)

    def _apply_edit(self, edit: TextEdit) -> None:
        document = self.document()
        first_block = document.findBlockByNumber(edit.first_line)
        last_block = document.findBlockByNumber(edit.last_line)
        replacing = QTextCursor(document)
        replacing.setPosition(first_block.position())
        replacing.setPosition(last_block.position() + last_block.length() - 1, QTextCursor.MoveMode.KeepAnchor)
        replacing.insertText("\n".join(edit.replacement))  # one undo step, however many lines

        selection = self.textCursor()
        selection.setPosition(self._qt_position_of(edit.anchor))
        selection.setPosition(self._qt_position_of(edit.cursor), QTextCursor.MoveMode.KeepAnchor)
        self.setTextCursor(selection)
        self.ensureCursorVisible()

    def _position_of(self, qt_position: int) -> Position:
        block = self.document().findBlock(qt_position)
        column = index_at_utf16_offset(block.text(), qt_position - block.position())
        return Position(block.blockNumber(), column)

    def _qt_position_of(self, position: Position) -> int:
        block = self.document().findBlockByNumber(position.line)
        return block.position() + utf16_length(block.text()[: position.column])
