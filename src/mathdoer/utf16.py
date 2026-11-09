"""Counting text the way a Qt text box does: in UTF-16 units."""


def utf16_length(text: str) -> int:
    """The length a Qt text box counts: characters outside the basic plane count twice."""
    return len(text.encode("utf-16-le", "surrogatepass")) // 2


def index_at_utf16_offset(text: str, offset: int) -> int:
    """The index of the character that a UTF-16 offset points at. An offset in the middle of
    a character gives that character; one past the end gives the length of the text."""
    consumed = 0
    for index, character in enumerate(text):
        width = 2 if ord(character) > 0xFFFF else 1
        if consumed + width > offset:
            return index
        consumed += width
    return len(text)
