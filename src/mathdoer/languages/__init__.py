"""What the rest of mathdoer needs to know about a language the prompt can be written in.

Everything specific to one language lives in that language's own module, for example
mathdoer.languages.python. Code outside these modules stays language-neutral.
"""
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from mathdoer.registry import RegistryEntry
from mathdoer.syntax import LexedLine

IDENTIFIER_PATTERN = re.compile(r"[a-z][a-z0-9_]*")
FILE_EXTENSION_PATTERN = re.compile(r"\.[A-Za-z0-9_]+")


@dataclass(frozen=True)
class EditingRules:
    """What the editor needs to know to edit code in a language."""

    comment_prefix: str
    # Given the lines of the document and a position in it (line, column), does the code
    # before that position open an indented block, so that a new line there is indented?
    opens_indented_block: Callable[[Sequence[str], int, int], bool]
    bracket_pairs: tuple[tuple[str, str], ...]
    indent_width: int = 4


@dataclass(frozen=True)
class Language:
    identifier: str
    display_name: str
    file_extension: str
    default_startup_path: Path
    default_settings_path: Path
    # Given the path of the interpreter, returns the command that starts the worker.
    # The worker follows the protocol described in mathdoer.running.
    build_worker_command: Callable[[Path], list[str]]
    # How a registry entry is written in this language: the name of the variable that holds
    # it, and its value as a literal that can be typed anywhere an expression can.
    format_name: Callable[[RegistryEntry], str]
    format_literal: Callable[[RegistryEntry], str]
    editing: EditingRules
    # Splits one line into tokens, given the lexer's state at the start of the line.
    lex_line: Callable[[str, int], LexedLine]

    def __post_init__(self):
        if not IDENTIFIER_PATTERN.fullmatch(self.identifier):
            raise ValueError(
                f"language identifier {self.identifier!r} must be lowercase letters, digits and underscores"
            )
        if not FILE_EXTENSION_PATTERN.fullmatch(self.file_extension):
            raise ValueError(
                f"language file extension {self.file_extension!r} must be a dot followed by letters or digits"
            )

    @property
    def startup_file_name(self) -> str:
        """Carries the language name so startup files never collide, whatever their extension."""
        return f"startup_{self.identifier}{self.file_extension}"

    @property
    def settings_file_name(self) -> str:
        """Settings are TOML whatever the language, so the language name keeps the files apart."""
        return f"settings_{self.identifier}.toml"
