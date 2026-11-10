"""Assembling and starting the application."""
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from mathdoer.interface.main_window import MainWindow
from mathdoer.interface_settings import DEFAULT_INTERFACE_SETTINGS, InterfaceSettingsError, read_interface_settings
from mathdoer.languages.python import PYTHON
from mathdoer.registry import shipped_registry_path
from mathdoer.running import RunSettings
from mathdoer.user_files import (
    ensure_startup_file,
    interface_settings_file_path,
    settings_file_path,
    user_configuration_directory,
)

UNREADABLE_SETTINGS_NOTICE = (
    "The default settings are in use. Changing a setting in Edit > Settings, or Restore defaults there, "
    "replaces the file."
)


def default_interpreter_path() -> Path | None:
    """The Python that runs prompts when the settings file names none: the one mathdoer runs
    on, which has no extra packages. A packaged program has none, because its own executable
    is mathdoer, and starting that to run a prompt would open another window."""
    if getattr(sys, "frozen", False):
        return None
    return Path(sys.executable)


def create_run_settings(configuration_directory: Path | None = None) -> RunSettings:
    directory = configuration_directory or user_configuration_directory()
    return RunSettings(
        language=PYTHON,
        default_interpreter_path=default_interpreter_path(),
        settings_path=settings_file_path(PYTHON, directory),
        startup_path=ensure_startup_file(PYTHON, directory),
        registry_path=shipped_registry_path(),
        working_directory=Path.home(),
    )


def create_main_window(configuration_directory: Path | None = None, **window_options) -> MainWindow:
    """The window, with the interface settings the user saved. A settings file that cannot be
    read is not an obstacle: the window starts with the default settings and says why in the
    output box, and the file is left as it is until a setting is changed."""
    directory = configuration_directory or user_configuration_directory()
    interface_settings_path = interface_settings_file_path(directory)
    try:
        interface_settings, problem = read_interface_settings(interface_settings_path), None
    except InterfaceSettingsError as error:
        interface_settings, problem = DEFAULT_INTERFACE_SETTINGS, f"{error} {UNREADABLE_SETTINGS_NOTICE}"
    window = MainWindow(
        create_run_settings(directory),
        interface_settings=interface_settings,
        interface_settings_path=interface_settings_path,
        **window_options,
    )
    if problem is not None:
        window.report_problem(problem)
    return window


def main() -> int:
    application = QApplication(sys.argv)
    application.setStyle("Fusion")
    window = create_main_window()
    window.show()
    return application.exec()
