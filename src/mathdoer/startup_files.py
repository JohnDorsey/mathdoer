"""Where the user's startup files live, and creating them from the bundled defaults."""
import os
import shutil
import sys
from pathlib import Path

from mathdoer.languages import Language

APPLICATION_DIRECTORY_NAME = "mathdoer"


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


def ensure_startup_file(language: Language, directory: Path) -> Path:
    """Create the startup file from the bundled default if it does not exist; never overwrite."""
    path = startup_file_path(language, directory)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(language.default_startup_path, path)
    return path
