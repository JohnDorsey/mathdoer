"""Tests for the settings window: pages listed on the left, the settings of the chosen page on the right."""
import random
from dataclasses import replace

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QCheckBox, QLabel, QPushButton, QSpinBox
from settings_helpers import every_feature_off, random_settings

from mathdoer.interface.settings_window import SettingsWindow
from mathdoer.interface.theme import DARK_THEME, contrast_ratio
from mathdoer.interface_settings import (
    DEFAULT_INTERFACE_SETTINGS,
    SETTING_DESCRIPTIONS,
    SETTINGS_PAGES,
    descriptions_on_page,
)

YES_OR_NO_DESCRIPTIONS = [d for d in SETTING_DESCRIPTIONS if d.value_type is bool]
NUMBER_DESCRIPTIONS = [d for d in SETTING_DESCRIPTIONS if d.value_type is int]


class SizeOfTheWindow:
    """The size the main window would report, changed by the test."""

    def __init__(self, width=900, height=700):
        self.size = (width, height)

    def __call__(self):
        return self.size


@pytest.fixture
def size_of_the_window():
    return SizeOfTheWindow()


@pytest.fixture
def make_settings_window(qtbot, size_of_the_window):
    def make(settings=DEFAULT_INTERFACE_SETTINGS):
        dialog = SettingsWindow(settings, DARK_THEME, size_of_the_window)
        qtbot.addWidget(dialog)
        dialog.show()
        qtbot.waitExposed(dialog)
        return dialog

    return make


@pytest.fixture
def dialog(make_settings_window):
    return make_settings_window()


class Announcements:
    """The settings the window announced, in order."""

    def __init__(self, dialog):
        self.settings = []
        dialog.settings_changed.connect(self.settings.append)


def widget_of(dialog, description):
    if description.value_type is bool:
        return dialog.checkbox_for(description.name)
    return dialog.spin_box_for(description.name)


def value_of(widget):
    return widget.isChecked() if isinstance(widget, QCheckBox) else widget.value()


# ------------------------------------------------------------------------------- pages

def test_the_window_is_titled_settings_and_lists_the_pages_in_order(dialog):
    assert dialog.windowTitle() == "Settings"
    assert dialog.page_titles() == ["Window", "Display", "Editing", "Line commands", "Find"]
    assert dialog.page_titles() == [page.title for page in SETTINGS_PAGES]


def test_the_first_page_is_shown_first(dialog):
    assert dialog.current_page_title == "Window"
    assert dialog.page_list.currentRow() == 0


def test_choosing_a_page_in_the_list_shows_it(dialog):
    dialog.page_list.setCurrentRow(2)
    assert dialog.current_page_title == "Editing"
    assert dialog.checkbox_for("tab_key_inserts_spaces").isVisible()
    assert not dialog.checkbox_for("show_line_numbers").isVisible()


def test_clicking_a_page_title_shows_the_page(qtbot, dialog):
    item = dialog.page_list.item(3)
    qtbot.mouseClick(dialog.page_list.viewport(), Qt.MouseButton.LeftButton, pos=dialog.page_list.visualItemRect(item).center())
    assert dialog.current_page_title == "Line commands"


def test_show_page_chooses_a_page_by_its_title(dialog):
    dialog.show_page("Find")
    assert dialog.current_page_title == "Find"
    assert dialog.page_list.currentRow() == 4


def test_each_page_shows_exactly_the_settings_that_belong_to_it(dialog):
    for page in SETTINGS_PAGES:
        dialog.show_page(page.title)
        shown = {d.name for d in SETTING_DESCRIPTIONS if widget_of(dialog, d).isVisible()}
        assert shown == {d.name for d in descriptions_on_page(page)}, page.title


def test_a_page_with_a_note_shows_it_and_says_when_a_size_applies(dialog):
    def shown_text():
        return [label.text() for label in dialog.findChildren(QLabel) if label.isVisible()]

    assert any("next time mathdoer starts" in text for text in shown_text())
    dialog.show_page("Display")
    assert not any("next time mathdoer starts" in text for text in shown_text())


# ------------------------------------------------------------------ the widgets shown

def test_every_setting_has_a_widget_that_shows_its_value_and_label(dialog):
    for description in SETTING_DESCRIPTIONS:
        widget = widget_of(dialog, description)
        assert value_of(widget) == description.default, description.name
        if description.value_type is bool:
            assert widget.text() == description.label
        else:
            assert (widget.minimum(), widget.maximum()) == (description.minimum, description.maximum)
            assert dialog.label_for(description.name) == description.label


def test_the_window_shows_the_settings_it_is_given(make_settings_window):
    generator = random.Random(8)
    for settings in (every_feature_off(), *(random_settings(generator) for _ in range(20))):
        dialog = make_settings_window(settings)
        assert dialog.settings == settings
        for description in SETTING_DESCRIPTIONS:
            assert value_of(widget_of(dialog, description)) == getattr(settings, description.name), description.name


def test_the_widgets_are_of_the_kind_the_setting_needs(dialog):
    for description in YES_OR_NO_DESCRIPTIONS:
        assert isinstance(dialog.checkbox_for(description.name), QCheckBox)
    for description in NUMBER_DESCRIPTIONS:
        assert isinstance(dialog.spin_box_for(description.name), QSpinBox)


# ------------------------------------------------------------------ changing a setting

@pytest.mark.parametrize("description", YES_OR_NO_DESCRIPTIONS, ids=lambda description: description.name)
def test_clicking_a_checkbox_changes_that_setting_alone_and_announces_it(dialog, description):
    announced = Announcements(dialog)
    dialog.show_page(description.page.title)
    checkbox = dialog.checkbox_for(description.name)
    checkbox.click()
    assert announced.settings == [replace(DEFAULT_INTERFACE_SETTINGS, **{description.name: False})]
    assert dialog.settings == announced.settings[-1]
    checkbox.click()
    assert announced.settings[-1] == DEFAULT_INTERFACE_SETTINGS
    assert len(announced.settings) == 2


def test_a_real_mouse_click_on_a_checkbox_changes_the_setting(qtbot, dialog):
    announced = Announcements(dialog)
    dialog.show_page("Display")
    checkbox = dialog.checkbox_for("show_line_numbers")
    qtbot.mouseClick(checkbox, Qt.MouseButton.LeftButton, pos=QPoint(8, checkbox.height() // 2))  # on the box
    assert announced.settings == [replace(DEFAULT_INTERFACE_SETTINGS, show_line_numbers=False)]


def test_changing_a_number_changes_that_setting_and_announces_it(dialog):
    announced = Announcements(dialog)
    dialog.spin_box_for("window_width").setValue(1234)
    dialog.spin_box_for("window_height").setValue(567)
    assert announced.settings == [
        replace(DEFAULT_INTERFACE_SETTINGS, window_width=1234),
        replace(DEFAULT_INTERFACE_SETTINGS, window_width=1234, window_height=567),
    ]


def test_a_number_typed_in_the_box_counts_once_it_is_finished(qtbot, dialog):
    """Typing 1200 passes through 1, 12 and 120; only the finished number is a setting."""
    announced = Announcements(dialog)
    spin_box = dialog.spin_box_for("window_width")
    spin_box.selectAll()
    qtbot.keyClicks(spin_box, "1200")
    assert announced.settings == []
    qtbot.keyClick(spin_box, Qt.Key.Key_Return)
    assert announced.settings == [replace(DEFAULT_INTERFACE_SETTINGS, window_width=1200)]


def test_a_number_cannot_be_set_beyond_its_limits(dialog):
    spin_box = dialog.spin_box_for("window_width")
    spin_box.setValue(1)
    assert spin_box.value() == 400
    spin_box.setValue(10 ** 6)
    assert spin_box.value() == 10000
    assert dialog.settings.window_width == 10000


# ----------------------------------------------------------------------- requirements

def test_a_setting_that_requires_another_is_greyed_while_the_other_is_off_and_keeps_its_value(dialog):
    announced = Announcements(dialog)
    dialog.show_page("Editing")
    dependent = dialog.checkbox_for("indent_after_block_opening")
    assert dependent.isEnabled()

    dialog.checkbox_for("enter_keeps_indentation").click()
    assert not dependent.isEnabled()
    assert dependent.isChecked()
    assert announced.settings[-1].indent_after_block_opening is True

    dialog.checkbox_for("enter_keeps_indentation").click()
    assert dependent.isEnabled()


def test_every_requirement_is_greyed_or_not_according_to_the_setting_it_requires(make_settings_window):
    generator = random.Random(3)
    for _ in range(20):
        settings = random_settings(generator)
        dialog = make_settings_window(settings)
        for description in SETTING_DESCRIPTIONS:
            expected = True if description.requires is None else getattr(settings, description.requires)
            assert widget_of(dialog, description).isEnabled() == expected, description.name


# ------------------------------------------------------------------------ set_settings

def test_set_settings_shows_the_settings_without_announcing_them(qtbot, dialog):
    with qtbot.assertNotEmitted(dialog.settings_changed):
        dialog.set_settings(every_feature_off())
    assert dialog.settings == every_feature_off()
    assert all(not dialog.checkbox_for(d.name).isChecked() for d in YES_OR_NO_DESCRIPTIONS)
    assert not dialog.checkbox_for("indent_after_block_opening").isEnabled()


def test_set_settings_shows_the_numbers_too(dialog):
    dialog.set_settings(replace(DEFAULT_INTERFACE_SETTINGS, window_width=1500, window_height=1000))
    assert dialog.spin_box_for("window_width").value() == 1500
    assert dialog.spin_box_for("window_height").value() == 1000


# --------------------------------------------------------------------- the buttons

def test_restore_defaults_puts_every_setting_back_and_announces_it_once(make_settings_window):
    generator = random.Random(4)
    dialog = make_settings_window(random_settings(generator))
    announced = Announcements(dialog)
    dialog.restore_defaults_button.click()
    assert announced.settings == [DEFAULT_INTERFACE_SETTINGS]
    assert dialog.settings == DEFAULT_INTERFACE_SETTINGS
    for description in SETTING_DESCRIPTIONS:
        assert value_of(widget_of(dialog, description)) == description.default, description.name


def test_restore_defaults_announces_even_when_nothing_changes(dialog):
    """It is also how a settings file that cannot be read is replaced."""
    announced = Announcements(dialog)
    dialog.restore_defaults_button.click()
    assert announced.settings == [DEFAULT_INTERFACE_SETTINGS]


def test_use_current_size_copies_the_size_of_the_window_into_the_boxes_and_announces_it_once(dialog, size_of_the_window):
    announced = Announcements(dialog)
    size_of_the_window.size = (1234, 567)
    dialog.use_current_size_button.click()
    assert dialog.spin_box_for("window_width").value() == 1234
    assert dialog.spin_box_for("window_height").value() == 567
    assert announced.settings == [replace(DEFAULT_INTERFACE_SETTINGS, window_width=1234, window_height=567)]


def test_use_current_size_keeps_a_size_that_is_too_small_or_too_large_within_the_limits(dialog, size_of_the_window):
    size_of_the_window.size = (100, 50)
    dialog.use_current_size_button.click()
    assert (dialog.settings.window_width, dialog.settings.window_height) == (400, 300)
    size_of_the_window.size = (50000, 50000)
    dialog.use_current_size_button.click()
    assert (dialog.settings.window_width, dialog.settings.window_height) == (10000, 10000)


def test_the_use_current_size_button_is_on_the_window_page_only(dialog):
    assert dialog.use_current_size_button.isVisible()
    dialog.show_page("Display")
    assert not dialog.use_current_size_button.isVisible()
    assert dialog.restore_defaults_button.isVisible()  # the buttons below the pages stay


def test_the_close_button_and_escape_close_the_window(qtbot, dialog):
    dialog.close_button.click()
    assert dialog.isHidden()
    dialog.show()
    qtbot.keyClick(dialog, Qt.Key.Key_Escape)
    assert dialog.isHidden()


def test_there_are_only_these_buttons(dialog):
    assert sorted(button.text() for button in dialog.findChildren(QPushButton)) == [
        "Close", "Restore defaults", "Use current size",
    ]


# ------------------------------------------------------------------------------ theme

def test_the_window_uses_the_theme(dialog):
    assert dialog.palette().window().color().name() == DARK_THEME.window_background
    assert dialog.palette().windowText().color().name() == DARK_THEME.default_text
    checkbox = dialog.checkbox_for("show_line_numbers")
    assert checkbox.palette().windowText().color().name() == DARK_THEME.default_text
    assert dialog.spin_box_for("window_width").palette().base().color().name() == DARK_THEME.text_background


def test_the_list_of_pages_marks_the_chosen_page_with_the_selection_colors(dialog):
    style = dialog.page_list.styleSheet()
    assert DARK_THEME.selection_background in style and DARK_THEME.selection_text in style
    assert contrast_ratio(DARK_THEME.selection_text, DARK_THEME.selection_background) >= 7
    assert contrast_ratio(DARK_THEME.default_text, DARK_THEME.panel_background) >= 7
