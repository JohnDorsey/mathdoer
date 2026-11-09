"""Tests for turning a theme into Qt palettes."""
from PySide6.QtGui import QPalette

from mathdoer.interface.styling import text_box_palette, window_palette
from mathdoer.interface.theme import DARK_THEME

ACTIVE = QPalette.ColorGroup.Active
DISABLED = QPalette.ColorGroup.Disabled
ROLE = QPalette.ColorRole


def test_the_window_palette_colors_the_window_and_its_text(qapp):
    palette = window_palette(DARK_THEME)
    assert palette.color(ACTIVE, ROLE.Window).name() == DARK_THEME.window_background
    assert palette.color(ACTIVE, ROLE.WindowText).name() == DARK_THEME.default_text
    assert palette.color(ACTIVE, ROLE.Button).name() == DARK_THEME.window_background
    assert palette.color(ACTIVE, ROLE.ButtonText).name() == DARK_THEME.default_text
    assert palette.color(ACTIVE, ROLE.Base).name() == DARK_THEME.text_background
    assert palette.color(ACTIVE, ROLE.Text).name() == DARK_THEME.default_text


def test_the_window_palette_uses_the_selection_colors_for_menu_highlights(qapp):
    palette = window_palette(DARK_THEME)
    assert palette.color(ACTIVE, ROLE.Highlight).name() == DARK_THEME.selection_background
    assert palette.color(ACTIVE, ROLE.HighlightedText).name() == DARK_THEME.selection_text


def test_disabled_items_use_the_disabled_text_color(qapp):
    palette = window_palette(DARK_THEME)
    for role in (ROLE.WindowText, ROLE.Text, ROLE.ButtonText):
        assert palette.color(DISABLED, role).name() == DARK_THEME.disabled_text, role


def test_the_text_box_palette_colors_a_box(qapp):
    palette = text_box_palette(QPalette(), DARK_THEME)
    assert palette.base().color().name() == DARK_THEME.text_background
    assert palette.text().color().name() == DARK_THEME.default_text


def test_the_text_box_palette_leaves_the_palette_it_was_given_alone(qapp):
    original = QPalette()
    before = original.color(ACTIVE, ROLE.Base).name()
    text_box_palette(original, DARK_THEME)
    assert original.color(ACTIVE, ROLE.Base).name() == before


def test_the_window_palette_derives_its_borders_from_the_window_color(qapp):
    palette = window_palette(DARK_THEME)
    # Shades for borders and separators: darker or lighter than the window, never the system's.
    assert palette.color(ACTIVE, ROLE.Dark).lightness() < palette.color(ACTIVE, ROLE.Window).lightness()
    assert palette.color(ACTIVE, ROLE.Light).lightness() > palette.color(ACTIVE, ROLE.Window).lightness()
