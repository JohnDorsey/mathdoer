"""What the prompt box and the output box have in common."""
from PySide6.QtWidgets import QFrame, QPlainTextEdit

from mathdoer.interface.fonts import monospace_font
from mathdoer.interface.styling import text_box_palette
from mathdoer.interface.theme import Theme


class TextBox(QPlainTextEdit):
    """A text box in the theme's colors and the monospace font."""

    def __init__(self, theme: Theme, parent=None):
        super().__init__(parent)
        self.setFont(monospace_font())
        self.setPalette(text_box_palette(self.palette(), theme))
        self.setFrameShape(QFrame.Shape.NoFrame)
