"""What the rest of mathdoer needs to know about a language the prompt can be written in.

Everything specific to one language lives in that language's own module, for example
mathdoer.languages.python. Code outside these modules stays language-neutral.
"""
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

IDENTIFIER_PATTERN = re.compile(r"[a-z][a-z0-9_]*")
FILE_EXTENSION_PATTERN = re.compile(r"\.[A-Za-z0-9_]+")


@dataclass(frozen=True)
class Language:
    identifier: str
    display_name: str
    file_extension: str
    default_startup_path: Path
    # Given the path of the interpreter, returns the command that starts the worker.
    # The worker follows the protocol described in mathdoer.running.
    build_worker_command: Callable[[Path], list[str]]

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
