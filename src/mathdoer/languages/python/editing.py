"""The Python rules the editor follows."""
from collections.abc import Sequence

from mathdoer.languages.python.lexer import NORMAL, lex_line
from mathdoer.syntax import TokenKind

_OPENING_BRACKETS = "([{"
_CLOSING_BRACKETS = ")]}"


def opens_indented_block(lines: Sequence[str], line: int, column: int) -> bool:
    """Does the code before the position end with a colon that opens a block?

    A colon inside brackets, a string or a comment does not, and neither does one that is
    followed by more code on the same line (as in `if x: pass`).
    """
    depth = 0
    state = NORMAL
    for index in range(line):
        lexed = lex_line(lines[index], state)
        depth = _depth_after(depth, lines[index], lexed.tokens)
        state = lexed.end_state

    text = lines[line][:column]
    lexed = lex_line(text, state)
    depth = _depth_after(depth, text, lexed.tokens)
    if depth != 0 or lexed.end_state != NORMAL:
        return False

    code_end = len(text)
    for token in lexed.tokens:
        if token.kind is TokenKind.COMMENT:
            code_end = token.start
    code = text[:code_end].rstrip()
    if not code.endswith(":"):
        return False
    colon_index = len(code) - 1
    return not any(
        token.kind is TokenKind.STRING and token.start <= colon_index < token.end for token in lexed.tokens
    )


def _depth_after(depth: int, text: str, tokens) -> int:
    """The bracket depth after the line, counting only brackets that are code."""
    not_code = [False] * len(text)
    for token in tokens:
        if token.kind in (TokenKind.STRING, TokenKind.COMMENT):
            for index in range(token.start, token.end):
                not_code[index] = True
    for index, character in enumerate(text):
        if not_code[index]:
            continue
        if character in _OPENING_BRACKETS:
            depth += 1
        elif character in _CLOSING_BRACKETS:
            depth = max(0, depth - 1)
    return depth
