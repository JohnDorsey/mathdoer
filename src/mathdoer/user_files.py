"""Where the user's startup and settings files live, and creating them from the bundled defaults."""
import os
import shutil
import sys
from pathlib import Path

from mathdoer.languages import Language

APPLICATION_DIRECTORY_NAME = "mathdoer"
INTERFACE_SETTINGS_FILE_NAME = "interface_settings.toml"


def user_configuration_directory() -> Path:
    if sys.platform == "win32":
        application_data = os.environ.get("APPDATA")
        base = Path(application_data) if application_data else Path.home() / "AppData" / "Roaming"
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        configuration_home = os.environ.get("XDG_CONFIG_HOME")
        base = Path(configuration_home) if configuration_home else Path.home() / ".config"
    return base / APPLICATION_DIRECTORY_NAME


def startup_file_path(language: Language, directory: Path) -> Path:
    return Path(directory) / language.startup_file_name


def settings_file_path(language: Language, directory: Path) -> Path:
    return Path(directory) / language.settings_file_name


def interface_settings_file_path(directory: Path) -> Path:
    """The settings of the interface are the same whatever the language, and the settings window
    writes them; the name keeps the file apart from a language's settings file."""
    return Path(directory) / INTERFACE_SETTINGS_FILE_NAME


def create_file_if_missing(default_path: Path, path: Path) -> Path:
    """Create the file at the path as a copy of the bundled default if it does not exist;
    never overwrite."""
    path = Path(path)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(default_path, path)
    return path


def create_startup_file_if_missing(language: Language, path: Path) -> Path:
    return create_file_if_missing(language.default_startup_path, path)


def ensure_startup_file(language: Language, directory: Path) -> Path:
    return create_startup_file_if_missing(language, startup_file_path(language, directory))
