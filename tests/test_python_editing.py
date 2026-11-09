"""Tests for the Python rules the editor follows."""
import pytest

from mathdoer.languages.python import PYTHON
from mathdoer.languages.python.editing import opens_indented_block


def opens(lines, line, column=None):
    """Does the text before the position (default: the end of the line) open a block?"""
    return opens_indented_block(lines, line, len(lines[line]) if column is None else column)


@pytest.mark.parametrize(
    "line",
    ["if x:", "else:", "try:", "finally:", "while True:", "for i in range(3):", "class A:",
     "class A(B):", "def f(x: int) -> int:", "with open(p) as f:", "elif a and b:", "    if x:",
     "\tif x:", "if x:   ", "if x:  # why", "if x:#why", "match x:", "case 1:"],
)
def test_a_line_that_ends_with_a_colon_opens_a_block(line):
    assert opens([line], 0)


@pytest.mark.parametrize(
    "line",
    ["x = 1", "", "   ", "if x: pass", "x = d[1:", "x = {1:", "f(a,", "# note:", "x = 'a:'", "x = 'a:",
     'x = "a:', "print(x)", "x: int", "y = [", "z = )"],
)
def test_other_lines_do_not(line):
    assert not opens([line], 0)


def test_only_the_text_before_the_position_counts():
    line = "if x:"
    assert opens([line], 0, 5)
    assert not opens([line], 0, 4)
    assert not opens([line], 0, 0)


def test_a_comment_after_the_colon_is_ignored_even_when_the_position_is_inside_it():
    line = "if x:  # comment: here"
    assert opens([line], 0, len(line))
    assert opens([line], 0, 5)
    assert opens([line], 0, 10)


def test_a_colon_inside_a_comment_alone_is_not_a_block():
    assert not opens(["x = 1  # see below:"], 0)


def test_a_colon_inside_a_bracket_opened_on_an_earlier_line_is_not_a_block():
    assert not opens(["d = {", "    1:"], 1)
    assert not opens(["x = [", "    a[1:"], 1)


def test_a_colon_after_brackets_that_have_closed_is_a_block():
    assert opens(["d = {", "}", "if x:"], 2)
    assert opens(["if (a and", "      b):"], 1)


def test_a_colon_on_a_line_after_a_colon_line_is_judged_by_its_own_line():
    assert not opens(["if x:", ""], 1)
    assert not opens(["if x:", "    y = 1"], 1)
    assert opens(["if x:", "    if y:"], 1)


def test_nothing_inside_a_triple_quoted_string_is_code():
    assert not opens(['s = """', "if x:"], 1)
    assert not opens(["s = '''", "if x:"], 1)
    assert opens(['s = """a', 'b"""', "if x:"], 2)


def test_a_string_split_by_a_backslash_continues_on_the_next_line():
    assert not opens(["s = 'abc\\", "if x:"], 1)


def test_extra_closing_brackets_do_not_make_the_depth_negative():
    assert opens(["x = )", "if y:"], 1)


def test_a_position_in_the_middle_of_a_multi_line_document_sees_only_what_comes_before_it():
    lines = ["a = (1,", "     2)", "if a:", "    pass"]
    assert opens(lines, 2)
    assert not opens(lines, 0)
    assert not opens(lines, 1)


def test_python_is_described_to_the_editor():
    rules = PYTHON.editing
    assert rules.comment_prefix == "#"
    assert rules.bracket_pairs == (("(", ")"), ("[", "]"), ("{", "}"))
    assert rules.indent_width == 4
    assert rules.opens_indented_block is opens_indented_block
