"""Tests for the interface settings as they apply to the prompt box: each feature can be turned off."""
import random
from dataclasses import replace

import pytest
from editor_helpers import caret_of, line_formats, load, press, selection_of
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QKeyEvent, QTextCursor, QWheelEvent
from settings_helpers import every_feature_off, random_settings

from mathdoer.interface.theme import DARK_THEME
from mathdoer.interface_settings import DEFAULT_INTERFACE_SETTINGS
from mathdoer.languages.python import PYTHON

Key = Qt.Key
NONE = Qt.KeyboardModifier.NoModifier
SHIFT = Qt.KeyboardModifier.ShiftModifier
CONTROL = Qt.KeyboardModifier.ControlModifier
ALT = Qt.KeyboardModifier.AltModifier


def change(editor, **changes):
    """Apply the default settings with the changes."""
    editor.apply_interface_settings(replace(DEFAULT_INTERFACE_SETTINGS, **changes))


def move_caret(editor, position):
    cursor = editor.textCursor()
    cursor.setPosition(position)
    editor.setTextCursor(cursor)


def highlighted_brackets(editor):
    """The brackets highlighted, as (position, text); a found match is highlighted another way."""
    return sorted(
        (item.cursor.selectionStart(), item.cursor.selectedText())
        for item in editor.extraSelections()
        if item.format.background().color().name() == DARK_THEME.matching_bracket_background
    )


def ctrl_wheel(box, delta):
    event = QWheelEvent(
        QPointF(10, 10), box.mapToGlobal(QPointF(10, 10)), QPoint(0, 0), QPoint(0, delta),
        Qt.MouseButton.NoButton, CONTROL, Qt.ScrollPhase.NoScrollPhase, False,
    )
    box.wheelEvent(event)


# ------------------------------------------------------------------------ line numbers

def test_line_numbers_can_be_turned_off_and_on(editor):
    editor.setPlainText("a\nb\nc")
    width = editor.gutter_width()
    assert width > 0 and editor.visible_line_numbers() == [1, 2, 3]

    change(editor, show_line_numbers=False)
    assert editor.gutter_width() == 0
    assert editor.viewportMargins().left() == 0
    assert editor.viewport().geometry().left() == editor.contentsRect().left()
    assert not editor.gutter.isVisibleTo(editor)
    assert editor.visible_line_numbers() == []

    change(editor)
    assert editor.gutter_width() == width
    assert editor.viewportMargins().left() == width
    assert editor.gutter.isVisibleTo(editor)
    assert editor.visible_line_numbers() == [1, 2, 3]


def test_the_gutter_stays_away_while_line_numbers_are_off_however_the_text_and_font_change(editor):
    change(editor, show_line_numbers=False)
    editor.setPlainText("\n".join(f"line {number}" for number in range(1, 1501)))
    assert editor.viewportMargins().left() == 0
    font = editor.font()
    font.setPointSize(font.pointSize() + 6)
    editor.setFont(font)
    assert editor.viewportMargins().left() == 0
    assert editor.gutter_width() == 0


# ---------------------------------------------------------------------- syntax colors

def test_syntax_colors_can_be_turned_off_and_on(editor):
    editor.setPlainText("x = 1  # note")
    assert line_formats(editor, 0) != []

    change(editor, highlight_syntax=False)
    assert line_formats(editor, 0) == []
    editor.setPlainText("if x:  # new text stays plain\n    y = 'two'")
    assert line_formats(editor, 0) == [] and line_formats(editor, 1) == []

    change(editor)
    assert line_formats(editor, 0) != [] and line_formats(editor, 1) != []


def test_a_bracket_in_a_multi_line_string_is_still_not_a_bracket_while_the_colors_are_off(editor):
    """Matching brackets reads the lexer's state of each line, which the highlighter keeps."""
    text = "'''\n(x)\n'''"
    for highlight_syntax in (True, False):
        change(editor, highlight_syntax=highlight_syntax)
        editor.setPlainText(text)
        move_caret(editor, 5)  # after the ( on the second line
        assert highlighted_brackets(editor) == [], highlight_syntax


def test_brackets_are_matched_while_the_colors_are_off(editor):
    change(editor, highlight_syntax=False)
    editor.setPlainText("(x)")
    move_caret(editor, 1)
    assert highlighted_brackets(editor) == [(0, "("), (2, ")")]


# ------------------------------------------------------------------ bracket highlight

def test_the_bracket_highlight_can_be_turned_off_and_on(editor):
    editor.setPlainText("(x)")
    move_caret(editor, 1)
    assert highlighted_brackets(editor) == [(0, "("), (2, ")")]

    change(editor, highlight_matching_brackets=False)
    assert highlighted_brackets(editor) == []
    move_caret(editor, 3)
    move_caret(editor, 1)  # moving the caret next to a bracket does not bring it back
    assert highlighted_brackets(editor) == []

    change(editor)
    assert highlighted_brackets(editor) == [(0, "("), (2, ")")]


def test_turning_the_bracket_highlight_off_keeps_the_highlighted_matches_of_a_search(editor):
    editor.setPlainText("(x)")
    match = QTextCursor(editor.document())
    match.setPosition(1)
    match.setPosition(2, QTextCursor.MoveMode.KeepAnchor)
    editor.set_search_highlights([match])
    move_caret(editor, 1)
    change(editor, highlight_matching_brackets=False)
    [remaining] = editor.extraSelections()
    assert remaining.format.background().color().name() == DARK_THEME.find_match_background


# ------------------------------------------------------------------ indentation guides

def test_the_indentation_guides_can_be_turned_off_and_on(editor):
    editor.setPlainText("def f():\n        x")
    assert editor.visible_indentation_guides()
    change(editor, show_indentation_guides=False)
    assert editor.visible_indentation_guides() == []
    change(editor)
    assert editor.visible_indentation_guides()


def test_the_indentation_guides_are_painted_only_while_they_are_on(editor):
    editor.setPlainText("def f():\n        x")
    guide = editor.visible_indentation_guides()[0]

    def colors_at_and_beside_the_guide():
        # The offscreen platform has no fonts and draws every character, spaces too, as a hollow
        # box in the upper part of the line, so the pixel looked at is near the bottom of the line.
        image = editor.viewport().grab().toImage()
        y = guide.bottom - 2
        return image.pixelColor(guide.x, y).name(), image.pixelColor(guide.x + 3, y).name()

    at_the_guide, beside_the_guide = colors_at_and_beside_the_guide()
    assert at_the_guide == DARK_THEME.indentation_guide != beside_the_guide
    change(editor, show_indentation_guides=False)
    at_the_guide, beside_the_guide = colors_at_and_beside_the_guide()
    assert at_the_guide == beside_the_guide != DARK_THEME.indentation_guide
    change(editor)
    at_the_guide, beside_the_guide = colors_at_and_beside_the_guide()
    assert at_the_guide == DARK_THEME.indentation_guide != beside_the_guide


# --------------------------------------------------------------------- wrapping, zoom

def test_wrapping_long_lines_follows_the_setting(editor):
    assert editor.word_wrap
    change(editor, wrap_prompt_box_lines=False)
    assert not editor.word_wrap
    change(editor)
    assert editor.word_wrap


def test_ctrl_wheel_asks_for_a_zoom_only_while_the_setting_is_on(qtbot, editor):
    with qtbot.waitSignal(editor.zoom_requested) as zoom:
        ctrl_wheel(editor, 120)
    assert zoom.args == [1]

    change(editor, zoom_with_mouse_wheel=False)
    with qtbot.assertNotEmitted(editor.zoom_requested):
        ctrl_wheel(editor, 120)

    change(editor)
    with qtbot.waitSignal(editor.zoom_requested):
        ctrl_wheel(editor, -120)


# ------------------------------------------------------------------------------- Tab

def test_tab_inserts_a_tab_character_when_spaces_are_turned_off(qtbot, editor):
    change(editor, tab_key_inserts_spaces=False)
    load(editor, "ab")
    press(qtbot, editor, Key.Key_Tab)
    assert editor.toPlainText() == "ab\t" and caret_of(editor) == (0, 3)

    load(editor, "x", caret=(0, 0))
    press(qtbot, editor, Key.Key_Tab)
    assert editor.toPlainText() == "\tx" and caret_of(editor) == (0, 1)

    load(editor, "hello", anchor=(0, 1), caret=(0, 4))
    press(qtbot, editor, Key.Key_Tab)
    assert editor.toPlainText() == "h\to" and caret_of(editor) == (0, 2)


def test_tab_over_several_lines_indents_each_with_a_tab_character_when_spaces_are_turned_off(qtbot, editor):
    change(editor, tab_key_inserts_spaces=False)
    load(editor, "a\nb", anchor=(0, 0), caret=(1, 1))
    press(qtbot, editor, Key.Key_Tab)
    assert editor.toPlainText() == "\ta\n\tb" and caret_of(editor) == (1, 2)


def test_tab_keeps_to_the_spaces_of_a_line_already_indented_with_spaces(qtbot, editor):
    change(editor, tab_key_inserts_spaces=False)
    load(editor, "    x", caret=(0, 0))
    press(qtbot, editor, Key.Key_Tab)
    assert editor.toPlainText() == "        x"


def test_enter_after_a_colon_adds_a_tab_character_when_spaces_are_turned_off(qtbot, editor):
    change(editor, tab_key_inserts_spaces=False)
    load(editor, "if x:")
    press(qtbot, editor, Key.Key_Return)
    assert editor.toPlainText() == "if x:\n\t" and caret_of(editor) == (1, 1)


def test_shift_tab_still_removes_a_tab_character_when_spaces_are_turned_off(qtbot, editor):
    change(editor, tab_key_inserts_spaces=False)
    load(editor, "\tx")
    press(qtbot, editor, Key.Key_Backtab, SHIFT)
    assert editor.toPlainText() == "x"


def test_tab_replaces_a_selection_across_lines_when_it_is_not_to_indent_the_lines(qtbot, editor):
    change(editor, tab_indents_selected_lines=False)
    load(editor, "one\ntwo\nthree", anchor=(0, 1), caret=(2, 2))
    press(qtbot, editor, Key.Key_Tab)
    assert editor.toPlainText() == "o   ree" and caret_of(editor) == (0, 4)
    editor.undo()
    assert editor.toPlainText() == "one\ntwo\nthree"  # one step, however many lines were selected


def test_tab_replaces_a_selection_made_backwards_the_same_way(qtbot, editor):
    change(editor, tab_indents_selected_lines=False)
    load(editor, "one\ntwo\nthree", anchor=(2, 2), caret=(0, 1))
    press(qtbot, editor, Key.Key_Tab)
    assert editor.toPlainText() == "o   ree"


def test_tab_replaces_a_selection_with_a_tab_character_when_both_are_turned_off(qtbot, editor):
    change(editor, tab_indents_selected_lines=False, tab_key_inserts_spaces=False)
    load(editor, "one\ntwo", anchor=(0, 1), caret=(1, 1))
    press(qtbot, editor, Key.Key_Tab)
    assert editor.toPlainText() == "o\two"


def test_tab_still_indents_every_line_while_the_setting_is_on(qtbot, editor):
    load(editor, "one\ntwo", anchor=(0, 0), caret=(1, 1))
    press(qtbot, editor, Key.Key_Tab)
    assert editor.toPlainText() == "    one\n    two"


@pytest.mark.parametrize("key, modifiers", [(Key.Key_Backtab, SHIFT), (Key.Key_Tab, SHIFT)])
def test_shift_tab_does_nothing_when_it_is_turned_off(qtbot, editor, key, modifiers):
    change(editor, shift_tab_removes_indentation=False)
    load(editor, "    x\n    y", anchor=(0, 0), caret=(1, 5))
    press(qtbot, editor, key, modifiers)
    assert editor.toPlainText() == "    x\n    y"
    event = QKeyEvent(QEvent.Type.KeyPress, key, modifiers)
    event.setAccepted(False)
    editor.keyPressEvent(event)
    assert event.isAccepted()  # taken, so it does not move the focus to another widget


def test_shift_tab_removes_indentation_while_the_setting_is_on(qtbot, editor):
    load(editor, "    x")
    press(qtbot, editor, Key.Key_Backtab, SHIFT)
    assert editor.toPlainText() == "x"


# ------------------------------------------------------------------------------ Enter

def test_enter_starts_an_unindented_line_when_keeping_the_indentation_is_turned_off(qtbot, editor):
    change(editor, enter_keeps_indentation=False)
    load(editor, "    if x:")
    press(qtbot, editor, Key.Key_Return)
    assert editor.toPlainText() == "    if x:\n" and caret_of(editor) == (1, 0)


def test_shift_enter_and_the_keypad_enter_start_a_plain_line_too(qtbot, editor):
    change(editor, enter_keeps_indentation=False)
    load(editor, "    if x:")
    press(qtbot, editor, Key.Key_Return, SHIFT)
    assert editor.toPlainText() == "    if x:\n"
    press(qtbot, editor, Key.Key_Enter)
    assert editor.toPlainText() == "    if x:\n\n"


def test_enter_in_the_middle_of_a_line_splits_it_without_touching_the_spaces_when_indentation_is_off(qtbot, editor):
    change(editor, enter_keeps_indentation=False)
    load(editor, "a  b", caret=(0, 2))
    press(qtbot, editor, Key.Key_Return)
    assert editor.toPlainText() == "a \n b"


def test_enter_replaces_a_selection_when_indentation_is_off(qtbot, editor):
    change(editor, enter_keeps_indentation=False)
    load(editor, "abc", anchor=(0, 1), caret=(0, 2))
    press(qtbot, editor, Key.Key_Return)
    assert editor.toPlainText() == "a\nc"


def test_a_level_after_a_block_opening_needs_the_indentation_to_be_kept(qtbot, editor):
    change(editor, enter_keeps_indentation=False, indent_after_block_opening=True)
    load(editor, "if x:")
    press(qtbot, editor, Key.Key_Return)
    assert editor.toPlainText() == "if x:\n"


def test_enter_after_a_colon_adds_no_level_when_that_is_turned_off(qtbot, editor):
    change(editor, indent_after_block_opening=False)
    load(editor, "  if x:")
    press(qtbot, editor, Key.Key_Return)
    assert editor.toPlainText() == "  if x:\n  " and caret_of(editor) == (1, 2)


def test_enter_adds_a_level_after_a_colon_while_the_setting_is_on(qtbot, editor):
    load(editor, "  if x:")
    press(qtbot, editor, Key.Key_Return)
    assert editor.toPlainText() == "  if x:\n      "


# ------------------------------------------------------------------------------ Home

def test_home_goes_straight_to_the_start_of_the_line_when_the_first_character_is_turned_off(qtbot, editor):
    change(editor, home_key_goes_to_first_character=False)
    load(editor, "    x", caret=(0, 5))
    press(qtbot, editor, Key.Key_Home)
    assert caret_of(editor) == (0, 0)
    press(qtbot, editor, Key.Key_Home)
    assert caret_of(editor) == (0, 0)


def test_shift_home_selects_to_the_start_of_the_line_when_the_first_character_is_turned_off(qtbot, editor):
    change(editor, home_key_goes_to_first_character=False)
    load(editor, "    x", caret=(0, 5))
    press(qtbot, editor, Key.Key_Home, SHIFT)
    assert selection_of(editor) == (0, 5)


def test_home_goes_to_the_first_character_while_the_setting_is_on(qtbot, editor):
    load(editor, "    x", caret=(0, 5))
    press(qtbot, editor, Key.Key_Home)
    assert caret_of(editor) == (0, 4)


# ---------------------------------------------------------------------- line commands

LINE_COMMANDS = [
    ("toggle_comment_command", Key.Key_Slash, CONTROL, "x", (0, 1)),
    ("duplicate_lines_command", Key.Key_D, CONTROL, "x", (0, 1)),
    ("move_lines_command", Key.Key_Up, ALT, "a\nb", (1, 1)),
    ("move_lines_command", Key.Key_Down, ALT, "a\nb", (0, 0)),
    ("delete_lines_command", Key.Key_K, CONTROL | SHIFT, "a\nb", (0, 0)),
]


@pytest.mark.parametrize("setting, key, modifiers, text, caret", LINE_COMMANDS)
def test_a_line_command_does_nothing_when_turned_off_and_works_again_when_turned_on(
    qtbot, editor, setting, key, modifiers, text, caret
):
    change(editor, **{setting: False})
    load(editor, text, caret=caret)
    press(qtbot, editor, key, modifiers)
    assert editor.toPlainText() == text

    change(editor)
    press(qtbot, editor, key, modifiers)
    assert editor.toPlainText() != text


def test_the_line_commands_are_turned_off_one_at_a_time(qtbot, editor):
    change(editor, toggle_comment_command=False)
    load(editor, "x", caret=(0, 1))
    press(qtbot, editor, Key.Key_D, CONTROL)
    assert editor.toPlainText() == "x\nx"


# ---------------------------------------------------------------------- all together

def test_with_every_feature_off_the_box_edits_plain_text(qtbot, editor):
    editor.apply_interface_settings(every_feature_off())
    editor.setPlainText("if (x:  # comment\n\ty = 1")
    assert editor.gutter_width() == 0 and editor.visible_line_numbers() == []
    assert editor.visible_indentation_guides() == []
    assert line_formats(editor, 0) == [] and line_formats(editor, 1) == []
    move_caret(editor, 4)
    assert editor.extraSelections() == []
    assert not editor.word_wrap

    load(editor, "    if x:")
    press(qtbot, editor, Key.Key_Return)
    assert editor.toPlainText() == "    if x:\n"
    press(qtbot, editor, Key.Key_Tab)
    assert editor.toPlainText() == "    if x:\n\t"
    press(qtbot, editor, Key.Key_Home)
    assert caret_of(editor) == (1, 0)
    press(qtbot, editor, Key.Key_Slash, CONTROL)
    press(qtbot, editor, Key.Key_D, CONTROL)
    press(qtbot, editor, Key.Key_Up, ALT)
    press(qtbot, editor, Key.Key_K, CONTROL | SHIFT)
    assert editor.toPlainText() == "    if x:\n\t"


def test_no_combination_of_settings_breaks_the_keys_the_display_or_the_undo_history(qtbot, editor):
    generator = random.Random(2026)
    snippets = ["if x:", "    y = (1,", "\tz", "'''", "# c", "", "  ", "def f(): pass", "[a, {b}]"]
    keys = [
        (Key.Key_Tab, NONE), (Key.Key_Backtab, SHIFT), (Key.Key_Return, NONE), (Key.Key_Home, NONE),
        (Key.Key_Slash, CONTROL), (Key.Key_D, CONTROL), (Key.Key_Up, ALT), (Key.Key_Down, ALT),
        (Key.Key_K, CONTROL | SHIFT), (Key.Key_Left, NONE), (Key.Key_Backspace, NONE),
    ]
    for _ in range(60):
        settings = random_settings(generator)
        editor.apply_interface_settings(settings)
        lines = [generator.choice(snippets) for _ in range(generator.randint(1, 6))]
        caret_line = generator.randrange(len(lines))
        load(editor, "\n".join(lines), caret=(caret_line, generator.randint(0, len(lines[caret_line]))))
        for key, modifiers in generator.sample(keys, 6):
            press(qtbot, editor, key, modifiers)
        assert isinstance(editor.toPlainText(), str)
        assert (editor.gutter_width() > 0) == settings.show_line_numbers
        assert editor.word_wrap == settings.wrap_prompt_box_lines
        while editor.document().isUndoAvailable():
            editor.undo()


# ------------------------------------------------------------------------------ tab width

def space_width(editor):
    return editor.fontMetrics().horizontalAdvance(" ")


def test_a_tab_stop_is_as_wide_as_the_tab_width_setting_says(editor):
    for width in (1, 2, 4, 8, 16):
        change(editor, tab_width=width)
        assert editor.tabStopDistance() == pytest.approx(width * space_width(editor)), width


def test_the_tab_stop_follows_the_tab_width_when_the_font_changes_afterwards(editor):
    change(editor, tab_width=8)
    editor.set_font_size(editor.font().pointSize() + 6)
    assert editor.tabStopDistance() == pytest.approx(8 * space_width(editor))


def test_tab_inserts_as_many_spaces_as_the_tab_width(qtbot, editor):
    change(editor, tab_width=2)
    load(editor, "ab")
    press(qtbot, editor, Key.Key_Tab)
    assert editor.toPlainText() == "ab  "

    change(editor, tab_width=8)
    load(editor, "ab")
    press(qtbot, editor, Key.Key_Tab)
    assert editor.toPlainText() == "ab" + " " * 6  # to the next tab stop, as before


def test_tab_over_several_lines_indents_by_the_tab_width(qtbot, editor):
    change(editor, tab_width=3)
    load(editor, "a\nb", anchor=(0, 0), caret=(1, 1))
    press(qtbot, editor, Key.Key_Tab)
    assert editor.toPlainText() == "   a\n   b"


def test_shift_tab_removes_one_tab_width_of_indentation(qtbot, editor):
    change(editor, tab_width=8)
    load(editor, " " * 16 + "x")
    press(qtbot, editor, Key.Key_Backtab, SHIFT)
    assert editor.toPlainText() == " " * 8 + "x"


def test_enter_after_a_colon_adds_a_tab_width_of_spaces(qtbot, editor):
    change(editor, tab_width=2)
    load(editor, "if x:")
    press(qtbot, editor, Key.Key_Return)
    assert editor.toPlainText() == "if x:\n  " and caret_of(editor) == (1, 2)


def test_the_indentation_guides_stand_one_tab_width_apart(editor):
    editor.setPlainText("def f():\n" + " " * 16 + "x")
    change(editor, tab_width=8)
    columns = [guide.column for guide in editor.visible_indentation_guides() if guide.line == 1]
    assert columns == [0, 8]
    change(editor, tab_width=4)
    columns = [guide.column for guide in editor.visible_indentation_guides() if guide.line == 1]
    assert columns == [0, 4, 8, 12]
    xs = [guide.x for guide in editor.visible_indentation_guides() if guide.line == 1]
    assert xs[1] - xs[0] == pytest.approx(4 * space_width(editor), abs=1)


def test_a_tab_character_counts_as_a_tab_width_of_columns_for_the_guides(editor):
    editor.setPlainText("def f():\n\t\tx")
    change(editor, tab_width=3)
    assert [guide.column for guide in editor.visible_indentation_guides() if guide.line == 1] == [0, 3]


def test_the_default_tab_width_is_what_the_python_rules_say(qtbot, editor):
    assert DEFAULT_INTERFACE_SETTINGS.tab_width == PYTHON.editing.indent_width
    change(editor)
    load(editor, "ab")
    press(qtbot, editor, Key.Key_Tab)
    assert editor.toPlainText() == "ab  "  # to the next tab stop, four columns apart
