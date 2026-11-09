"""Tests for the language description and the Python language."""
from pathlib import Path

import pytest

from mathdoer.languages import Language
from mathdoer.languages.python import PYTHON


def make_language(**overrides):
    fields = dict(
        identifier="example",
        display_name="Example",
        file_extension=".ex",
        default_startup_path=Path("startup_example.ex"),
        build_worker_command=lambda interpreter_path: [str(interpreter_path), "worker"],
    )
    fields.update(overrides)
    return Language(**fields)


def test_python_is_described_as_decided():
    assert PYTHON.identifier == "python"
    assert PYTHON.display_name == "Python"
    assert PYTHON.file_extension == ".py"


def test_the_startup_file_name_carries_the_language_name():
    assert PYTHON.startup_file_name == "startup_python.py"
    assert make_language().startup_file_name == "startup_example.ex"


def test_languages_that_share_an_extension_get_different_startup_file_names():
    first = make_language(identifier="first", file_extension=".py")
    second = make_language(identifier="second", file_extension=".py")
    assert first.startup_file_name != second.startup_file_name


def test_the_bundled_default_startup_file_follows_the_naming_convention():
    assert PYTHON.default_startup_path.is_file()
    assert PYTHON.default_startup_path.name == PYTHON.startup_file_name


@pytest.mark.parametrize("identifier", ["", "Python", "py thon", "py-thon", "1python", "python!"])
def test_rejects_identifiers_that_are_not_lowercase_words(identifier):
    with pytest.raises(ValueError, match="identifier"):
        make_language(identifier=identifier)


@pytest.mark.parametrize("extension", ["", "py", ".", "..py", ".p y"])
def test_rejects_file_extensions_that_are_not_a_dot_and_a_word(extension):
    with pytest.raises(ValueError, match="extension"):
        make_language(file_extension=extension)


def test_the_python_worker_command_runs_the_worker_script_in_utf8_mode():
    interpreter_path = Path("some") / "python.exe"
    command = PYTHON.build_worker_command(interpreter_path)
    assert command[:3] == [str(interpreter_path), "-X", "utf8"]
    assert Path(command[3]).name == "worker.py"
    assert Path(command[3]).is_file()
    assert len(command) == 4
