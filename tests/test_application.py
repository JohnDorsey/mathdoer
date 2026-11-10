"""Tests for assembling the application."""
import sys
from dataclasses import replace
from pathlib import Path

from editor_helpers import foreground_at

from mathdoer.application import create_main_window, create_run_settings, default_interpreter_path
from mathdoer.interface.theme import DARK_THEME
from mathdoer.interface_settings import DEFAULT_INTERFACE_SETTINGS, read_interface_settings, write_interface_settings
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


# ------------------------------------------------------------------------ the window

UNREADABLE_SETTINGS = "# mine\nshow_line_numbers = \n"  # a value is missing on line 2


def settings_file(directory):
    return directory / "interface_settings.toml"


def test_a_window_starts_with_the_default_interface_settings_when_there_is_no_file(qtbot, tmp_path):
    window = create_main_window(tmp_path)
    qtbot.addWidget(window)
    assert window.interface_settings == DEFAULT_INTERFACE_SETTINGS
    assert window.interface_settings_path == settings_file(tmp_path)
    assert not settings_file(tmp_path).exists()  # it is made when a setting changes, not before
    assert window.output_box.output_text() == ""


def test_a_window_starts_with_the_interface_settings_in_the_file(qtbot, tmp_path):
    write_interface_settings(
        settings_file(tmp_path),
        replace(DEFAULT_INTERFACE_SETTINGS, show_line_numbers=False, window_width=1200, window_height=900),
    )
    # A size that the offscreen screen is too small for, so it shows only if the option is used.
    window = create_main_window(tmp_path, screen_size=lambda: (2560, 1400))
    qtbot.addWidget(window)
    assert window.prompt_box.gutter_width() == 0
    assert (window.width(), window.height()) == (1200, 900)
    assert window.output_box.output_text() == ""


def test_a_file_that_cannot_be_read_gives_the_defaults_and_says_so_in_red_in_the_output_box(qtbot, tmp_path):
    settings_file(tmp_path).write_text(UNREADABLE_SETTINGS, encoding="utf-8")
    window = create_main_window(tmp_path)
    qtbot.addWidget(window)
    assert window.interface_settings == DEFAULT_INTERFACE_SETTINGS
    text = window.output_box.output_text()
    assert str(settings_file(tmp_path)) in text
    assert "line 2" in text
    assert "default settings are in use" in text
    assert foreground_at(window.output_box, 0) == DARK_THEME.error_text
    assert foreground_at(window.output_box, len(text) - 2) == DARK_THEME.error_text
    assert settings_file(tmp_path).read_text(encoding="utf-8") == UNREADABLE_SETTINGS  # left as it was


def test_the_first_change_replaces_a_file_that_cannot_be_read(qtbot, tmp_path):
    settings_file(tmp_path).write_text(UNREADABLE_SETTINGS, encoding="utf-8")
    window = create_main_window(tmp_path)
    qtbot.addWidget(window)
    changed = replace(DEFAULT_INTERFACE_SETTINGS, show_indentation_guides=False)
    window.change_interface_settings(changed)
    assert read_interface_settings(settings_file(tmp_path)) == changed


def test_restore_defaults_replaces_a_file_that_cannot_be_read(qtbot, tmp_path):
    settings_file(tmp_path).write_text(UNREADABLE_SETTINGS, encoding="utf-8")
    window = create_main_window(tmp_path)
    qtbot.addWidget(window)
    window.open_settings_window()
    window.settings_window.restore_defaults_button.click()
    assert read_interface_settings(settings_file(tmp_path)) == DEFAULT_INTERFACE_SETTINGS


def test_the_message_says_what_to_do_about_the_file(qtbot, tmp_path):
    settings_file(tmp_path).write_text("nonsense = 1\n", encoding="utf-8")
    window = create_main_window(tmp_path)
    qtbot.addWidget(window)
    text = window.output_box.output_text()
    assert "'nonsense'" in text
    assert "Settings" in text and "replaces the file" in text


def test_running_from_source_the_default_interpreter_is_the_one_mathdoer_runs_on(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)
    assert default_interpreter_path() == Path(sys.executable)


def test_a_packaged_program_has_no_default_interpreter_because_its_own_executable_is_mathdoer(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    assert default_interpreter_path() is None
    assert create_run_settings(tmp_path / "configuration").default_interpreter_path is None
