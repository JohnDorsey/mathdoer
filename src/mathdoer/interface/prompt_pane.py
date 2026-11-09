"""The top half of the window: the find bar above the prompt box."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QVBoxLayout, QWidget

from mathdoer.interface.find_bar import FindBar
from mathdoer.interface.prompt_editor import PromptEditor
from mathdoer.interface.theme import Theme

CLOSE_FIND_BAR_SHORTCUT = "Esc"


class PromptPane(QWidget):
    def __init__(self, editor: PromptEditor, theme: Theme, parent=None):
        super().__init__(parent)
        self.editor = editor
        self.find_bar = FindBar(editor, theme)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.find_bar)
        layout.addWidget(editor)

        # Esc closes the bar from the bar or from the text, and from nowhere else.
        QShortcut(
            QKeySequence(CLOSE_FIND_BAR_SHORTCUT),
            self,
            activated=self.find_bar.close_bar,
            context=Qt.ShortcutContext.WidgetWithChildrenShortcut,
        )
