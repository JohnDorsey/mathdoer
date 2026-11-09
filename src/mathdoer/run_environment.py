"""The environment variables a run's process starts with.

mathdoer is usually started inside a virtual environment (uv run does it). A run must not
inherit that: launcher programs, such as the Windows python3.exe alias and py.exe, pick the
active virtual environment's interpreter instead of the one they were asked for, and a bare
interpreter name would be found in the environment's folder first.
"""
import os
import sys
from collections.abc import Mapping
from pathlib import Path

VIRTUAL_ENVIRONMENT_VARIABLE = "VIRTUAL_ENV"
VIRTUAL_ENVIRONMENT_PROMPT_VARIABLE = "VIRTUAL_ENV_PROMPT"
SEARCH_PATH_VARIABLE = "PATH"


def own_virtual_environment() -> Path | None:
    """The virtual environment this process runs in, or None when it does not run in one."""
    return Path(sys.prefix) if sys.prefix != sys.base_prefix else None


def without_virtual_environment(
    environment: Mapping[str, str], virtual_environment: Path | None
) -> dict[str, str]:
    """A copy of the environment as it was before the virtual environment was activated:
    without the variables that activate it and without its folders on the search path.
    Another virtual environment that happens to be active is left alone."""
    result = dict(environment)
    if virtual_environment is None:
        return result
    if VIRTUAL_ENVIRONMENT_VARIABLE in result and _same_folder(
        result[VIRTUAL_ENVIRONMENT_VARIABLE], virtual_environment
    ):
        del result[VIRTUAL_ENVIRONMENT_VARIABLE]
        result.pop(VIRTUAL_ENVIRONMENT_PROMPT_VARIABLE, None)
    if SEARCH_PATH_VARIABLE in result:
        kept_entries = [
            entry
            for entry in result[SEARCH_PATH_VARIABLE].split(os.pathsep)
            if not entry or not _is_inside(entry, virtual_environment)
        ]
        result[SEARCH_PATH_VARIABLE] = os.pathsep.join(kept_entries)
    return result


def create_run_environment() -> dict[str, str]:
    """The environment of this process, as a run should start with it."""
    return without_virtual_environment(os.environ, own_virtual_environment())


def _normalized(path: str | Path) -> str:
    return os.path.normcase(os.path.realpath(path))


def _same_folder(first: str | Path, second: str | Path) -> bool:
    return _normalized(first) == _normalized(second)


def _is_inside(path: str | Path, folder: str | Path) -> bool:
    folder_text = _normalized(folder)
    path_text = _normalized(path)
    return path_text == folder_text or path_text.startswith(folder_text + os.sep)
