"""Tests for the bounded output buffer."""
import random

import pytest

from mathdoer.output_buffer import DEFAULT_MAXIMUM_CHARACTER_COUNT, OutputBuffer


def test_the_default_cap_is_one_million_characters():
    assert DEFAULT_MAXIMUM_CHARACTER_COUNT == 1_000_000
    assert OutputBuffer().maximum_character_count == 1_000_000


def test_a_new_buffer_is_empty_and_not_truncated():
    buffer = OutputBuffer(maximum_character_count=10)
    assert buffer.text == ""
    assert len(buffer) == 0
    assert buffer.truncated is False
    assert buffer.discarded_character_count == 0


def test_text_within_the_cap_is_kept_whole():
    buffer = OutputBuffer(maximum_character_count=10)
    buffer.append("hello")
    buffer.append(" you")
    assert buffer.text == "hello you"
    assert len(buffer) == 9
    assert buffer.truncated is False


def test_text_exactly_at_the_cap_is_not_truncated():
    buffer = OutputBuffer(maximum_character_count=5)
    buffer.append("12345")
    assert buffer.text == "12345"
    assert buffer.truncated is False


def test_overflow_discards_from_the_beginning_not_the_end():
    buffer = OutputBuffer(maximum_character_count=10)
    buffer.append("0123456789")
    buffer.append("abc")
    assert buffer.text == "3456789abc"
    assert buffer.truncated is True
    assert buffer.discarded_character_count == 3


def test_one_append_larger_than_the_cap_keeps_only_its_end():
    buffer = OutputBuffer(maximum_character_count=4)
    buffer.append("abcdefghij")
    assert buffer.text == "ghij"
    assert buffer.discarded_character_count == 6
    assert buffer.truncated is True


def test_appending_nothing_changes_nothing():
    buffer = OutputBuffer(maximum_character_count=4)
    buffer.append("")
    assert buffer.text == ""
    assert buffer.truncated is False


def test_clear_forgets_the_text_and_the_truncation():
    buffer = OutputBuffer(maximum_character_count=3)
    buffer.append("abcdef")
    buffer.clear()
    assert (buffer.text, buffer.truncated, buffer.discarded_character_count) == ("", False, 0)
    buffer.append("xy")
    assert buffer.text == "xy"
    assert buffer.truncated is False


@pytest.mark.parametrize("cap", [0, -1])
def test_the_cap_must_be_positive(cap):
    with pytest.raises(ValueError):
        OutputBuffer(maximum_character_count=cap)


def test_append_returns_the_text_it_discarded():
    buffer = OutputBuffer(maximum_character_count=5)
    assert buffer.append("abc") == ""
    assert buffer.append("defg") == "ab"
    assert buffer.text == "cdefg"
    assert buffer.append("0123456789") == "cdefg" + "01234"
    assert buffer.text == "56789"


def test_a_new_buffer_has_no_segments():
    assert OutputBuffer().segments == ()


def test_segments_remember_which_text_was_an_error_and_merge_neighbours_of_the_same_kind():
    buffer = OutputBuffer(maximum_character_count=10)
    buffer.append("ab")
    buffer.append("cd")
    buffer.append("EF", is_error=True)
    buffer.append("gh")
    assert buffer.segments == (("abcd", False), ("EF", True), ("gh", False))
    assert buffer.text == "abcdEFgh"


def test_overflow_cuts_segments_from_the_front():
    buffer = OutputBuffer(maximum_character_count=5)
    buffer.append("abc")
    buffer.append("DE", is_error=True)
    buffer.append("fg")
    assert buffer.segments == (("c", False), ("DE", True), ("fg", False))


def test_an_oversized_error_append_keeps_only_its_end_as_an_error():
    buffer = OutputBuffer(maximum_character_count=3)
    buffer.append("abc")
    buffer.append("123456", is_error=True)
    assert buffer.segments == (("456", True),)


def test_appending_nothing_as_an_error_changes_nothing():
    buffer = OutputBuffer(maximum_character_count=3)
    buffer.append("", is_error=True)
    assert buffer.segments == ()


def test_clear_forgets_the_segments():
    buffer = OutputBuffer(maximum_character_count=3)
    buffer.append("abc", is_error=True)
    buffer.clear()
    assert buffer.segments == ()


@pytest.mark.parametrize("cap", [1, 2, 7, 50])
def test_the_discarded_text_is_exactly_the_missing_beginning_of_the_history(cap):
    generator = random.Random(1000 + cap)
    buffer = OutputBuffer(maximum_character_count=cap)
    history = ""
    all_discarded = ""
    for _ in range(300):
        chunk = "".join(generator.choice("abcdefghij\n") for _ in range(generator.randint(0, 3 * cap)))
        all_discarded += buffer.append(chunk, is_error=generator.random() < 0.5)
        history += chunk
        assert all_discarded + buffer.text == history
        assert "".join(text for text, _ in buffer.segments) == buffer.text


@pytest.mark.parametrize("cap", [1, 2, 7, 50])
def test_behaves_like_slicing_the_whole_history(cap):
    generator = random.Random(cap)
    buffer = OutputBuffer(maximum_character_count=cap)
    history = ""
    for _ in range(400):
        chunk = "".join(generator.choice("abcdefghij\n") for _ in range(generator.randint(0, 3 * cap)))
        buffer.append(chunk)
        history += chunk
        assert buffer.text == history[-cap:]
        assert len(buffer) == min(len(history), cap)
        assert buffer.discarded_character_count == max(0, len(history) - cap)
        assert buffer.truncated == (len(history) > cap)
