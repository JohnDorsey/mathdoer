"""Tests for syntax highlighting and the highlighted pair of brackets in the prompt box."""
from dataclasses import replace

import pytest
from PySide6.QtGui import QTextCursor

from mathdoer.interface.prompt_editor import PromptEditor
from mathdoer.interface.theme import DARK_THEME
from mathdoer.languages.python import PYTHON
from mathdoer.syntax import LexedLine, Token, TokenKind

COLORS = DARK_THEME.token_colors
COMMENT, STRING, NUMBER = COLORS[TokenKind.COMMENT], COLORS[TokenKind.STRING], COLORS[TokenKind.NUMBER]
KEYWORD, BUILTIN, OPERATOR = COLORS[TokenKind.KEYWORD], COLORS[TokenKind.BUILTIN], COLORS[TokenKind.OPERATOR]


@pytest.fixture
def editor(qtbot):
    widget = PromptEditor(DARK_THEME, PYTHON)
    qtbot.addWidget(widget)
    widget.resize(600, 300)
    widget.show()
    return widget


def line_formats(editor, line):
    """The colors applied to a line, as (start, length, color) in UTF-16 units."""
    block = editor.document().findBlockByNumber(line)
    return [
        (item.start, item.length, item.format.foreground().color().name())
        for item in block.layout().formats()
    ]


def move_caret(editor, position):
    cursor = editor.textCursor()
    cursor.setPosition(position)
    editor.setTextCursor(cursor)


def highlighted_brackets(editor):
    return sorted((item.cursor.selectionStart(), item.cursor.selectedText()) for item in editor.extraSelections())


# ----------------------------------------------------------------------- highlighting

def test_numbers_comments_and_operators_get_their_colors(editor):
    editor.setPlainText("x = 1  # note")
    assert line_formats(editor, 0) == [(2, 1, OPERATOR), (4, 1, NUMBER), (7, 6, COMMENT)]


def test_keywords_and_builtins_get_their_colors(editor):
    editor.setPlainText("if x and len(y):")
    assert line_formats(editor, 0) == [(0, 2, KEYWORD), (5, 3, KEYWORD), (9, 3, BUILTIN)]


def test_names_that_are_neither_have_no_color_of_their_own(editor):
    editor.setPlainText("abc = abc")
    assert line_formats(editor, 0) == [(4, 1, OPERATOR)]


def test_every_kind_of_text_is_colored_with_its_theme_color(editor):
    editor.setPlainText('@decorator\nclass A:\n    def f(self, n=0x1F):\n        return len("s")  # c')
    seen = {color for line in range(4) for _, _, color in line_formats(editor, line)}
    assert seen == set(COLORS.values())


def test_a_triple_quoted_string_is_colored_across_its_lines(editor):
    editor.setPlainText('"""abc\ndef\nghi"""\nx = 1')
    assert line_formats(editor, 0) == [(0, 6, STRING)]
    assert line_formats(editor, 1) == [(0, 3, STRING)]
    assert line_formats(editor, 2) == [(0, 6, STRING)]
    assert line_formats(editor, 3) == [(2, 1, OPERATOR), (4, 1, NUMBER)]


def test_closing_a_string_recolors_the_lines_after_it(editor):
    editor.setPlainText('"""abc\ndef')
    assert line_formats(editor, 1) == [(0, 3, STRING)]
    cursor = QTextCursor(editor.document())
    cursor.setPosition(6)
    cursor.insertText('"""')
    assert editor.document().findBlockByNumber(0).text() == '"""abc"""'
    assert line_formats(editor, 1) == [(0, 3, KEYWORD)]  # code again: def is a keyword, not text
    cursor.setPosition(6)
    cursor.setPosition(9, QTextCursor.MoveMode.KeepAnchor)
    cursor.removeSelectedText()
    assert line_formats(editor, 1) == [(0, 3, STRING)]


def test_colors_are_placed_correctly_after_characters_outside_the_basic_plane(editor):
    editor.setPlainText('😀 = "ab"')
    assert line_formats(editor, 0) == [(3, 1, OPERATOR), (5, 4, STRING)]


def test_highlighting_is_not_part_of_the_undo_history(qtbot, editor):
    editor.setPlainText("x = 1")
    assert not editor.document().isUndoAvailable()
    qtbot.keyClicks(editor, "y")
    editor.undo()
    assert editor.toPlainText() == "x = 1"
    assert not editor.document().isUndoAvailable()


def test_the_language_decides_what_is_colored(qtbot):
    def everything_is_a_comment(text, state):
        return LexedLine((Token(0, len(text), TokenKind.COMMENT),) if text else (), 0)

    widget = PromptEditor(DARK_THEME, replace(PYTHON, lex_line=everything_is_a_comment))
    qtbot.addWidget(widget)
    widget.setPlainText("if x:")
    assert line_formats(widget, 0) == [(0, 5, COMMENT)]


def test_a_line_with_nothing_to_color_has_no_formats(editor):
    editor.setPlainText("abc\n\n   ")
    assert [line_formats(editor, line) for line in range(3)] == [[], [], []]


# ----------------------------------------------------------------- the bracket pair

def test_the_pair_next_to_the_caret_is_highlighted(editor):
    editor.setPlainText("f(x)")
    move_caret(editor, 4)
    assert highlighted_brackets(editor) == [(1, "("), (3, ")")]


def test_the_highlight_uses_the_theme_color(editor):
    editor.setPlainText("f(x)")
    move_caret(editor, 4)
    colors = {item.format.background().color().name() for item in editor.extraSelections()}
    assert colors == {DARK_THEME.matching_bracket_background}


def test_the_highlight_goes_away_when_the_caret_moves_off_the_bracket(editor):
    editor.setPlainText("f(x)")
    move_caret(editor, 4)
    move_caret(editor, 0)
    assert highlighted_brackets(editor) == []


def test_the_highlight_follows_the_caret(editor):
    editor.setPlainText("(a) [b]")
    move_caret(editor, 3)
    assert highlighted_brackets(editor) == [(0, "("), (2, ")")]
    move_caret(editor, 7)
    assert highlighted_brackets(editor) == [(4, "["), (6, "]")]


def test_typing_the_closing_bracket_highlights_the_pair(qtbot, editor):
    qtbot.keyClicks(editor, "f(x")
    assert highlighted_brackets(editor) == []
    qtbot.keyClicks(editor, ")")
    assert highlighted_brackets(editor) == [(1, "("), (3, ")")]


def test_a_bracket_without_a_partner_is_not_highlighted(editor):
    editor.setPlainText("f(x")
    move_caret(editor, 2)
    assert highlighted_brackets(editor) == []


def test_brackets_in_strings_and_comments_are_ignored(editor):
    editor.setPlainText('print("(") + (1)  # )')
    move_caret(editor, 16)
    assert highlighted_brackets(editor) == [(13, "("), (15, ")")]
    move_caret(editor, 8)
    assert highlighted_brackets(editor) == []


def test_a_pair_on_different_lines_is_highlighted(editor):
    editor.setPlainText("def f(\n    a,\n    b):")
    move_caret(editor, len("def f(\n    a,\n    b)"))
    assert highlighted_brackets(editor) == [(5, "("), (len("def f(\n    a,\n    b)") - 1, ")")]


def test_lines_inside_a_triple_quoted_string_are_not_searched_for_brackets(editor):
    editor.setPlainText('s = """\n(\n"""\n(x)')
    text = editor.toPlainText()
    move_caret(editor, text.index("(x)") + 3)
    assert highlighted_brackets(editor) == [(text.index("(x)"), "("), (text.index("(x)") + 2, ")")]
    move_caret(editor, text.index("(\n") + 1)
    assert highlighted_brackets(editor) == []


def test_a_pair_of_brackets_inside_a_triple_quoted_string_is_not_highlighted(editor):
    editor.setPlainText('s = """\n(\n)\n"""')
    move_caret(editor, editor.toPlainText().index("(") + 1)
    assert highlighted_brackets(editor) == []


def test_positions_after_wide_characters_are_right(editor):
    editor.setPlainText("😀(x)")
    move_caret(editor, 5)
    assert highlighted_brackets(editor) == [(2, "("), (4, ")")]


def test_the_highlight_does_not_change_the_text_or_the_undo_history(editor):
    editor.setPlainText("f(x)")
    move_caret(editor, 4)
    assert editor.toPlainText() == "f(x)"
    assert not editor.document().isUndoAvailable()


def test_moving_the_caret_again_does_not_pile_up_highlights(editor):
    editor.setPlainText("f(x)")
    for _ in range(5):
        move_caret(editor, 4)
        move_caret(editor, 3)
    assert len(editor.extraSelections()) == 2


def test_a_bracket_next_to_the_end_of_a_selection_counts(editor):
    editor.setPlainText("f(x)")
    cursor = editor.textCursor()
    cursor.setPosition(0)
    cursor.setPosition(4, QTextCursor.MoveMode.KeepAnchor)
    editor.setTextCursor(cursor)
    assert highlighted_brackets(editor) == [(1, "("), (3, ")")]
