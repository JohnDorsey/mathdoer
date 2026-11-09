"""Helpers for tests that drive the prompt box with text, a caret and key presses."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor

NONE = Qt.KeyboardModifier.NoModifier


def qt_index(text, line, column):
    """The text box position of a line and column in text that has no wide characters."""
    return sum(len(earlier) + 1 for earlier in text.split("\n")[:line]) + column


def load(editor, text, caret=None, anchor=None):
    """Put the text in the box. The caret is (line, column), by default the end of the text."""
    editor.setPlainText(text)
    lines = text.split("\n")
    caret = caret or (len(lines) - 1, len(lines[-1]))
    cursor = editor.textCursor()
    cursor.setPosition(qt_index(text, *(anchor or caret)))
    cursor.setPosition(qt_index(text, *caret), QTextCursor.MoveMode.KeepAnchor)
    editor.setTextCursor(cursor)


def caret_of(editor):
    cursor = editor.textCursor()
    return cursor.blockNumber(), cursor.positionInBlock()


def selection_of(editor):
    cursor = editor.textCursor()
    return cursor.selectionStart(), cursor.selectionEnd()


def press(qtbot, editor, key, modifiers=NONE):
    qtbot.keyClick(editor, key, modifiers)


def line_formats(editor, line):
    """The colors applied to a line, as (start, length, color) in UTF-16 units."""
    block = editor.document().findBlockByNumber(line)
    return [
        (item.start, item.length, item.format.foreground().color().name())
        for item in block.layout().formats()
    ]
