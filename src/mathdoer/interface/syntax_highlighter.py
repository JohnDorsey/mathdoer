"""Coloring code as it is typed, using the language's lexer and the theme's colors."""
from PySide6.QtGui import QColor, QSyntaxHighlighter, QTextCharFormat, QTextDocument

from mathdoer.interface.theme import Theme
from mathdoer.languages import Language
from mathdoer.utf16 import utf16_length


class SyntaxHighlighter(QSyntaxHighlighter):
    """The lexer's state at the end of each line is kept with the line, so the next line
    starts from it and an edit that changes it recolors the lines after it."""

    def __init__(self, document: QTextDocument, language: Language, theme: Theme):
        super().__init__(document)
        self._lex_line = language.lex_line
        self._formats = {}
        for kind, color in theme.token_colors.items():
            text_format = QTextCharFormat()
            text_format.setForeground(QColor(color))
            self._formats[kind] = text_format

    def highlightBlock(self, text: str) -> None:
        state_before = max(self.previousBlockState(), 0)  # -1 for the first line
        lexed = self._lex_line(text, state_before)
        has_wide_characters = utf16_length(text) != len(text)
        for token in lexed.tokens:
            start, end = token.start, token.end
            if has_wide_characters:  # Qt counts in UTF-16 units
                start, end = utf16_length(text[:start]), utf16_length(text[:end])
            self.setFormat(start, end - start, self._formats[token.kind])
        self.setCurrentBlockState(lexed.end_state)
