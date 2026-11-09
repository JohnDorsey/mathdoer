"""What a language's lexer reports about a line of code, for highlighting and bracket matching.

The kinds are the same for every language, so a theme colors them whatever the language is.
"""
from dataclasses import dataclass
from enum import Enum


class TokenKind(Enum):
    COMMENT = "comment"
    STRING = "string"
    NUMBER = "number"
    KEYWORD = "keyword"
    BUILTIN = "builtin"  # names the language provides, such as len and ValueError
    FUNCTION_NAME = "function_name"  # the name in a definition
    CLASS_NAME = "class_name"
    DECORATOR = "decorator"
    OPERATOR = "operator"


@dataclass(frozen=True)
class Token:
    start: int  # index of the first character in the line
    end: int  # index after the last character
    kind: TokenKind


@dataclass(frozen=True)
class LexedLine:
    """The tokens of one line, in order and not overlapping, and the lexer's state at the end
    of the line. State 0 means ordinary code; other states are the language's own, for
    example 'inside a triple-quoted string'. Text with no token is ordinary text."""

    tokens: tuple[Token, ...]
    end_state: int
