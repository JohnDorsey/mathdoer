"""Assembling and starting the application."""
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from mathdoer.interface.main_window import MainWindow
from mathdoer.languages.python import PYTHON
from mathdoer.registry import shipped_registry_path
from mathdoer.running import RunSettings
from mathdoer.startup_files import ensure_startup_file, user_configuration_directory


def create_run_settings(configuration_directory: Path | None = None) -> RunSettings:
    directory = configuration_directory or user_configuration_directory()
    return RunSettings(
        language=PYTHON,
        interpreter_path=Path(sys.executable),
        startup_path=ensure_startup_file(PYTHON, directory),
        registry_path=shipped_registry_path(),
        working_directory=Path.home(),
    )


def main() -> int:
    application = QApplication(sys.argv)
    application.setStyle("Fusion")
    window = MainWindow(create_run_settings())
    window.show()
    return application.exec()
