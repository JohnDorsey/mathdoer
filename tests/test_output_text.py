"""Tests for preparing program output for the output box."""
import pytest

from mathdoer.output_text import normalize_output_text, utf16_length


@pytest.mark.parametrize(
    "text, expected",
    [
        ("plain", "plain"),
        ("", ""),
        ("a\nb", "a\nb"),
        ("a\r\nb", "a\nb"),
        ("a\rb", "a\nb"),
        ("a\r\r\nb\n", "a\n\nb\n"),
        ("héllo ✓ 😀", "héllo ✓ 😀"),
        ("\udc80", "�"),
        ("a\ud800b", "a�b"),
        ("😀", "😀"),
    ],
)
def test_line_breaks_become_newlines_and_lone_surrogates_become_the_replacement_character(
    text, expected
):
    assert normalize_output_text(text) == expected


def test_normalized_text_can_always_be_encoded_as_utf8():
    normalize_output_text("\udc80x\ud800").encode("utf-8")


@pytest.mark.parametrize(
    "text, expected",
    [("", 0), ("a", 1), ("é", 1), ("✓", 1), ("\n", 1), ("😀", 2), ("a😀b", 4), ("\udc80", 1)],
)
def test_utf16_length_counts_the_units_the_text_box_counts(text, expected):
    assert utf16_length(text) == expected
