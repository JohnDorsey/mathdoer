"""Tests for the read-only output box."""
import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontDatabase, QFontInfo, QTextCursor

from mathdoer.interface.fonts import MONOSPACE_FAMILIES
from mathdoer.interface.output_display import OutputDisplay, truncation_notice
from mathdoer.interface.theme import DARK_THEME


@pytest.fixture
def display(qtbot):
    widget = OutputDisplay(DARK_THEME)
    qtbot.addWidget(widget)
    widget.resize(500, 200)
    return widget


def foreground_at(display, index):
    cursor = QTextCursor(display.document())
    cursor.setPosition(index + 1)
    return cursor.charFormat().foreground().color().name()


def plain(text):
    return [(text, False)]


# ------------------------------------------------------------------- the widget

def test_the_box_is_read_only_but_selectable_and_keeps_no_undo_history(display):
    assert display.isReadOnly()
    assert display.textInteractionFlags() & Qt.TextInteractionFlag.TextSelectableByMouse
    assert display.textInteractionFlags() & Qt.TextInteractionFlag.TextSelectableByKeyboard
    assert not display.isUndoRedoEnabled()


def test_the_box_uses_the_theme_colors(display):
    palette = display.palette()
    assert palette.base().color().name() == DARK_THEME.text_background
    assert palette.text().color().name() == DARK_THEME.default_text
    assert palette.highlight().color().name() == DARK_THEME.selection_background
    assert palette.highlightedText().color().name() == DARK_THEME.selection_text


def test_the_box_asks_for_a_monospace_font(display):
    assert display.font().styleHint() == QFont.StyleHint.Monospace
    assert display.font().fixedPitch()
    assert display.font().families() == MONOSPACE_FAMILIES


def test_the_font_that_is_found_is_fixed_pitch(display):
    if not QFontDatabase.families():
        pytest.skip("the offscreen platform has an empty font database")
    assert QFontInfo(display.font()).fixedPitch()


# ----------------------------------------------------------------------- output

def test_output_is_shown_and_errors_are_colored(display):
    display.apply_changes(segments=[("out\n", False), ("err\n", True)])
    assert display.toPlainText() == "out\nerr\n"
    assert foreground_at(display, 0) == DARK_THEME.default_text
    assert foreground_at(display, 2) == DARK_THEME.default_text
    assert foreground_at(display, 4) == DARK_THEME.error_text
    assert foreground_at(display, 6) == DARK_THEME.error_text


def test_output_accumulates_across_calls(display):
    display.apply_changes(segments=plain("ab"))
    display.apply_changes(segments=plain("cd"))
    assert display.toPlainText() == "abcd"


def test_nothing_changes_when_given_nothing(display):
    display.apply_changes()
    assert display.toPlainText() == ""


# --------------------------------------------------------------------- progress

def test_progress_is_shown_after_the_output_on_its_own_line(display):
    display.apply_changes(segments=plain("abc"), progress_text="/")
    assert display.toPlainText() == "abc\n/"


def test_progress_needs_no_extra_line_when_the_output_ends_with_a_newline(display):
    display.apply_changes(segments=plain("abc\n"), progress_text="/")
    assert display.toPlainText() == "abc\n/"


def test_progress_alone_in_an_empty_box_has_no_leading_newline(display):
    display.apply_changes(progress_text="/")
    assert display.toPlainText() == "/"


def test_progress_is_in_the_normal_text_color(display):
    display.apply_changes(segments=[("err\n", True)], progress_text="|")
    assert foreground_at(display, len("err\n")) == DARK_THEME.default_text


def test_progress_is_replaced_not_repeated(display):
    display.apply_changes(segments=plain("abc"), progress_text="/")
    display.apply_changes(progress_text="- 00:05")
    assert display.toPlainText() == "abc\n- 00:05"


def test_removing_progress_removes_the_line_break_it_added(display):
    display.apply_changes(segments=plain("abc"), progress_text="/")
    display.apply_changes(progress_text=None)
    assert display.toPlainText() == "abc"
    display.apply_changes(segments=plain("def"))
    assert display.toPlainText() == "abcdef"


def test_new_output_goes_before_the_progress(display):
    display.apply_changes(segments=plain("abc"), progress_text="/")
    display.apply_changes(segments=plain("def"), progress_text="-")
    assert display.toPlainText() == "abcdef\n-"


# ---------------------------------------------------------------- discarding

def test_discarded_text_is_removed_from_the_beginning_and_a_notice_is_shown(display):
    display.apply_changes(segments=plain("abcdef"))
    display.apply_changes(discarded_text="abc", discarded_character_count=3)
    assert display.toPlainText() == truncation_notice(3) + "\n" + "def"
    assert foreground_at(display, 0) == DARK_THEME.notice_text


def test_the_notice_is_updated_not_duplicated(display):
    display.apply_changes(segments=plain("abcdef"))
    display.apply_changes(discarded_text="abc", discarded_character_count=3)
    display.apply_changes(discarded_text="d", discarded_character_count=4)
    assert display.toPlainText() == truncation_notice(4) + "\n" + "ef"
    assert display.toPlainText().count("truncated") == 1


def test_the_notice_names_the_number_of_discarded_characters():
    assert "1234" in truncation_notice(1234)
    assert "truncated" in truncation_notice(1234)


def test_text_added_and_discarded_in_the_same_call_leaves_the_newest(display):
    display.apply_changes(
        segments=plain("abcdefgh"), discarded_text="abcde", discarded_character_count=5
    )
    assert display.toPlainText() == truncation_notice(5) + "\n" + "fgh"


def test_discarding_counts_characters_outside_the_basic_plane_correctly(display):
    display.apply_changes(segments=plain("😀😀abc"))
    display.apply_changes(discarded_text="😀", discarded_character_count=1)
    assert display.toPlainText() == truncation_notice(1) + "\n" + "😀abc"
    display.apply_changes(discarded_text="😀a", discarded_character_count=3)
    assert display.toPlainText() == truncation_notice(3) + "\n" + "bc"


def test_discarding_works_with_progress_showing(display):
    display.apply_changes(segments=plain("abcdef"), progress_text="/")
    display.apply_changes(discarded_text="ab", discarded_character_count=2, progress_text="-")
    assert display.toPlainText() == truncation_notice(2) + "\n" + "cdef\n-"


def test_discarded_error_text_leaves_the_rest_in_its_own_color(display):
    display.apply_changes(segments=[("ab", False), ("CD", True)])
    display.apply_changes(discarded_text="a", discarded_character_count=1)
    body_start = len(truncation_notice(1)) + 1
    assert display.toPlainText()[body_start:] == "bCD"
    assert foreground_at(display, body_start) == DARK_THEME.default_text
    assert foreground_at(display, body_start + 1) == DARK_THEME.error_text


# --------------------------------------------------------------------- markers

def test_a_marker_goes_on_its_own_line_in_the_notice_color(display):
    display.apply_changes(segments=plain("abc"))
    display.append_marker("[cancelled]")
    assert display.toPlainText() == "abc\n[cancelled]"
    assert foreground_at(display, len("abc\n")) == DARK_THEME.notice_text


def test_a_marker_after_a_newline_needs_no_extra_line(display):
    display.apply_changes(segments=plain("abc\n"))
    display.append_marker("[cancelled]")
    assert display.toPlainText() == "abc\n[cancelled]"


def test_a_marker_in_an_empty_box_has_no_leading_newline(display):
    display.append_marker("[cancelled]")
    assert display.toPlainText() == "[cancelled]"


def test_a_marker_replaces_the_progress(display):
    display.apply_changes(segments=plain("abc"), progress_text="/")
    display.append_marker("[cancelled]")
    assert display.toPlainText() == "abc\n[cancelled]"


# ------------------------------------------------------------------ output text

def test_the_output_text_is_what_is_shown_without_the_progress_line(display):
    display.apply_changes(segments=plain("abc"), progress_text="/ 00:05")
    assert display.output_text() == "abc"
    assert display.toPlainText() == "abc\n/ 00:05"


def test_the_output_text_keeps_the_notice_and_markers(display):
    display.apply_changes(segments=plain("abcdef"), discarded_text="ab", discarded_character_count=2)
    display.append_marker("[cancelled]")
    assert display.output_text() == truncation_notice(2) + "\n" + "cdef\n[cancelled]"


def test_the_output_text_of_an_empty_box_is_empty(display):
    assert display.output_text() == ""
    display.apply_changes(progress_text="/")
    assert display.output_text() == ""


# ----------------------------------------------------------------------- clear

def test_clearing_forgets_everything_including_the_notice_and_progress(display):
    display.apply_changes(
        segments=plain("abcdef"), discarded_text="abc", discarded_character_count=3,
        progress_text="/",
    )
    display.clear_output()
    assert display.toPlainText() == ""
    display.apply_changes(segments=plain("xyz"), progress_text="-")
    assert display.toPlainText() == "xyz\n-"
    display.apply_changes(discarded_text="x", discarded_character_count=1)
    assert display.toPlainText() == truncation_notice(1) + "\n" + "yz"


# --------------------------------------------------------------------- scrolling

def lines(count):
    return plain("".join(f"line {number}\n" for number in range(count)))


def test_the_view_follows_new_output_while_at_the_bottom(qtbot, display):
    display.show()
    display.apply_changes(segments=lines(200))
    bar = display.verticalScrollBar()
    qtbot.waitUntil(lambda: bar.maximum() > 0 and bar.value() == bar.maximum())
    display.apply_changes(segments=lines(50))
    qtbot.waitUntil(lambda: bar.value() == bar.maximum())


def test_the_view_stays_put_when_the_user_has_scrolled_up(qtbot, display):
    display.show()
    display.apply_changes(segments=lines(200))
    bar = display.verticalScrollBar()
    qtbot.waitUntil(lambda: bar.maximum() > 0)
    bar.setValue(0)
    display.apply_changes(segments=lines(50))
    qtbot.wait(50)
    assert bar.value() == 0
