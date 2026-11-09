"""Tests for where the indentation guides go."""
import pytest

from mathdoer.indentation_guides import guide_columns, indentation_of


@pytest.mark.parametrize(
    "line, expected",
    [
        ("x", 0),
        ("    x", 4),
        ("  x", 2),
        ("        x", 8),
        ("\tx", 4),
        ("\t\tx", 8),
        ("  \tx", 4),  # two spaces and a tab reach the next tab stop
        ("   \t x", 5),
        ("", None),
        ("   ", None),
        ("\t", None),
        (" \t ", None),
    ],
)
def test_indentation_is_the_columns_of_leading_whitespace_and_blank_lines_have_none(line, expected):
    assert indentation_of(line, 4) == expected


def test_the_width_of_a_tab_stop_is_the_indent_width():
    assert indentation_of("\tx", 2) == 2
    assert indentation_of("\tx", 8) == 8


@pytest.mark.parametrize(
    "line, expected",
    [
        ("x", ()),
        ("  x", (0,)),
        ("    x", (0,)),
        ("     x", (0, 4)),
        ("        x", (0, 4)),
        ("            x", (0, 4, 8)),
        ("\tx", (0,)),
        ("\t\tx", (0, 4)),
    ],
)
def test_a_line_has_a_guide_at_each_indentation_level_inside_its_indentation(line, expected):
    assert guide_columns([line], 0, 4) == expected


def test_guides_follow_the_indent_width():
    assert guide_columns(["      x"], 0, 2) == (0, 2, 4)


def test_a_blank_line_between_two_indented_lines_continues_their_guides():
    assert guide_columns(["    a", "", "    b"], 1, 4) == (0,)
    assert guide_columns(["        a", "", "        b"], 1, 4) == (0, 4)


def test_a_blank_line_takes_the_deeper_of_the_lines_around_it():
    assert guide_columns(["    a", "", "b"], 1, 4) == (0,)
    assert guide_columns(["a", "", "        b"], 1, 4) == (0, 4)
    assert guide_columns(["        a", "", "    b"], 1, 4) == (0, 4)


def test_a_line_of_only_whitespace_counts_as_blank():
    assert guide_columns(["    a", "  ", "    b"], 1, 4) == (0,)
    assert guide_columns(["    a", "\t\t\t", "b"], 1, 4) == (0,)


def test_blank_lines_at_the_edges_of_the_text_look_the_one_way_there_is():
    assert guide_columns(["", "    a"], 0, 4) == (0,)
    assert guide_columns(["    a", ""], 1, 4) == (0,)


def test_a_document_of_only_blank_lines_has_no_guides():
    assert guide_columns(["", "  ", ""], 1, 4) == ()


def test_several_blank_lines_in_a_row_all_look_to_the_same_lines():
    lines = ["    a", "", "", "", "    b"]
    assert [guide_columns(lines, index, 4) for index in (1, 2, 3)] == [(0,), (0,), (0,)]


def test_a_line_with_text_is_never_extended_by_its_neighbours():
    assert guide_columns(["        a", "b", "        c"], 1, 4) == ()


def test_only_nearby_lines_are_searched():
    lines = ["    a"] + [""] * 6 + ["b"]
    assert guide_columns(lines, 3, 4, search_limit=3) == (0,)  # the indented line is three away
    assert guide_columns(lines, 5, 4, search_limit=3) == ()  # now it is too far, and "b" has none


def test_it_works_on_any_sequence_of_lines_without_copying_them():
    class CountingLines:
        def __init__(self, lines):
            self.lines, self.reads = lines, 0

        def __len__(self):
            return len(self.lines)

        def __getitem__(self, index):
            self.reads += 1
            return self.lines[index]

    lines = CountingLines(["    x"] * 10_000)
    assert guide_columns(lines, 5_000, 4) == (0,)
    assert lines.reads == 1
