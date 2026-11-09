"""Tests for locating and creating the user's startup and settings files."""
import sys
from pathlib import Path

import pytest

from mathdoer.languages.python import PYTHON
from mathdoer.user_files import (
    create_file_if_missing,
    create_startup_file_if_missing,
    ensure_startup_file,
    settings_file_path,
    startup_file_path,
    user_configuration_directory,
)


def test_windows_uses_the_roaming_application_data_folder(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setenv("APPDATA", str(tmp_path / "Roaming"))
    assert user_configuration_directory() == tmp_path / "Roaming" / "mathdoer"


def test_windows_without_the_variable_falls_back_to_the_standard_location(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    assert user_configuration_directory() == tmp_path / "AppData" / "Roaming" / "mathdoer"


def test_macos_uses_application_support(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    assert user_configuration_directory() == tmp_path / "Library" / "Application Support" / "mathdoer"


def test_linux_uses_the_xdg_configuration_variable_when_set(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    assert user_configuration_directory() == tmp_path / "xdg" / "mathdoer"


@pytest.mark.parametrize("unset_value", [None, ""])
def test_linux_falls_back_to_dot_config(monkeypatch, tmp_path, unset_value):
    monkeypatch.setattr(sys, "platform", "linux")
    if unset_value is None:
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    else:
        monkeypatch.setenv("XDG_CONFIG_HOME", unset_value)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    assert user_configuration_directory() == tmp_path / ".config" / "mathdoer"


def test_the_startup_file_path_is_the_language_file_name_in_the_directory(tmp_path):
    assert startup_file_path(PYTHON, tmp_path) == tmp_path / "startup_python.py"


def test_ensure_creates_the_directory_and_the_file_from_the_bundled_default(tmp_path):
    directory = tmp_path / "does" / "not" / "exist"
    path = ensure_startup_file(PYTHON, directory)
    assert path == directory / "startup_python.py"
    assert path.read_text(encoding="utf-8") == PYTHON.default_startup_path.read_text(encoding="utf-8")


def test_ensure_never_overwrites_the_users_edits(tmp_path):
    path = ensure_startup_file(PYTHON, tmp_path)
    path.write_text("MY_OWN = 1\n", encoding="utf-8")
    assert ensure_startup_file(PYTHON, tmp_path) == path
    assert path.read_text(encoding="utf-8") == "MY_OWN = 1\n"


def test_a_missing_startup_file_is_recreated_from_the_default_at_its_own_path(tmp_path):
    path = tmp_path / "nested" / "my_startup.py"
    assert create_startup_file_if_missing(PYTHON, path) == path
    assert path.read_text(encoding="utf-8") == PYTHON.default_startup_path.read_text(encoding="utf-8")


def test_an_existing_startup_file_is_left_alone_by_create_if_missing(tmp_path):
    path = tmp_path / "my_startup.py"
    path.write_text("MINE = 1\n", encoding="utf-8")
    create_startup_file_if_missing(PYTHON, path)
    assert path.read_text(encoding="utf-8") == "MINE = 1\n"


def test_ensure_keeps_an_empty_file_the_user_made_on_purpose(tmp_path):
    path = ensure_startup_file(PYTHON, tmp_path)
    path.write_text("", encoding="utf-8")
    ensure_startup_file(PYTHON, tmp_path)
    assert path.read_text(encoding="utf-8") == ""


def test_the_settings_file_path_is_the_language_settings_file_name_in_the_directory(tmp_path):
    assert settings_file_path(PYTHON, tmp_path) == tmp_path / "settings_python.toml"


def test_a_missing_file_is_created_with_its_parent_folders_from_the_given_default(tmp_path):
    default = tmp_path / "default.toml"
    default.write_text("# the default\n", encoding="utf-8")
    path = tmp_path / "nested" / "settings.toml"
    assert create_file_if_missing(default, path) == path
    assert path.read_text(encoding="utf-8") == "# the default\n"


def test_an_existing_file_is_never_overwritten_by_create_file_if_missing(tmp_path):
    default = tmp_path / "default.toml"
    default.write_text("# the default\n", encoding="utf-8")
    path = tmp_path / "settings.toml"
    path.write_text("# mine\n", encoding="utf-8")
    create_file_if_missing(default, path)
    assert path.read_text(encoding="utf-8") == "# mine\n"


def test_the_default_settings_text_is_copied_exactly(tmp_path):
    path = tmp_path / PYTHON.settings_file_name
    create_file_if_missing(PYTHON.default_settings_path, path)
    assert path.read_bytes() == PYTHON.default_settings_path.read_bytes()
