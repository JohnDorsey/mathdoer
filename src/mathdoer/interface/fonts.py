"""Fonts of the interface."""
from PySide6.QtGui import QFont

MONOSPACE_FAMILIES = ["Consolas", "Menlo", "DejaVu Sans Mono", "Courier New"]
DEFAULT_POINT_SIZE = 11
MINIMUM_POINT_SIZE = 6
MAXIMUM_POINT_SIZE = 72


def clamp_point_size(point_size: int) -> int:
    return max(MINIMUM_POINT_SIZE, min(MAXIMUM_POINT_SIZE, point_size))


def monospace_font(point_size: int = DEFAULT_POINT_SIZE) -> QFont:
    font = QFont()
    font.setFamilies(MONOSPACE_FAMILIES)
    font.setStyleHint(QFont.StyleHint.Monospace)
    font.setFixedPitch(True)
    font.setPointSize(clamp_point_size(point_size))
    return font
