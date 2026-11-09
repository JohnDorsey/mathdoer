"""Tests for the dark high-contrast theme."""
import re

import pytest

from mathdoer.interface.theme import DARK_THEME, Theme, contrast_ratio
from mathdoer.syntax import TokenKind

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


def every_color(theme):
    """Each color of a theme with its name, those for kinds of text included."""
    for field_name, value in vars(theme).items():
        if field_name == "token_colors":
            for kind, color in value.items():
                yield f"token_colors[{kind.name}]", color
        elif field_name != "name":
            yield field_name, value


def test_every_theme_color_is_a_six_digit_hex_color():
    colors = dict(every_color(DARK_THEME))
    assert len(colors) > 20
    for name, color in colors.items():
        assert re.fullmatch(r"#[0-9a-f]{6}", color), name


def test_every_kind_of_text_has_a_color():
    assert set(DARK_THEME.token_colors) == set(TokenKind)


@pytest.mark.parametrize("kind", list(TokenKind), ids=lambda kind: kind.name)
def test_every_kind_of_text_is_as_easy_to_read_as_ordinary_text(kind):
    ratio = contrast_ratio(DARK_THEME.token_colors[kind], DARK_THEME.text_background)
    assert ratio >= MINIMUM_TEXT_CONTRAST, f"{kind.name}: {ratio:.2f}"


def test_the_kinds_of_text_can_be_told_apart():
    colors = {kind: color for kind, color in DARK_THEME.token_colors.items() if kind is not TokenKind.OPERATOR}
    assert len(set(colors.values())) == len(colors)
    assert DARK_THEME.default_text not in colors.values()


def test_operators_look_like_ordinary_text():
    assert DARK_THEME.token_colors[TokenKind.OPERATOR] == DARK_THEME.default_text


def test_the_highlighted_brackets_keep_the_text_readable_and_stand_apart():
    assert contrast_ratio(DARK_THEME.default_text, DARK_THEME.matching_bracket_background) >= MINIMUM_TEXT_CONTRAST
    assert DARK_THEME.matching_bracket_background not in (
        DARK_THEME.text_background, DARK_THEME.selection_background,
    )
    assert contrast_ratio(DARK_THEME.matching_bracket_background, DARK_THEME.text_background) >= 2


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
