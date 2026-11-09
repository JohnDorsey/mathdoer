"""Finding the bracket that matches the one next to the caret.

Brackets inside strings and comments are not brackets, so the language's lexer is asked
which characters are code. Each kind of bracket is matched with its own kind only.
"""
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from mathdoer.languages import EditingRules
from mathdoer.line_editing import Position
from mathdoer.syntax import LexedLine, TokenKind

DEFAULT_LINE_LIMIT = 2000  # how far from the caret to look for the partner
_NOT_CODE = (TokenKind.STRING, TokenKind.COMMENT)


@dataclass(frozen=True)
class BracketPair:
    first: Position  # the bracket that comes earlier in the text
    second: Position


def find_bracket_pair(
    lines: Sequence[str],
    position: Position,
    rules: EditingRules,
    lex_line: Callable[[str, int], LexedLine],
    state_before: Callable[[int], int] | None = None,
    line_limit: int = DEFAULT_LINE_LIMIT,
) -> BracketPair | None:
    """The pair of brackets for the caret at the position, or None. The bracket before the
    caret is tried first, then the one after it. If the lexer's state at the start of each
    line is known (state_before), the lines above the caret need not be lexed to find it."""
    partners = {}
    for opening, closing in rules.bracket_pairs:
        partners[opening], partners[closing] = closing, opening
    openers = {opening for opening, _ in rules.bracket_pairs}
    scanner = _BracketScanner(lines, lex_line, state_before, set(partners))

    line_text = lines[position.line]
    for column in (position.column - 1, position.column):
        if not 0 <= column < len(line_text) or line_text[column] not in partners:
            continue
        if column not in scanner.bracket_columns(position.line):
            continue  # a bracket that is only text
        here = Position(position.line, column)
        found = _find_partner(scanner, here, line_text[column], partners, openers, len(lines), line_limit)
        if found is not None:
            first, second = sorted((here, found))
            return BracketPair(first, second)
    return None


def _find_partner(scanner, here, character, partners, openers, line_count, line_limit) -> Position | None:
    partner_character = partners[character]
    step = 1 if character in openers else -1
    depth = 1
    line = here.line
    while 0 <= line < line_count and abs(line - here.line) <= line_limit:
        entries = scanner.brackets(line)
        for column, found in entries if step > 0 else reversed(entries):
            if line == here.line and (column <= here.column if step > 0 else column >= here.column):
                continue  # on the caret's own line, only what lies in the direction of the search
            if found == character:
                depth += 1
            elif found == partner_character:
                depth -= 1
                if depth == 0:
                    return Position(line, column)
        line += step
    return None


class _BracketScanner:
    """The brackets that are code on each line, found only for the lines asked about."""

    def __init__(self, lines, lex_line, state_before, bracket_characters):
        self._lines = lines
        self._lex_line = lex_line
        self._supplied_state_before = state_before
        self._bracket_characters = bracket_characters
        self._brackets: dict[int, list[tuple[int, str]]] = {}
        self._states = [0]  # the state before each line, worked out when not supplied

    def brackets(self, index: int) -> list[tuple[int, str]]:
        if index not in self._brackets:
            self._brackets[index] = self._find_brackets(index)
        return self._brackets[index]

    def bracket_columns(self, index: int) -> set[int]:
        return {column for column, _ in self.brackets(index)}

    def _find_brackets(self, index: int) -> list[tuple[int, str]]:
        text = self._lines[index]
        if not any(character in self._bracket_characters for character in text):
            return []
        lexed = self._lex_line(text, self._state_before(index))
        not_code = [(token.start, token.end) for token in lexed.tokens if token.kind in _NOT_CODE]
        return [
            (column, character)
            for column, character in enumerate(text)
            if character in self._bracket_characters
            and not any(start <= column < end for start, end in not_code)
        ]

    def _state_before(self, index: int) -> int:
        if self._supplied_state_before is not None:
            return self._supplied_state_before(index)
        while len(self._states) <= index:
            previous = len(self._states) - 1
            self._states.append(self._lex_line(self._lines[previous], self._states[previous]).end_state)
        return self._states[index]
