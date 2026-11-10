"""Tests for the font of each box: the settings give each box its own family and size, and zooming
moves both from there."""
from dataclasses import replace

import pytest
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QFont, QWheelEvent

from mathdoer.interface.fonts import (
    DEFAULT_POINT_SIZE,
    MAXIMUM_POINT_SIZE,
    MINIMUM_POINT_SIZE,
    MONOSPACE_FAMILIES,
    monospace_font,
)
from mathdoer.interface.output_display import OutputDisplay
from mathdoer.interface.theme import DARK_THEME
from mathdoer.interface_settings import DEFAULT_INTERFACE_SETTINGS, SETTING_DESCRIPTIONS, read_interface_settings

Key = Qt.Key
CONTROL = Qt.KeyboardModifier.ControlModifier
COURIER_FIRST = ["Courier New", "Consolas", "Menlo", "DejaVu Sans Mono"]


def settings_with(**changes):
    return replace(DEFAULT_INTERFACE_SETTINGS, **changes)


def font_of(box):
    return box.font().families(), box.font().pointSize()


def point_sizes(window):
    return window.prompt_box.font().pointSize(), window.output_box.font().pointSize()


def ctrl_wheel(box, delta):
    event = QWheelEvent(
        QPointF(10, 10), box.mapToGlobal(QPointF(10, 10)), QPoint(0, 0), QPoint(0, delta),
        Qt.MouseButton.NoButton, CONTROL, Qt.ScrollPhase.NoScrollPhase, False,
    )
    box.wheelEvent(event)


# ----------------------------------------------------------------------- the font itself

def test_the_font_without_a_family_is_the_one_the_boxes_always_had():
    font = monospace_font()
    assert font.families() == MONOSPACE_FAMILIES
    assert font.pointSize() == DEFAULT_POINT_SIZE


def test_a_family_goes_first_and_the_usual_fonts_follow_it_as_fallbacks():
    font = monospace_font(13, "Lucida Console")
    assert font.families() == ["Lucida Console", *MONOSPACE_FAMILIES]
    assert font.pointSize() == 13


def test_a_family_that_is_one_of_the_usual_fonts_is_not_listed_twice():
    assert monospace_font(11, "Courier New").families() == COURIER_FIRST
    assert monospace_font(11, "Consolas").families() == MONOSPACE_FAMILIES


def test_any_family_keeps_the_font_monospace_and_the_size_within_limits():
    font = monospace_font(1000, "Whatever")
    assert font.styleHint() == QFont.StyleHint.Monospace and font.fixedPitch()
    assert font.pointSize() == MAXIMUM_POINT_SIZE
    assert monospace_font(0, "Whatever").pointSize() == MINIMUM_POINT_SIZE


def test_the_limits_of_the_font_size_are_the_limits_of_the_setting():
    sizes = [d for d in SETTING_DESCRIPTIONS if d.name.endswith("_font_size")]
    assert len(sizes) == 2
    assert {(d.minimum, d.maximum) for d in sizes} == {(MINIMUM_POINT_SIZE, MAXIMUM_POINT_SIZE)}
    assert {d.default for d in sizes} == {DEFAULT_POINT_SIZE}


# ------------------------------------------------------------------------------ one box

@pytest.fixture
def output(qtbot):
    widget = OutputDisplay(DARK_THEME)
    qtbot.addWidget(widget)
    return widget


def test_set_font_changes_the_family_and_the_size(output):
    output.set_font("Courier New", 15)
    assert font_of(output) == (COURIER_FIRST, 15)


def test_set_font_size_keeps_the_family(output):
    output.set_font("Courier New", 15)
    output.set_font_size(20)
    assert font_of(output) == (COURIER_FIRST, 20)


def test_a_box_takes_the_font_of_the_settings_that_are_for_it(output, editor):
    settings = settings_with(
        prompt_box_font_family="Courier New", prompt_box_font_size=14,
        output_box_font_family="Lucida Console", output_box_font_size=9,
    )
    output.apply_interface_settings(settings)
    editor.apply_interface_settings(settings)
    assert font_of(output) == (["Lucida Console", *MONOSPACE_FAMILIES], 9)
    assert font_of(editor) == (COURIER_FIRST, 14)


def test_settings_that_leave_the_font_alone_leave_the_zoom_alone(output):
    output.apply_interface_settings(DEFAULT_INTERFACE_SETTINGS)
    output.set_font_size(30)
    output.apply_interface_settings(settings_with(wrap_output_box_lines=False, tab_width=2))
    assert output.font().pointSize() == 30


def test_a_new_font_in_the_settings_replaces_the_zoom_of_that_box_only(output, editor):
    output.set_font_size(30)
    editor.set_font_size(30)
    settings = settings_with(output_box_font_size=12)
    output.apply_interface_settings(settings)
    editor.apply_interface_settings(settings)
    assert output.font().pointSize() == 12
    assert editor.font().pointSize() == 30  # no setting of the prompt box changed


def test_a_font_chosen_again_after_another_still_replaces_the_zoom(output):
    output.apply_interface_settings(settings_with(output_box_font_size=12))
    output.set_font_size(30)
    output.apply_interface_settings(settings_with(output_box_font_size=12, wrap_output_box_lines=False))
    assert output.font().pointSize() == 30
    output.apply_interface_settings(settings_with(output_box_font_size=13))
    output.apply_interface_settings(settings_with(output_box_font_size=12))
    assert output.font().pointSize() == 12


def test_reset_zoom_goes_back_to_the_font_of_the_settings(output):
    output.apply_interface_settings(settings_with(output_box_font_family="Courier New", output_box_font_size=17))
    output.set_font_size(30)
    output.reset_zoom()
    assert font_of(output) == (COURIER_FIRST, 17)


def test_reset_zoom_on_a_box_that_never_had_settings_goes_to_the_default_font(output):
    output.set_font_size(30)
    output.reset_zoom()
    assert font_of(output) == (MONOSPACE_FAMILIES, DEFAULT_POINT_SIZE)


# ------------------------------------------------------------------------- the window

def test_a_new_window_has_the_usual_font_in_both_boxes(window):
    assert font_of(window.prompt_box) == (MONOSPACE_FAMILIES, DEFAULT_POINT_SIZE)
    assert font_of(window.output_box) == (MONOSPACE_FAMILIES, DEFAULT_POINT_SIZE)


def test_a_window_opens_with_the_font_of_each_box_from_the_settings(make_window):
    window = make_window(
        interface_settings=settings_with(
            prompt_box_font_family="Courier New", prompt_box_font_size=15,
            output_box_font_family="Lucida Console", output_box_font_size=8,
        )
    )
    assert window.prompt_box.font().families()[0] == "Courier New" and window.prompt_box.font().pointSize() == 15
    assert window.output_box.font().families()[0] == "Lucida Console" and window.output_box.font().pointSize() == 8
    assert window.font_size == 15


def test_changing_the_settings_changes_the_font_of_each_box_at_once(window):
    window.change_interface_settings(settings_with(prompt_box_font_family="Courier New", output_box_font_size=20))
    assert window.prompt_box.font().families()[0] == "Courier New" and window.prompt_box.font().pointSize() == 11
    assert window.output_box.font().families()[0] == "Consolas" and window.output_box.font().pointSize() == 20


def test_the_fonts_and_the_tab_width_are_saved_with_the_settings(window):
    window.change_interface_settings(settings_with(output_box_font_family='Odd "name"', tab_width=7))
    saved = read_interface_settings(window.interface_settings_path)
    assert saved.output_box_font_family == 'Odd "name"' and saved.tab_width == 7


def test_a_tab_width_from_the_settings_reaches_the_prompt_box(window):
    window.change_interface_settings(settings_with(tab_width=8))
    editor = window.prompt_box
    assert editor.tabStopDistance() == pytest.approx(8 * editor.fontMetrics().horizontalAdvance(" "))


def test_zooming_moves_each_box_by_a_point_from_its_own_size(qtbot, window):
    window.change_interface_settings(settings_with(prompt_box_font_size=14, output_box_font_size=9))
    qtbot.keyClick(window.prompt_box, Key.Key_Plus, CONTROL)
    assert point_sizes(window) == (15, 10)
    ctrl_wheel(window.output_box, -120)
    ctrl_wheel(window.output_box, -120)
    assert point_sizes(window) == (13, 8)
    assert window.font_size == 13


def test_ctrl_zero_puts_each_box_back_to_the_size_in_the_settings(qtbot, window):
    window.change_interface_settings(settings_with(prompt_box_font_size=14, output_box_font_size=9))
    for _ in range(3):
        qtbot.keyClick(window.prompt_box, Key.Key_Plus, CONTROL)
    qtbot.keyClick(window.prompt_box, Key.Key_0, CONTROL)
    assert point_sizes(window) == (14, 9)


def test_each_box_stops_at_a_limit_on_its_own(qtbot, window):
    window.change_interface_settings(settings_with(prompt_box_font_size=70, output_box_font_size=10))
    for _ in range(5):
        qtbot.keyClick(window.prompt_box, Key.Key_Plus, CONTROL)
    assert point_sizes(window) == (MAXIMUM_POINT_SIZE, 15)
    for _ in range(5):
        qtbot.keyClick(window.prompt_box, Key.Key_Minus, CONTROL)
    assert point_sizes(window) == (MAXIMUM_POINT_SIZE - 5, 10)


def test_a_zoom_survives_changes_to_other_settings_and_a_new_size_replaces_it(qtbot, window):
    qtbot.keyClick(window.prompt_box, Key.Key_Plus, CONTROL)
    window.change_interface_settings(settings_with(show_line_numbers=False))
    assert window.font_size == DEFAULT_POINT_SIZE + 1
    window.change_interface_settings(settings_with(show_line_numbers=False, prompt_box_font_size=20))
    assert window.font_size == 20
    assert window.output_box.font().pointSize() == DEFAULT_POINT_SIZE + 1  # its font did not change


def test_restoring_the_defaults_puts_the_fonts_back(window):
    window.change_interface_settings(settings_with(prompt_box_font_family="Courier New", output_box_font_size=30))
    window.change_interface_settings(DEFAULT_INTERFACE_SETTINGS)
    assert font_of(window.prompt_box) == (MONOSPACE_FAMILIES, DEFAULT_POINT_SIZE)
    assert font_of(window.output_box) == (MONOSPACE_FAMILIES, DEFAULT_POINT_SIZE)


def test_the_gutter_and_the_tab_stops_follow_the_font_of_the_prompt_box_only(window):
    editor = window.prompt_box
    editor.setPlainText("a\nb")
    before = editor.gutter_width()
    window.change_interface_settings(settings_with(output_box_font_size=40))
    assert editor.gutter_width() == before
    window.change_interface_settings(settings_with(output_box_font_size=40, prompt_box_font_size=30))
    assert editor.gutter_width() > before
    assert editor.tabStopDistance() == pytest.approx(4 * editor.fontMetrics().horizontalAdvance(" "))
