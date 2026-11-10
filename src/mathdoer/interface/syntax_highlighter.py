"""Coloring code as it is typed, using the language's lexer and the theme's colors."""
from PySide6.QtGui import QColor, QSyntaxHighlighter, QTextCharFormat, QTextDocument

from mathdoer.interface.none_references import balanced_none_references
from mathdoer.interface.theme import Theme
from mathdoer.languages import Language
from mathdoer.utf16 import utf16_length


class SyntaxHighlighter(QSyntaxHighlighter):
    """The lexer's state at the end of each line is kept with the line, so the next line
    starts from it and an edit that changes it recolors the lines after it.

    Coloring can be turned off. The lines are still lexed and keep their states, because
    matching brackets needs them to tell code from strings and comments."""

    def __init__(self, document: QTextDocument, language: Language, theme: Theme):
        super().__init__(document)
        self._lex_line = language.lex_line
        self._coloring = True
        self._formats = {}
        for kind, color in theme.token_colors.items():
            text_format = QTextCharFormat()
            text_format.setForeground(QColor(color))
            self._formats[kind] = text_format

    @property
    def coloring(self) -> bool:
        return self._coloring

    def set_coloring(self, coloring: bool) -> None:
        if coloring != self._coloring:
            self._coloring = coloring
            self.rehighlight()

    def highlightBlock(self, text: str) -> None:
        with balanced_none_references():  # the calls into Qt below lose references to None on Linux
            state_before = max(self.previousBlockState(), 0)  # -1 for the first line
            lexed = self._lex_line(text, state_before)
            if self._coloring:
                has_wide_characters = utf16_length(text) != len(text)
                for token in lexed.tokens:
                    start, end = token.start, token.end
                    if has_wide_characters:  # Qt counts in UTF-16 units
                        start, end = utf16_length(text[:start]), utf16_length(text[:end])
                    self.setFormat(start, end - start, self._formats[token.kind])
            self.setCurrentBlockState(lexed.end_state)
