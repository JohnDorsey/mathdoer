"""Fonts of the interface."""
from PySide6.QtGui import QFont

from mathdoer.interface_settings import DEFAULT_FONT_FAMILY, DEFAULT_POINT_SIZE, MAXIMUM_POINT_SIZE, MINIMUM_POINT_SIZE

# What a font that is not installed falls back to; the first is the default family of the settings.
MONOSPACE_FAMILIES = ["Consolas", "Menlo", "DejaVu Sans Mono", "Courier New"]
assert MONOSPACE_FAMILIES[0] == DEFAULT_FONT_FAMILY


def clamp_point_size(point_size: int) -> int:
    return max(MINIMUM_POINT_SIZE, min(MAXIMUM_POINT_SIZE, point_size))


def monospace_font(point_size: int = DEFAULT_POINT_SIZE, family: str = DEFAULT_FONT_FAMILY) -> QFont:
    """The family, then the usual monospace fonts for where it is not installed."""
    font = QFont()
    font.setFamilies([family, *(name for name in MONOSPACE_FAMILIES if name != family)])
    font.setStyleHint(QFont.StyleHint.Monospace)
    font.setFixedPitch(True)
    font.setPointSize(clamp_point_size(point_size))
    return font
