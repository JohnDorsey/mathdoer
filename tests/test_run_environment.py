"""Tests for the environment a run's process starts with.

mathdoer is usually started inside a virtual environment (uv run does it). A run on a
different interpreter must not inherit that: launcher programs such as the Windows
python3.exe alias and py.exe pick the active virtual environment's Python over the one
they were asked for.
"""
import os
import sys
from pathlib import Path

import pytest

from mathdoer import run_environment
from mathdoer.run_environment import (
    create_run_environment,
    own_virtual_environment,
    without_virtual_environment,
)

windows_only = pytest.mark.skipif(sys.platform != "win32", reason="Windows paths ignore case")


def search_path(*entries):
    return os.pathsep.join(str(entry) for entry in entries)


# ------------------------------------------------------------ the activation variables

def test_the_variables_that_activate_our_own_virtual_environment_are_removed(tmp_path):
    root = tmp_path / "venv"
    environment = {"VIRTUAL_ENV": str(root), "VIRTUAL_ENV_PROMPT": "mathdoer", "KEPT": "yes"}
    assert without_virtual_environment(environment, root) == {"KEPT": "yes"}


def test_a_different_virtual_environment_stays_active(tmp_path):
    other = tmp_path / "other"
    environment = {"VIRTUAL_ENV": str(other), "VIRTUAL_ENV_PROMPT": "other"}
    assert without_virtual_environment(environment, tmp_path / "venv") == environment


def test_the_activation_variable_may_be_written_differently_from_our_prefix(tmp_path):
    root = tmp_path / "venv"
    written = f"{tmp_path}{os.sep}.{os.sep}other{os.sep}..{os.sep}venv"  # the same folder
    assert without_virtual_environment({"VIRTUAL_ENV": written}, root) == {}


@windows_only
def test_on_windows_case_and_slashes_do_not_matter(tmp_path):
    root = tmp_path / "venv"
    written = str(root).upper().replace("\\", "/")
    environment = {"VIRTUAL_ENV": written, "PATH": search_path(root / "Scripts", tmp_path / "bin")}
    assert without_virtual_environment(environment, root) == {"PATH": str(tmp_path / "bin")}


# ------------------------------------------------------------------------ the search path

def test_search_path_entries_inside_our_virtual_environment_are_removed_and_the_rest_keep_their_order(tmp_path):
    root = tmp_path / "venv"
    environment = {
        "PATH": search_path(
            root / "Lib" / "site-packages" / "PySide6",  # the Qt package puts itself on the path
            root / "Scripts",
            tmp_path / "first",
            root,
            tmp_path / "second",
        )
    }
    result = without_virtual_environment(environment, root)
    assert result["PATH"] == search_path(tmp_path / "first", tmp_path / "second")


def test_a_folder_that_only_starts_with_the_same_letters_is_kept(tmp_path):
    root = tmp_path / "venv"
    sibling = tmp_path / "venv2" / "Scripts"
    environment = {"PATH": search_path(root / "Scripts", sibling)}
    assert without_virtual_environment(environment, root)["PATH"] == str(sibling)


def test_empty_search_path_entries_are_left_alone(tmp_path):
    root = tmp_path / "venv"
    environment = {"PATH": os.pathsep.join(["", str(tmp_path / "first"), ""])}
    assert without_virtual_environment(environment, root)["PATH"] == environment["PATH"]


def test_an_empty_entry_is_not_taken_for_the_current_folder_even_when_that_is_inside_the_environment(
    tmp_path, monkeypatch
):
    root = tmp_path / "venv"
    root.mkdir()
    monkeypatch.chdir(root)
    environment = {"PATH": os.pathsep.join(["", str(tmp_path / "first")])}
    assert without_virtual_environment(environment, root)["PATH"] == environment["PATH"]


def test_a_missing_search_path_is_fine(tmp_path):
    assert without_virtual_environment({"KEPT": "yes"}, tmp_path / "venv") == {"KEPT": "yes"}


@windows_only
def test_on_windows_search_path_entries_match_whatever_their_case_or_slashes(tmp_path):
    root = tmp_path / "venv"
    written = str(root / "Scripts").upper().replace("\\", "/")
    environment = {"PATH": search_path(written, tmp_path / "bin")}
    assert without_virtual_environment(environment, root)["PATH"] == str(tmp_path / "bin")


# -------------------------------------------------------------------- everything else

def test_without_a_virtual_environment_of_our_own_nothing_changes(tmp_path):
    environment = {"VIRTUAL_ENV": str(tmp_path / "venv"), "PATH": search_path(tmp_path / "venv" / "Scripts")}
    result = without_virtual_environment(environment, None)
    assert result == environment
    assert result is not environment


def test_the_environment_that_was_given_is_not_modified(tmp_path):
    root = tmp_path / "venv"
    environment = {"VIRTUAL_ENV": str(root), "PATH": search_path(root / "Scripts", tmp_path / "bin")}
    before = dict(environment)
    without_virtual_environment(environment, root)
    assert environment == before


def test_every_other_variable_is_kept_unchanged(tmp_path):
    root = tmp_path / "venv"
    environment = {"VIRTUAL_ENV": str(root), "HOME": "h", "PYTHONPATH": "p", "TEMP": "t"}
    assert without_virtual_environment(environment, root) == {"HOME": "h", "PYTHONPATH": "p", "TEMP": "t"}


# ------------------------------------------------------ our own virtual environment

def test_outside_a_virtual_environment_there_is_none_of_our_own(monkeypatch):
    monkeypatch.setattr(sys, "prefix", "same")
    monkeypatch.setattr(sys, "base_prefix", "same")
    assert own_virtual_environment() is None


def test_inside_a_virtual_environment_it_is_the_prefix(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "prefix", str(tmp_path / "venv"))
    monkeypatch.setattr(sys, "base_prefix", str(tmp_path / "base"))
    assert own_virtual_environment() == tmp_path / "venv"


def test_the_run_environment_is_the_real_environment_without_our_virtual_environment(monkeypatch, tmp_path):
    root = tmp_path / "venv"
    monkeypatch.setattr(run_environment, "own_virtual_environment", lambda: root)
    monkeypatch.setenv("VIRTUAL_ENV", str(root))
    monkeypatch.setenv("PATH", search_path(root / "Scripts", tmp_path / "bin"))
    monkeypatch.setenv("MATHDOER_TEST_KEPT", "yes")
    result = create_run_environment()
    assert "VIRTUAL_ENV" not in result
    assert result["PATH"] == str(tmp_path / "bin")
    assert result["MATHDOER_TEST_KEPT"] == "yes"
    assert os.environ["VIRTUAL_ENV"] == str(root)  # the real environment is untouched
    assert isinstance(result, dict)
    assert Path(result["PATH"]).name == "bin"
