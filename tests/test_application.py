"""Tests for assembling the application."""
import sys
from pathlib import Path

from mathdoer.application import create_run_settings
from mathdoer.languages.python import PYTHON
from mathdoer.registry import shipped_registry_path


def test_run_settings_use_python_this_interpreter_and_the_users_startup_file(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")
    settings = create_run_settings(tmp_path / "configuration")
    assert settings.language is PYTHON
    assert settings.default_interpreter_path == Path(sys.executable)
    assert settings.startup_path == tmp_path / "configuration" / "startup_python.py"
    assert settings.settings_path == tmp_path / "configuration" / "settings_python.toml"
    assert settings.registry_path == shipped_registry_path()
    assert settings.working_directory == tmp_path / "home"


def test_creating_the_settings_creates_the_startup_file_from_the_default(tmp_path):
    settings = create_run_settings(tmp_path / "configuration")
    assert settings.startup_path.read_text(encoding="utf-8") == PYTHON.default_startup_path.read_text(
        encoding="utf-8"
    )


def test_creating_the_settings_does_not_create_the_settings_file_because_a_run_does_not_need_it(tmp_path):
    settings = create_run_settings(tmp_path / "configuration")
    assert not settings.settings_path.exists()


def test_creating_the_settings_keeps_an_edited_startup_file(tmp_path):
    first = create_run_settings(tmp_path)
    first.startup_path.write_text("MINE = 1\n", encoding="utf-8")
    second = create_run_settings(tmp_path)
    assert second.startup_path.read_text(encoding="utf-8") == "MINE = 1\n"
