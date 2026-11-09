"""Tests for the interface settings: what they are, how their file holds them, and what it may contain."""
import random
import tomllib
from dataclasses import fields, replace

import pytest

from mathdoer.interface_settings import (
    DEFAULT_INTERFACE_SETTINGS,
    SETTING_DESCRIPTIONS,
    SETTINGS_PAGES,
    InterfaceSettings,
    InterfaceSettingsError,
    SettingDescription,
    descriptions_on_page,
    read_interface_settings,
    render_interface_settings,
    write_interface_settings,
)

FILE_NAME = "interface_settings.toml"

# The names are the keys of the file, so they are written out here: renaming one is a decision.
EXPECTED_NAMES = [
    "window_width",
    "window_height",
    "show_line_numbers",
    "highlight_syntax",
    "highlight_matching_brackets",
    "show_indentation_guides",
    "wrap_prompt_box_lines",
    "wrap_output_box_lines",
    "zoom_with_keys",
    "zoom_with_mouse_wheel",
    "tab_key_inserts_spaces",
    "tab_indents_selected_lines",
    "shift_tab_removes_indentation",
    "enter_keeps_indentation",
    "indent_after_block_opening",
    "home_key_goes_to_first_character",
    "toggle_comment_command",
    "duplicate_lines_command",
    "move_lines_command",
    "delete_lines_command",
    "find_and_replace_bar",
]
YES_OR_NO_DESCRIPTIONS = [description for description in SETTING_DESCRIPTIONS if description.value_type is bool]
NUMBER_DESCRIPTIONS = [description for description in SETTING_DESCRIPTIONS if description.value_type is int]


@pytest.fixture
def settings_path(tmp_path):
    return tmp_path / FILE_NAME


def read_error_for(settings_path):
    with pytest.raises(InterfaceSettingsError) as caught:
        read_interface_settings(settings_path)
    return str(caught.value)


def random_settings(generator):
    values = {}
    for description in SETTING_DESCRIPTIONS:
        if description.value_type is bool:
            values[description.name] = generator.choice([True, False])
        else:
            values[description.name] = generator.randint(description.minimum, description.maximum)
    return InterfaceSettings(**values)


# ------------------------------------------------------------------ what the settings are

def test_the_settings_are_these_in_this_order():
    assert [description.name for description in SETTING_DESCRIPTIONS] == EXPECTED_NAMES


def test_the_descriptions_cover_the_fields_of_the_class_in_order():
    assert [description.name for description in SETTING_DESCRIPTIONS] == [field.name for field in fields(InterfaceSettings)]


def test_every_feature_is_on_by_default_so_that_nothing_changes_until_one_is_turned_off():
    assert YES_OR_NO_DESCRIPTIONS
    for description in YES_OR_NO_DESCRIPTIONS:
        assert getattr(DEFAULT_INTERFACE_SETTINGS, description.name) is True, description.name


def test_the_window_starts_at_900_by_700_by_default():
    assert (DEFAULT_INTERFACE_SETTINGS.window_width, DEFAULT_INTERFACE_SETTINGS.window_height) == (900, 700)


def test_the_window_size_is_the_only_pair_of_numbers():
    assert [description.name for description in NUMBER_DESCRIPTIONS] == ["window_width", "window_height"]


def test_the_pages_are_these_in_this_order():
    assert [page.title for page in SETTINGS_PAGES] == ["Window", "Display", "Editing", "Line commands", "Find"]


def test_every_page_has_settings_and_every_setting_is_on_exactly_one_page():
    on_pages = [description.name for page in SETTINGS_PAGES for description in descriptions_on_page(page)]
    assert sorted(on_pages) == sorted(EXPECTED_NAMES)
    assert all(descriptions_on_page(page) for page in SETTINGS_PAGES)


def test_the_settings_of_a_page_keep_their_order():
    for page in SETTINGS_PAGES:
        names = [description.name for description in descriptions_on_page(page)]
        assert names == [name for name in EXPECTED_NAMES if name in names]


def test_every_setting_has_a_label_and_no_two_labels_are_alike():
    labels = [description.label for description in SETTING_DESCRIPTIONS]
    assert all(label.strip() for label in labels)
    assert len(set(labels)) == len(labels)


def test_every_page_has_a_title_and_no_two_titles_are_alike():
    titles = [page.title for page in SETTINGS_PAGES]
    assert all(title.strip() for title in titles)
    assert len(set(titles)) == len(titles)


def test_a_requirement_names_an_earlier_yes_or_no_setting_on_the_same_page():
    earlier = {}
    for description in SETTING_DESCRIPTIONS:
        if description.requires is not None:
            required = earlier[description.requires]
            assert required.value_type is bool
            assert required.page == description.page
        earlier[description.name] = description


def test_the_only_requirement_is_that_a_new_line_must_keep_the_indentation_to_add_a_level():
    requirements = {d.name: d.requires for d in SETTING_DESCRIPTIONS if d.requires is not None}
    assert requirements == {"indent_after_block_opening": "enter_keeps_indentation"}


def test_numbers_have_limits_around_their_default_and_yes_or_no_settings_have_none():
    for description in NUMBER_DESCRIPTIONS:
        assert description.minimum <= description.default <= description.maximum
    for description in YES_OR_NO_DESCRIPTIONS:
        assert description.minimum is None and description.maximum is None


def test_the_limits_of_the_window_size():
    limits = {d.name: (d.minimum, d.maximum) for d in NUMBER_DESCRIPTIONS}
    assert limits == {"window_width": (400, 10000), "window_height": (300, 10000)}


def test_the_limits_themselves_are_allowed():
    InterfaceSettings(window_width=400, window_height=300)
    InterfaceSettings(window_width=10000, window_height=10000)


def test_true_and_false_are_not_numbers_even_where_zero_and_one_are_allowed():
    """No current number setting allows 1, so this is checked on a description made for it."""
    small_number = SettingDescription(
        name="small_number", value_type=int, default=5, page=SETTINGS_PAGES[0], label="A small number",
        requires=None, minimum=0, maximum=10,
    )
    assert small_number.problem_with(1) is None
    assert small_number.problem_with(0) is None
    assert small_number.problem_with(True) is not None
    assert small_number.problem_with(False) is not None
    assert small_number.problem_with(11) is not None
    assert small_number.problem_with(5.0) is not None


@pytest.mark.parametrize(
    "name, value",
    [
        ("window_width", 399),
        ("window_width", 10001),
        ("window_height", 299),
        ("window_height", 10001),
        ("window_width", 900.0),
        ("window_width", "900"),
        ("window_width", True),
        ("show_line_numbers", 1),
        ("show_line_numbers", "true"),
        ("show_line_numbers", None),
    ],
)
def test_a_value_of_the_wrong_kind_or_outside_the_limits_cannot_be_set(name, value):
    with pytest.raises(ValueError, match=name):
        InterfaceSettings(**{name: value})


# ----------------------------------------------------------------------------- rendering

def test_the_rendered_file_is_toml_that_holds_each_setting_once():
    text = render_interface_settings(DEFAULT_INTERFACE_SETTINGS)
    assert list(tomllib.loads(text)) == EXPECTED_NAMES


def test_the_rendered_file_writes_values_as_toml_values():
    text = render_interface_settings(replace(DEFAULT_INTERFACE_SETTINGS, show_line_numbers=False, window_width=1234))
    assert "show_line_numbers = false\n" in text
    assert "window_width = 1234\n" in text
    assert "highlight_syntax = true\n" in text


def test_the_rendered_file_has_a_heading_for_each_page_and_says_the_settings_window_writes_it():
    text = render_interface_settings(DEFAULT_INTERFACE_SETTINGS)
    for page in SETTINGS_PAGES:
        assert f"\n# {page.title}\n" in text
    header = text.split("\n\n")[0]
    assert "Edit > Settings" in header
    assert "comments" in header


def test_what_is_rendered_is_read_back_exactly(settings_path):
    generator = random.Random(5)
    every_feature_off = replace(
        DEFAULT_INTERFACE_SETTINGS, **{description.name: False for description in YES_OR_NO_DESCRIPTIONS}
    )
    smallest = replace(DEFAULT_INTERFACE_SETTINGS, window_width=400, window_height=300)
    largest = replace(DEFAULT_INTERFACE_SETTINGS, window_width=10000, window_height=10000)
    cases = [DEFAULT_INTERFACE_SETTINGS, every_feature_off, smallest, largest]
    cases += [random_settings(generator) for _ in range(60)]
    for settings in cases:
        settings_path.write_text(render_interface_settings(settings), encoding="utf-8")
        assert read_interface_settings(settings_path) == settings


# ------------------------------------------------------------------------------ reading

def test_a_missing_file_means_the_defaults(settings_path):
    assert not settings_path.exists()
    assert read_interface_settings(settings_path) == DEFAULT_INTERFACE_SETTINGS


@pytest.mark.parametrize("text", ["", "\n\n", "# only a comment\n", "# show_line_numbers = false\n"])
def test_a_file_that_sets_nothing_means_the_defaults(settings_path, text):
    settings_path.write_text(text, encoding="utf-8")
    assert read_interface_settings(settings_path) == DEFAULT_INTERFACE_SETTINGS


def test_a_setting_missing_from_the_file_keeps_its_default(settings_path):
    settings_path.write_text("show_line_numbers = false\nwindow_width = 1000  # wide\n", encoding="utf-8")
    assert read_interface_settings(settings_path) == replace(
        DEFAULT_INTERFACE_SETTINGS, show_line_numbers=False, window_width=1000
    )


def test_a_byte_order_mark_at_the_start_of_the_file_is_skipped(settings_path):
    settings_path.write_bytes(b"\xef\xbb\xbf" + b"find_and_replace_bar = false\n")
    assert read_interface_settings(settings_path).find_and_replace_bar is False


@pytest.mark.parametrize(
    "text, expected",
    [
        ("show_line_numbers = 'yes'\n", "true or false"),
        ("show_line_numbers = 1\n", "true or false"),
        ("highlight_syntax = [true]\n", "true or false"),
        ("window_width = true\n", "whole number"),
        ("window_width = 900.5\n", "whole number"),
        ("window_width = '900'\n", "whole number"),
        ("window_width = 399\n", "from 400 to 10000"),
        ("window_height = 10001\n", "from 300 to 10000"),
    ],
)
def test_a_value_that_does_not_fit_is_an_error_naming_the_setting_the_file_and_what_is_allowed(
    settings_path, text, expected
):
    settings_path.write_text(text, encoding="utf-8")
    message = read_error_for(settings_path)
    assert f"'{text.split(' ')[0]}'" in message
    assert str(settings_path) in message
    assert expected in message


def test_an_unknown_setting_is_an_error_naming_it_so_a_typo_is_not_silent(settings_path):
    settings_path.write_text("show_linenumbers = true\n", encoding="utf-8")
    message = read_error_for(settings_path)
    assert "'show_linenumbers'" in message
    assert str(settings_path) in message
    assert "show_line_numbers" in message  # the settings that do exist are listed


def test_invalid_toml_is_an_error_naming_the_file_and_the_line(settings_path):
    settings_path.write_text("# first line\nshow_line_numbers = \n", encoding="utf-8")
    message = read_error_for(settings_path)
    assert str(settings_path) in message
    assert "line 2" in message


def test_a_file_that_is_not_utf8_is_an_error_naming_the_file(settings_path):
    settings_path.write_bytes(b"show_line_numbers = '\xff\xfe'\n")
    assert str(settings_path) in read_error_for(settings_path)


def test_a_path_that_cannot_be_read_is_an_error_naming_the_file(settings_path):
    settings_path.mkdir()  # a folder where the file should be
    assert str(settings_path) in read_error_for(settings_path)


# ------------------------------------------------------------------------------ writing

def test_writing_creates_the_folders_and_the_file(tmp_path):
    path = tmp_path / "one" / "two" / FILE_NAME
    settings = replace(DEFAULT_INTERFACE_SETTINGS, show_line_numbers=False)
    write_interface_settings(path, settings)
    assert read_interface_settings(path) == settings


def test_writing_replaces_the_whole_file_and_leaves_no_temporary_file_behind(settings_path, tmp_path):
    settings_path.write_text("# my notes\nshow_line_numbers = false\n", encoding="utf-8")
    write_interface_settings(settings_path, DEFAULT_INTERFACE_SETTINGS)
    assert "my notes" not in settings_path.read_text(encoding="utf-8")
    assert read_interface_settings(settings_path) == DEFAULT_INTERFACE_SETTINGS
    assert list(tmp_path.iterdir()) == [settings_path]


def test_the_file_is_written_as_utf8_with_unix_line_breaks(settings_path):
    write_interface_settings(settings_path, DEFAULT_INTERFACE_SETTINGS)
    data = settings_path.read_bytes()
    assert b"\r" not in data
    data.decode("utf-8")


def test_a_write_that_fails_raises_and_leaves_no_temporary_file_behind(settings_path, tmp_path):
    settings_path.mkdir()  # a folder where the file should be
    with pytest.raises(OSError):
        write_interface_settings(settings_path, DEFAULT_INTERFACE_SETTINGS)
    assert list(tmp_path.iterdir()) == [settings_path]
