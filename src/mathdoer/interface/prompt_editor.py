"""The prompt box: a text box that edits code the way a code editor does."""
from collections.abc import Callable, Sequence

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent, QTextCursor, QTextDocument

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


class PromptEditor(TextBox):
    def __init__(self, theme: Theme, language: Language, parent=None):
        super().__init__(theme, parent)
        self._rules = language.editing
        self.setTabStopDistance(self._rules.indent_width * self.fontMetrics().horizontalAdvance(" "))

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
