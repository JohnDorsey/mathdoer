"""Tests for converting between characters and the UTF-16 units a Qt text box counts."""
import pytest

from mathdoer.utf16 import index_at_utf16_offset, utf16_length


@pytest.mark.parametrize(
    "text, expected",
    [("", 0), ("a", 1), ("é", 1), ("✓", 1), ("\n", 1), ("😀", 2), ("a😀b", 4), ("\udc80", 1)],
)
def test_utf16_length_counts_the_units_the_text_box_counts(text, expected):
    assert utf16_length(text) == expected


@pytest.mark.parametrize(
    "offset, expected_index",
    [
        (0, 0),
        (1, 1),
        (2, 1),  # inside the pair of units that make one character: the character containing it
        (3, 2),
        (4, 3),
        (5, 3),  # past the end
        (100, 3),
    ],
)
def test_the_index_at_a_utf16_offset_counts_characters(offset, expected_index):
    assert index_at_utf16_offset("a😀b", offset) == expected_index


def test_the_index_of_an_offset_in_text_without_wide_characters_is_the_offset():
    text = "héllo wörld ✓"
    for offset in range(len(text) + 1):
        assert index_at_utf16_offset(text, offset) == offset


def test_the_index_and_the_length_agree_for_every_prefix():
    text = "a😀b😀😀c\udc80d"
    for index in range(len(text) + 1):
        assert index_at_utf16_offset(text, utf16_length(text[:index])) == index


def test_the_index_in_an_empty_text_is_zero():
    assert index_at_utf16_offset("", 0) == 0
    assert index_at_utf16_offset("", 5) == 0
