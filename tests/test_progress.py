"""Tests for the spinner and elapsed-time text shown while a prompt runs."""
import pytest

from mathdoer.progress import (
    ELAPSED_TIME_DELAY_SECONDS,
    SPINNER_FRAME_SECONDS,
    SPINNER_FRAMES,
    format_elapsed_time,
    progress_text,
    spinner_frame,
)


def test_the_spinner_alternates_between_slash_dash_backslash_and_bar():
    assert SPINNER_FRAMES == ("/", "-", "\\", "|")


def test_the_timer_appears_after_five_seconds():
    assert ELAPSED_TIME_DELAY_SECONDS == 5


@pytest.mark.parametrize(
    "elapsed_seconds, expected",
    [
        (0.0, "/"),
        (SPINNER_FRAME_SECONDS * 0.99, "/"),
        (SPINNER_FRAME_SECONDS, "-"),
        (SPINNER_FRAME_SECONDS * 2, "\\"),
        (SPINNER_FRAME_SECONDS * 3, "|"),
        (SPINNER_FRAME_SECONDS * 4, "/"),
        (SPINNER_FRAME_SECONDS * 4 * 1000 + SPINNER_FRAME_SECONDS, "-"),
        (-3.0, "/"),
    ],
)
def test_the_spinner_frame_follows_the_elapsed_time(elapsed_seconds, expected):
    assert spinner_frame(elapsed_seconds) == expected


@pytest.mark.parametrize(
    "elapsed_seconds, expected",
    [
        (0, "00:00"),
        (5, "00:05"),
        (5.99, "00:05"),
        (59, "00:59"),
        (60, "01:00"),
        (754, "12:34"),
        (3599.9, "59:59"),
        (3600, "01:00:00"),
        (3661, "01:01:01"),
        (86399, "23:59:59"),
        (86400, "1:00:00:00"),
        (90061, "1:01:01:01"),
        (864000, "10:00:00:00"),
        (-5, "00:00"),
    ],
)
def test_elapsed_time_is_minutes_then_hours_then_days(elapsed_seconds, expected):
    assert format_elapsed_time(elapsed_seconds) == expected


@pytest.mark.parametrize(
    "elapsed_seconds, expected",
    [
        (0.0, "/"),
        (0.5, "/"),
        (4.0, "/"),
        (4.999, "|"),
        (5.0, "/ 00:05"),
        (5.125, "- 00:05"),
        (65.25, "\\ 01:05"),
        (3600.0, "/ 01:00:00"),
    ],
)
def test_progress_text_is_the_spinner_and_after_five_seconds_the_timer(elapsed_seconds, expected):
    assert progress_text(elapsed_seconds) == expected
