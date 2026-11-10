"""Tests for the main window: layout, running with Ctrl+Enter, cancelling with Shift+Esc."""
import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QSplitter

from mathdoer.interface.icon import application_icon
from mathdoer.interface.output_display import truncation_notice
from mathdoer.interface.theme import DARK_THEME

LONG_RUN = "import time\nprint('started', flush=True)\ntime.sleep(120)"
SILENT_LONG_RUN = "import time\ntime.sleep(120)"
RUN_TIMEOUT_MILLISECONDS = 30000


def press_ctrl_enter(qtbot, widget, key=Qt.Key.Key_Return):
    qtbot.keyClick(widget, key, Qt.KeyboardModifier.ControlModifier)


def press_shift_escape(qtbot, widget):
    qtbot.keyClick(widget, Qt.Key.Key_Escape, Qt.KeyboardModifier.ShiftModifier)


def start_run(qtbot, window, prompt_text):
    window.prompt_box.setPlainText(prompt_text)
    press_ctrl_enter(qtbot, window.prompt_box)
    run = window.current_run
    assert run is not None, "Ctrl+Enter did not start a run"
    return run


def run_to_the_end(qtbot, window, prompt_text):
    start_run(qtbot, window, prompt_text)
    qtbot.waitUntil(lambda: window.current_run is None, timeout=RUN_TIMEOUT_MILLISECONDS)
    return window.output_box.toPlainText()


def wait_for_output(qtbot, window, text):
    qtbot.waitUntil(lambda: text in window.output_box.toPlainText(), timeout=RUN_TIMEOUT_MILLISECONDS)


def foreground_at(display, index):
    cursor = QTextCursor(display.document())
    cursor.setPosition(index + 1)
    return cursor.charFormat().foreground().color().name()


# ------------------------------------------------------------------------ layout

def test_the_window_has_a_title(window):
    assert window.windowTitle() == "mathdoer"


def test_the_window_and_the_settings_window_wear_the_icon(window):
    assert not window.windowIcon().isNull()
    assert window.windowIcon().availableSizes() == application_icon().availableSizes()
    window.open_settings_window()
    assert window.settings_window.windowIcon().availableSizes() == application_icon().availableSizes()


def test_the_prompt_box_is_above_the_output_box_in_a_draggable_splitter(window):
    splitter = window.centralWidget()
    assert isinstance(splitter, QSplitter)
    assert splitter.orientation() == Qt.Orientation.Vertical
    assert splitter.widget(0) is window.prompt_pane
    assert window.prompt_box.parent() is window.prompt_pane
    assert splitter.widget(1) is window.output_box
    assert splitter.handleWidth() >= 4
    assert not splitter.childrenCollapsible()


def test_both_boxes_start_with_room_and_the_prompt_box_is_the_smaller(qtbot, window):
    qtbot.waitUntil(lambda: all(size > 0 for size in window.centralWidget().sizes()))
    prompt_size, output_size = window.centralWidget().sizes()
    assert 0 < prompt_size < output_size


def test_dragging_the_splitter_resizes_the_boxes(qtbot, window):
    splitter = window.centralWidget()
    qtbot.waitUntil(lambda: all(size > 0 for size in splitter.sizes()))
    total = sum(splitter.sizes())
    splitter.setSizes([total - 100, 100])
    assert splitter.sizes()[0] > splitter.sizes()[1]


def test_the_window_can_be_resized(qtbot, window):
    window.resize(1000, 800)
    qtbot.waitUntil(lambda: window.width() == 1000 and window.height() == 800)


def test_the_prompt_box_is_editable_and_the_output_box_is_not(window):
    assert not window.prompt_box.isReadOnly()
    assert window.output_box.isReadOnly()


def test_typing_starts_in_the_prompt_box(window):
    assert window.focusWidget() is window.prompt_box


def test_the_prompt_box_uses_the_theme(window):
    palette = window.prompt_box.palette()
    assert palette.base().color().name() == DARK_THEME.text_background
    assert palette.text().color().name() == DARK_THEME.default_text


# ----------------------------------------------------------------------- running

def test_ctrl_enter_runs_the_prompt_and_shows_the_result(qtbot, window):
    assert run_to_the_end(qtbot, window, "1 + 1") == "2\n"


def test_ctrl_enter_on_the_keypad_enter_key_also_runs(qtbot, window):
    window.prompt_box.setPlainText("print('keypad')")
    press_ctrl_enter(qtbot, window.prompt_box, key=Qt.Key.Key_Enter)
    assert window.current_run is not None
    qtbot.waitUntil(lambda: window.current_run is None, timeout=RUN_TIMEOUT_MILLISECONDS)
    assert window.output_box.toPlainText() == "keypad\n"


def test_ctrl_enter_works_while_the_output_box_has_focus(qtbot, window):
    window.prompt_box.setPlainText("print('from output box')")
    window.output_box.setFocus()
    press_ctrl_enter(qtbot, window.output_box)
    assert window.current_run is not None
    qtbot.waitUntil(lambda: window.current_run is None, timeout=RUN_TIMEOUT_MILLISECONDS)
    assert window.output_box.toPlainText() == "from output box\n"


def test_plain_enter_adds_a_line_and_does_not_run(qtbot, window):
    window.prompt_box.setPlainText("1 + 1")
    window.prompt_box.moveCursor(QTextCursor.MoveOperation.End)
    qtbot.keyClick(window.prompt_box, Qt.Key.Key_Return)
    assert window.prompt_box.toPlainText() == "1 + 1\n"
    assert window.current_run is None


def test_the_prompt_text_is_left_alone_by_a_run(qtbot, window):
    run_to_the_end(qtbot, window, "x = 1\nx + 1")
    assert window.prompt_box.toPlainText() == "x = 1\nx + 1"


def test_each_run_starts_with_an_empty_output_box(qtbot, window):
    run_to_the_end(qtbot, window, "print('first')")
    assert run_to_the_end(qtbot, window, "print('second')") == "second\n"


def test_output_is_shown_while_the_run_is_still_going(qtbot, window):
    start_run(qtbot, window, LONG_RUN)
    wait_for_output(qtbot, window, "started")
    assert window.is_running
    window.cancel_run()
    qtbot.waitUntil(lambda: not window.is_running, timeout=RUN_TIMEOUT_MILLISECONDS)


def test_ctrl_enter_is_ignored_while_a_run_is_going(qtbot, window):
    first_run = start_run(qtbot, window, LONG_RUN)
    wait_for_output(qtbot, window, "started")
    press_ctrl_enter(qtbot, window.prompt_box)
    qtbot.wait(100)
    assert window.current_run is first_run
    assert "started" in window.output_box.toPlainText()
    window.cancel_run()
    qtbot.waitUntil(lambda: not window.is_running, timeout=RUN_TIMEOUT_MILLISECONDS)


def test_errors_are_shown_in_the_error_color(qtbot, window):
    text = run_to_the_end(qtbot, window, "print('fine')\n1 / 0")
    assert text.startswith("fine\n")
    error_start = text.index("Traceback")
    assert foreground_at(window.output_box, 0) == DARK_THEME.default_text
    assert foreground_at(window.output_box, error_start) == DARK_THEME.error_text
    assert "ZeroDivisionError" in text


def test_a_startup_error_is_shown_and_the_prompt_is_not_run(qtbot, make_window):
    window = make_window(startup_text="1 / 0")
    text = run_to_the_end(qtbot, window, "print('PROMPT-WAS-RUN')")
    assert "startup file" in text.lower()
    assert "ZeroDivisionError" in text
    assert "PROMPT-WAS-RUN" not in text


def test_a_worker_that_dies_is_reported(qtbot, window):
    text = run_to_the_end(qtbot, window, "import os\nprint('hi', flush=True)\nos._exit(7)")
    assert text == "hi\n[the worker stopped unexpectedly (exit code 7)]"


def test_an_interpreter_that_cannot_start_is_explained_once(qtbot, make_window, tmp_path):
    window = make_window(interpreter_path=tmp_path / "nowhere" / "python.exe")
    text = run_to_the_end(qtbot, window, "1")
    assert "Cannot start" in text
    assert "[the worker stopped" not in text


def test_a_problem_in_the_settings_file_is_explained_once_in_the_error_color(qtbot, make_window):
    window = make_window(settings_text="interpreter = 'mathdoer_no_such_program'\n")
    text = run_to_the_end(qtbot, window, "print('PROMPT-WAS-RUN')")
    assert "mathdoer_no_such_program" in text
    assert "settings_python.toml" in text
    assert "PROMPT-WAS-RUN" not in text
    assert "[the worker stopped" not in text
    assert foreground_at(window.output_box, 0) == DARK_THEME.error_text
    assert not window.is_running


def test_fixing_the_settings_file_fixes_the_next_run_without_restarting(qtbot, make_window, make_wrapper_interpreter):
    window = make_window(settings_text="interpreter = 'mathdoer_no_such_program'\n")
    assert "not found" in run_to_the_end(qtbot, window, "print('fine')")
    wrapper = make_wrapper_interpreter()
    window.language_settings_path.write_text(f"interpreter = '{wrapper}'\n", encoding="utf-8")
    assert run_to_the_end(qtbot, window, "import os\nprint(os.environ['MATHDOER_TEST_WRAPPER'])") == "yes\n"


def test_carriage_returns_in_output_become_line_breaks(qtbot, window):
    assert run_to_the_end(qtbot, window, r"print('a\r\nb\rc')") == "a\nb\nc\n"


# ----------------------------------------------------------------------- cancel

def test_shift_escape_cancels_the_run_and_marks_the_output(qtbot, window):
    start_run(qtbot, window, LONG_RUN)
    wait_for_output(qtbot, window, "started")
    press_shift_escape(qtbot, window.prompt_box)
    qtbot.waitUntil(lambda: not window.is_running, timeout=RUN_TIMEOUT_MILLISECONDS)
    assert window.output_box.toPlainText() == "started\n[cancelled]"


def test_shift_escape_works_while_the_output_box_has_focus(qtbot, window):
    start_run(qtbot, window, LONG_RUN)
    wait_for_output(qtbot, window, "started")
    window.output_box.setFocus()
    press_shift_escape(qtbot, window.output_box)
    qtbot.waitUntil(lambda: not window.is_running, timeout=RUN_TIMEOUT_MILLISECONDS)
    assert window.output_box.toPlainText().endswith("[cancelled]")


def test_shift_escape_with_nothing_running_does_nothing(qtbot, window):
    press_shift_escape(qtbot, window.prompt_box)
    qtbot.wait(50)
    assert window.output_box.toPlainText() == ""
    assert window.current_run is None


def test_a_new_run_can_start_after_a_cancel(qtbot, window):
    start_run(qtbot, window, LONG_RUN)
    wait_for_output(qtbot, window, "started")
    window.cancel_run()
    qtbot.waitUntil(lambda: not window.is_running, timeout=RUN_TIMEOUT_MILLISECONDS)
    assert run_to_the_end(qtbot, window, "print('again')") == "again\n"


def test_closing_the_window_stops_a_run_that_is_going(qtbot, window):
    run = start_run(qtbot, window, LONG_RUN)
    wait_for_output(qtbot, window, "started")
    window.close()
    assert run.wait(15)


# --------------------------------------------------------- spinner and elapsed time

def test_a_spinner_shows_while_the_run_has_produced_nothing(qtbot, window, fake_clock):
    start_run(qtbot, window, SILENT_LONG_RUN)
    assert window.output_box.toPlainText() == "/"
    fake_clock.advance(0.125)
    window.poll_run()
    assert window.output_box.toPlainText() == "-"
    window.cancel_run()
    qtbot.waitUntil(lambda: not window.is_running, timeout=RUN_TIMEOUT_MILLISECONDS)


def test_after_five_seconds_the_spinner_is_followed_by_the_elapsed_time(qtbot, window, fake_clock):
    start_run(qtbot, window, SILENT_LONG_RUN)
    fake_clock.advance(4.9)
    window.poll_run()
    assert ":" not in window.output_box.toPlainText()
    fake_clock.advance(0.1)
    window.poll_run()
    assert window.output_box.toPlainText() == "/ 00:05"
    fake_clock.advance(60.25)
    window.poll_run()
    assert window.output_box.toPlainText() == "\\ 01:05"
    window.cancel_run()
    qtbot.waitUntil(lambda: not window.is_running, timeout=RUN_TIMEOUT_MILLISECONDS)


def test_the_spinner_follows_the_output_and_disappears_when_the_run_ends(qtbot, window, fake_clock):
    start_run(qtbot, window, LONG_RUN)
    wait_for_output(qtbot, window, "started")
    assert window.output_box.toPlainText().startswith("started\n")
    assert window.output_box.toPlainText().count("\n") == 1
    window.cancel_run()
    qtbot.waitUntil(lambda: not window.is_running, timeout=RUN_TIMEOUT_MILLISECONDS)
    assert window.output_box.toPlainText() == "started\n[cancelled]"


def test_no_spinner_is_left_after_a_run_that_finishes(qtbot, window):
    assert run_to_the_end(qtbot, window, "print('done')") == "done\n"


# --------------------------------------------------------------- the output cap

def test_overflowing_output_loses_the_beginning_and_shows_a_notice(qtbot, make_window):
    window = make_window(maximum_output_characters=50)
    text = run_to_the_end(qtbot, window, "for number in range(30):\n    print(f'line {number}')")
    everything = "".join(f"line {number}\n" for number in range(30))
    discarded = len(everything) - 50
    assert text == truncation_notice(discarded) + "\n" + everything[-50:]


def test_the_cap_counts_characters_outside_the_basic_plane_once(qtbot, make_window):
    window = make_window(maximum_output_characters=5)
    text = run_to_the_end(qtbot, window, "print('😀' * 10)")
    assert text == truncation_notice(6) + "\n" + "😀😀😀😀\n"


def test_the_cap_counts_a_windows_line_break_as_one_character(qtbot, make_window):
    window = make_window(maximum_output_characters=7)
    text = run_to_the_end(qtbot, window, r"print('ab\r\ncd\r\n' * 5, end='')")
    everything = "ab\ncd\n" * 5
    assert text == truncation_notice(len(everything) - 7) + "\n" + everything[-7:]


def test_a_new_run_starts_without_the_old_notice(qtbot, make_window):
    window = make_window(maximum_output_characters=10)
    run_to_the_end(qtbot, window, "print('x' * 100)")
    assert "truncated" in window.output_box.toPlainText()
    assert run_to_the_end(qtbot, window, "print('ok')") == "ok\n"
