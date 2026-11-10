"""Running a prompt in a separate process and streaming what it reports.

Every language provides a worker program, started with Language.build_worker_command.
The worker and this module speak a small protocol:

* The worker's standard input carries one line of JSON, the request, with the keys
  REQUEST_PROMPT_TEXT_KEY and REQUEST_STARTUP_PATH_KEY. Standard input is then closed.
* The worker's standard output carries one JSON object per line, each with
  MESSAGE_KIND_KEY (MESSAGE_KIND_OUTPUT or MESSAGE_KIND_ERROR) and MESSAGE_TEXT_KEY.
  Messages arrive in the order the code wrote them, whichever stream it wrote to.
* Anything else the process writes to standard error, or to the protocol pipe in a form
  that is not a message, is shown as error text so nothing is lost.
* The exit code says how the run ended: EXIT_CODE_COMPLETED, EXIT_CODE_PROMPT_ERROR
  (the prompt failed) or EXIT_CODE_STARTUP_ERROR (the startup file failed). The worker has
  already reported the error as text. Any other exit code means the worker crashed.
"""
import codecs
import json
import os
import queue
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from mathdoer.languages import Language
from mathdoer.run_environment import SEARCH_PATH_VARIABLE, create_run_environment
from mathdoer.user_settings import UserSettingsError, resolve_interpreter

EXIT_CODE_COMPLETED = 0
EXIT_CODE_PROMPT_ERROR = 1
EXIT_CODE_STARTUP_ERROR = 2
MESSAGE_KIND_KEY = "kind"
MESSAGE_TEXT_KEY = "text"
MESSAGE_KIND_OUTPUT = "output"
MESSAGE_KIND_ERROR = "error"
REQUEST_PROMPT_TEXT_KEY = "prompt_text"
REQUEST_STARTUP_PATH_KEY = "startup_path"

REGISTRY_ENVIRONMENT_VARIABLE = "MATHDOER_REGISTRY_FILE"

# After the worker exits, how long to wait for its output to drain. A child process that
# the prompt started can keep the pipes open long after the worker is gone.
OUTPUT_DRAIN_SECONDS = 2.0
STRAY_READ_SIZE = 65536


class RunOutcome(Enum):
    COMPLETED = "completed"
    PROMPT_ERROR = "prompt_error"
    STARTUP_ERROR = "startup_error"
    CANCELLED = "cancelled"
    CRASHED = "crashed"


@dataclass(frozen=True)
class OutputText:
    text: str
    is_error: bool


@dataclass(frozen=True)
class RunFinished:
    outcome: RunOutcome
    exit_code: int | None


RunEvent = OutputText | RunFinished

_OUTCOMES_BY_EXIT_CODE = {
    EXIT_CODE_COMPLETED: RunOutcome.COMPLETED,
    EXIT_CODE_PROMPT_ERROR: RunOutcome.PROMPT_ERROR,
    EXIT_CODE_STARTUP_ERROR: RunOutcome.STARTUP_ERROR,
}


@dataclass(frozen=True)
class RunSettings:
    """Everything about a run except the prompt."""

    language: Language
    # Runs use this interpreter unless the settings file names another. None when there is none:
    # a run then needs the settings file to name one.
    default_interpreter_path: Path | None
    settings_path: Path
    startup_path: Path
    registry_path: Path
    working_directory: Path

    def start(self, prompt_text: str) -> "Run":
        """Read the settings file, then start a run. A problem in the settings file raises
        nothing: the run has already ended, with the explanation as error text."""
        try:
            interpreter_path = resolve_interpreter(
                self.settings_path,
                self.default_interpreter_path,
                create_run_environment().get(SEARCH_PATH_VARIABLE),
            )
        except UserSettingsError as error:
            return Run.failed_to_start(str(error))
        return Run(
            language=self.language,
            interpreter_path=interpreter_path,
            prompt_text=prompt_text,
            startup_path=self.startup_path,
            registry_path=self.registry_path,
            working_directory=self.working_directory,
        )


class Run:
    """One run of a prompt. Starts immediately; poll() returns the events so far."""

    def __init__(
        self,
        *,
        language: Language,
        interpreter_path: Path,
        prompt_text: str,
        startup_path: Path,
        registry_path: Path,
        working_directory: Path,
    ):
        self._set_up_state()
        command = language.build_worker_command(Path(interpreter_path))
        environment = {**create_run_environment(), REGISTRY_ENVIRONMENT_VARIABLE: str(registry_path)}
        try:
            self._process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=working_directory,
                env=environment,
                **_platform_process_options(),
            )
        except OSError as error:
            self._fail_to_start(f"Cannot start {interpreter_path}: {error}")
            return

        request = json.dumps(
            {REQUEST_PROMPT_TEXT_KEY: prompt_text, REQUEST_STARTUP_PATH_KEY: str(startup_path)}
        )
        self._reader_threads = [
            threading.Thread(target=self._read_protocol_messages, daemon=True),
            threading.Thread(target=self._read_stray_text, daemon=True),
        ]
        threads = [
            threading.Thread(target=self._send_request, args=(request,), daemon=True),
            *self._reader_threads,
            threading.Thread(target=self._wait_for_exit, daemon=True),
        ]
        for thread in threads:
            thread.start()

    @classmethod
    def failed_to_start(cls, explanation: str) -> "Run":
        """A run that has already ended because it could not be started."""
        run = cls.__new__(cls)
        run._set_up_state()
        run._fail_to_start(explanation)
        return run

    @property
    def is_finished(self) -> bool:
        return self._finished.is_set()

    def poll(self) -> list[RunEvent]:
        """Return the events that arrived since the last call, without waiting."""
        events = []
        while True:
            try:
                events.append(self._events.get_nowait())
            except queue.Empty:
                return events

    def wait(self, timeout: float | None = None) -> bool:
        """Wait until the run has finished. Returns whether it has."""
        return self._finished.wait(timeout)

    def cancel(self) -> None:
        """Stop the run and everything it started. Does nothing once the run has ended."""
        with self._cancel_lock:
            if self._process is None or self._cancelled or self._process.poll() is not None:
                return
            self._cancelled = True
        _kill_process_tree(self._process)

    def _set_up_state(self) -> None:
        self._events: queue.Queue[RunEvent] = queue.Queue()
        self._finished = threading.Event()
        self._cancel_lock = threading.Lock()
        self._cancelled = False
        self._process = None

    def _fail_to_start(self, explanation: str) -> None:
        self._events.put(OutputText(explanation + "\n", is_error=True))
        self._finish(RunOutcome.CRASHED, None)

    def _finish(self, outcome: RunOutcome, exit_code: int | None) -> None:
        self._events.put(RunFinished(outcome, exit_code))
        self._finished.set()

    def _send_request(self, request: str) -> None:
        try:
            self._process.stdin.write(request.encode("ascii") + b"\n")
            self._process.stdin.close()
        except OSError:
            pass  # the worker is already gone; its exit code will say what happened

    def _read_protocol_messages(self) -> None:
        try:
            for line in iter(self._process.stdout.readline, b""):
                self._events.put(_parse_protocol_line(line))
        except (OSError, ValueError):
            pass

    def _read_stray_text(self) -> None:
        decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        try:
            while chunk := self._process.stderr.read1(STRAY_READ_SIZE):
                text = decoder.decode(chunk)
                if text:
                    self._events.put(OutputText(text, is_error=True))
        except (OSError, ValueError):
            return
        text = decoder.decode(b"", final=True)
        if text:
            self._events.put(OutputText(text, is_error=True))

    def _wait_for_exit(self) -> None:
        exit_code = self._process.wait()
        deadline = time.monotonic() + OUTPUT_DRAIN_SECONDS
        for thread in self._reader_threads:
            thread.join(max(0.0, deadline - time.monotonic()))
        with self._cancel_lock:
            cancelled = self._cancelled
        if cancelled:
            outcome = RunOutcome.CANCELLED
        else:
            outcome = _OUTCOMES_BY_EXIT_CODE.get(exit_code, RunOutcome.CRASHED)
        self._finish(outcome, exit_code)


def _parse_protocol_line(line: bytes) -> OutputText:
    try:
        message = json.loads(line)
    except ValueError:
        message = None
    if (
        isinstance(message, dict)
        and message.get(MESSAGE_KIND_KEY) in (MESSAGE_KIND_OUTPUT, MESSAGE_KIND_ERROR)
        and isinstance(message.get(MESSAGE_TEXT_KEY), str)
    ):
        return OutputText(message[MESSAGE_TEXT_KEY], message[MESSAGE_KIND_KEY] == MESSAGE_KIND_ERROR)
    return OutputText(line.decode("utf-8", errors="replace"), is_error=True)


def _platform_process_options() -> dict:
    if sys.platform == "win32":
        return {"creationflags": subprocess.CREATE_NO_WINDOW}
    return {"start_new_session": True}


def _kill_process_tree(process: subprocess.Popen) -> None:
    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(process.pid)],
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    try:
        process.kill()
    except OSError:
        pass
