"""The Constants and Units menus, built from the registry."""
from collections.abc import Callable

from PySide6.QtWidgets import QMenu, QMenuBar

from mathdoer.registry import Registry, RegistryEntry


def add_registry_menus(
    menu_bar: QMenuBar, registry: Registry, choose_entry: Callable[[RegistryEntry], None]
) -> None:
    """Add a Constants menu and a Units menu with a submenu for each category."""
    constants_menu = menu_bar.addMenu("Constants")
    for constant in registry.constants:
        _add_choice(constants_menu, f"{constant.label} [{constant.unit}]", constant, choose_entry)

    units_menu = menu_bar.addMenu("Units")
    for category in registry.unit_categories():
        category_menu = units_menu.addMenu(category)
        for unit in registry.units_in_category(category):
            _add_choice(category_menu, unit.label, unit, choose_entry)


def _add_choice(
    menu: QMenu, text: str, entry: RegistryEntry, choose_entry: Callable[[RegistryEntry], None]
) -> None:
    action = menu.addAction(text)
    action.triggered.connect(lambda checked=False, entry=entry: choose_entry(entry))
