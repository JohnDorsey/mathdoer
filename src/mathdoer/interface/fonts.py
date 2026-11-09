"""Fonts of the interface."""
from PySide6.QtGui import QFont

MONOSPACE_FAMILIES = ["Consolas", "Menlo", "DejaVu Sans Mono", "Courier New"]
DEFAULT_POINT_SIZE = 11


def monospace_font(point_size: int = DEFAULT_POINT_SIZE) -> QFont:
    font = QFont()
    font.setFamilies(MONOSPACE_FAMILIES)
    font.setStyleHint(QFont.StyleHint.Monospace)
    font.setFixedPitch(True)
    font.setPointSize(point_size)
    return font
