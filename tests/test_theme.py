"""Tests for the dark high-contrast theme."""
import re

import pytest

from mathdoer.interface.theme import DARK_THEME, Theme, contrast_ratio

MINIMUM_TEXT_CONTRAST = 7.0  # WCAG AAA for normal text
MINIMUM_BOUNDARY_CONTRAST = 3.0  # WCAG for interface boundaries


def test_contrast_ratio_matches_the_wcag_reference_values():
    assert contrast_ratio("#000000", "#ffffff") == pytest.approx(21.0)
    assert contrast_ratio("#ffffff", "#000000") == pytest.approx(21.0)
    assert contrast_ratio("#777777", "#777777") == pytest.approx(1.0)
    assert contrast_ratio("#ff0000", "#ffffff") == pytest.approx(3.998, abs=0.001)
    assert contrast_ratio("#767676", "#ffffff") == pytest.approx(4.542, abs=0.001)


def test_contrast_ratio_accepts_only_six_digit_hex_colors():
    for bad_color in ["fff", "#fff", "#gggggg", "#12345", "white"]:
        with pytest.raises(ValueError):
            contrast_ratio(bad_color, "#000000")


def test_every_theme_color_is_a_six_digit_hex_color():
    for field_name, color in vars(DARK_THEME).items():
        if field_name != "name":
            assert re.fullmatch(r"#[0-9a-f]{6}", color), field_name


@pytest.mark.parametrize("text_color_name", ["default_text", "error_text", "notice_text"])
def test_text_has_very_high_contrast_against_the_text_background(text_color_name):
    ratio = contrast_ratio(getattr(DARK_THEME, text_color_name), DARK_THEME.text_background)
    assert ratio >= MINIMUM_TEXT_CONTRAST, f"{text_color_name}: {ratio:.2f}"


def test_selected_text_has_very_high_contrast_against_the_selection():
    ratio = contrast_ratio(DARK_THEME.selection_text, DARK_THEME.selection_background)
    assert ratio >= MINIMUM_TEXT_CONTRAST


@pytest.mark.parametrize("background_name", ["window_background", "text_background"])
def test_disabled_text_is_still_easy_to_read(background_name):
    ratio = contrast_ratio(DARK_THEME.disabled_text, getattr(DARK_THEME, background_name))
    assert ratio >= 4.5, f"{background_name}: {ratio:.2f}"


def test_disabled_text_is_not_confused_with_normal_text():
    assert DARK_THEME.disabled_text != DARK_THEME.default_text


def test_line_numbers_are_as_easy_to_read_as_the_text():
    ratio = contrast_ratio(DARK_THEME.line_number_text, DARK_THEME.line_number_background)
    assert ratio >= MINIMUM_TEXT_CONTRAST, f"{ratio:.2f}"


def test_the_line_number_margin_is_set_apart_from_the_text():
    assert DARK_THEME.line_number_background != DARK_THEME.text_background


def test_indentation_guides_stand_out_from_the_text_background():
    assert contrast_ratio(DARK_THEME.indentation_guide, DARK_THEME.text_background) >= MINIMUM_BOUNDARY_CONTRAST


def test_indentation_guides_are_quieter_than_text():
    assert contrast_ratio(DARK_THEME.indentation_guide, DARK_THEME.text_background) < contrast_ratio(
        DARK_THEME.default_text, DARK_THEME.text_background
    ) / 2


def test_the_splitter_handle_stands_out_from_its_surroundings():
    for neighbour in (DARK_THEME.text_background, DARK_THEME.window_background):
        assert contrast_ratio(DARK_THEME.splitter_handle, neighbour) >= MINIMUM_BOUNDARY_CONTRAST


def test_the_theme_is_dark():
    assert contrast_ratio(DARK_THEME.text_background, "#000000") < contrast_ratio(
        DARK_THEME.text_background, "#ffffff"
    )
    assert contrast_ratio(DARK_THEME.window_background, "#000000") < 3


def test_error_notice_and_normal_text_can_be_told_apart():
    colors = {DARK_THEME.default_text, DARK_THEME.error_text, DARK_THEME.notice_text}
    assert len(colors) == 3


def test_a_theme_is_immutable():
    assert isinstance(DARK_THEME, Theme)
    with pytest.raises(AttributeError):
        DARK_THEME.default_text = "#000000"
