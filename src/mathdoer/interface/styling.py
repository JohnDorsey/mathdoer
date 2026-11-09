"""Applying a theme to widgets."""
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QMenuBar

from mathdoer.interface.theme import Theme


def window_palette(theme: Theme) -> QPalette:
    """The palette for a window and its menus. It starts from the window color, so the
    shades the style derives for borders and separators fit the theme."""
    palette = text_box_palette(QPalette(QColor(theme.window_background)), theme)
    palette.setColor(QPalette.ColorRole.Window, QColor(theme.window_background))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(theme.default_text))
    palette.setColor(QPalette.ColorRole.Button, QColor(theme.window_background))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(theme.default_text))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(theme.window_background))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(theme.default_text))
    for role in (QPalette.ColorRole.WindowText, QPalette.ColorRole.Text, QPalette.ColorRole.ButtonText):
        palette.setColor(QPalette.ColorGroup.Disabled, role, QColor(theme.disabled_text))
    return palette


def apply_menu_theme(menu_bar: QMenuBar, theme: Theme) -> None:
    """Windows gives menus palettes of their own, which the window's palette does not
    override, so the menu bar and every menu and submenu get the theme explicitly."""
    palette = window_palette(theme)
    menu_bar.setPalette(palette)
    _apply_palette_to_submenus(menu_bar, palette)


def _apply_palette_to_submenus(owner, palette: QPalette) -> None:
    for action in owner.actions():
        menu = action.menu()
        if menu is not None:
            menu.setPalette(palette)
            _apply_palette_to_submenus(menu, palette)


def text_box_palette(palette: QPalette, theme: Theme) -> QPalette:
    """The palette for a text box: its background, text and selection colors."""
    palette = QPalette(palette)
    palette.setColor(QPalette.ColorRole.Base, QColor(theme.text_background))
    palette.setColor(QPalette.ColorRole.Text, QColor(theme.default_text))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(theme.selection_background))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(theme.selection_text))
    return palette
