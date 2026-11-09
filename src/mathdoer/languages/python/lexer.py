"""A lexer for Python that works one line at a time.

It is for highlighting and bracket matching while the code is being typed, so it never
fails: unfinished strings, stray brackets and other mistakes just lex as well as they can.
"""
import builtins
import keyword
import re

from mathdoer.syntax import LexedLine, Token, TokenKind

NORMAL = 0
IN_TRIPLE_SINGLE_QUOTED_STRING = 1
IN_TRIPLE_DOUBLE_QUOTED_STRING = 2
IN_CONTINUED_SINGLE_QUOTED_STRING = 3  # a ' string whose line ended with a backslash
IN_CONTINUED_DOUBLE_QUOTED_STRING = 4  # the same for a " string

_DELIMITER_OF_STATE = {
    IN_TRIPLE_SINGLE_QUOTED_STRING: "'''",
    IN_TRIPLE_DOUBLE_QUOTED_STRING: '"""',
    IN_CONTINUED_SINGLE_QUOTED_STRING: "'",
    IN_CONTINUED_DOUBLE_QUOTED_STRING: '"',
}
_TRIPLE_STATE_OF_DELIMITER = {"'''": IN_TRIPLE_SINGLE_QUOTED_STRING, '"""': IN_TRIPLE_DOUBLE_QUOTED_STRING}
_CONTINUED_STATE_OF_DELIMITER = {"'": IN_CONTINUED_SINGLE_QUOTED_STRING, '"': IN_CONTINUED_DOUBLE_QUOTED_STRING}

KEYWORDS = frozenset(keyword.kwlist)  # including True, False and None
BUILTINS = frozenset(name for name in dir(builtins) if not name.startswith("_"))

_STRING_START = re.compile(r"(?:rb|br|fr|rf|r|b|f|u)?('''|\"\"\"|'|\")", re.IGNORECASE)
_NUMBER = re.compile(
    r"0[xX][0-9a-fA-F_]+|0[bB][01_]+|0[oO][0-7_]+"
    r"|(?:\d[\d_]*(?:\.[\d_]*)?|\.\d[\d_]*)(?:[eE][+-]?\d[\d_]*)?[jJ]?"
)
_NAME = re.compile(r"[^\W\d]\w*")
_DECORATOR = re.compile(r"@[\w.]*")
_OPERATOR = re.compile(r"[-+*/%=<>!&|^~@]+")
_OPERATOR_CHARACTERS = "-+*/%=<>!&|^~@"


def lex_line(text: str, state: int) -> LexedLine:
    tokens: list[Token] = []
    position = 0

    delimiter = _DELIMITER_OF_STATE.get(state)
    if delimiter is not None:
        end, closed, continues = _scan_string_body(text, 0, delimiter)
        if end > 0:
            tokens.append(Token(0, end, TokenKind.STRING))
        state = _state_after_string(delimiter, closed, continues)
        if state != NORMAL:
            return LexedLine(tuple(tokens), state)
        position = end

    after_dot = False  # the last thing seen was a dot, so a name here is an attribute
    pending_definition: TokenKind | None = None  # the last thing seen was def or class

    while position < len(text):
        character = text[position]
        if character.isspace():
            position += 1
            continue

        if character == "#":
            tokens.append(Token(position, len(text), TokenKind.COMMENT))
            break

        string_start = _STRING_START.match(text, position)
        if string_start:
            delimiter = string_start.group(1)
            end, closed, continues = _scan_string_body(text, string_start.end(), delimiter)
            tokens.append(Token(position, end, TokenKind.STRING))
            position = end
            state = _state_after_string(delimiter, closed, continues)
            if state != NORMAL:
                return LexedLine(tuple(tokens), state)
            after_dot, pending_definition = False, None
            continue

        if character.isdigit() or (character == "." and text[position + 1:position + 2].isdigit()):
            match = _NUMBER.match(text, position)
            tokens.append(Token(position, match.end(), TokenKind.NUMBER))
            position = match.end()
            after_dot, pending_definition = False, None
            continue

        name = _NAME.match(text, position)
        if name:
            kind = _kind_of_name(name.group(), after_dot, pending_definition)
            if kind is not None:
                tokens.append(Token(position, name.end(), kind))
            pending_definition = _definition_kind_after(name.group(), kind)
            after_dot = False
            position = name.end()
            continue

        if character == "@" and not text[:position].strip():
            decorator = _DECORATOR.match(text, position)
            tokens.append(Token(position, decorator.end(), TokenKind.DECORATOR))
            position = decorator.end()
            after_dot, pending_definition = False, None
            continue

        if character in _OPERATOR_CHARACTERS:
            operator = _OPERATOR.match(text, position)
            tokens.append(Token(position, operator.end(), TokenKind.OPERATOR))
            position = operator.end()
            after_dot, pending_definition = False, None
            continue

        after_dot, pending_definition = character == ".", None
        position += 1

    return LexedLine(tuple(tokens), NORMAL)


def _kind_of_name(name: str, after_dot: bool, pending_definition: TokenKind | None) -> TokenKind | None:
    if after_dot:
        return None
    if name in KEYWORDS:
        return TokenKind.KEYWORD
    if pending_definition is not None:
        return pending_definition
    if name in BUILTINS:
        return TokenKind.BUILTIN
    return None


def _definition_kind_after(name: str, kind: TokenKind | None) -> TokenKind | None:
    if kind is TokenKind.KEYWORD and name == "def":
        return TokenKind.FUNCTION_NAME
    if kind is TokenKind.KEYWORD and name == "class":
        return TokenKind.CLASS_NAME
    return None


def _scan_string_body(text: str, index: int, delimiter: str) -> tuple[int, bool, bool]:
    """Find the end of a string whose body starts at the index. Returns where the string
    ends in this line, whether the closing delimiter was found, and whether a backslash at
    the end of the line makes it go on."""
    length = len(text)
    while index < length:
        character = text[index]
        if character == "\\":
            if index + 1 >= length:
                return length, False, True
            index += 2
        elif text.startswith(delimiter, index):
            return index + len(delimiter), True, False
        else:
            index += 1
    return length, False, False


def _state_after_string(delimiter: str, closed: bool, continues: bool) -> int:
    if closed:
        return NORMAL
    if len(delimiter) == 3:
        return _TRIPLE_STATE_OF_DELIMITER[delimiter]
    return _CONTINUED_STATE_OF_DELIMITER[delimiter] if continues else NORMAL
