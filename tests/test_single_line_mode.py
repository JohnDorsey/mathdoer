"""Tests for single-line mode: Enter runs the prompt and Alt+Enter starts a new line; otherwise
Enter starts a new line and Ctrl+Enter runs."""
from dataclasses import replace

import pytest
from editor_helpers import caret_of, load, press
from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor

from mathdoer.interface_settings import DEFAULT_INTERFACE_SETTINGS, read_interface_settings

Key = Qt.Key
SHIFT = Qt.KeyboardModifier.ShiftModifier
CONTROL = Qt.KeyboardModifier.ControlModifier
ALT = Qt.KeyboardModifier.AltModifier
KEYPAD = Qt.KeyboardModifier.KeypadModifier
ENTER_KEYS = [Key.Key_Return, Key.Key_Enter]
RUN_TIMEOUT_MILLISECONDS = 30000


def single_line(**changes):
    return replace(DEFAULT_INTERFACE_SETTINGS, single_line_mode=True, **changes)


class RunRequests:
    def __init__(self, editor):
        self.count = 0
        editor.run_requested.connect(self._count)

    def _count(self):
        self.count += 1


@pytest.fixture
def requests(editor):
    return RunRequests(editor)


# ----------------------------------------------------------------------- the prompt box

@pytest.mark.parametrize("key", ENTER_KEYS)
def test_enter_asks_to_run_and_leaves_the_text_alone_in_single_line_mode(qtbot, editor, requests, key):
    editor.apply_interface_settings(single_line())
    load(editor, "    if x:")
    press(qtbot, editor, key)
    assert requests.count == 1
    assert editor.toPlainText() == "    if x:" and caret_of(editor) == (0, 9)


def test_the_enter_key_on_the_keypad_asks_to_run_too(qtbot, editor, requests):
    editor.apply_interface_settings(single_line())
    load(editor, "1")
    press(qtbot, editor, Key.Key_Enter, KEYPAD)
    assert requests.count == 1 and editor.toPlainText() == "1"


@pytest.mark.parametrize("key", ENTER_KEYS)
def test_alt_enter_starts_a_new_line_with_the_indentation_kept_in_single_line_mode(qtbot, editor, requests, key):
    editor.apply_interface_settings(single_line())
    load(editor, "    if x:")
    press(qtbot, editor, key, ALT)
    assert requests.count == 0
    assert editor.toPlainText() == "    if x:\n        " and caret_of(editor) == (1, 8)


def test_alt_enter_on_the_keypad_starts_a_new_line_too(qtbot, editor, requests):
    editor.apply_interface_settings(single_line())
    load(editor, "ab", caret=(0, 1))
    press(qtbot, editor, Key.Key_Enter, ALT | KEYPAD)
    assert editor.toPlainText() == "a\nb" and requests.count == 0


def test_alt_enter_starts_a_plain_new_line_when_keeping_the_indentation_is_off(qtbot, editor, requests):
    editor.apply_interface_settings(single_line(enter_keeps_indentation=False))
    load(editor, "    if x:")
    press(qtbot, editor, Key.Key_Return, ALT)
    assert editor.toPlainText() == "    if x:\n" and caret_of(editor) == (1, 0)
    assert requests.count == 0


def test_alt_enter_replaces_a_selection_with_a_new_line_whether_or_not_it_keeps_the_indentation(qtbot, editor):
    for keeps in (True, False):
        editor.apply_interface_settings(single_line(enter_keeps_indentation=keeps))
        load(editor, "hello", anchor=(0, 1), caret=(0, 4))
        press(qtbot, editor, Key.Key_Return, ALT)
        assert editor.toPlainText() == "h\no", keeps


def test_alt_enter_is_one_undo_step(qtbot, editor):
    editor.apply_interface_settings(single_line(enter_keeps_indentation=False))
    load(editor, "ab", caret=(0, 1))
    press(qtbot, editor, Key.Key_Return, ALT)
    editor.undo()
    assert editor.toPlainText() == "ab"


def test_shift_enter_still_starts_a_new_line_in_single_line_mode(qtbot, editor, requests):
    editor.apply_interface_settings(single_line())
    load(editor, "if x:")
    press(qtbot, editor, Key.Key_Return, SHIFT)
    assert editor.toPlainText() == "if x:\n    " and requests.count == 0


@pytest.mark.parametrize("key", ENTER_KEYS)
def test_ctrl_enter_is_left_to_the_window_in_either_mode(qtbot, editor, requests, key):
    for settings in (DEFAULT_INTERFACE_SETTINGS, single_line()):
        editor.apply_interface_settings(settings)
        load(editor, "x")
        press(qtbot, editor, key, CONTROL)
        assert editor.toPlainText() == "x" and requests.count == 0, settings.single_line_mode


@pytest.mark.parametrize("key", ENTER_KEYS)
def test_enter_starts_a_new_line_and_never_asks_to_run_in_multi_line_mode(qtbot, editor, requests, key):
    load(editor, "if x:")
    press(qtbot, editor, key)
    assert editor.toPlainText() == "if x:\n    " and requests.count == 0


def test_alt_enter_does_nothing_in_multi_line_mode(qtbot, editor, requests):
    load(editor, "ab")
    press(qtbot, editor, Key.Key_Return, ALT)
    assert editor.toPlainText() == "ab" and requests.count == 0


def test_turning_single_line_mode_off_again_gives_enter_back_to_the_text(qtbot, editor, requests):
    editor.apply_interface_settings(single_line())
    editor.apply_interface_settings(DEFAULT_INTERFACE_SETTINGS)
    load(editor, "a")
    press(qtbot, editor, Key.Key_Return)
    assert editor.toPlainText() == "a\n" and requests.count == 0


def test_the_other_editing_keys_are_not_touched_by_single_line_mode(qtbot, editor, requests):
    editor.apply_interface_settings(single_line())
    load(editor, "ab")
    press(qtbot, editor, Key.Key_Tab)
    assert editor.toPlainText() == "ab  "
    press(qtbot, editor, Key.Key_D, CONTROL)
    assert editor.toPlainText() == "ab  \nab  " and requests.count == 0


# ------------------------------------------------------------------------- the window

def test_enter_runs_the_prompt_in_single_line_mode(qtbot, make_window):
    window = make_window(interface_settings=single_line())
    window.prompt_box.setPlainText("print('single')")
    qtbot.keyClick(window.prompt_box, Key.Key_Return)
    assert window.current_run is not None
    qtbot.waitUntil(lambda: window.current_run is None, timeout=RUN_TIMEOUT_MILLISECONDS)
    assert window.output_box.toPlainText() == "single\n"
    assert window.prompt_box.toPlainText() == "print('single')"


def test_ctrl_enter_still_runs_in_single_line_mode(qtbot, make_window):
    window = make_window(interface_settings=single_line())
    window.prompt_box.setPlainText("print('ctrl')")
    qtbot.keyClick(window.prompt_box, Key.Key_Return, CONTROL)
    assert window.current_run is not None
    qtbot.waitUntil(lambda: window.current_run is None, timeout=RUN_TIMEOUT_MILLISECONDS)
    assert window.output_box.toPlainText() == "ctrl\n"


def test_switching_the_mode_in_the_settings_takes_effect_at_once(qtbot, window):
    window.prompt_box.setPlainText("1")
    window.prompt_box.moveCursor(QTextCursor.MoveOperation.End)
    window.change_interface_settings(single_line())
    qtbot.keyClick(window.prompt_box, Key.Key_Return)
    assert window.current_run is not None
    qtbot.waitUntil(lambda: window.current_run is None, timeout=RUN_TIMEOUT_MILLISECONDS)
    window.change_interface_settings(DEFAULT_INTERFACE_SETTINGS)
    qtbot.keyClick(window.prompt_box, Key.Key_Return)
    assert window.current_run is None and window.prompt_box.toPlainText() == "1\n"


def test_enter_while_a_run_is_going_does_not_start_another_or_change_the_text(qtbot, make_window):
    window = make_window(interface_settings=single_line())
    window.prompt_box.setPlainText("import time\nprint('started', flush=True)\ntime.sleep(30)")
    qtbot.keyClick(window.prompt_box, Key.Key_Return)
    first_run = window.current_run
    qtbot.waitUntil(lambda: "started" in window.output_box.toPlainText(), timeout=RUN_TIMEOUT_MILLISECONDS)
    text = window.prompt_box.toPlainText()
    qtbot.keyClick(window.prompt_box, Key.Key_Return)
    assert window.current_run is first_run and window.prompt_box.toPlainText() == text
    window.cancel_run()
    qtbot.waitUntil(lambda: not window.is_running, timeout=RUN_TIMEOUT_MILLISECONDS)


def test_enter_in_the_find_bar_does_not_run_the_prompt_in_single_line_mode(qtbot, make_window):
    window = make_window(interface_settings=single_line())
    window.prompt_box.setPlainText("a a a")
    window.find_bar.show_find()
    qtbot.keyClicks(window.find_bar.find_field, "a")
    qtbot.keyClick(window.find_bar.find_field, Key.Key_Return)
    assert window.current_run is None
    assert window.prompt_box.toPlainText() == "a a a"


def test_the_mode_is_saved_in_the_file(window):
    window.change_interface_settings(single_line())
    assert read_interface_settings(window.interface_settings_path).single_line_mode is True
