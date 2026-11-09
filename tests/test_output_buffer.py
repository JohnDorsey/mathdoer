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
