"""Shared fixtures: start real worker processes and record what they report."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")  # before Qt is imported anywhere

import sys
import time
from pathlib import Path

import pytest

from mathdoer.languages.python import PYTHON
from mathdoer.registry import shipped_registry_path
from mathdoer.running import OutputText, RunFinished, RunSettings


class RunRecorder:
    """Collects a run's events as they arrive so tests can look at them in order."""

    def __init__(self, run):
        self.run = run
        self.events = []

    def update(self):
        self.events.extend(self.run.poll())

    def wait_for_text(self, text, timeout=20.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self.update()
            if text in self.combined_text:
                return self
            time.sleep(0.01)
        pytest.fail(f"never saw {text!r}; saw {self.combined_text!r}")

    def finish(self, timeout=30.0):
        if not self.run.wait(timeout):
            self.run.cancel()
            pytest.fail(f"the run did not finish; saw {self.combined_text!r}")
        self.update()
        return self

    @property
    def combined_text(self):
        return "".join(event.text for event in self.events if isinstance(event, OutputText))

    @property
    def output_text(self):
        return "".join(
            event.text for event in self.events if isinstance(event, OutputText) and not event.is_error
        )

    @property
    def error_text(self):
        return "".join(
            event.text for event in self.events if isinstance(event, OutputText) and event.is_error
        )

    @property
    def finished_event(self):
        finished = [event for event in self.events if isinstance(event, RunFinished)]
        assert len(finished) == 1, f"expected exactly one RunFinished, got {finished}"
        return finished[0]

    @property
    def outcome(self):
        return self.finished_event.outcome

    @property
    def exit_code(self):
        return self.finished_event.exit_code


@pytest.fixture
def startup_value_of():
    """The value the default Python startup file gives a registry entry: a whole number
    written without a point or exponent is an int, anything else a float."""

    def value_of(entry):
        return int(entry.value_text) if entry.value_text.isdigit() else float(entry.value)

    return value_of


@pytest.fixture
def make_python_run_settings(tmp_path):
    """Settings for Python runs in a temporary folder, with a startup file of the given text
    (None leaves the startup file missing)."""

    def make(
        startup_text="",
        working_directory=None,
        interpreter_path=None,
        registry_path=None,
        settings_text=None,
    ):
        startup_path = tmp_path / PYTHON.startup_file_name
        if startup_text is not None:
            startup_path.write_text(startup_text, encoding="utf-8")
        settings_path = tmp_path / PYTHON.settings_file_name
        if settings_text is not None:
            settings_path.write_text(settings_text, encoding="utf-8")
        return RunSettings(
            language=PYTHON,
            default_interpreter_path=interpreter_path or Path(sys.executable),
            settings_path=settings_path,
            startup_path=startup_path,
            registry_path=registry_path or shipped_registry_path(),
            working_directory=working_directory or tmp_path,
        )

    return make


@pytest.fixture
def make_fake_interpreter(tmp_path):
    """A file that counts as an executable program, without being a real interpreter."""

    def make(name="fake_interpreter", directory=None):
        directory = Path(directory or tmp_path)
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / (name + (".exe" if sys.platform == "win32" else ""))
        path.write_text("", encoding="utf-8")
        path.chmod(0o755)
        return path

    return make


@pytest.fixture
def make_wrapper_interpreter(tmp_path):
    """A program that runs the real Python with the variable MATHDOER_TEST_WRAPPER set to
    "yes", so a test can tell that a run used it. The fixture returns the program's path."""

    def make(name="wrapper_interpreter"):
        if sys.platform == "win32":
            path = tmp_path / f"{name}.cmd"
            path.write_text(f'@set MATHDOER_TEST_WRAPPER=yes\r\n@"{sys.executable}" %*\r\n', encoding="ascii")
        else:
            path = tmp_path / name
            path.write_text(f'#!/bin/sh\nMATHDOER_TEST_WRAPPER=yes exec "{sys.executable}" "$@"\n')
            path.chmod(0o755)
        return path

    return make


class FakeClock:
    """A clock the test moves by hand, so spinner and timer text is deterministic."""

    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


@pytest.fixture
def fake_clock():
    return FakeClock()


@pytest.fixture
def make_window(qtbot, make_python_run_settings, fake_clock):
    """Show a main window, ready for key presses. Options for the run settings
    (working_directory, interpreter_path, registry_path, settings_text) and the startup file
    text are passed to make_python_run_settings; the rest go to MainWindow."""
    from mathdoer.interface.main_window import MainWindow

    def make(startup_text="", **options):
        settings_options = {
            name: options.pop(name)
            for name in ("working_directory", "interpreter_path", "registry_path", "settings_text")
            if name in options
        }
        settings = make_python_run_settings(startup_text=startup_text, **settings_options)
        window = MainWindow(settings, clock=fake_clock, **options)
        qtbot.addWidget(window)
        window.resize(900, 700)
        window.show()
        window.activateWindow()
        # A window-level shortcut only fires once the window is active, and the
        # offscreen platform finishes activating a moment after show().
        qtbot.waitUntil(window.isActiveWindow, timeout=5000)
        return window

    return make


@pytest.fixture
def window(make_window):
    return make_window()


@pytest.fixture
def start_python_run(make_python_run_settings):
    """Start a Python run without waiting for it. Runs still going at teardown are cancelled."""
    recorders = []

    def start(prompt_text, **settings_options):
        recorder = RunRecorder(make_python_run_settings(**settings_options).start(prompt_text))
        recorders.append(recorder)
        return recorder

    yield start
    for recorder in recorders:
        recorder.run.cancel()


@pytest.fixture
def run_python(start_python_run):
    """Run a prompt to the end and return the recorded result."""

    def run(prompt_text, **options):
        return start_python_run(prompt_text, **options).finish()

    return run
