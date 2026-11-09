"""Tests for the prompt box: its editing keys, driven with real key events."""
import pytest
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent, QTextCursor

from editor_helpers import caret_of, load, press, qt_index, selection_of
from mathdoer.interface.prompt_editor import PromptEditor
from mathdoer.interface.theme import DARK_THEME
from mathdoer.languages.python import PYTHON

Key = Qt.Key
NONE = Qt.KeyboardModifier.NoModifier
SHIFT = Qt.KeyboardModifier.ShiftModifier
CONTROL = Qt.KeyboardModifier.ControlModifier
ALT = Qt.KeyboardModifier.AltModifier


@pytest.fixture
def editor(qtbot):
    widget = PromptEditor(DARK_THEME, PYTHON)
    qtbot.addWidget(widget)
    widget.resize(600, 300)
    widget.show()
    return widget


# ------------------------------------------------------------------------------ Tab

def test_tab_inserts_spaces_up_to_the_next_tab_stop(qtbot, editor):
    load(editor, "ab")
    press(qtbot, editor, Key.Key_Tab)
    assert editor.toPlainText() == "ab  "
    assert caret_of(editor) == (0, 4)


def test_tab_at_the_start_of_a_line_inserts_four_spaces(qtbot, editor):
    load(editor, "x", caret=(0, 0))
    press(qtbot, editor, Key.Key_Tab)
    assert editor.toPlainText() == "    x"
    assert caret_of(editor) == (0, 4)


def test_tab_over_several_lines_indents_them_all_and_keeps_them_selected(qtbot, editor):
    load(editor, "a\nb\nc", caret=(2, 1), anchor=(0, 0))
    press(qtbot, editor, Key.Key_Tab)
    assert editor.toPlainText() == "    a\n    b\n    c"
    assert selection_of(editor) == (0, len("    a\n    b\n    c"))


def test_tab_replaces_a_selection_inside_one_line(qtbot, editor):
    load(editor, "hello", caret=(0, 4), anchor=(0, 1))
    press(qtbot, editor, Key.Key_Tab)
    assert editor.toPlainText() == "h   o"
    assert caret_of(editor) == (0, 4)


def test_shift_tab_takes_a_level_of_indentation_off_the_line(qtbot, editor):
    load(editor, "    x")
    press(qtbot, editor, Key.Key_Backtab, SHIFT)
    assert editor.toPlainText() == "x"
    assert caret_of(editor) == (0, 1)


def test_shift_tab_over_several_lines_dedents_them_all(qtbot, editor):
    load(editor, "    a\n        b\nc", caret=(2, 1), anchor=(0, 0))
    press(qtbot, editor, Key.Key_Backtab, SHIFT)
    assert editor.toPlainText() == "a\n    b\nc"


def test_shift_tab_with_nothing_to_remove_changes_nothing_and_leaves_no_undo_step(qtbot, editor):
    load(editor, "x")
    press(qtbot, editor, Key.Key_Backtab, SHIFT)
    assert editor.toPlainText() == "x"
    assert not editor.document().isUndoAvailable()


def test_tab_in_the_leading_tabs_of_a_line_inserts_a_tab(qtbot, editor):
    load(editor, "\tx", caret=(0, 1))
    press(qtbot, editor, Key.Key_Tab)
    assert editor.toPlainText() == "\t\tx"


# ---------------------------------------------------------------------------- Enter

def test_enter_after_a_colon_indents_the_next_line(qtbot, editor):
    load(editor, "if x:")
    press(qtbot, editor, Key.Key_Return)
    assert editor.toPlainText() == "if x:\n    "
    assert caret_of(editor) == (1, 4)


def test_typing_continues_at_the_new_indentation(qtbot, editor):
    load(editor, "if x:")
    press(qtbot, editor, Key.Key_Return)
    qtbot.keyClicks(editor, "y = 1")
    assert editor.toPlainText() == "if x:\n    y = 1"


def test_enter_keeps_the_indentation_of_the_line(qtbot, editor):
    load(editor, "    x = 1")
    press(qtbot, editor, Key.Key_Return)
    assert editor.toPlainText() == "    x = 1\n    "
    assert caret_of(editor) == (1, 4)


def test_enter_on_a_line_of_only_indentation_clears_it_and_keeps_the_indentation_going(qtbot, editor):
    load(editor, "    x = 1")
    press(qtbot, editor, Key.Key_Return)
    press(qtbot, editor, Key.Key_Return)
    assert editor.toPlainText() == "    x = 1\n\n    "
    assert caret_of(editor) == (2, 4)


def test_enter_in_the_middle_of_a_line_splits_it(qtbot, editor):
    load(editor, "    foo bar", caret=(0, 7))
    press(qtbot, editor, Key.Key_Return)
    assert editor.toPlainText() == "    foo\n    bar"
    assert caret_of(editor) == (1, 4)


def test_enter_over_a_selection_replaces_it(qtbot, editor):
    load(editor, "abcdef", caret=(0, 4), anchor=(0, 1))
    press(qtbot, editor, Key.Key_Return)
    assert editor.toPlainText() == "a\nef"
    assert caret_of(editor) == (1, 0)


def test_shift_enter_and_keypad_enter_start_a_line_too(qtbot, editor):
    load(editor, "if x:")
    press(qtbot, editor, Key.Key_Return, SHIFT)
    assert editor.toPlainText() == "if x:\n    "
    load(editor, "if y:")
    press(qtbot, editor, Key.Key_Enter, Qt.KeyboardModifier.KeypadModifier)
    assert editor.toPlainText() == "if y:\n    "


def test_ctrl_enter_inserts_no_line_and_is_left_for_the_window(qtbot, editor):
    load(editor, "abc")
    press(qtbot, editor, Key.Key_Return, CONTROL)
    press(qtbot, editor, Key.Key_Enter, CONTROL)
    assert editor.toPlainText() == "abc"
    for key in (Key.Key_Return, Key.Key_Enter):
        event = QKeyEvent(QEvent.Type.KeyPress, key, CONTROL)
        editor.keyPressEvent(event)
        assert not event.isAccepted()


def test_enter_does_not_indent_after_a_colon_inside_brackets_or_a_string(qtbot, editor):
    load(editor, "d = {1:")
    press(qtbot, editor, Key.Key_Return)
    assert editor.toPlainText() == "d = {1:\n"
    load(editor, "s = 'a:")
    press(qtbot, editor, Key.Key_Return)
    assert editor.toPlainText() == "s = 'a:\n"


# ----------------------------------------------------------------- comment and lines

def test_ctrl_slash_comments_and_uncomments_the_line(qtbot, editor):
    load(editor, "x = 1", caret=(0, 3))
    press(qtbot, editor, Key.Key_Slash, CONTROL)
    assert editor.toPlainText() == "# x = 1"
    assert caret_of(editor) == (0, 5)
    press(qtbot, editor, Key.Key_Slash, CONTROL)
    assert editor.toPlainText() == "x = 1"
    assert caret_of(editor) == (0, 3)


def test_ctrl_slash_comments_every_selected_line(qtbot, editor):
    load(editor, "a\n\n  b", caret=(2, 3), anchor=(0, 0))
    press(qtbot, editor, Key.Key_Slash, CONTROL)
    assert editor.toPlainText() == "# a\n\n#   b"


def test_ctrl_d_duplicates_the_line_and_moves_to_the_copy(qtbot, editor):
    load(editor, "a\nb", caret=(0, 1))
    press(qtbot, editor, Key.Key_D, CONTROL)
    assert editor.toPlainText() == "a\na\nb"
    assert caret_of(editor) == (1, 1)


def test_ctrl_d_duplicates_every_selected_line(qtbot, editor):
    load(editor, "a\nb\nc", caret=(1, 1), anchor=(0, 0))
    press(qtbot, editor, Key.Key_D, CONTROL)
    assert editor.toPlainText() == "a\nb\na\nb\nc"
    assert selection_of(editor) == (qt_index("a\nb\na\nb\nc", 2, 0), qt_index("a\nb\na\nb\nc", 3, 1))


def test_alt_up_and_down_move_the_line(qtbot, editor):
    load(editor, "a\nb\nc", caret=(1, 1))
    press(qtbot, editor, Key.Key_Up, ALT)
    assert editor.toPlainText() == "b\na\nc"
    assert caret_of(editor) == (0, 1)
    press(qtbot, editor, Key.Key_Down, ALT)
    press(qtbot, editor, Key.Key_Down, ALT)
    assert editor.toPlainText() == "a\nc\nb"
    assert caret_of(editor) == (2, 1)


def test_alt_up_on_the_first_line_and_alt_down_on_the_last_do_nothing(qtbot, editor):
    load(editor, "a\nb", caret=(0, 0))
    press(qtbot, editor, Key.Key_Up, ALT)
    assert editor.toPlainText() == "a\nb"
    load(editor, "a\nb", caret=(1, 0))
    press(qtbot, editor, Key.Key_Down, ALT)
    assert editor.toPlainText() == "a\nb"


def test_ctrl_shift_k_deletes_the_line(qtbot, editor):
    load(editor, "a\nbcd\ne", caret=(1, 2))
    press(qtbot, editor, Key.Key_K, CONTROL | SHIFT)
    assert editor.toPlainText() == "a\ne"
    assert caret_of(editor) == (1, 1)


def test_ctrl_shift_k_on_the_last_line_moves_up(qtbot, editor):
    load(editor, "a\nb", caret=(1, 1))
    press(qtbot, editor, Key.Key_K, CONTROL | SHIFT)
    assert editor.toPlainText() == "a"
    assert caret_of(editor) == (0, 1)


# ----------------------------------------------------------------------------- Home

def test_home_goes_to_the_first_character_and_then_to_the_start_of_the_line(qtbot, editor):
    load(editor, "    x = 1")
    press(qtbot, editor, Key.Key_Home)
    assert caret_of(editor) == (0, 4)
    press(qtbot, editor, Key.Key_Home)
    assert caret_of(editor) == (0, 0)
    press(qtbot, editor, Key.Key_Home)
    assert caret_of(editor) == (0, 4)


def test_shift_home_selects_up_to_the_same_place(qtbot, editor):
    load(editor, "    x = 1")
    press(qtbot, editor, Key.Key_Home, SHIFT)
    assert selection_of(editor) == (4, 9)
    press(qtbot, editor, Key.Key_Home, SHIFT)
    assert selection_of(editor) == (0, 9)


def test_home_on_a_later_line_stays_on_that_line(qtbot, editor):
    load(editor, "a\n    b", caret=(1, 5))
    press(qtbot, editor, Key.Key_Home)
    assert caret_of(editor) == (1, 4)


def test_ctrl_home_still_goes_to_the_start_of_the_document(qtbot, editor):
    load(editor, "a\n    b", caret=(1, 5))
    press(qtbot, editor, Key.Key_Home, CONTROL)
    assert caret_of(editor) == (0, 0)


def test_home_on_a_wrapped_line_goes_to_the_start_of_the_row_it_is_on(qtbot, editor):
    editor.resize(220, 300)
    load(editor, "word " * 40)
    qtbot.wait(50)
    expected = QTextCursor(editor.textCursor())
    expected.movePosition(QTextCursor.MoveOperation.StartOfLine)
    assert expected.positionInBlock() > 0  # the line did wrap
    press(qtbot, editor, Key.Key_Home)
    assert editor.textCursor().positionInBlock() == expected.positionInBlock()


# --------------------------------------------------------------- what Qt already does

def test_backspace_removes_one_space_of_indentation_not_a_whole_level(qtbot, editor):
    load(editor, "        x", caret=(0, 8))
    press(qtbot, editor, Key.Key_Backspace)
    assert editor.toPlainText() == "       x"


def test_brackets_and_quotes_are_not_closed_automatically(qtbot, editor):
    for typed in ["(", "[", "{", '"', "'"]:
        editor.clear()
        qtbot.keyClicks(editor, typed)
        assert editor.toPlainText() == typed


def test_ctrl_left_and_right_move_by_word(qtbot, editor):
    load(editor, "foo bar_baz", caret=(0, 0))
    press(qtbot, editor, Key.Key_Right, CONTROL)
    assert caret_of(editor) == (0, 4)
    press(qtbot, editor, Key.Key_Right, CONTROL)
    assert caret_of(editor) == (0, 11)
    press(qtbot, editor, Key.Key_Left, CONTROL)
    assert caret_of(editor) == (0, 4)
    press(qtbot, editor, Key.Key_Left, CONTROL)
    assert caret_of(editor) == (0, 0)


def test_ctrl_shift_arrows_select_by_word(qtbot, editor):
    load(editor, "foo bar", caret=(0, 0))
    press(qtbot, editor, Key.Key_Right, CONTROL | SHIFT)
    assert selection_of(editor) == (0, 4)


def test_ctrl_backspace_deletes_the_word_before_the_caret(qtbot, editor):
    load(editor, "foo bar baz")
    press(qtbot, editor, Key.Key_Backspace, CONTROL)
    assert editor.toPlainText() == "foo bar "
    press(qtbot, editor, Key.Key_Backspace, CONTROL)
    assert editor.toPlainText() == "foo "


def test_ctrl_delete_deletes_the_word_after_the_caret(qtbot, editor):
    load(editor, "foo bar baz", caret=(0, 0))
    press(qtbot, editor, Key.Key_Delete, CONTROL)
    assert editor.toPlainText() == "bar baz"


def test_an_identifier_with_underscores_is_one_word(qtbot, editor):
    load(editor, "some_long_name = 1", caret=(0, 0))
    press(qtbot, editor, Key.Key_Delete, CONTROL)
    assert editor.toPlainText() == "= 1"


# -------------------------------------------------------------------- undo and redo

@pytest.mark.parametrize(
    "text, caret, key, modifiers",
    [
        ("ab", None, Key.Key_Tab, NONE),
        ("    x", None, Key.Key_Backtab, SHIFT),
        ("if x:", None, Key.Key_Return, NONE),
        ("x = 1", None, Key.Key_Slash, CONTROL),
        ("a\nb", (0, 0), Key.Key_D, CONTROL),
        ("a\nb", (1, 0), Key.Key_Up, ALT),
        ("a\nb\nc", (1, 0), Key.Key_K, CONTROL | SHIFT),
    ],
)
def test_each_command_is_one_undo_step_that_can_be_redone(qtbot, editor, text, caret, key, modifiers):
    load(editor, text, caret=caret)
    press(qtbot, editor, key, modifiers)
    changed = editor.toPlainText()
    assert changed != text
    editor.undo()
    assert editor.toPlainText() == text
    assert not editor.document().isUndoAvailable()
    editor.redo()
    assert editor.toPlainText() == changed


def test_ctrl_z_undoes_and_ctrl_y_and_ctrl_shift_z_redo(qtbot, editor):
    load(editor, "ab")
    press(qtbot, editor, Key.Key_Tab)
    press(qtbot, editor, Key.Key_Z, CONTROL)
    assert editor.toPlainText() == "ab"
    press(qtbot, editor, Key.Key_Y, CONTROL)
    assert editor.toPlainText() == "ab  "
    press(qtbot, editor, Key.Key_Z, CONTROL)
    press(qtbot, editor, Key.Key_Z, CONTROL | SHIFT)
    assert editor.toPlainText() == "ab  "


# ------------------------------------------------------- characters outside the basic plane

def test_commands_find_the_right_column_after_wide_characters(qtbot, editor):
    editor.setPlainText("😀x")
    cursor = editor.textCursor()
    cursor.setPosition(2)  # between the emoji and the x: the emoji counts as two positions
    editor.setTextCursor(cursor)
    press(qtbot, editor, Key.Key_Return)
    assert editor.toPlainText() == "😀\nx"
    assert caret_of(editor) == (1, 0)


def test_tab_after_a_wide_character_counts_it_as_one_column(qtbot, editor):
    editor.setPlainText("😀")
    cursor = editor.textCursor()
    cursor.movePosition(QTextCursor.MoveOperation.End)
    editor.setTextCursor(cursor)
    press(qtbot, editor, Key.Key_Tab)
    assert editor.toPlainText() == "😀   "


def test_the_selection_after_a_command_lands_after_wide_characters(qtbot, editor):
    editor.setPlainText("😀 a\nb")
    cursor = editor.textCursor()
    cursor.setPosition(0)
    cursor.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
    editor.setTextCursor(cursor)
    press(qtbot, editor, Key.Key_Slash, CONTROL)
    assert editor.toPlainText() == "# 😀 a\n# b"
    assert selection_of(editor) == (0, len("# 😀 a\n# b".encode("utf-16-le")) // 2)


# -------------------------------------------------------------------------- ordinary typing

def test_ordinary_typing_is_left_alone(qtbot, editor):
    qtbot.keyClicks(editor, "x = 1 + 2")
    assert editor.toPlainText() == "x = 1 + 2"
    press(qtbot, editor, Key.Key_Backspace)
    assert editor.toPlainText() == "x = 1 + "


def test_the_tab_stop_distance_is_four_spaces_wide(editor):
    assert editor.tabStopDistance() == pytest.approx(4 * editor.fontMetrics().horizontalAdvance(" "))
