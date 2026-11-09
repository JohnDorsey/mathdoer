"""The Python language: its worker script and its default startup and settings files."""
from pathlib import Path

from mathdoer.languages import EditingRules, Language
from mathdoer.languages.python.editing import opens_indented_block
from mathdoer.languages.python.lexer import lex_line
from mathdoer.registry import RegistryEntry

LANGUAGE_FOLDER = Path(__file__).parent
WORKER_PATH = LANGUAGE_FOLDER / "worker.py"


def build_worker_command(interpreter_path: Path) -> list[str]:
    # UTF-8 mode makes open() default to UTF-8 in the user's code, as on other platforms.
    return [str(interpreter_path), "-X", "utf8", str(WORKER_PATH)]


def format_name(entry: RegistryEntry) -> str:
    return entry.name


def format_literal(entry: RegistryEntry) -> str:
    """The stored digits, so nothing is lost. A ratio goes in parentheses so it can follow
    an operator; a ratio with decimals becomes a ratio of whole numbers, which Python
    divides with correct rounding, so the literal is exactly the value of the named constant."""
    numerator_text, separator, denominator_text = entry.value_text.partition("/")
    if not separator:
        return entry.value_text
    if numerator_text.isdigit() and denominator_text.isdigit():
        return f"({entry.value_text})"
    return f"({entry.value.numerator}/{entry.value.denominator})"


PYTHON = Language(
    identifier="python",
    display_name="Python",
    file_extension=".py",
    default_startup_path=LANGUAGE_FOLDER / "startup_python.py",
    default_settings_path=LANGUAGE_FOLDER / "settings_python.toml",
    build_worker_command=build_worker_command,
    format_name=format_name,
    format_literal=format_literal,
    editing=EditingRules(
        comment_prefix="#",
        opens_indented_block=opens_indented_block,
        bracket_pairs=(("(", ")"), ("[", "]"), ("{", "}")),
        indent_width=4,
    ),
    lex_line=lex_line,
)
