"""Tests for finding the bracket that matches the one next to the caret."""
import pytest

from mathdoer.bracket_matching import BracketPair, find_bracket_pair
from mathdoer.languages import EditingRules
from mathdoer.languages.python import PYTHON
from mathdoer.languages.python.lexer import IN_TRIPLE_DOUBLE_QUOTED_STRING
from mathdoer.line_editing import Position
from mathdoer.syntax import LexedLine

P = Position


def pair_at(lines, line, column, **options):
    return find_bracket_pair(lines, P(line, column), PYTHON.editing, PYTHON.lex_line, **options)


def test_the_caret_just_after_a_closing_bracket_finds_its_opener():
    assert pair_at(["f(x)"], 0, 4) == BracketPair(P(0, 1), P(0, 3))


def test_the_caret_just_before_an_opening_bracket_finds_its_closer():
    assert pair_at(["f(x)"], 0, 1) == BracketPair(P(0, 1), P(0, 3))


def test_the_caret_just_after_an_opening_bracket_and_just_before_a_closing_one_work_too():
    assert pair_at(["f(x)"], 0, 2) == BracketPair(P(0, 1), P(0, 3))
    assert pair_at(["f(x)"], 0, 3) == BracketPair(P(0, 1), P(0, 3))


def test_the_bracket_before_the_caret_wins_over_the_one_after_it():
    assert pair_at(["(a)(b)"], 0, 3) == BracketPair(P(0, 0), P(0, 2))


def test_when_the_bracket_before_the_caret_has_no_partner_the_one_after_is_tried():
    assert pair_at(["x)(y)"], 0, 2) == BracketPair(P(0, 2), P(0, 4))


def test_nested_brackets_pair_up_properly():
    assert pair_at(["((a))"], 0, 1) == BracketPair(P(0, 0), P(0, 4))
    assert pair_at(["((a))"], 0, 2) == BracketPair(P(0, 1), P(0, 3))
    assert pair_at(["((a))"], 0, 5) == BracketPair(P(0, 0), P(0, 4))


def test_each_kind_of_bracket_is_matched_with_its_own_kind():
    assert pair_at(["a (b [c] d) e"], 0, 8) == BracketPair(P(0, 5), P(0, 7))
    assert pair_at(["a (b [c] d) e"], 0, 11) == BracketPair(P(0, 2), P(0, 10))
    assert pair_at(["{[()]}"], 0, 1) == BracketPair(P(0, 0), P(0, 5))


def test_a_bracket_of_another_kind_in_between_does_not_confuse_the_count():
    assert pair_at(["([)]"], 0, 1) == BracketPair(P(0, 0), P(0, 2))


def test_a_bracket_with_no_partner_has_no_pair():
    assert pair_at(["f(x"], 0, 2) is None
    assert pair_at(["x)"], 0, 2) is None
    assert pair_at(["((a)"], 0, 0) is None  # the outer bracket is the only one beside the caret


def test_no_bracket_beside_the_caret_means_no_pair():
    assert pair_at(["abc"], 0, 1) is None
    assert pair_at([""], 0, 0) is None
    assert pair_at(["f(x)"], 0, 0) is None


def test_the_ends_of_a_line_are_safe_places_for_the_caret():
    assert pair_at(["()"], 0, 0) == BracketPair(P(0, 0), P(0, 1))
    assert pair_at(["()"], 0, 2) == BracketPair(P(0, 0), P(0, 1))


def test_brackets_inside_strings_are_not_counted_and_do_not_match():
    lines = ['print("(") + (1)']
    assert pair_at(lines, 0, 16) == BracketPair(P(0, 13), P(0, 15))
    assert pair_at(lines, 0, 6) == BracketPair(P(0, 5), P(0, 9))  # skips the one inside the string
    assert pair_at(lines, 0, 8) is None  # next to a bracket that is only text


def test_brackets_inside_comments_are_not_counted():
    assert pair_at(["f(x)  # )"], 0, 2) == BracketPair(P(0, 1), P(0, 3))
    assert pair_at(["f(x  # )"], 0, 2) is None
    assert pair_at(["# (a)"], 0, 3) is None


def test_a_pair_can_span_several_lines():
    lines = ["def f(", "    a,", "    b):"]
    assert pair_at(lines, 2, 6) == BracketPair(P(0, 5), P(2, 5))
    assert pair_at(lines, 0, 6) == BracketPair(P(0, 5), P(2, 5))


def test_lines_inside_a_triple_quoted_string_are_not_code():
    lines = ['s = """', "(", '"""', "(x)"]
    assert pair_at(lines, 3, 3) == BracketPair(P(3, 0), P(3, 2))
    assert pair_at(lines, 1, 1) is None
    lines = ['s = """', "(", '"""', "x)"]
    assert pair_at(lines, 3, 2) is None


def test_only_lines_near_the_caret_are_searched():
    lines = ["("] + ["x"] * 10 + [")"]
    assert pair_at(lines, 0, 1, line_limit=5) is None
    assert pair_at(lines, 0, 1, line_limit=11) == BracketPair(P(0, 0), P(11, 0))
    assert pair_at(lines, 11, 1, line_limit=5) is None
    assert pair_at(lines, 11, 1, line_limit=11) == BracketPair(P(0, 0), P(11, 0))


def test_the_state_of_each_line_can_be_supplied_instead_of_worked_out():
    lines = ["(", "x)"]
    assert pair_at(lines, 0, 1) == BracketPair(P(0, 0), P(1, 1))
    asked = []

    def pretend_line_one_is_inside_a_string(index):
        asked.append(index)
        return IN_TRIPLE_DOUBLE_QUOTED_STRING if index == 1 else 0

    assert pair_at(lines, 0, 1, state_before=pretend_line_one_is_inside_a_string) is None
    assert 1 in asked


def test_a_supplied_state_means_the_lines_before_the_caret_are_not_lexed():
    class CountingLines:
        def __init__(self, lines):
            self.lines, self.read = lines, set()

        def __len__(self):
            return len(self.lines)

        def __getitem__(self, index):
            self.read.add(index)
            return self.lines[index]

    lines = CountingLines(["x"] * 1000 + ["f(x)"] + ["y"] * 1000)
    assert pair_at(lines, 1000, 4, state_before=lambda index: 0) == BracketPair(P(1000, 1), P(1000, 3))
    assert lines.read == {1000}


def test_the_brackets_come_from_the_language():
    rules = EditingRules("//", lambda lines, line, column: False, (("<", ">"),), 4)
    nothing = lambda text, state: LexedLine((), 0)  # noqa: E731
    assert find_bracket_pair(["<a(b)>"], P(0, 6), rules, nothing) == BracketPair(P(0, 0), P(0, 5))
    assert find_bracket_pair(["<a(b)>"], P(0, 4), rules, nothing) is None


def test_a_pair_has_its_earlier_bracket_first():
    for column in (1, 2, 3, 4):
        pair = pair_at(["f(x)"], 0, column)
        assert pair.first < pair.second


def test_in_balanced_text_every_bracket_is_paired_the_way_a_stack_would_pair_it():
    text = "(()(()))"
    partner, stack = {}, []
    for index, character in enumerate(text):
        if character == "(":
            stack.append(index)
        else:
            opener = stack.pop()
            partner[opener], partner[index] = index, opener
    for column in range(len(text) + 1):
        bracket = column - 1 if column > 0 else 0  # the one before the caret, or the first
        expected = BracketPair(P(0, min(bracket, partner[bracket])), P(0, max(bracket, partner[bracket])))
        assert pair_at([text], 0, column) == expected, column
