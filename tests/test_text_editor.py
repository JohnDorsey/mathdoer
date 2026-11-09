"""Tests for opening a file in the system's editor for text files."""
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

from mathdoer import text_editor
from mathdoer.text_editor import build_command_line, open_in_text_editor, windows_text_editor_command

windows_only = pytest.mark.skipif(sys.platform != "win32", reason="asks Windows")

PATH = Path(r"C:\my docs\startup_python.py")


@pytest.mark.parametrize(
    "template, expected",
    [
        # a template that already quotes the placeholder
        (r'"C:\Program Files\npp\notepad++.exe" "%1"',
         r'"C:\Program Files\npp\notepad++.exe" "C:\my docs\startup_python.py"'),
        # one that does not: the path is quoted for it
        (r"C:\Windows\system32\NOTEPAD.EXE %1",
         r'C:\Windows\system32\NOTEPAD.EXE "C:\my docs\startup_python.py"'),
        (r'"C:\app.exe" %L', r'"C:\app.exe" "C:\my docs\startup_python.py"'),
        # placeholders that stand for other arguments are dropped
        (r'"C:\app.exe" "%1" %*', r'"C:\app.exe" "C:\my docs\startup_python.py"'),
        (r'"C:\app.exe" "%1" %2 %3', r'"C:\app.exe" "C:\my docs\startup_python.py"'),
        # no placeholder at all: the path is added at the end
        (r'"C:\app.exe"', r'"C:\app.exe" "C:\my docs\startup_python.py"'),
        (r"C:\app.exe", r'C:\app.exe "C:\my docs\startup_python.py"'),
        # the placeholder in the middle of the line
        (r'"C:\app.exe" /open "%1" /readonly',
         r'"C:\app.exe" /open "C:\my docs\startup_python.py" /readonly'),
    ],
)
def test_the_path_goes_where_the_template_puts_it(template, expected):
    assert build_command_line(template, PATH) == expected


def test_environment_variables_in_the_template_are_expanded(monkeypatch):
    monkeypatch.setenv("MATHDOER_TEST_ROOT", r"C:\Tools")
    assert build_command_line(r"%MATHDOER_TEST_ROOT%\edit.exe %1", PATH) == (
        r'C:\Tools\edit.exe "C:\my docs\startup_python.py"'
    )


@windows_only
def test_windows_knows_an_editor_for_text_files_and_it_exists():
    template = windows_text_editor_command()
    assert "%1" in template or "%L" in template
    executable = shlex.split(template, posix=False)[0].strip('"')
    assert Path(executable).exists(), executable


@pytest.fixture
def launches(monkeypatch):
    launched = []
    monkeypatch.setattr(subprocess, "Popen", lambda *args, **kwargs: launched.append(args[0]))
    return launched


def test_windows_launches_the_editor_the_system_reports(monkeypatch, launches):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(text_editor, "windows_text_editor_command", lambda: r'"C:\e.exe" "%1"')
    open_in_text_editor(PATH)
    assert launches == [r'"C:\e.exe" "C:\my docs\startup_python.py"']


def test_windows_falls_back_to_notepad_when_nothing_is_associated(monkeypatch, launches):
    monkeypatch.setattr(sys, "platform", "win32")

    def no_association():
        raise OSError("No application is associated")

    monkeypatch.setattr(text_editor, "windows_text_editor_command", no_association)
    open_in_text_editor(PATH)
    assert launches == [r'notepad.exe "C:\my docs\startup_python.py"']


def test_macos_opens_the_file_in_the_default_text_editor(monkeypatch, launches):
    monkeypatch.setattr(sys, "platform", "darwin")
    open_in_text_editor(PATH)
    assert launches == [["open", "-t", str(PATH)]]


def test_linux_hands_the_file_to_the_desktop(monkeypatch, launches):
    monkeypatch.setattr(sys, "platform", "linux")
    open_in_text_editor(PATH)
    assert launches == [["xdg-open", str(PATH)]]


def test_a_failure_to_launch_is_reported_to_the_caller(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")

    def cannot_launch(*args, **kwargs):
        raise FileNotFoundError("xdg-open")

    monkeypatch.setattr(subprocess, "Popen", cannot_launch)
    with pytest.raises(FileNotFoundError):
        open_in_text_editor(PATH)
