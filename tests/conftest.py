"""Shared fixtures: start real worker processes and record what they report."""
import sys
import time
from pathlib import Path

import pytest

from mathdoer.languages.python import PYTHON
from mathdoer.registry import shipped_registry_path
from mathdoer.running import OutputText, Run, RunFinished


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
def start_python_run(tmp_path):
    """Start a Python run without waiting for it. Runs still going at teardown are cancelled."""
    recorders = []

    def start(
        prompt_text,
        startup_text="",
        working_directory=None,
        interpreter_path=None,
        registry_path=None,
    ):
        startup_path = tmp_path / PYTHON.startup_file_name
        if startup_text is not None:
            startup_path.write_text(startup_text, encoding="utf-8")
        run = Run(
            language=PYTHON,
            interpreter_path=interpreter_path or Path(sys.executable),
            prompt_text=prompt_text,
            startup_path=startup_path,
            registry_path=registry_path or shipped_registry_path(),
            working_directory=working_directory or tmp_path,
        )
        recorder = RunRecorder(run)
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
