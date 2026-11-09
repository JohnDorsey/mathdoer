"""Preparing program output for the output box."""


def normalize_output_text(text: str) -> str:
    """Line breaks become newlines, and lone surrogates, which a text box cannot hold,
    become the replacement character."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    try:
        text.encode("utf-8")
    except UnicodeEncodeError:
        text = text.encode("utf-16", "surrogatepass").decode("utf-16", "replace")
    return text
