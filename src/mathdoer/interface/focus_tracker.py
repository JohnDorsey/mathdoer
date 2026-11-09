"""Which text box a command that acts on 'the box I am in' should act on."""
from collections.abc import Sequence

from PySide6.QtWidgets import QApplication, QWidget


class ActiveBoxTracker:
    """The box that has the focus, or if the focus is elsewhere, for example on the menu bar
    after the menu was opened from the keyboard, the box that had it last."""

    def __init__(self, boxes: Sequence[QWidget]):
        self._boxes = tuple(boxes)
        self._last_focused_box = self._boxes[0]
        QApplication.instance().focusChanged.connect(self._remember_focused_box)

    def active_box(self) -> QWidget:
        focused = QApplication.focusWidget()
        if self._is_one_of_the_boxes(focused):
            return focused
        return self._last_focused_box

    def _remember_focused_box(self, old: QWidget | None, new: QWidget | None) -> None:
        if self._is_one_of_the_boxes(new):
            self._last_focused_box = new

    def _is_one_of_the_boxes(self, widget: QWidget | None) -> bool:
        return any(widget is box for box in self._boxes)
