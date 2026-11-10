"""The user's settings for a language, kept in a TOML file that is read before every run,
so a change takes effect on the next run without restarting.

The settings are:

* interpreter: the program that runs the prompt, as the full path of an executable or the
  name of one found on the search path. Without it prompts run on the default interpreter.
"""
import shutil
import tomllib
from pathlib import Path

from mathdoer.toml_files import read_toml_file

INTERPRETER_SETTING = "interpreter"
KNOWN_SETTINGS = (INTERPRETER_SETTING,)

# TOML reads a backslash in a double-quoted string as the start of an escape, which is the
# usual mistake when a Windows path is pasted into the file.
BACKSLASH_ERROR_FRAGMENTS = ("Unescaped", "hex value", "escape")
BACKSLASH_HINT = "In a path, put single quotes around the text so that backslashes are taken literally."


class UserSettingsError(Exception):
    """The settings file cannot be used. The message is for the user: it names the file
    and says what to change."""


def resolve_interpreter(
    settings_path: Path, default_interpreter_path: Path | None, search_path: str | None = None
) -> Path:
    """The interpreter the settings file names, or the default when it does not name one
    (including when there is no settings file). A name without a folder is looked up on the
    search path given, or on the one of this process. Raises UserSettingsError, also when
    nothing names an interpreter and there is no default."""
    settings = _read_settings(settings_path)
    unknown_settings = sorted(name for name in settings if name not in KNOWN_SETTINGS)
    if unknown_settings:
        names = ", ".join(f"'{name}'" for name in unknown_settings)
        known = ", ".join(KNOWN_SETTINGS)
        raise UserSettingsError(f"Unknown setting {names} in {settings_path}. The settings are: {known}.")
    if INTERPRETER_SETTING not in settings:
        if default_interpreter_path is None:
            raise UserSettingsError(
                f"No interpreter is set, and mathdoer has none of its own. Set '{INTERPRETER_SETTING}' in "
                f"{settings_path} to the Python that should run your prompts (3.11 or later)."
            )
        return default_interpreter_path
    return _find_interpreter(settings[INTERPRETER_SETTING], settings_path, search_path)


def _read_settings(settings_path: Path) -> dict:
    try:
        return read_toml_file(settings_path)
    except FileNotFoundError:
        return {}
    except tomllib.TOMLDecodeError as error:
        hint = BACKSLASH_HINT if any(fragment in str(error) for fragment in BACKSLASH_ERROR_FRAGMENTS) else ""
        raise UserSettingsError(f"Cannot read the settings file {settings_path}: {error}. {hint}".strip()) from error
    except (OSError, UnicodeDecodeError) as error:
        raise UserSettingsError(f"Cannot read the settings file {settings_path}: {error}") from error


def _find_interpreter(value: object, settings_path: Path, search_path: str | None) -> Path:
    if not isinstance(value, str):
        raise UserSettingsError(
            f"The setting '{INTERPRETER_SETTING}' in {settings_path} must be text in quotes, not {value!r}."
        )
    name = value.strip()
    if not name:
        raise UserSettingsError(
            f"The setting '{INTERPRETER_SETTING}' in {settings_path} is empty. "
            "Remove the line to use the default interpreter."
        )
    found = shutil.which(name, path=search_path)
    if found is None:
        raise UserSettingsError(
            f"The interpreter '{name}' set in {settings_path} was not found. "
            "Give the full path of the program, or the name of one on the search path."
        )
    return Path(found)
