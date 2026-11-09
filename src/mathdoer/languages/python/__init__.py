"""The Python language: its worker script and its default startup file."""
from pathlib import Path

from mathdoer.languages import Language

LANGUAGE_FOLDER = Path(__file__).parent
WORKER_PATH = LANGUAGE_FOLDER / "worker.py"


def build_worker_command(interpreter_path: Path) -> list[str]:
    # UTF-8 mode makes open() default to UTF-8 in the user's code, as on other platforms.
    return [str(interpreter_path), "-X", "utf8", str(WORKER_PATH)]


PYTHON = Language(
    identifier="python",
    display_name="Python",
    file_extension=".py",
    default_startup_path=LANGUAGE_FOLDER / "startup_python.py",
    build_worker_command=build_worker_command,
)
