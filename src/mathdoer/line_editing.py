"""Editing commands that work on lines of text, with no text box involved.

Each command takes the lines of the document and the two ends of the selection (the anchor,
where it started, and the cursor, where it is now; they are equal when nothing is selected)
and returns a TextEdit: which lines to replace, what to replace them with, and where the
selection ends up afterwards. A command returns None when it would change nothing.

Columns count characters. A selection that ends at the start of a line does not include that
line, as in most editors.
"""
from collections.abc import Sequence
from dataclasses import dataclass

from mathdoer.languages import EditingRules

WHITESPACE = " \t"


@dataclass(frozen=True, order=True)
class Position:
    line: int
    column: int


@dataclass(frozen=True)
class TextEdit:
    """Replace the lines first_line to last_line (both included) with the replacement, which
    is never empty, then select from the anchor to the cursor (positions in the new text)."""

    first_line: int
    last_line: int
    replacement: tuple[str, ...]
    anchor: Position
    cursor: Position


def leading_whitespace(line: str) -> str:
    return line[: len(line) - len(line.lstrip(WHITESPACE))]


def home_column(line: str, column: int) -> int:
    """Where Home goes: to the first character that is not whitespace, or if the caret is
    already there, to the start of the line."""
    first_character = len(leading_whitespace(line))
    return first_character if column != first_character else 0


def tab_insertion(line: str, column: int, rules: EditingRules, *, use_tab_character: bool = False) -> str:
    """What Tab inserts at the column of the line: spaces up to the next tab stop, or a tab
    character if asked to. A line already indented with the other kind of whitespace keeps to
    its own, as Python rejects a line that mixes the two."""
    whitespace = leading_whitespace(line)
    inside_indentation = column <= len(whitespace)
    if inside_indentation and "\t" in whitespace:
        return "\t"
    if use_tab_character and not (inside_indentation and whitespace):
        return "\t"
    return " " * (rules.indent_width - _display_width(line[:column], rules.indent_width) % rules.indent_width)


def indent(
    lines: Sequence[str],
    anchor: Position,
    cursor: Position,
    rules: EditingRules,
    *,
    use_tab_character: bool = False,
) -> TextEdit | None:
    """Tab. Over several lines it indents each of them; otherwise it replaces the selection,
    if any, with spaces up to the next tab stop (or a tab character, if asked to)."""
    start, end = sorted((anchor, cursor))
    if start.line == end.line:
        line = lines[start.line]
        insertion = tab_insertion(line, start.column, rules, use_tab_character=use_tab_character)
        position = Position(start.line, start.column + len(insertion))
        new_line = line[: start.column] + insertion + line[end.column:]
        return TextEdit(start.line, start.line, (new_line,), position, position)

    first, last = _touched_lines(anchor, cursor)
    added = []
    new_lines = []
    for index in range(first, last + 1):
        line = lines[index]
        prefix = _indentation_to_add(line, rules.indent_width, use_tab_character) if line else ""
        added.append(len(prefix))
        new_lines.append(prefix + line)
    if not any(added):
        return None

    def shifted(position: Position) -> Position:
        if first <= position.line <= last and position.column > 0:
            return Position(position.line, position.column + added[position.line - first])
        return position

    return TextEdit(first, last, tuple(new_lines), shifted(anchor), shifted(cursor))


def dedent(lines: Sequence[str], anchor: Position, cursor: Position, rules: EditingRules) -> TextEdit | None:
    """Shift+Tab. Takes one level of indentation off the current line, or every selected line."""
    first, last = _touched_lines(anchor, cursor)
    removed = [_indentation_to_remove(lines[index], rules.indent_width) for index in range(first, last + 1)]
    if not any(removed):
        return None
    new_lines = tuple(lines[index][removed[index - first]:] for index in range(first, last + 1))

    def shifted(position: Position) -> Position:
        if first <= position.line <= last:
            return Position(position.line, max(0, position.column - removed[position.line - first]))
        return position

    return TextEdit(first, last, new_lines, shifted(anchor), shifted(cursor))


def insert_newline(
    lines: Sequence[str],
    anchor: Position,
    cursor: Position,
    rules: EditingRules,
    *,
    indent_after_block_opening: bool = True,
    use_tab_character: bool = False,
) -> TextEdit:
    """Enter. Replaces the selection with a line break; the new line keeps the indentation of
    the line it came from, plus one level if the code before the caret opens a block (and
    block openings are to add a level). The level is a tab character, if asked to, on a line
    that has no indentation yet."""
    start, end = sorted((anchor, cursor))
    line = lines[start.line]
    whitespace = leading_whitespace(line)
    head = line[: start.column]
    tail = lines[end.line][end.column:]
    new_head = head if head.strip() else ""

    if start.column < len(whitespace):
        # Inside the indentation there is nothing to carry over: the line is just split.
        new_tail, caret_column = tail, 0
    else:
        indentation = whitespace
        if indent_after_block_opening and rules.opens_indented_block(lines, start.line, start.column):
            indentation += _indent_unit(whitespace, rules.indent_width, use_tab_character)
        new_tail, caret_column = indentation + tail.lstrip(WHITESPACE), len(indentation)

    position = Position(start.line + 1, caret_column)
    return TextEdit(start.line, end.line, (new_head, new_tail), position, position)


def toggle_comment(
    lines: Sequence[str], anchor: Position, cursor: Position, rules: EditingRules
) -> TextEdit | None:
    """Comment the lines out, or if they all are commented already, take the comments off.
    The marker goes at the shallowest indentation, and blank lines are left alone (unless
    the only line is blank)."""
    first, last = _touched_lines(anchor, cursor)
    prefix = rules.comment_prefix
    candidates = [index for index in range(first, last + 1) if lines[index].strip()]
    if not candidates:
        if first != last:
            return None
        candidates = [first]

    if all(lines[index].lstrip(WHITESPACE).startswith(prefix) for index in candidates):
        return _uncomment(lines, anchor, cursor, first, last, candidates, prefix)
    return _comment(lines, anchor, cursor, first, last, candidates, prefix)


def duplicate_lines(lines: Sequence[str], anchor: Position, cursor: Position) -> TextEdit:
    """Copy the current line, or the selected lines, below themselves and move to the copy."""
    first, last = _touched_lines(anchor, cursor)
    block = tuple(lines[index] for index in range(first, last + 1))
    count = len(block)

    def shifted(position: Position) -> Position:
        return Position(position.line + count, position.column)

    return TextEdit(first, last, block + block, shifted(anchor), shifted(cursor))


def move_lines(
    lines: Sequence[str], anchor: Position, cursor: Position, direction: int
) -> TextEdit | None:
    """Move the current line, or the selected lines, up (direction -1) or down (1)."""
    first, last = _touched_lines(anchor, cursor)
    block = tuple(lines[index] for index in range(first, last + 1))
    if direction < 0:
        if first == 0:
            return None
        edit_first, edit_last = first - 1, last
        replacement = block + (lines[first - 1],)
    else:
        if last == len(lines) - 1:
            return None
        edit_first, edit_last = first, last + 1
        replacement = (lines[last + 1],) + block

    step = -1 if direction < 0 else 1

    def shifted(position: Position) -> Position:
        line = position.line + step
        if line >= len(lines):
            # A selection that ended at the start of the last line, which has moved up: it now
            # ends at the end of the moved lines, which are the last in the document.
            return Position(len(lines) - 1, len(block[-1]))
        return Position(line, position.column)

    return TextEdit(edit_first, edit_last, replacement, shifted(anchor), shifted(cursor))


def delete_lines(lines: Sequence[str], anchor: Position, cursor: Position) -> TextEdit:
    """Delete the current line, or the selected lines. The caret goes to the same column of
    the line that takes their place."""
    first, last = _touched_lines(anchor, cursor)
    if first == 0 and last == len(lines) - 1:
        start_of_text = Position(0, 0)
        return TextEdit(0, last, ("",), start_of_text, start_of_text)
    if last < len(lines) - 1:
        edit_first, edit_last, remaining_line = first, last + 1, last + 1
        caret_line = first
    else:
        edit_first, edit_last, remaining_line = first - 1, last, first - 1
        caret_line = first - 1
    replacement = (lines[remaining_line],)
    position = Position(caret_line, min(cursor.column, len(replacement[0])))
    return TextEdit(edit_first, edit_last, replacement, position, position)


def _touched_lines(anchor: Position, cursor: Position) -> tuple[int, int]:
    """The first and last line a command works on: those the selection touches, except that
    a selection ending at the start of a line does not include that line."""
    start, end = sorted((anchor, cursor))
    if end.line > start.line and end.column == 0:
        return start.line, end.line - 1
    return start.line, end.line


def _display_width(text: str, width: int) -> int:
    """The columns the text takes when tabs advance to the next multiple of the width."""
    column = 0
    for character in text:
        column = (column // width + 1) * width if character == "\t" else column + 1
    return column


def _indents_with_tab(whitespace: str, use_tab_character: bool) -> bool:
    """A line indented with tabs gets a tab. A line indented with spaces gets spaces, as Python
    rejects mixing the two. A line with no indentation gets what the caller asked for."""
    return "\t" in whitespace or (use_tab_character and not whitespace)


def _indent_unit(whitespace: str, width: int, use_tab_character: bool) -> str:
    """One level of indentation, in the style of the whitespace it follows."""
    return "\t" if _indents_with_tab(whitespace, use_tab_character) else " " * width


def _indentation_to_add(line: str, width: int, use_tab_character: bool) -> str:
    whitespace = leading_whitespace(line)
    if _indents_with_tab(whitespace, use_tab_character):
        return "\t"
    return " " * (width - len(whitespace) % width)


def _indentation_to_remove(line: str, width: int) -> int:
    """How many characters one level of dedenting takes off the start of the line."""
    whitespace = leading_whitespace(line)
    if not whitespace:
        return 0
    if whitespace[0] == "\t":
        return 1
    spaces = len(whitespace) - len(whitespace.lstrip(" "))
    previous_tab_stop = ((spaces - 1) // width) * width
    return spaces - previous_tab_stop


def _comment(lines, anchor, cursor, first, last, candidates, prefix) -> TextEdit:
    indentation = min(len(leading_whitespace(lines[index])) for index in candidates)
    inserted = prefix + " "
    new_lines = [lines[index] for index in range(first, last + 1)]
    for index in candidates:
        line = lines[index]
        new_lines[index - first] = line[:indentation] + inserted + line[indentation:]

    # A caret stays with the text after it, so it moves past the new marker. The start of a
    # selection stays where it is, so the marker is inside the selection.
    selection_start = min(anchor, cursor) if anchor != cursor else None

    def shifted(position: Position) -> Position:
        if position.line not in candidates:
            return position
        if position == selection_start:
            moves = position.column > indentation
        else:
            moves = position.column >= indentation
        return Position(position.line, position.column + len(inserted)) if moves else position

    return TextEdit(first, last, tuple(new_lines), shifted(anchor), shifted(cursor))


def _uncomment(lines, anchor, cursor, first, last, candidates, prefix) -> TextEdit:
    new_lines = [lines[index] for index in range(first, last + 1)]
    removals = {}  # line -> (length of the indentation, characters removed after it)
    for index in candidates:
        line = lines[index]
        indentation = len(leading_whitespace(line))
        after = line[indentation:]
        removed = len(prefix) + (1 if after[len(prefix):].startswith(" ") else 0)
        removals[index] = (indentation, removed)
        new_lines[index - first] = line[:indentation] + after[removed:]

    def shifted(position: Position) -> Position:
        if position.line in removals:
            indentation, removed = removals[position.line]
            if position.column > indentation:
                return Position(position.line, max(indentation, position.column - removed))
        return position

    return TextEdit(first, last, tuple(new_lines), shifted(anchor), shifted(cursor))
