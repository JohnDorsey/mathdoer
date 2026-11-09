"""Tests for running a prompt in a separate process with the Python worker."""
import importlib.util
import math
import os
import signal
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest

from mathdoer.languages.python import PYTHON
from mathdoer.registry import load_registry
from mathdoer.running import (
    EXIT_CODE_COMPLETED,
    EXIT_CODE_PROMPT_ERROR,
    EXIT_CODE_STARTUP_ERROR,
    MESSAGE_KIND_ERROR,
    MESSAGE_KIND_KEY,
    MESSAGE_KIND_OUTPUT,
    MESSAGE_TEXT_KEY,
    REQUEST_PROMPT_TEXT_KEY,
    REQUEST_STARTUP_PATH_KEY,
    RunOutcome,
)

windows_only = pytest.mark.skipif(sys.platform != "win32", reason="uses Windows process tools")


def prompt(text):
    return textwrap.dedent(text).strip("\n")


def process_is_running(process_identifier):
    listing = subprocess.run(
        ["tasklist", "/FI", f"PID eq {process_identifier}", "/NH", "/FO", "CSV"],
        capture_output=True, text=True,
    ).stdout
    return f'"{process_identifier}"' in listing


def terminate_if_running(process_identifier):
    try:
        os.kill(process_identifier, signal.SIGTERM)
    except OSError:
        pass


# ------------------------------------------------- the worker and the app agree

def test_the_worker_and_the_app_agree_on_the_protocol():
    worker_path = Path(PYTHON.build_worker_command(Path("python"))[3])
    spec = importlib.util.spec_from_file_location("worker_under_test", worker_path)
    worker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(worker)
    for name, expected in {
        "EXIT_CODE_COMPLETED": EXIT_CODE_COMPLETED,
        "EXIT_CODE_PROMPT_ERROR": EXIT_CODE_PROMPT_ERROR,
        "EXIT_CODE_STARTUP_ERROR": EXIT_CODE_STARTUP_ERROR,
        "MESSAGE_KIND_OUTPUT": MESSAGE_KIND_OUTPUT,
        "MESSAGE_KIND_ERROR": MESSAGE_KIND_ERROR,
        "MESSAGE_KIND_KEY": MESSAGE_KIND_KEY,
        "MESSAGE_TEXT_KEY": MESSAGE_TEXT_KEY,
        "REQUEST_PROMPT_TEXT_KEY": REQUEST_PROMPT_TEXT_KEY,
        "REQUEST_STARTUP_PATH_KEY": REQUEST_STARTUP_PATH_KEY,
    }.items():
        assert getattr(worker, name) == expected, name


def test_the_exit_codes_are_distinct():
    assert len({EXIT_CODE_COMPLETED, EXIT_CODE_PROMPT_ERROR, EXIT_CODE_STARTUP_ERROR}) == 3


# ------------------------------------------------------------ output and values

def test_print_output_is_reported(run_python):
    result = run_python('print("hello")')
    assert result.output_text == "hello\n"
    assert result.error_text == ""
    assert result.outcome is RunOutcome.COMPLETED
    assert result.exit_code == EXIT_CODE_COMPLETED


def test_partial_lines_are_reported_without_a_newline(run_python):
    assert run_python('print("a", end="")').output_text == "a"


def test_the_value_of_the_last_expression_is_shown(run_python):
    assert run_python("1 + 1").output_text == "2\n"


def test_the_last_expression_is_shown_with_repr_like_the_python_repl(run_python):
    assert run_python('"hi"').output_text == "'hi'\n"


def test_only_the_last_expression_is_shown(run_python):
    assert run_python("1\n2").output_text == "2\n"


def test_an_expression_that_is_not_last_is_not_shown(run_python):
    assert run_python("1\nx = 2").output_text == ""


def test_a_last_expression_with_no_value_shows_nothing(run_python):
    assert run_python("None").output_text == ""
    assert run_python("print('once')").output_text == "once\n"


def test_an_empty_prompt_does_nothing(run_python):
    result = run_python("")
    assert result.output_text == "" and result.outcome is RunOutcome.COMPLETED


def test_multi_line_code_with_functions_and_a_final_call(run_python):
    code = prompt(
        """
        def square(number):
            return number * number

        values = [square(n) for n in range(4)]
        sum(values)
        """
    )
    assert run_python(code).output_text == "14\n"


def test_the_prompt_runs_as_the_main_module(run_python):
    code = prompt(
        """
        if __name__ == "__main__":
            print("main")
        """
    )
    assert run_python(code).output_text == "main\n"


def test_nothing_is_remembered_between_runs(run_python):
    assert run_python("x = 5").outcome is RunOutcome.COMPLETED
    second = run_python("x")
    assert second.outcome is RunOutcome.PROMPT_ERROR
    assert "NameError" in second.error_text


def test_error_text_goes_to_the_error_stream(run_python):
    result = run_python("import sys\nprint('oops', file=sys.stderr)")
    assert result.error_text == "oops\n"
    assert result.output_text == ""


def test_unicode_survives_the_trip(run_python):
    assert run_python('print("héllo ✓ 😀")').output_text == "héllo ✓ 😀\n"


def test_a_lone_surrogate_does_not_break_the_stream(run_python):
    result = run_python(r'print("\udc80")')
    assert result.output_text == "\udc80\n"
    assert result.outcome is RunOutcome.COMPLETED


def test_a_hundred_thousand_lines_arrive_complete_and_in_order(run_python):
    result = run_python("for number in range(100000):\n    print(number)")
    assert result.output_text == "".join(f"{number}\n" for number in range(100000))


# ------------------------------------------------------------------------ errors

def test_a_runtime_error_is_a_trimmed_traceback_with_prompt_line_numbers(run_python):
    result = run_python("x = 1\ny = 2\nz = x / 0")
    assert result.outcome is RunOutcome.PROMPT_ERROR
    assert result.exit_code == EXIT_CODE_PROMPT_ERROR
    assert 'File "<prompt>", line 3, in <module>' in result.error_text
    assert "z = x / 0" in result.error_text
    assert "ZeroDivisionError: division by zero" in result.error_text
    assert result.error_text.startswith("Traceback (most recent call last):")
    assert "worker" not in result.error_text


def test_an_error_in_the_last_expression_is_reported_the_same_way(run_python):
    result = run_python("1/0")
    assert 'File "<prompt>", line 1, in <module>' in result.error_text
    assert "worker" not in result.error_text


def test_an_error_inside_a_function_shows_each_prompt_frame(run_python):
    code = prompt(
        """
        def broken():
            return 1 / 0

        def caller():
            return broken()

        caller()
        """
    )
    text = run_python(code).error_text
    assert 'line 2, in broken' in text and 'line 5, in caller' in text and 'line 7, in <module>' in text
    assert "worker" not in text


def test_chained_exceptions_are_shown_in_full(run_python):
    code = prompt(
        """
        try:
            1 / 0
        except ZeroDivisionError as error:
            raise ValueError("bad") from error
        """
    )
    text = run_python(code).error_text
    assert "ZeroDivisionError" in text and "ValueError: bad" in text
    assert "direct cause" in text
    assert "worker" not in text


def test_a_syntax_error_is_reported_with_the_prompt_line(run_python):
    result = run_python("x = 1\n1 +")
    assert result.outcome is RunOutcome.PROMPT_ERROR
    assert 'File "<prompt>", line 2' in result.error_text
    assert "SyntaxError" in result.error_text
    assert "worker" not in result.error_text


def test_output_before_an_error_is_kept_and_comes_first(run_python):
    result = run_python("print('before')\n1/0")
    assert result.combined_text.startswith("before\n")
    assert result.combined_text.index("before") < result.combined_text.index("ZeroDivisionError")
    assert result.output_text == "before\n"


def test_input_fails_with_a_clear_message(run_python):
    result = run_python("input('name? ')")
    assert result.outcome is RunOutcome.PROMPT_ERROR
    assert "input() is not supported" in result.error_text


def test_reading_standard_input_gives_nothing_instead_of_hanging(run_python):
    assert run_python("import sys\nprint(repr(sys.stdin.read()))").output_text == "''\n"


def test_exit_stops_the_prompt_quietly(run_python):
    result = run_python("print(1)\nexit()\nprint(2)")
    assert result.output_text == "1\n"
    assert result.outcome is RunOutcome.COMPLETED


def test_exit_with_a_message_shows_the_message_as_an_error(run_python):
    result = run_python("import sys\nsys.exit('bye')")
    assert result.error_text == "bye\n"
    assert result.outcome is RunOutcome.COMPLETED


# ------------------------------------------------------------------ startup file

def test_the_startup_file_runs_first_in_the_same_namespace(run_python):
    assert run_python("LIMIT * 2", startup_text="LIMIT = 7").output_text == "14\n"


def test_a_startup_error_is_labelled_and_the_prompt_is_not_run(run_python):
    result = run_python("print('ran')", startup_text="LIMIT = 1 / 0")
    assert result.outcome is RunOutcome.STARTUP_ERROR
    assert result.exit_code == EXIT_CODE_STARTUP_ERROR
    assert result.output_text == ""
    assert "startup file" in result.error_text.lower()
    assert "startup_python.py" in result.error_text
    assert "ZeroDivisionError" in result.error_text
    assert "worker" not in result.error_text


def test_a_startup_syntax_error_is_labelled_too(run_python):
    result = run_python("print('ran')", startup_text="def (")
    assert result.outcome is RunOutcome.STARTUP_ERROR
    assert "SyntaxError" in result.error_text
    assert result.output_text == ""


def test_a_missing_startup_file_is_a_startup_error(run_python):
    result = run_python("print('ran')", startup_text=None)
    assert result.outcome is RunOutcome.STARTUP_ERROR
    assert "startup file" in result.error_text.lower()
    assert result.output_text == ""


# ------------------------------------------------------- environment and imports

def test_the_prompt_runs_in_the_working_directory(run_python, tmp_path):
    working_directory = tmp_path / "work"
    working_directory.mkdir()
    result = run_python("import os\nprint(os.getcwd())", working_directory=working_directory)
    assert Path(result.output_text.strip()).resolve() == working_directory.resolve()


def test_modules_in_the_working_directory_can_be_imported(run_python, tmp_path):
    (tmp_path / "mymodule.py").write_text("VALUE = 3\n", encoding="utf-8")
    assert run_python("import mymodule\nmymodule.VALUE").output_text == "3\n"


def test_a_module_in_the_working_directory_does_not_shadow_the_standard_library(run_python, tmp_path):
    (tmp_path / "math.py").write_text("raise RuntimeError('shadowed')\n", encoding="utf-8")
    assert run_python("import math\nmath.pi").output_text == f"{math.pi!r}\n"


def test_the_workers_own_folder_is_not_importable(run_python):
    result = run_python("import worker")
    assert result.outcome is RunOutcome.PROMPT_ERROR
    assert "ModuleNotFoundError" in result.error_text


def test_the_registry_location_is_passed_in_the_environment(run_python):
    from mathdoer.registry import shipped_registry_path

    result = run_python("import os\nprint(os.environ['MATHDOER_REGISTRY_FILE'])")
    assert result.output_text == f"{shipped_registry_path()}\n"


# ------------------------------------------------ stray output and child processes

def test_text_written_straight_to_the_operating_system_stream_is_shown_not_lost(run_python):
    result = run_python('import os\nos.write(1, b"stray\\n")\nprint("after")')
    assert "stray" in result.combined_text
    assert result.output_text == "after\n"
    assert result.outcome is RunOutcome.COMPLETED


def test_a_child_process_does_not_corrupt_the_output(run_python):
    code = prompt(
        """
        import subprocess, sys
        subprocess.run([sys.executable, "-c", "print('child says hi')"])
        print("after")
        """
    )
    result = run_python(code)
    assert "child says hi" in result.combined_text
    assert result.output_text == "after\n"
    assert result.outcome is RunOutcome.COMPLETED


def test_a_run_finishes_even_if_a_child_process_keeps_running(start_python_run):
    code = prompt(
        """
        import subprocess, sys
        child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
        print(child.pid)
        """
    )
    recorder = start_python_run(code)
    started = time.monotonic()
    recorder.finish(timeout=20)
    try:
        assert recorder.outcome is RunOutcome.COMPLETED
        assert time.monotonic() - started < 10
    finally:
        terminate_if_running(int(recorder.output_text.strip()))


# ------------------------------------------------------------ streaming and cancel

def test_output_is_streamed_while_the_run_is_still_going(start_python_run):
    recorder = start_python_run("import time\nprint('first', flush=True)\ntime.sleep(60)\nprint('second')")
    recorder.wait_for_text("first")
    assert not recorder.run.is_finished
    recorder.run.cancel()
    recorder.finish(timeout=15)


def test_cancel_stops_the_run_quickly_and_keeps_the_output_so_far(start_python_run):
    recorder = start_python_run("import time\nprint('started', flush=True)\ntime.sleep(120)")
    recorder.wait_for_text("started")
    cancelled_at = time.monotonic()
    recorder.run.cancel()
    recorder.finish(timeout=15)
    assert recorder.outcome is RunOutcome.CANCELLED
    assert time.monotonic() - cancelled_at < 10
    assert recorder.output_text == "started\n"


def test_cancel_works_on_a_busy_loop(start_python_run):
    recorder = start_python_run("print('busy', flush=True)\nwhile True:\n    pass")
    recorder.wait_for_text("busy")
    recorder.run.cancel()
    recorder.finish(timeout=15)
    assert recorder.outcome is RunOutcome.CANCELLED


def test_cancelling_twice_is_harmless(start_python_run):
    recorder = start_python_run("import time\nprint('started', flush=True)\ntime.sleep(120)")
    recorder.wait_for_text("started")
    recorder.run.cancel()
    recorder.run.cancel()
    recorder.finish(timeout=15)
    assert recorder.outcome is RunOutcome.CANCELLED


def test_cancelling_a_finished_run_changes_nothing(run_python):
    result = run_python("1")
    result.run.cancel()
    result.update()
    assert result.outcome is RunOutcome.COMPLETED


@windows_only
def test_cancel_also_stops_processes_the_prompt_started(start_python_run):
    code = prompt(
        """
        import subprocess, sys, time
        child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"])
        print(child.pid, flush=True)
        time.sleep(120)
        """
    )
    recorder = start_python_run(code)
    recorder.wait_for_text("\n")
    child_identifier = int(recorder.output_text.strip())
    assert process_is_running(child_identifier)
    recorder.run.cancel()
    recorder.finish(timeout=15)
    try:
        deadline = time.monotonic() + 10
        while process_is_running(child_identifier) and time.monotonic() < deadline:
            time.sleep(0.1)
        assert not process_is_running(child_identifier)
    finally:
        terminate_if_running(child_identifier)


# ---------------------------------------------------------------------- crashes

def test_a_worker_that_dies_unexpectedly_is_a_crash_with_its_exit_code(run_python):
    result = run_python("import os\nprint('hi', flush=True)\nos._exit(7)")
    assert result.outcome is RunOutcome.CRASHED
    assert result.exit_code == 7
    assert result.output_text == "hi\n"


def test_an_interpreter_that_cannot_start_is_a_crash_with_an_explanation(run_python, tmp_path):
    missing = tmp_path / "nowhere" / "python.exe"
    result = run_python("1", interpreter_path=missing)
    assert result.outcome is RunOutcome.CRASHED
    assert result.exit_code is None
    assert "Cannot start" in result.error_text
    assert "nowhere" in result.error_text


# --------------------------------------------------- the bundled default startup

@pytest.fixture
def run_with_default_startup(run_python):
    default_text = PYTHON.default_startup_path.read_text(encoding="utf-8")
    return lambda prompt_text: run_python(prompt_text, startup_text=default_text)


def test_the_default_startup_file_runs_cleanly(run_with_default_startup):
    result = run_with_default_startup("")
    assert result.outcome is RunOutcome.COMPLETED
    assert result.combined_text == ""


@pytest.mark.parametrize(
    "expression, expected_output",
    [
        ("SPEED_OF_LIGHT", "299792458\n"),
        ("INCH", "0.0254\n"),
        ("KNOT", "0.5144444444444445\n"),
        ("type(SPEED_OF_LIGHT).__name__", "'int'\n"),
        ("type(INCH).__name__", "'float'\n"),
        ("sqrt(16)", "4.0\n"),
        ("pi", f"{math.pi!r}\n"),
        ("pow(2, 100)", "1267650600228229401496703205376\n"),
    ],
)
def test_the_default_startup_defines_math_and_the_registry_names(
    run_with_default_startup, expression, expected_output
):
    assert run_with_default_startup(expression).output_text == expected_output


def expected_registry_value(entry):
    return int(entry.value_text) if entry.value_text.isdigit() else float(entry.value)


def test_every_registry_name_gets_its_value_from_the_default_startup(run_with_default_startup):
    entries = load_registry().entries()
    names = [entry.name for entry in entries]
    result = run_with_default_startup(
        f"for registry_name in {names!r}:\n    print(registry_name, repr(globals()[registry_name]))"
    )
    expected = "".join(f"{entry.name} {expected_registry_value(entry)!r}\n" for entry in entries)
    assert result.output_text == expected


def test_the_default_startup_leaves_only_math_and_registry_names_behind(run_with_default_startup):
    result = run_with_default_startup(
        "print(sorted(name for name in dir() if not name.startswith('_')))"
    )
    expected = sorted(
        {name for name in dir(math) if not name.startswith("_")}
        | {entry.name for entry in load_registry().entries()}
    )
    assert result.output_text == f"{expected!r}\n"
