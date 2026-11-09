"""Colors of the interface. Qt-free, so the contrast of a theme can be tested."""
import re
from collections.abc import Mapping
from dataclasses import dataclass

from mathdoer.syntax import TokenKind

HEX_COLOR_PATTERN = re.compile(r"#[0-9a-fA-F]{6}")


@dataclass(frozen=True)
class Theme:
    name: str
    window_background: str
    text_background: str
    default_text: str
    error_text: str
    notice_text: str
    disabled_text: str
    selection_background: str
    selection_text: str
    splitter_handle: str
    line_number_text: str  # Notepad++: "Line number margin"
    line_number_background: str
    indentation_guide: str  # Notepad++: "Indent guideline style"
    matching_bracket_background: str  # Notepad++: "Brace highlight style"
    # One color for each kind of text the lexer reports; Notepad++'s per-language styles
    # (COMMENTLINE, NUMBER, STRING, WORD, WORD2, DEFNAME, CLASSNAME, DECORATOR, OPERATOR) map to them.
    token_colors: Mapping[TokenKind, str]


# Dark with high contrast: every text color is at least 7:1 against its background.
DARK_THEME = Theme(
    name="dark",
    window_background="#202020",
    text_background="#0c0c0c",
    default_text="#ffffff",
    error_text="#ff7b7b",
    notice_text="#ffd75f",
    disabled_text="#b0b0b0",
    selection_background="#1a4fa0",
    selection_text="#ffffff",
    splitter_handle="#8a8a8a",
    line_number_text="#b0b0b0",
    line_number_background="#161616",
    indentation_guide="#606060",
    matching_bracket_background="#0c5c4e",
    token_colors={
        TokenKind.COMMENT: "#7ee787",
        TokenKind.STRING: "#ffb454",
        TokenKind.NUMBER: "#b5a4ff",
        TokenKind.KEYWORD: "#ff7ab2",
        TokenKind.BUILTIN: "#6fd7ff",
        TokenKind.FUNCTION_NAME: "#ffe27a",
        TokenKind.CLASS_NAME: "#5eead4",
        TokenKind.DECORATOR: "#f2a0ff",
        TokenKind.OPERATOR: "#ffffff",
    },
)


def contrast_ratio(color_a: str, color_b: str) -> float:
    """WCAG contrast ratio between two #rrggbb colors, from 1 (identical) to 21."""
    luminance_a, luminance_b = _relative_luminance(color_a), _relative_luminance(color_b)
    lighter, darker = max(luminance_a, luminance_b), min(luminance_a, luminance_b)
    return (lighter + 0.05) / (darker + 0.05)


def _relative_luminance(color: str) -> float:
    if not HEX_COLOR_PATTERN.fullmatch(color):
        raise ValueError(f"expected a #rrggbb color, got {color!r}")
    red, green, blue = (_linear_channel(int(color[index:index + 2], 16)) for index in (1, 3, 5))
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def _linear_channel(value: int) -> float:
    fraction = value / 255
    return fraction / 12.92 if fraction <= 0.04045 else ((fraction + 0.055) / 1.055) ** 2.4
