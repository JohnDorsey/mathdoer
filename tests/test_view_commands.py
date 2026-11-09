"""Tests for the window-level view commands: zoom with Ctrl and +, - and 0, and word wrap with Alt+Z."""
import pytest
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QApplication

from mathdoer.interface.fonts import DEFAULT_POINT_SIZE, MAXIMUM_POINT_SIZE, MINIMUM_POINT_SIZE

Key = Qt.Key
CONTROL = Qt.KeyboardModifier.ControlModifier
ALT = Qt.KeyboardModifier.AltModifier
KEYPAD = Qt.KeyboardModifier.KeypadModifier


def sizes(window):
    return window.prompt_box.font().pointSize(), window.output_box.font().pointSize()


def wheel(box, delta):
    event = QWheelEvent(
        QPointF(10, 10), box.mapToGlobal(QPointF(10, 10)), QPoint(0, 0), QPoint(0, delta),
        Qt.MouseButton.NoButton, CONTROL, Qt.ScrollPhase.NoScrollPhase, False,
    )
    box.wheelEvent(event)


def test_the_window_starts_at_the_default_size(window):
    assert window.font_size == DEFAULT_POINT_SIZE
    assert sizes(window) == (DEFAULT_POINT_SIZE, DEFAULT_POINT_SIZE)


@pytest.mark.parametrize("key", [Key.Key_Plus, Key.Key_Equal])
def test_ctrl_plus_and_ctrl_equals_zoom_in_both_boxes(qtbot, window, key):
    qtbot.keyClick(window.prompt_box, key, CONTROL)
    assert window.font_size == DEFAULT_POINT_SIZE + 1
    assert sizes(window) == (DEFAULT_POINT_SIZE + 1,) * 2


def test_ctrl_minus_zooms_out(qtbot, window):
    qtbot.keyClick(window.prompt_box, Key.Key_Minus, CONTROL)
    assert sizes(window) == (DEFAULT_POINT_SIZE - 1,) * 2


def test_ctrl_zero_goes_back_to_the_default(qtbot, window):
    for _ in range(3):
        qtbot.keyClick(window.prompt_box, Key.Key_Plus, CONTROL)
    qtbot.keyClick(window.prompt_box, Key.Key_0, CONTROL)
    assert window.font_size == DEFAULT_POINT_SIZE
    assert sizes(window) == (DEFAULT_POINT_SIZE,) * 2


def test_the_keypad_plus_and_minus_zoom_too(qtbot, window):
    qtbot.keyClick(window.prompt_box, Key.Key_Plus, CONTROL | KEYPAD)
    assert window.font_size == DEFAULT_POINT_SIZE + 1
    qtbot.keyClick(window.prompt_box, Key.Key_Minus, CONTROL | KEYPAD)
    assert window.font_size == DEFAULT_POINT_SIZE


def test_zoom_keys_work_from_the_output_box_too(qtbot, window):
    window.output_box.setFocus()
    qtbot.keyClick(window.output_box, Key.Key_Plus, CONTROL)
    assert window.font_size == DEFAULT_POINT_SIZE + 1


def test_zooming_stops_at_the_limits(qtbot, window):
    for _ in range(MAXIMUM_POINT_SIZE):
        qtbot.keyClick(window.prompt_box, Key.Key_Plus, CONTROL)
    assert window.font_size == MAXIMUM_POINT_SIZE
    for _ in range(MAXIMUM_POINT_SIZE):
        qtbot.keyClick(window.prompt_box, Key.Key_Minus, CONTROL)
    assert window.font_size == MINIMUM_POINT_SIZE
    assert sizes(window) == (MINIMUM_POINT_SIZE,) * 2


def test_ctrl_wheel_over_either_box_zooms_both(window):
    wheel(window.prompt_box, 120)
    assert sizes(window) == (DEFAULT_POINT_SIZE + 1,) * 2
    wheel(window.output_box, -120)
    wheel(window.output_box, -120)
    assert sizes(window) == (DEFAULT_POINT_SIZE - 1,) * 2


def test_zooming_updates_the_gutter_and_the_tab_stops_of_the_prompt_box(qtbot, window):
    window.prompt_box.setPlainText("def f():\n        x")
    before = window.prompt_box.gutter_width()
    for _ in range(5):
        qtbot.keyClick(window.prompt_box, Key.Key_Plus, CONTROL)
    editor = window.prompt_box
    assert editor.gutter_width() > before
    assert editor.tabStopDistance() == pytest.approx(4 * editor.fontMetrics().horizontalAdvance(" "))


def test_zooming_leaves_the_text_and_the_caret_alone(qtbot, window):
    window.prompt_box.setPlainText("hello\nworld")
    cursor = window.prompt_box.textCursor()
    cursor.setPosition(8)
    window.prompt_box.setTextCursor(cursor)
    qtbot.keyClick(window.prompt_box, Key.Key_Plus, CONTROL)
    assert window.prompt_box.toPlainText() == "hello\nworld"
    assert window.prompt_box.textCursor().position() == 8


def test_alt_z_toggles_word_wrap_of_the_box_that_has_the_focus(qtbot, window):
    window.prompt_box.setFocus()
    qtbot.keyClick(window.prompt_box, Key.Key_Z, ALT)
    assert not window.prompt_box.word_wrap
    assert window.output_box.word_wrap
    qtbot.keyClick(window.prompt_box, Key.Key_Z, ALT)
    assert window.prompt_box.word_wrap

    window.output_box.setFocus()
    qtbot.keyClick(window.output_box, Key.Key_Z, ALT)
    assert not window.output_box.word_wrap
    assert window.prompt_box.word_wrap


def test_alt_z_uses_the_box_that_last_had_the_focus_when_the_menu_bar_has_it(qtbot, window):
    window.output_box.setFocus()
    window.menuBar().setFocus(Qt.FocusReason.MenuBarFocusReason)
    assert QApplication.focusWidget() is window.menuBar()
    qtbot.keyClick(window.menuBar(), Key.Key_Z, ALT)
    assert not window.output_box.word_wrap
    assert window.prompt_box.word_wrap


def test_word_wrap_is_on_in_both_boxes_to_begin_with(window):
    assert window.prompt_box.word_wrap and window.output_box.word_wrap


def test_typing_z_with_alt_inserts_nothing(qtbot, window):
    window.prompt_box.setFocus()
    qtbot.keyClick(window.prompt_box, Key.Key_Z, ALT)
    assert window.prompt_box.toPlainText() == ""
