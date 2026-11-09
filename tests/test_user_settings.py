"""Tests for reading the user's settings file and choosing the interpreter from it."""
import tomllib
from pathlib import Path

import pytest

from mathdoer.languages.python import PYTHON
from mathdoer.user_settings import UserSettingsError, resolve_interpreter

DEFAULT_INTERPRETER = Path("the") / "default" / "python.exe"
SETTINGS_FILE_NAME = "settings_python.toml"


@pytest.fixture
def settings_path(tmp_path):
    return tmp_path / SETTINGS_FILE_NAME


def resolve(settings_path):
    return resolve_interpreter(settings_path, DEFAULT_INTERPRETER)


def error_message_for(settings_path):
    with pytest.raises(UserSettingsError) as caught:
        resolve(settings_path)
    return str(caught.value)


# ----------------------------------------------------------- when nothing is set

def test_a_missing_settings_file_means_the_default_interpreter(settings_path):
    assert not settings_path.exists()
    assert resolve(settings_path) == DEFAULT_INTERPRETER


@pytest.mark.parametrize("text", ["", "\n\n", "# only a comment\n", "# interpreter = 'x'\n"])
def test_a_settings_file_that_does_not_name_an_interpreter_means_the_default(settings_path, text):
    settings_path.write_text(text, encoding="utf-8")
    assert resolve(settings_path) == DEFAULT_INTERPRETER


# ------------------------------------------------------------ naming an interpreter

def test_a_full_path_names_that_interpreter(settings_path, make_fake_interpreter):
    interpreter = make_fake_interpreter()
    settings_path.write_text(f"interpreter = '{interpreter}'\n", encoding="utf-8")
    assert resolve(settings_path) == interpreter


def test_a_path_in_a_basic_string_works_when_the_backslashes_are_escaped(settings_path, make_fake_interpreter):
    interpreter = make_fake_interpreter()
    escaped = str(interpreter).replace("\\", "\\\\")
    settings_path.write_text(f'interpreter = "{escaped}"\n', encoding="utf-8")
    assert resolve(settings_path) == interpreter


def test_a_bare_name_is_looked_up_on_the_search_path(
    settings_path, make_fake_interpreter, tmp_path, monkeypatch
):
    interpreter = make_fake_interpreter("mathdoer_test_python", tmp_path / "somewhere")
    monkeypatch.setenv("PATH", str(interpreter.parent))
    settings_path.write_text("interpreter = 'mathdoer_test_python'\n", encoding="utf-8")
    assert Path(resolve(settings_path)).resolve() == interpreter.resolve()


def test_a_given_search_path_replaces_the_one_of_the_environment(
    settings_path, make_fake_interpreter, tmp_path, monkeypatch
):
    """The caller can look a name up on a different search path, for example one without
    mathdoer's own virtual environment on it."""
    wanted = make_fake_interpreter("mathdoer_test_python", tmp_path / "wanted")
    unwanted = make_fake_interpreter("mathdoer_test_python", tmp_path / "unwanted")
    monkeypatch.setenv("PATH", str(unwanted.parent))
    settings_path.write_text("interpreter = 'mathdoer_test_python'\n", encoding="utf-8")
    found = resolve_interpreter(settings_path, DEFAULT_INTERPRETER, search_path=str(wanted.parent))
    assert Path(found).resolve() == wanted.resolve()


def test_a_name_that_is_only_on_the_environment_search_path_is_not_found_on_a_given_one(
    settings_path, make_fake_interpreter, tmp_path, monkeypatch
):
    only_in_environment = make_fake_interpreter("mathdoer_test_python", tmp_path / "environment")
    monkeypatch.setenv("PATH", str(only_in_environment.parent))
    settings_path.write_text("interpreter = 'mathdoer_test_python'\n", encoding="utf-8")
    with pytest.raises(UserSettingsError, match="not found"):
        resolve_interpreter(settings_path, DEFAULT_INTERPRETER, search_path=str(tmp_path / "empty"))


def test_the_surrounding_spaces_of_the_text_do_not_matter(settings_path, make_fake_interpreter):
    interpreter = make_fake_interpreter()
    settings_path.write_text(f"interpreter = '  {interpreter}  '\n", encoding="utf-8")
    assert resolve(settings_path) == interpreter


def test_the_other_settings_do_not_change_which_interpreter_is_named(settings_path, make_fake_interpreter):
    interpreter = make_fake_interpreter()
    settings_path.write_text(
        f"# my settings\n\ninterpreter = '{interpreter}'  # for numpy\n", encoding="utf-8"
    )
    assert resolve(settings_path) == interpreter


# ------------------------------------------------------------------ what is rejected

def test_an_interpreter_that_does_not_exist_is_an_error_naming_it_and_the_file(settings_path, tmp_path):
    missing = tmp_path / "nowhere" / "python.exe"
    settings_path.write_text(f"interpreter = '{missing}'\n", encoding="utf-8")
    message = error_message_for(settings_path)
    assert str(missing) in message
    assert str(settings_path) in message
    assert "not found" in message


def test_a_bare_name_that_is_not_on_the_search_path_is_an_error(settings_path, tmp_path, monkeypatch):
    monkeypatch.setenv("PATH", str(tmp_path))
    settings_path.write_text("interpreter = 'mathdoer_no_such_program'\n", encoding="utf-8")
    assert "mathdoer_no_such_program" in error_message_for(settings_path)


def test_a_folder_is_not_an_interpreter(settings_path, tmp_path):
    settings_path.write_text(f"interpreter = '{tmp_path}'\n", encoding="utf-8")
    assert "not found" in error_message_for(settings_path)


@pytest.mark.parametrize("empty_text", ["''", "'   '"])
def test_an_empty_interpreter_is_an_error_that_says_how_to_use_the_default(settings_path, empty_text):
    settings_path.write_text(f"interpreter = {empty_text}\n", encoding="utf-8")
    message = error_message_for(settings_path)
    assert "empty" in message
    assert "remove" in message.lower()


@pytest.mark.parametrize("value", ["3", "true", "['python']", "{ path = 'python' }"])
def test_an_interpreter_that_is_not_text_is_an_error(settings_path, value):
    settings_path.write_text(f"interpreter = {value}\n", encoding="utf-8")
    message = error_message_for(settings_path)
    assert "interpreter" in message
    assert "text" in message


def test_an_unknown_setting_is_an_error_naming_it_so_a_typo_is_not_silent(settings_path):
    settings_path.write_text("interpretor = 'python'\n", encoding="utf-8")
    message = error_message_for(settings_path)
    assert "interpretor" in message
    assert str(settings_path) in message
    assert "interpreter" in message  # the settings that do exist are listed


def test_invalid_toml_is_an_error_naming_the_file_and_the_line(settings_path):
    settings_path.write_text("# first line\ninterpreter = \n", encoding="utf-8")
    message = error_message_for(settings_path)
    assert str(settings_path) in message
    assert "line 2" in message


def test_an_unescaped_backslash_gets_a_hint_about_single_quotes(settings_path):
    settings_path.write_text('interpreter = "C:\\Python311\\python.exe"\n', encoding="utf-8")
    message = error_message_for(settings_path)
    assert str(settings_path) in message
    assert "single quotes" in message


def test_a_file_that_is_not_utf8_is_an_error_naming_the_file(settings_path):
    settings_path.write_bytes(b"interpreter = '\xff\xfe'\n")
    message = error_message_for(settings_path)
    assert str(settings_path) in message


def test_a_settings_path_that_cannot_be_read_is_an_error_naming_the_file(settings_path):
    settings_path.mkdir()  # a folder where the file should be
    message = error_message_for(settings_path)
    assert str(settings_path) in message


def test_the_file_is_read_again_on_every_call(settings_path, make_fake_interpreter):
    interpreter = make_fake_interpreter()
    settings_path.write_text("interpreter = 'mathdoer_no_such_program'\n", encoding="utf-8")
    with pytest.raises(UserSettingsError):
        resolve(settings_path)
    settings_path.write_text(f"interpreter = '{interpreter}'\n", encoding="utf-8")
    assert resolve(settings_path) == interpreter
    settings_path.write_text("", encoding="utf-8")
    assert resolve(settings_path) == DEFAULT_INTERPRETER


# ----------------------------------------------------------- the bundled default file

def test_the_bundled_default_settings_file_follows_the_naming_convention():
    assert PYTHON.default_settings_path.is_file()
    assert PYTHON.default_settings_path.name == PYTHON.settings_file_name == SETTINGS_FILE_NAME


def test_the_bundled_default_settings_file_is_valid_and_sets_nothing():
    text = PYTHON.default_settings_path.read_text(encoding="utf-8")
    assert tomllib.loads(text) == {}


def test_the_bundled_default_settings_file_explains_the_interpreter_setting_and_quoting():
    text = PYTHON.default_settings_path.read_text(encoding="utf-8")
    assert "# interpreter = " in text
    comment_words = " ".join(line.lstrip("# ").strip() for line in text.splitlines())  # ignores line wrapping
    assert "single quotes" in comment_words


def test_the_commented_example_in_the_default_file_is_valid_once_uncommented():
    """Removing the leading # from the example must give a valid setting, so the example is
    not a trap; its backslashes must survive, which is what the single quotes are for."""
    example_lines = [
        line for line in PYTHON.default_settings_path.read_text(encoding="utf-8").splitlines()
        if line.startswith("# interpreter = ")
    ]
    assert len(example_lines) == 1
    assert tomllib.loads(example_lines[0][2:]) == {"interpreter": "C:\\Python311\\python.exe"}
