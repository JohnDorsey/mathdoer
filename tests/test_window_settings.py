"""Tests for the interface settings as they apply to the window: zoom, find, wrapping and saving."""
from dataclasses import replace

from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent
from settings_helpers import every_feature_off

from mathdoer.interface.fonts import DEFAULT_POINT_SIZE
from mathdoer.interface.theme import DARK_THEME
from mathdoer.interface_settings import DEFAULT_INTERFACE_SETTINGS, read_interface_settings

Key = Qt.Key
NONE = Qt.KeyboardModifier.NoModifier
SHIFT = Qt.KeyboardModifier.ShiftModifier
CONTROL = Qt.KeyboardModifier.ControlModifier
ALT = Qt.KeyboardModifier.AltModifier


def settings_with(**changes):
    return replace(DEFAULT_INTERFACE_SETTINGS, **changes)


def ctrl_wheel(box, delta):
    event = QWheelEvent(
        QPointF(10, 10), box.mapToGlobal(QPointF(10, 10)), QPoint(0, 0), QPoint(0, delta),
        Qt.MouseButton.NoButton, CONTROL, Qt.ScrollPhase.NoScrollPhase, False,
    )
    box.wheelEvent(event)


def saved_settings(window):
    return read_interface_settings(window.interface_settings_path)


# -------------------------------------------------------------------- starting and saving

def test_a_new_window_has_the_default_settings(window):
    assert window.interface_settings == DEFAULT_INTERFACE_SETTINGS


def test_settings_given_to_a_new_window_are_applied_when_it_opens(qtbot, make_window):
    window = make_window(
        interface_settings=settings_with(
            show_line_numbers=False, wrap_output_box_lines=False, zoom_with_keys=False, find_and_replace_bar=False
        )
    )
    assert window.interface_settings.show_line_numbers is False
    assert window.prompt_box.gutter_width() == 0
    assert window.prompt_box.word_wrap and not window.output_box.word_wrap
    qtbot.keyClick(window.prompt_box, Key.Key_Plus, CONTROL)
    assert window.font_size == DEFAULT_POINT_SIZE
    qtbot.keyClick(window.prompt_box, Key.Key_F, CONTROL)
    assert window.find_bar.isHidden()


def test_changing_the_settings_applies_them_to_the_boxes_and_saves_the_file(window):
    changed = settings_with(show_line_numbers=False, highlight_syntax=False, wrap_output_box_lines=False)
    window.prompt_box.setPlainText("x = 1")
    window.change_interface_settings(changed)
    assert window.interface_settings == changed
    assert window.prompt_box.gutter_width() == 0
    assert window.prompt_box.document().firstBlock().layout().formats() == []
    assert not window.output_box.word_wrap
    assert saved_settings(window) == changed


def test_the_window_tells_whoever_listens_about_a_change(qtbot, window):
    changed = settings_with(show_line_numbers=False)
    with qtbot.waitSignal(window.interface_settings_changed) as signal:
        window.change_interface_settings(changed)
    assert signal.args == [changed]


def test_a_window_without_a_settings_path_saves_nothing(make_window, tmp_path):
    window = make_window(interface_settings_path=None)
    window.change_interface_settings(settings_with(show_line_numbers=False))
    assert window.prompt_box.gutter_width() == 0
    assert not list(tmp_path.glob("interface_settings*"))
    assert window.output_box.output_text() == ""


def test_a_save_that_fails_is_reported_in_the_output_box_and_the_settings_still_apply(make_window, tmp_path):
    folder_in_the_way = tmp_path / "interface_settings_folder"
    folder_in_the_way.mkdir()
    window = make_window(interface_settings_path=folder_in_the_way)
    changed = settings_with(show_line_numbers=False)
    window.change_interface_settings(changed)
    assert "[could not save the settings: " in window.output_box.output_text()
    assert window.interface_settings == changed
    assert window.prompt_box.gutter_width() == 0


# ---------------------------------------------------------------------------------- zoom

def test_the_zoom_keys_do_nothing_when_turned_off_and_the_wheel_still_zooms(qtbot, window):
    window.change_interface_settings(settings_with(zoom_with_keys=False))
    for key in (Key.Key_Plus, Key.Key_Equal, Key.Key_Minus, Key.Key_0):
        qtbot.keyClick(window.prompt_box, key, CONTROL)
    assert window.font_size == DEFAULT_POINT_SIZE
    assert window.prompt_box.toPlainText() == ""
    ctrl_wheel(window.prompt_box, 120)
    assert window.font_size == DEFAULT_POINT_SIZE + 1


def test_the_zoom_keys_work_again_when_turned_back_on(qtbot, window):
    window.change_interface_settings(settings_with(zoom_with_keys=False))
    window.change_interface_settings(DEFAULT_INTERFACE_SETTINGS)
    qtbot.keyClick(window.prompt_box, Key.Key_Plus, CONTROL)
    assert window.font_size == DEFAULT_POINT_SIZE + 1


def test_the_mouse_wheel_does_not_zoom_either_box_when_turned_off_and_the_keys_still_do(qtbot, window):
    window.change_interface_settings(settings_with(zoom_with_mouse_wheel=False))
    ctrl_wheel(window.prompt_box, 120)
    ctrl_wheel(window.output_box, -120)
    assert window.font_size == DEFAULT_POINT_SIZE
    qtbot.keyClick(window.prompt_box, Key.Key_Plus, CONTROL)
    assert window.font_size == DEFAULT_POINT_SIZE + 1


# ---------------------------------------------------------------------------------- find

def test_the_find_bar_closes_and_its_keys_do_nothing_when_turned_off(qtbot, window):
    window.prompt_box.setPlainText("abc")
    window.find_bar.show_find()
    window.find_bar.find_field.setText("b")
    assert not window.find_bar.isHidden()

    window.change_interface_settings(settings_with(find_and_replace_bar=False))
    assert window.find_bar.isHidden()
    assert not any(
        item.format.background().color().name() == DARK_THEME.find_match_background
        for item in window.prompt_box.extraSelections()
    )
    window.prompt_box.setFocus()
    for key, modifiers in [(Key.Key_F, CONTROL), (Key.Key_H, CONTROL), (Key.Key_F3, NONE), (Key.Key_F3, SHIFT)]:
        qtbot.keyClick(window.prompt_box, key, modifiers)
        assert window.find_bar.isHidden(), (key, modifiers)
    assert window.prompt_box.toPlainText() == "abc"


def test_the_find_bar_opens_again_when_turned_back_on(qtbot, window):
    window.change_interface_settings(settings_with(find_and_replace_bar=False))
    window.change_interface_settings(DEFAULT_INTERFACE_SETTINGS)
    qtbot.keyClick(window.prompt_box, Key.Key_F, CONTROL)
    assert not window.find_bar.isHidden()


# ------------------------------------------------------------------------------ wrapping

def test_each_box_wraps_lines_according_to_its_own_setting(window):
    window.change_interface_settings(settings_with(wrap_prompt_box_lines=False))
    assert not window.prompt_box.word_wrap and window.output_box.word_wrap
    window.change_interface_settings(settings_with(wrap_output_box_lines=False))
    assert window.prompt_box.word_wrap and not window.output_box.word_wrap


def test_alt_z_changes_the_wrapping_setting_of_the_box_that_has_the_focus_and_saves_it(qtbot, window):
    window.prompt_box.setFocus()
    with qtbot.waitSignal(window.interface_settings_changed):
        qtbot.keyClick(window.prompt_box, Key.Key_Z, ALT)
    assert not window.prompt_box.word_wrap
    assert window.interface_settings == settings_with(wrap_prompt_box_lines=False)
    assert saved_settings(window) == settings_with(wrap_prompt_box_lines=False)

    window.output_box.setFocus()
    qtbot.keyClick(window.output_box, Key.Key_Z, ALT)
    assert not window.output_box.word_wrap
    assert saved_settings(window) == settings_with(wrap_prompt_box_lines=False, wrap_output_box_lines=False)

    window.prompt_box.setFocus()
    qtbot.keyClick(window.prompt_box, Key.Key_Z, ALT)
    assert window.prompt_box.word_wrap
    assert saved_settings(window) == settings_with(wrap_output_box_lines=False)


def test_a_change_of_another_setting_keeps_the_wrapping_that_alt_z_chose(qtbot, window):
    window.prompt_box.setFocus()
    qtbot.keyClick(window.prompt_box, Key.Key_Z, ALT)
    window.change_interface_settings(replace(window.interface_settings, show_line_numbers=False))
    assert not window.prompt_box.word_wrap


# ------------------------------------------------------------------------- all together

def test_running_still_works_with_every_feature_off(qtbot, window):
    window.change_interface_settings(every_feature_off())
    window.prompt_box.setFocus()
    window.prompt_box.setPlainText("6 * 7")
    qtbot.keyClick(window.prompt_box, Key.Key_Return, CONTROL)
    qtbot.waitUntil(lambda: not window.is_running, timeout=20000)
    assert window.output_box.output_text().strip() == "42"
    assert window.prompt_box.toPlainText() == "6 * 7"  # Ctrl+Enter is not a new line
