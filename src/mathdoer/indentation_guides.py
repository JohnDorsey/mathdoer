"""Where the indentation guides, the thin vertical lines in leading whitespace, go.

Guides are in columns, with a tab advancing to the next multiple of the indent width.
"""
from collections.abc import Sequence

DEFAULT_SEARCH_LIMIT = 500


def indentation_of(line: str, indent_width: int) -> int | None:
    """The columns of leading whitespace, or None for a blank line (empty or only whitespace)."""
    if not line.strip(" \t"):
        return None
    columns = 0
    for character in line:
        if character == " ":
            columns += 1
        elif character == "\t":
            columns = (columns // indent_width + 1) * indent_width
        else:
            break
    return columns


def guide_columns(
    lines: Sequence[str], index: int, indent_width: int, search_limit: int = DEFAULT_SEARCH_LIMIT
) -> tuple[int, ...]:
    """The columns of the guides on a line: one at each indentation level inside its
    indentation. A blank line continues the guides of the nearest lines with text above and
    below it, as deep as the deeper of the two, so a guide runs unbroken through blank lines.
    Only lines within the search limit are looked at."""
    depth = indentation_of(lines[index], indent_width)
    if depth is None:
        above = _nearest_indentation(lines, index, -1, indent_width, search_limit)
        below = _nearest_indentation(lines, index, 1, indent_width, search_limit)
        depth = max(above or 0, below or 0)
    return tuple(range(0, depth, indent_width))


def _nearest_indentation(
    lines: Sequence[str], index: int, step: int, indent_width: int, search_limit: int
) -> int | None:
    for distance in range(1, search_limit + 1):
        neighbour = index + step * distance
        if not 0 <= neighbour < len(lines):
            return None
        indentation = indentation_of(lines[neighbour], indent_width)
        if indentation is not None:
            return indentation
    return None
