"""The spinner and elapsed-time text shown in the output while a prompt runs."""

SPINNER_FRAMES = ("/", "-", "\\", "|")
SPINNER_FRAME_SECONDS = 0.125
ELAPSED_TIME_DELAY_SECONDS = 5

SECONDS_PER_MINUTE = 60
SECONDS_PER_HOUR = 3600
SECONDS_PER_DAY = 86400


def spinner_frame(elapsed_seconds: float) -> str:
    frame_number = int(max(0.0, elapsed_seconds) / SPINNER_FRAME_SECONDS)
    return SPINNER_FRAMES[frame_number % len(SPINNER_FRAMES)]


def format_elapsed_time(elapsed_seconds: float) -> str:
    """mm:ss, then hh:mm:ss from one hour, then d:hh:mm:ss from one day."""
    total_seconds = int(max(0.0, elapsed_seconds))
    days, remainder = divmod(total_seconds, SECONDS_PER_DAY)
    hours, remainder = divmod(remainder, SECONDS_PER_HOUR)
    minutes, seconds = divmod(remainder, SECONDS_PER_MINUTE)
    if days:
        return f"{days}:{hours:02}:{minutes:02}:{seconds:02}"
    if hours:
        return f"{hours:02}:{minutes:02}:{seconds:02}"
    return f"{minutes:02}:{seconds:02}"


def progress_text(elapsed_seconds: float) -> str:
    """The spinner, followed by the elapsed time once a run has taken a while."""
    frame = spinner_frame(elapsed_seconds)
    if elapsed_seconds < ELAPSED_TIME_DELAY_SECONDS:
        return frame
    return f"{frame} {format_elapsed_time(elapsed_seconds)}"
