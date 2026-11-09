"""Tests for the find and replace bar above the prompt box."""
import pytest
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent, QTextCursor
from PySide6.QtWidgets import QApplication

from mathdoer.interface.find_bar import MATCH_LIMIT
from mathdoer.interface.theme import DARK_THEME

Key = Qt.Key
CONTROL = Qt.KeyboardModifier.ControlModifier
SHIFT = Qt.KeyboardModifier.ShiftModifier
NONE = Qt.KeyboardModifier.NoModifier

DOC = "alpha beta alpha gamma ALPHA"  # alpha at 0, 11 and (as ALPHA) 23; beta at 6; gamma at 17


@pytest.fixture
def editor(window):
    window.prompt_box.setPlainText(DOC)
    cursor = window.prompt_box.textCursor()
    cursor.setPosition(0)
    window.prompt_box.setTextCursor(cursor)
    return window.prompt_box


@pytest.fixture
def bar(window):
    return window.find_bar


def select_range(editor, start, end):
    cursor = QTextCursor(editor.document())
    cursor.setPosition(start)
    cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
    editor.setTextCursor(cursor)


def selection_of(editor):
    cursor = editor.textCursor()
    return cursor.selectionStart(), cursor.selectionEnd()


def type_find(qtbot, bar, text):
    bar.find_field.setFocus()
    bar.find_field.clear()
    qtbot.keyClicks(bar.find_field, text)


def search_highlights(editor, theme=DARK_THEME):
    return sorted(
        item.cursor.selectionStart()
        for item in editor.extraSelections()
        if item.format.background().color().name() == theme.find_match_background
    )


def open_find(qtbot, window):
    qtbot.keyClick(window.prompt_box, Key.Key_F, CONTROL)


def open_replace(qtbot, window):
    qtbot.keyClick(window.prompt_box, Key.Key_H, CONTROL)


# ------------------------------------------------------------------ opening and closing

def test_the_bar_is_not_shown_to_begin_with(window, bar):
    assert not bar.isVisible()


def test_ctrl_f_shows_the_find_field_and_puts_the_caret_in_it(qtbot, window, bar):
    open_find(qtbot, window)
    assert bar.isVisible()
    assert not bar.replace_field.isVisible()
    assert not bar.replace_button.isVisible()
    assert not bar.replace_all_button.isVisible()
    assert QApplication.focusWidget() is bar.find_field


def test_ctrl_h_shows_the_replace_field_and_buttons_too(qtbot, window, bar):
    open_replace(qtbot, window)
    assert bar.isVisible()
    assert bar.replace_field.isVisible()
    assert bar.replace_button.isVisible()
    assert bar.replace_all_button.isVisible()
    assert QApplication.focusWidget() is bar.find_field


def test_ctrl_h_on_an_open_find_bar_adds_the_replace_row(qtbot, window, bar):
    open_find(qtbot, window)
    qtbot.keyClick(bar.find_field, Key.Key_H, CONTROL)
    assert bar.replace_field.isVisible()


def test_ctrl_f_on_an_open_replace_bar_keeps_the_replace_row(qtbot, window, bar):
    open_replace(qtbot, window)
    qtbot.keyClick(bar.find_field, Key.Key_F, CONTROL)
    assert bar.replace_field.isVisible()
    assert QApplication.focusWidget() is bar.find_field


def test_the_shortcuts_work_from_the_output_box(qtbot, window, bar):
    window.output_box.setFocus()
    qtbot.keyClick(window.output_box, Key.Key_F, CONTROL)
    assert bar.isVisible()
    assert QApplication.focusWidget() is bar.find_field


def test_the_bar_pushes_the_text_down_instead_of_covering_it(qtbot, window, bar):
    top_before = window.prompt_box.geometry().top()
    open_find(qtbot, window)
    qtbot.waitUntil(lambda: window.prompt_box.geometry().top() > top_before)
    assert bar.geometry().bottom() < window.prompt_box.geometry().top()
    assert bar.geometry().top() <= top_before


def test_the_bar_is_above_the_prompt_box_and_inside_the_splitter(window, bar):
    pane = window.centralWidget().widget(0)
    assert pane is window.prompt_pane
    assert bar.parent() is pane and window.prompt_box.parent() is pane


def test_the_bar_uses_the_theme(window, bar):
    assert bar.palette().window().color().name() == DARK_THEME.panel_background
    assert bar.palette().text().color().name() == DARK_THEME.default_text
    assert bar.find_field.palette().base().color().name() == DARK_THEME.text_background


def test_the_two_fields_end_at_the_same_place(qtbot, window, bar):
    open_replace(qtbot, window)
    qtbot.waitUntil(lambda: bar.replace_field.geometry().width() > 50)
    assert bar.find_field.geometry().left() == bar.replace_field.geometry().left()
    assert bar.find_field.geometry().right() == bar.replace_field.geometry().right()


def test_the_replace_all_button_ends_where_the_close_button_does(qtbot, window, bar):
    open_replace(qtbot, window)
    qtbot.waitUntil(lambda: bar.replace_all_button.geometry().width() > 30)
    assert bar.replace_all_button.geometry().right() == bar.close_button.geometry().right()


def test_the_close_button_is_big_enough_to_hit_and_to_see(qtbot, window, bar):
    open_find(qtbot, window)
    assert bar.close_button.width() >= 24 and bar.close_button.height() >= 24
    assert bar.close_button.text() == "×"
    assert bar.close_button.font().pointSize() >= 14


def test_the_fields_have_a_visible_border_that_is_brighter_when_they_have_the_focus(window, bar):
    for field in (bar.find_field, bar.replace_field):
        assert DARK_THEME.control_border in field.styleSheet()
        assert f"QLineEdit:focus {{ border: 1px solid {DARK_THEME.default_text}" in field.styleSheet()


def test_the_hints_in_empty_fields_are_not_dim(window, bar):
    # Qt would otherwise draw them as half-transparent text; the style sheet decides their color.
    for field in (bar.find_field, bar.replace_field):
        assert field.placeholderText() in ("Find", "Replace")
        assert f"placeholder-text-color: {DARK_THEME.disabled_text}" in field.styleSheet()


def test_without_the_replace_row_the_bar_is_only_as_tall_as_its_find_row(qtbot, window, bar):
    open_find(qtbot, window)
    qtbot.waitUntil(lambda: bar.isVisible() and bar.height() > 0)
    margins = bar.layout().contentsMargins()
    tallest = max(
        widget.height()
        for widget in (bar.find_field, bar.match_case_box, bar.counter_label, bar.close_button)
    )
    assert bar.height() == margins.top() + tallest + margins.bottom()


def test_showing_the_replace_row_makes_the_bar_taller(qtbot, window, bar):
    open_find(qtbot, window)
    qtbot.waitUntil(lambda: bar.isVisible() and bar.height() > 0)
    find_only_height = bar.height()
    open_replace(qtbot, window)
    qtbot.waitUntil(lambda: bar.height() > find_only_height)


def test_escape_in_the_find_field_closes_the_bar_and_returns_to_the_text(qtbot, window, bar):
    open_find(qtbot, window)
    qtbot.keyClick(bar.find_field, Key.Key_Escape)
    assert not bar.isVisible()
    assert QApplication.focusWidget() is window.prompt_box


def test_escape_in_the_text_closes_the_bar_too(qtbot, window, bar):
    open_find(qtbot, window)
    window.prompt_box.setFocus()
    qtbot.keyClick(window.prompt_box, Key.Key_Escape)
    assert not bar.isVisible()
    assert QApplication.focusWidget() is window.prompt_box


def test_escape_in_the_output_box_leaves_the_bar_alone(qtbot, window, bar):
    open_find(qtbot, window)
    window.output_box.setFocus()
    qtbot.keyClick(window.output_box, Key.Key_Escape)
    assert bar.isVisible()


def test_escape_in_the_replace_field_closes_the_bar(qtbot, window, bar):
    open_replace(qtbot, window)
    bar.replace_field.setFocus()
    qtbot.keyClick(bar.replace_field, Key.Key_Escape)
    assert not bar.isVisible()


def test_the_close_button_closes_the_bar_and_returns_to_the_text(qtbot, window, bar):
    open_find(qtbot, window)
    assert bar.close_button.isVisible()
    assert "Esc" in bar.close_button.toolTip()
    bar.close_button.click()
    assert not bar.isVisible()
    assert QApplication.focusWidget() is window.prompt_box


def test_escape_with_the_bar_closed_does_nothing(qtbot, window, editor):
    qtbot.keyClick(editor, Key.Key_Escape)
    assert editor.toPlainText() == DOC
    assert not window.find_bar.isVisible()


def test_what_was_searched_for_is_still_there_when_the_bar_is_opened_again(qtbot, window, bar):
    open_find(qtbot, window)
    type_find(qtbot, bar, "beta")
    qtbot.keyClick(bar.find_field, Key.Key_Escape)
    open_find(qtbot, window)
    assert bar.find_field.text() == "beta"
    assert bar.find_field.selectedText() == "beta"


def test_closing_removes_the_highlights_and_opening_brings_them_back(qtbot, window, bar, editor):
    open_find(qtbot, window)
    type_find(qtbot, bar, "alpha")
    assert search_highlights(editor) == [0, 11, 23]
    bar.close_button.click()
    assert search_highlights(editor) == []
    open_find(qtbot, window)
    assert search_highlights(editor) == [0, 11, 23]


# ------------------------------------------------------------------------ pre-filling

def test_a_selection_inside_one_line_fills_in_the_find_field(qtbot, window, bar, editor):
    select_range(editor, 6, 10)
    open_find(qtbot, window)
    assert bar.find_field.text() == "beta"
    assert bar.find_field.selectedText() == "beta"


def test_a_selection_over_several_lines_leaves_the_find_field_alone(qtbot, window, bar):
    window.prompt_box.setPlainText("one\ntwo")
    window.prompt_box.selectAll()
    open_find(qtbot, window)
    assert bar.find_field.text() == ""


def test_without_a_selection_the_old_text_stays_and_is_selected(qtbot, window, bar, editor):
    open_find(qtbot, window)
    type_find(qtbot, bar, "gamma")
    window.prompt_box.setFocus()
    cursor = window.prompt_box.textCursor()
    cursor.clearSelection()
    window.prompt_box.setTextCursor(cursor)
    open_find(qtbot, window)
    assert bar.find_field.text() == "gamma"
    assert bar.find_field.selectedText() == "gamma"


# ----------------------------------------------------------------------------- finding

def test_typing_selects_the_first_match_at_or_after_the_caret(qtbot, window, bar, editor):
    open_find(qtbot, window)
    type_find(qtbot, bar, "alpha")
    assert selection_of(editor) == (0, 5)


def test_the_search_starts_at_the_caret(qtbot, window, bar, editor):
    cursor = editor.textCursor()
    cursor.setPosition(1)
    editor.setTextCursor(cursor)
    open_find(qtbot, window)
    type_find(qtbot, bar, "alpha")
    assert selection_of(editor) == (11, 16)


def test_typing_more_of_the_word_keeps_the_same_match(qtbot, window, bar, editor):
    open_find(qtbot, window)
    bar.find_field.setFocus()
    seen = []
    for letter in "alpha":
        qtbot.keyClicks(bar.find_field, letter)
        seen.append(selection_of(editor))
    assert seen == [(0, 1), (0, 2), (0, 3), (0, 4), (0, 5)]


def test_the_search_ignores_case_by_default(qtbot, window, bar, editor):
    open_find(qtbot, window)
    type_find(qtbot, bar, "ALPHA")
    assert selection_of(editor) == (0, 5)
    assert editor.textCursor().selectedText() == "alpha"


def test_enter_goes_to_the_next_match_and_wraps_round(qtbot, window, bar, editor):
    open_find(qtbot, window)
    type_find(qtbot, bar, "alpha")
    qtbot.keyClick(bar.find_field, Key.Key_Return)
    assert selection_of(editor) == (11, 16)
    qtbot.keyClick(bar.find_field, Key.Key_Return)
    assert selection_of(editor) == (23, 28)
    qtbot.keyClick(bar.find_field, Key.Key_Return)
    assert selection_of(editor) == (0, 5)


def test_shift_enter_goes_to_the_previous_match_and_wraps_round(qtbot, window, bar, editor):
    open_find(qtbot, window)
    type_find(qtbot, bar, "alpha")
    qtbot.keyClick(bar.find_field, Key.Key_Return, SHIFT)
    assert selection_of(editor) == (23, 28)
    qtbot.keyClick(bar.find_field, Key.Key_Return, SHIFT)
    assert selection_of(editor) == (11, 16)


def test_keypad_enter_works_like_enter(qtbot, window, bar, editor):
    open_find(qtbot, window)
    type_find(qtbot, bar, "alpha")
    qtbot.keyClick(bar.find_field, Key.Key_Enter, Qt.KeyboardModifier.KeypadModifier)
    assert selection_of(editor) == (11, 16)


def test_enter_in_the_find_field_does_not_touch_the_text(qtbot, window, bar, editor):
    open_find(qtbot, window)
    type_find(qtbot, bar, "alpha")
    qtbot.keyClick(bar.find_field, Key.Key_Return)
    assert editor.toPlainText() == DOC


def test_f3_and_shift_f3_move_through_the_matches_with_the_bar_open(qtbot, window, bar, editor):
    open_find(qtbot, window)
    type_find(qtbot, bar, "alpha")
    qtbot.keyClick(bar.find_field, Key.Key_F3)
    assert selection_of(editor) == (11, 16)
    qtbot.keyClick(bar.find_field, Key.Key_F3, SHIFT)
    assert selection_of(editor) == (0, 5)


def test_f3_works_from_the_text_after_the_bar_was_closed_and_brings_the_bar_back(qtbot, window, bar, editor):
    open_find(qtbot, window)
    type_find(qtbot, bar, "alpha")
    qtbot.keyClick(bar.find_field, Key.Key_Escape)
    cursor = editor.textCursor()
    cursor.setPosition(0)
    editor.setTextCursor(cursor)
    qtbot.keyClick(editor, Key.Key_F3)
    assert selection_of(editor) == (0, 5)
    assert bar.isVisible()
    assert QApplication.focusWidget() is editor  # the text keeps the focus
    qtbot.keyClick(editor, Key.Key_F3)
    assert selection_of(editor) == (11, 16)
    qtbot.keyClick(editor, Key.Key_F3, SHIFT)
    assert selection_of(editor) == (0, 5)


def test_f3_with_nothing_to_search_for_opens_the_bar_ready_to_type(qtbot, window, bar, editor):
    qtbot.keyClick(editor, Key.Key_F3)
    assert bar.isVisible()
    assert QApplication.focusWidget() is bar.find_field


def test_match_case_makes_the_search_exact(qtbot, window, bar, editor):
    open_find(qtbot, window)
    type_find(qtbot, bar, "alpha")
    assert bar.counter_label.text() == "1 of 3"
    bar.match_case_box.setChecked(True)
    assert bar.counter_label.text() == "1 of 2"
    assert search_highlights(editor) == [0, 11]
    qtbot.keyClick(bar.find_field, Key.Key_Return)
    qtbot.keyClick(bar.find_field, Key.Key_Return)
    assert selection_of(editor) == (0, 5)  # ALPHA at 23 does not count


def test_nothing_found_leaves_the_selection_alone(qtbot, window, bar, editor):
    select_range(editor, 6, 10)
    open_find(qtbot, window)
    type_find(qtbot, bar, "zzz")
    assert selection_of(editor) == (6, 10)
    qtbot.keyClick(bar.find_field, Key.Key_Return)
    assert selection_of(editor) == (6, 10)
    assert search_highlights(editor) == []


def test_an_empty_search_finds_nothing_and_highlights_nothing(qtbot, window, bar, editor):
    open_find(qtbot, window)
    type_find(qtbot, bar, "alpha")
    bar.find_field.clear()
    assert search_highlights(editor) == []
    assert bar.counter_label.text() == ""
    selected = selection_of(editor)
    qtbot.keyClick(bar.find_field, Key.Key_Return)
    assert selection_of(editor) == selected


def test_searching_an_empty_document_is_harmless(qtbot, window, bar):
    window.prompt_box.setPlainText("")
    open_find(qtbot, window)
    type_find(qtbot, bar, "a")
    qtbot.keyClick(bar.find_field, Key.Key_Return)
    assert bar.counter_label.text() == "No matches"


def test_searching_does_not_change_the_text_or_the_undo_history(qtbot, window, bar, editor):
    open_find(qtbot, window)
    type_find(qtbot, bar, "alpha")
    qtbot.keyClick(bar.find_field, Key.Key_Return)
    assert editor.toPlainText() == DOC
    assert not editor.document().isUndoAvailable()


def test_characters_outside_the_basic_plane_are_found_where_they_are(qtbot, window, bar):
    window.prompt_box.setPlainText("😀 x 😀")
    cursor = window.prompt_box.textCursor()
    cursor.setPosition(0)
    window.prompt_box.setTextCursor(cursor)
    open_find(qtbot, window)
    bar.find_field.setText("😀")
    assert selection_of(window.prompt_box) == (0, 2)
    qtbot.keyClick(bar.find_field, Key.Key_Return)
    assert selection_of(window.prompt_box) == (5, 7)


# ------------------------------------------------------------------------------ counter

def test_the_counter_says_which_match_of_how_many_is_selected(qtbot, window, bar, editor):
    open_find(qtbot, window)
    type_find(qtbot, bar, "alpha")
    assert bar.counter_label.text() == "1 of 3"
    qtbot.keyClick(bar.find_field, Key.Key_Return)
    assert bar.counter_label.text() == "2 of 3"
    qtbot.keyClick(bar.find_field, Key.Key_Return, SHIFT)
    assert bar.counter_label.text() == "1 of 3"


def test_when_no_match_is_selected_the_counter_says_how_many_there_are(qtbot, window, bar, editor):
    open_find(qtbot, window)
    type_find(qtbot, bar, "alpha")
    select_range(editor, 6, 10)
    assert bar.counter_label.text() == "3 matches"
    type_find(qtbot, bar, "gamma")
    select_range(editor, 0, 0)
    assert bar.counter_label.text() == "1 match"


def test_the_counter_says_when_there_is_no_match_and_shows_it_in_the_error_color(qtbot, window, bar, editor):
    open_find(qtbot, window)
    type_find(qtbot, bar, "zzz")
    assert bar.counter_label.text() == "No matches"
    assert bar.counter_label.palette().windowText().color().name() == DARK_THEME.error_text
    type_find(qtbot, bar, "alpha")
    assert bar.counter_label.palette().windowText().color().name() == DARK_THEME.default_text


def test_the_counter_follows_changes_to_the_text(qtbot, window, bar, editor):
    open_find(qtbot, window)
    type_find(qtbot, bar, "alpha")
    select_range(editor, 6, 10)  # "beta", which is not a match
    assert bar.counter_label.text() == "3 matches"
    cursor = QTextCursor(editor.document())
    cursor.setPosition(0)
    cursor.insertText("alpha ")
    assert bar.counter_label.text() == "4 matches"


def test_a_very_large_number_of_matches_is_counted_up_to_a_limit(qtbot, window, bar):
    window.prompt_box.setPlainText("a\n" * (MATCH_LIMIT + 500))
    cursor = window.prompt_box.textCursor()
    cursor.setPosition(0)
    window.prompt_box.setTextCursor(cursor)
    open_find(qtbot, window)
    type_find(qtbot, bar, "a")
    assert bar.counter_label.text() == f"1 of {MATCH_LIMIT}+"
    assert len(search_highlights(window.prompt_box)) == MATCH_LIMIT


# ---------------------------------------------------------------------------- highlights

def test_every_match_is_highlighted(qtbot, window, bar, editor):
    open_find(qtbot, window)
    type_find(qtbot, bar, "alpha")
    assert search_highlights(editor) == [0, 11, 23]
    type_find(qtbot, bar, "beta")
    assert search_highlights(editor) == [6]


def test_a_highlight_covers_exactly_the_found_text(qtbot, window, bar, editor):
    open_find(qtbot, window)
    type_find(qtbot, bar, "alpha")
    covered = sorted(
        (item.cursor.selectionStart(), item.cursor.selectionEnd())
        for item in editor.extraSelections()
        if item.format.background().color().name() == DARK_THEME.find_match_background
    )
    assert covered == [(0, 5), (11, 16), (23, 28)]


def test_highlights_use_the_theme_colors(qtbot, window, bar, editor):
    open_find(qtbot, window)
    type_find(qtbot, bar, "beta")
    [item] = [i for i in editor.extraSelections() if i.format.background().color().name() == DARK_THEME.find_match_background]
    assert item.format.foreground().color().name() == DARK_THEME.find_match_text


def test_highlights_follow_changes_to_the_text(qtbot, window, bar, editor):
    open_find(qtbot, window)
    type_find(qtbot, bar, "alpha")
    cursor = QTextCursor(editor.document())
    cursor.setPosition(0)
    cursor.insertText("alpha ")
    assert search_highlights(editor) == [0, 6, 17, 29]


def test_highlights_and_the_bracket_highlight_exist_together(qtbot, window, bar):
    window.prompt_box.setPlainText("f(alpha) alpha")
    cursor = window.prompt_box.textCursor()
    cursor.setPosition(8)
    window.prompt_box.setTextCursor(cursor)
    open_find(qtbot, window)
    type_find(qtbot, bar, "alpha")
    colors = [item.format.background().color().name() for item in window.prompt_box.extraSelections()]
    assert colors.count(DARK_THEME.find_match_background) == 2
    assert colors.count(DARK_THEME.matching_bracket_background) == 0  # the caret is no longer by a bracket
    select_range(window.prompt_box, 8, 8)
    colors = [item.format.background().color().name() for item in window.prompt_box.extraSelections()]
    assert colors.count(DARK_THEME.find_match_background) == 2
    assert colors.count(DARK_THEME.matching_bracket_background) == 2


# ----------------------------------------------------------------------------- replacing

def test_replace_puts_the_replacement_in_place_of_the_selected_match_and_moves_on(qtbot, window, bar, editor):
    open_replace(qtbot, window)
    type_find(qtbot, bar, "alpha")
    bar.replace_field.setText("X")
    bar.replace_button.click()
    assert editor.toPlainText() == "X beta alpha gamma ALPHA"
    assert selection_of(editor) == (7, 12)  # the next match, now two characters earlier


def test_replace_with_the_selection_elsewhere_only_moves_to_the_next_match(qtbot, window, bar, editor):
    open_replace(qtbot, window)
    type_find(qtbot, bar, "alpha")
    select_range(editor, 6, 10)  # "beta" is not a match
    bar.replace_field.setText("X")
    bar.replace_button.click()
    assert editor.toPlainText() == DOC
    assert selection_of(editor) == (11, 16)


def test_enter_in_the_replace_field_replaces_too(qtbot, window, bar, editor):
    open_replace(qtbot, window)
    type_find(qtbot, bar, "alpha")
    bar.replace_field.setFocus()
    qtbot.keyClicks(bar.replace_field, "X")
    qtbot.keyClick(bar.replace_field, Key.Key_Return)
    assert editor.toPlainText() == "X beta alpha gamma ALPHA"


def test_replacing_again_and_again_works_through_the_matches_and_wraps(qtbot, window, bar, editor):
    open_replace(qtbot, window)
    type_find(qtbot, bar, "alpha")
    bar.replace_field.setText("-")
    for _ in range(3):
        bar.replace_button.click()
    assert editor.toPlainText() == "- beta - gamma -"
    assert bar.counter_label.text() == "No matches"


def test_a_replacement_that_contains_the_search_text_is_not_searched_again(qtbot, window, bar):
    window.prompt_box.setPlainText("a a")
    cursor = window.prompt_box.textCursor()
    cursor.setPosition(0)
    window.prompt_box.setTextCursor(cursor)
    open_replace(qtbot, window)
    type_find(qtbot, bar, "a")
    bar.replace_field.setText("aa")
    bar.replace_button.click()
    assert window.prompt_box.toPlainText() == "aa a"
    assert selection_of(window.prompt_box) == (3, 4)


def test_replace_all_replaces_every_match(qtbot, window, bar, editor):
    open_replace(qtbot, window)
    type_find(qtbot, bar, "alpha")
    bar.replace_field.setText("X")
    bar.replace_all_button.click()
    assert editor.toPlainText() == "X beta X gamma X"
    assert bar.counter_label.text() == "Replaced 3"


def test_replace_all_is_one_undo_step(qtbot, window, bar, editor):
    open_replace(qtbot, window)
    type_find(qtbot, bar, "alpha")
    bar.replace_field.setText("X")
    bar.replace_all_button.click()
    editor.undo()
    assert editor.toPlainText() == DOC
    assert not editor.document().isUndoAvailable()
    editor.redo()
    assert editor.toPlainText() == "X beta X gamma X"


def test_replace_all_respects_match_case(qtbot, window, bar, editor):
    open_replace(qtbot, window)
    bar.match_case_box.setChecked(True)
    type_find(qtbot, bar, "alpha")
    bar.replace_field.setText("X")
    bar.replace_all_button.click()
    assert editor.toPlainText() == "X beta X gamma ALPHA"
    assert bar.counter_label.text() == "Replaced 2"


def test_replace_all_with_a_replacement_that_contains_the_search_text(qtbot, window, bar):
    window.prompt_box.setPlainText("banana")
    open_replace(qtbot, window)
    type_find(qtbot, bar, "a")
    bar.replace_field.setText("aa")
    bar.replace_all_button.click()
    assert window.prompt_box.toPlainText() == "baanaanaa"
    assert bar.counter_label.text() == "Replaced 3"


def test_an_empty_replacement_deletes_the_matches(qtbot, window, bar):
    window.prompt_box.setPlainText("a-b-c")
    open_replace(qtbot, window)
    type_find(qtbot, bar, "-")
    bar.replace_field.clear()
    bar.replace_all_button.click()
    assert window.prompt_box.toPlainText() == "abc"


def test_replace_all_with_nothing_to_find_does_nothing(qtbot, window, bar, editor):
    open_replace(qtbot, window)
    bar.find_field.clear()
    bar.replace_field.setText("X")
    bar.replace_all_button.click()
    assert editor.toPlainText() == DOC
    type_find(qtbot, bar, "zzz")
    bar.replace_all_button.click()
    assert editor.toPlainText() == DOC
    assert not editor.document().isUndoAvailable()


def test_replacing_works_around_characters_outside_the_basic_plane(qtbot, window, bar):
    window.prompt_box.setPlainText("😀 x 😀")
    open_replace(qtbot, window)
    bar.find_field.setText("😀")
    bar.replace_field.setText("y")
    bar.replace_all_button.click()
    assert window.prompt_box.toPlainText() == "y x y"


def test_the_highlights_follow_a_replacement(qtbot, window, bar, editor):
    open_replace(qtbot, window)
    type_find(qtbot, bar, "alpha")
    bar.replace_field.setText("beta")
    bar.replace_button.click()
    assert editor.toPlainText() == "beta beta alpha gamma ALPHA"
    assert search_highlights(editor) == [10, 22]  # "beta" is a character shorter than "alpha"


def test_replace_text_with_line_text_around_it_keeps_the_rest_of_the_document(qtbot, window, bar):
    window.prompt_box.setPlainText("x = 1\ny = 1\nz = 2")
    open_replace(qtbot, window)
    type_find(qtbot, bar, "1")
    bar.replace_field.setText("10")
    bar.replace_all_button.click()
    assert window.prompt_box.toPlainText() == "x = 10\ny = 10\nz = 2"


# --------------------------------------------------------------------------- the window

def test_ctrl_enter_in_the_find_field_runs_the_prompt(qtbot, window, bar):
    window.prompt_box.setPlainText("print('from the bar')")
    open_find(qtbot, window)
    qtbot.keyClick(bar.find_field, Key.Key_Return, CONTROL)
    assert window.current_run is not None
    qtbot.waitUntil(lambda: window.current_run is None, timeout=30000)
    assert window.output_box.toPlainText() == "from the bar\n"


def test_the_bar_does_not_disturb_typing_in_the_prompt_box(qtbot, window, bar, editor):
    open_find(qtbot, window)
    window.prompt_box.setFocus()
    qtbot.keyClicks(window.prompt_box, "x")
    assert editor.toPlainText() == "x" + DOC
