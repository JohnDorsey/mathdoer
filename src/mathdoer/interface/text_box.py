"""What the prompt box and the output box have in common."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QFrame, QPlainTextEdit

from mathdoer.interface.fonts import monospace_font
from mathdoer.interface.styling import text_box_palette
from mathdoer.interface.theme import Theme
from mathdoer.interface_settings import InterfaceSettings

WHEEL_UNITS_PER_ZOOM_STEP = 120  # one notch of a mouse wheel


class TextBox(QPlainTextEdit):
    """A text box in the theme's colors and the monospace font, which can be zoomed
    (it only asks: the window keeps the boxes at the same size) and can wrap long lines."""

    zoom_requested = Signal(int)  # 1 to zoom in, -1 to zoom out

    def __init__(self, theme: Theme, parent=None):
        super().__init__(parent)
        self._wheel_units_not_yet_used = 0
        self._zoom_with_mouse_wheel = True
        self.setFont(monospace_font())
        self.setPalette(text_box_palette(self.palette(), theme))
        self.setFrameShape(QFrame.Shape.NoFrame)

    def apply_interface_settings(self, settings: InterfaceSettings) -> None:
        """Take on the settings that concern this box. A box that has more of its own adds to this."""
        self._zoom_with_mouse_wheel = settings.zoom_with_mouse_wheel

    def set_font_size(self, point_size: int) -> None:
        self.setFont(monospace_font(point_size))

    @property
    def word_wrap(self) -> bool:
        return self.lineWrapMode() == QPlainTextEdit.LineWrapMode.WidgetWidth

    def set_word_wrap(self, wrapped: bool) -> None:
        self.setLineWrapMode(
            QPlainTextEdit.LineWrapMode.WidgetWidth if wrapped else QPlainTextEdit.LineWrapMode.NoWrap
        )

    def toggle_word_wrap(self) -> None:
        self.set_word_wrap(not self.word_wrap)

    def wheelEvent(self, event: QWheelEvent) -> None:
        # Without zooming, Ctrl and the wheel are left to Qt, which scrolls a page at a time.
        if not event.modifiers() & Qt.KeyboardModifier.ControlModifier or not self._zoom_with_mouse_wheel:
            super().wheelEvent(event)
            return
        # Smooth scrolling sends many small steps; each full notch is one zoom step.
        self._wheel_units_not_yet_used += event.angleDelta().y()
        steps = int(self._wheel_units_not_yet_used / WHEEL_UNITS_PER_ZOOM_STEP)
        self._wheel_units_not_yet_used -= steps * WHEEL_UNITS_PER_ZOOM_STEP
        for _ in range(abs(steps)):
            self.zoom_requested.emit(1 if steps > 0 else -1)
        event.accept()
