"""Tests for the Edit, Constants and Units menus."""
import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QGuiApplication, QPalette, QTextCursor
from PySide6.QtWidgets import QApplication, QMenu

from mathdoer.interface.theme import DARK_THEME
from mathdoer.languages.python import PYTHON
from mathdoer.registry import load_registry

REGISTRY = load_registry()
SHIFT = Qt.KeyboardModifier.ShiftModifier
NO_MODIFIER = Qt.KeyboardModifier.NoModifier


def top_level_menu(window, title):
    for action in window.menuBar().actions():
        if action.text() == title:
            return action.menu()
    raise AssertionError(f"no menu titled {title!r}")


def action_named(menu, text):
    for action in menu.actions():
        if action.text().split("\t")[0] == text:
            return action
    raise AssertionError(f"no action {text!r} in {[a.text() for a in menu.actions()]}")


def submenu_named(menu, title):
    for action in menu.actions():
        if action.menu() is not None and action.text() == title:
            return action.menu()
    raise AssertionError(f"no submenu {title!r}")


def constant_action(window, entry):
    return action_named(top_level_menu(window, "Constants"), f"{entry.label} [{entry.unit}]")


def unit_action(window, entry):
    return action_named(submenu_named(top_level_menu(window, "Units"), entry.category), entry.label)


def open_menu(menu):
    menu.aboutToShow.emit()


def select(box, start, end):
    cursor = box.textCursor()
    cursor.setPosition(start)
    cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
    box.setTextCursor(cursor)


def clipboard_text():
    return QGuiApplication.clipboard().text()


def set_clipboard_text(text):
    QGuiApplication.clipboard().setText(text)


@pytest.fixture
def shift_held(make_window):
    return make_window(keyboard_modifiers=lambda: SHIFT)


# --------------------------------------------------------------------- the menu bar

def test_the_menu_bar_has_edit_constants_and_units_in_that_order(window):
    assert [action.text() for action in window.menuBar().actions()] == ["Edit", "Constants", "Units"]


def test_the_menus_use_the_theme(window):
    assert window.palette().window().color().name() == DARK_THEME.window_background
    assert window.menuBar().palette().window().color().name() == DARK_THEME.window_background
    assert window.palette().highlight().color().name() == DARK_THEME.selection_background


@pytest.fixture
def system_menu_palettes(qapp):
    """What Windows does: it registers its own palettes for menus, which a window's palette
    does not override. Here they are loud green with black text, so any leak is obvious."""
    system_palette = QPalette()
    for role in (QPalette.ColorRole.Window, QPalette.ColorRole.Highlight):
        system_palette.setColor(role, QColor("#00ff00"))
    for role in (QPalette.ColorRole.WindowText, QPalette.ColorRole.HighlightedText):
        system_palette.setColor(role, QColor("#000000"))
    originals = {name: QApplication.palette(name) for name in ("QMenu", "QMenuBar")}
    for name in originals:
        QApplication.setPalette(system_palette, name)
    yield
    for name, palette in originals.items():
        QApplication.setPalette(palette, name)


def menus_in(menu_or_bar):
    """Every menu below a menu bar or a menu, submenus included."""
    for action in menu_or_bar.actions():
        if action.menu() is not None:
            yield action.menu()
            yield from menus_in(action.menu())


def test_every_menu_uses_the_theme_whatever_the_system_palettes_are(system_menu_palettes, window):
    menus = list(menus_in(window.menuBar()))
    assert len(menus) == 3 + len(REGISTRY.unit_categories())  # Edit, Constants, Units, their submenus
    for widget in [window.menuBar(), *menus]:
        name = widget.title() if isinstance(widget, QMenu) else "the menu bar"
        palette = widget.palette()
        assert palette.window().color().name() == DARK_THEME.window_background, name
        assert palette.windowText().color().name() == DARK_THEME.default_text, name
        assert palette.highlight().color().name() == DARK_THEME.selection_background, name
        assert palette.highlightedText().color().name() == DARK_THEME.selection_text, name


# ------------------------------------------------------- Constants and Units menus

def test_the_constants_menu_lists_every_constant_with_its_unit_in_order(window):
    menu = top_level_menu(window, "Constants")
    assert [action.text() for action in menu.actions()] == [
        f"{entry.label} [{entry.unit}]" for entry in REGISTRY.constants
    ]
    assert len(menu.actions()) == 20


def test_the_units_menu_has_a_submenu_per_category_in_order(window):
    menu = top_level_menu(window, "Units")
    assert [action.text() for action in menu.actions()] == list(REGISTRY.unit_categories())
    assert all(action.menu() is not None for action in menu.actions())
    assert len(menu.actions()) == 9


def test_each_units_submenu_lists_its_units_in_order(window):
    units_menu = top_level_menu(window, "Units")
    for category in REGISTRY.unit_categories():
        assert [action.text() for action in submenu_named(units_menu, category).actions()] == [
            unit.label for unit in REGISTRY.units_in_category(category)
        ]


def test_the_menus_come_from_the_registry_the_run_settings_name(make_window, tmp_path):
    registry_path = tmp_path / "small_registry.toml"
    registry_path.write_text(
        "format_version = 1\n\n"
        '[[constants]]\nname = "ONLY_CONSTANT"\nlabel = "Only constant"\nunit = "m"\n'
        'value = "1"\nbasis = "exact"\nsource = "test"\n\n'
        '[[units]]\nname = "ONLY_UNIT"\nlabel = "only unit"\ncategory = "Only category"\n'
        'value = "2"\nbasis = "exact"\nsource = "test"\n',
        encoding="utf-8",
    )
    window = make_window(registry_path=registry_path)
    assert [a.text() for a in top_level_menu(window, "Constants").actions()] == ["Only constant [m]"]
    assert [a.text() for a in top_level_menu(window, "Units").actions()] == ["Only category"]


def test_choosing_an_item_inserts_its_name_at_the_cursor(window):
    window.prompt_box.setPlainText("2 *  + 1")
    cursor = window.prompt_box.textCursor()
    cursor.setPosition(4)
    window.prompt_box.setTextCursor(cursor)
    constant_action(window, REGISTRY.entry_named("SPEED_OF_LIGHT")).trigger()
    assert window.prompt_box.toPlainText() == "2 * SPEED_OF_LIGHT + 1"
    assert window.prompt_box.textCursor().position() == len("2 * SPEED_OF_LIGHT")


def test_choosing_a_unit_inserts_its_name(window):
    unit_action(window, REGISTRY.entry_named("INCH")).trigger()
    assert window.prompt_box.toPlainText() == "INCH"


def test_choosing_an_item_replaces_the_selection(window):
    window.prompt_box.setPlainText("10 * oops")
    select(window.prompt_box, 5, 9)
    unit_action(window, REGISTRY.entry_named("FOOT")).trigger()
    assert window.prompt_box.toPlainText() == "10 * FOOT"


def test_choosing_an_item_returns_the_focus_to_the_prompt_box(window):
    window.output_box.setFocus()
    unit_action(window, REGISTRY.entry_named("YARD")).trigger()
    assert window.focusWidget() is window.prompt_box


def test_choosing_with_shift_held_inserts_the_literal_value(shift_held):
    constant_action(shift_held, REGISTRY.entry_named("SPEED_OF_LIGHT")).trigger()
    assert shift_held.prompt_box.toPlainText() == "299792458"
    shift_held.prompt_box.clear()
    unit_action(shift_held, REGISTRY.entry_named("KNOT")).trigger()
    assert shift_held.prompt_box.toPlainText() == "(1852/3600)"


def test_shift_combined_with_other_keys_still_inserts_the_literal(make_window):
    window = make_window(keyboard_modifiers=lambda: SHIFT | Qt.KeyboardModifier.ControlModifier)
    unit_action(window, REGISTRY.entry_named("INCH")).trigger()
    assert window.prompt_box.toPlainText() == "0.0254"


def test_other_modifiers_alone_insert_the_name(make_window):
    window = make_window(keyboard_modifiers=lambda: Qt.KeyboardModifier.ControlModifier)
    unit_action(window, REGISTRY.entry_named("INCH")).trigger()
    assert window.prompt_box.toPlainText() == "INCH"


def test_every_item_inserts_its_language_name_or_literal(make_window):
    for modifiers, format_text in ((NO_MODIFIER, PYTHON.format_name), (SHIFT, PYTHON.format_literal)):
        window = make_window(keyboard_modifiers=lambda modifiers=modifiers: modifiers)
        for entry in REGISTRY.constants:
            window.prompt_box.clear()
            constant_action(window, entry).trigger()
            assert window.prompt_box.toPlainText() == format_text(entry), entry.name
        for entry in REGISTRY.units:
            window.prompt_box.clear()
            unit_action(window, entry).trigger()
            assert window.prompt_box.toPlainText() == format_text(entry), entry.name


def test_by_default_the_modifiers_of_the_latest_input_decide(qtbot, window):
    # Qt remembers the modifiers of the most recent key or mouse event; a click on a menu
    # item is that event, so Shift+click is seen. (The spike on real Windows confirmed it.)
    inch = REGISTRY.entry_named("INCH")
    qtbot.keyClick(window.prompt_box, Qt.Key.Key_A, NO_MODIFIER)
    window.prompt_box.clear()
    unit_action(window, inch).trigger()
    assert window.prompt_box.toPlainText() == "INCH"

    qtbot.keyClick(window.prompt_box, Qt.Key.Key_A, SHIFT)
    window.prompt_box.clear()
    unit_action(window, inch).trigger()
    assert window.prompt_box.toPlainText() == "0.0254"


# ------------------------------------------------------------------------ Edit menu

def test_the_edit_menu_is_laid_out_in_groups(window):
    menu = top_level_menu(window, "Edit")
    layout = ["-" if action.isSeparator() else action.text().split("\t")[0] for action in menu.actions()]
    assert layout == [
        "Undo", "Redo", "-",
        "Cut", "Copy", "Paste", "Select all", "-",
        "Copy output", "-",
        "Edit startup file", "Edit settings",
    ]


def test_shortcut_hints_are_shown_but_are_not_real_shortcuts(window):
    menu = top_level_menu(window, "Edit")
    hints = {
        "Undo": "Ctrl+Z", "Redo": "Ctrl+Y", "Cut": "Ctrl+X", "Copy": "Ctrl+C",
        "Paste": "Ctrl+V", "Select all": "Ctrl+A",
    }
    for name, hint in hints.items():
        action = action_named(menu, name)
        assert action.text() == f"{name}\t{hint}"
        assert action.shortcut().isEmpty(), name  # the text boxes handle these keys themselves
    for name in ("Copy output", "Edit startup file", "Edit settings"):
        assert "\t" not in action_named(menu, name).text()


def test_undo_and_redo_work_on_the_prompt(qtbot, window):
    menu = top_level_menu(window, "Edit")
    qtbot.keyClicks(window.prompt_box, "abc")
    action_named(menu, "Undo").trigger()
    assert window.prompt_box.toPlainText() != "abc"
    action_named(menu, "Redo").trigger()
    assert window.prompt_box.toPlainText() == "abc"


def test_undo_and_redo_are_enabled_only_when_there_is_something_to_do(qtbot, window):
    menu = top_level_menu(window, "Edit")
    open_menu(menu)
    assert not action_named(menu, "Undo").isEnabled()
    assert not action_named(menu, "Redo").isEnabled()
    qtbot.keyClicks(window.prompt_box, "abc")
    open_menu(menu)
    assert action_named(menu, "Undo").isEnabled()
    action_named(menu, "Undo").trigger()
    open_menu(menu)
    assert action_named(menu, "Redo").isEnabled()


def test_cut_copy_and_paste_work_on_the_prompt(window):
    menu = top_level_menu(window, "Edit")
    window.prompt_box.setPlainText("hello world")
    select(window.prompt_box, 0, 5)
    action_named(menu, "Copy").trigger()
    assert clipboard_text() == "hello"
    action_named(menu, "Cut").trigger()
    assert window.prompt_box.toPlainText() == " world"
    cursor = window.prompt_box.textCursor()
    cursor.movePosition(QTextCursor.MoveOperation.End)
    window.prompt_box.setTextCursor(cursor)
    action_named(menu, "Paste").trigger()
    assert window.prompt_box.toPlainText() == " worldhello"


def test_cut_and_copy_are_enabled_only_with_a_selection(window):
    menu = top_level_menu(window, "Edit")
    window.prompt_box.setPlainText("hello")
    open_menu(menu)
    assert not action_named(menu, "Cut").isEnabled()
    assert not action_named(menu, "Copy").isEnabled()
    select(window.prompt_box, 0, 3)
    open_menu(menu)
    assert action_named(menu, "Cut").isEnabled()
    assert action_named(menu, "Copy").isEnabled()


def test_paste_is_enabled_only_when_there_is_text_to_paste(window):
    menu = top_level_menu(window, "Edit")
    set_clipboard_text("")
    open_menu(menu)
    assert not action_named(menu, "Paste").isEnabled()
    set_clipboard_text("something")
    open_menu(menu)
    assert action_named(menu, "Paste").isEnabled()


def test_select_all_acts_on_the_box_that_has_the_focus(window):
    menu = top_level_menu(window, "Edit")
    window.prompt_box.setPlainText("in the prompt")
    window.output_box.apply_changes(segments=[("in the output", False)])

    window.prompt_box.setFocus()
    action_named(menu, "Select all").trigger()
    assert window.prompt_box.textCursor().selectedText() == "in the prompt"

    window.output_box.setFocus()
    action_named(menu, "Select all").trigger()
    assert window.output_box.textCursor().selectedText() == "in the output"
    assert window.focusWidget() is window.output_box


def test_select_all_remembers_the_box_that_had_the_focus_while_the_menu_bar_has_it(window):
    # Opening a menu from the keyboard moves the focus to the menu bar.
    menu = top_level_menu(window, "Edit")
    window.prompt_box.setPlainText("in the prompt")
    window.output_box.apply_changes(segments=[("in the output", False)])
    window.output_box.setFocus()
    window.menuBar().setFocus(Qt.FocusReason.MenuBarFocusReason)
    assert QApplication.focusWidget() is window.menuBar()
    action_named(menu, "Select all").trigger()
    assert window.output_box.textCursor().selectedText() == "in the output"
    assert window.prompt_box.textCursor().selectedText() == ""


def test_copy_acts_on_the_output_box_when_it_had_the_focus(window):
    menu = top_level_menu(window, "Edit")
    window.prompt_box.setPlainText("prompt text")
    window.output_box.apply_changes(segments=[("output text", False)])
    window.output_box.setFocus()
    window.output_box.selectAll()
    open_menu(menu)
    assert action_named(menu, "Copy").isEnabled()
    action_named(menu, "Copy").trigger()
    assert clipboard_text() == "output text"


def test_select_all_is_disabled_when_the_active_box_is_empty(window):
    menu = top_level_menu(window, "Edit")
    open_menu(menu)
    assert not action_named(menu, "Select all").isEnabled()
    window.prompt_box.setPlainText("x")
    open_menu(menu)
    assert action_named(menu, "Select all").isEnabled()


def test_paste_goes_into_the_prompt_even_when_the_output_box_had_the_focus(window):
    menu = top_level_menu(window, "Edit")
    set_clipboard_text("pasted")
    window.output_box.setFocus()
    action_named(menu, "Paste").trigger()
    assert window.prompt_box.toPlainText() == "pasted"
    assert window.focusWidget() is window.prompt_box


def test_copy_output_copies_what_is_shown_without_the_progress_line(window):
    menu = top_level_menu(window, "Edit")
    window.output_box.apply_changes(segments=[("abc\n", False)], progress_text="/ 00:05")
    action_named(menu, "Copy output").trigger()
    assert clipboard_text() == "abc\n"


def test_copy_output_is_disabled_until_there_is_output(window):
    menu = top_level_menu(window, "Edit")
    open_menu(menu)
    assert not action_named(menu, "Copy output").isEnabled()
    window.output_box.apply_changes(progress_text="/")
    open_menu(menu)
    assert not action_named(menu, "Copy output").isEnabled()
    window.output_box.apply_changes(segments=[("result\n", False)])
    open_menu(menu)
    assert action_named(menu, "Copy output").isEnabled()


# -------------------------------------------------------------------- startup file

def test_edit_startup_file_is_always_enabled(window):
    menu = top_level_menu(window, "Edit")
    open_menu(menu)
    assert action_named(menu, "Edit startup file").isEnabled()


def test_edit_startup_file_opens_the_startup_file_in_the_text_editor(make_window, make_python_run_settings):
    opened = []
    window = make_window(open_in_text_editor=opened.append)
    action_named(top_level_menu(window, "Edit"), "Edit startup file").trigger()
    assert opened == [window.startup_path]


def test_edit_startup_file_recreates_a_missing_startup_file_from_the_default(make_window):
    opened = []
    window = make_window(startup_text=None, open_in_text_editor=opened.append)
    assert not window.startup_path.exists()
    action_named(top_level_menu(window, "Edit"), "Edit startup file").trigger()
    assert window.startup_path.read_text(encoding="utf-8") == PYTHON.default_startup_path.read_text(
        encoding="utf-8"
    )
    assert opened == [window.startup_path]


def test_edit_startup_file_leaves_an_existing_startup_file_alone(make_window):
    window = make_window(startup_text="MINE = 1\n", open_in_text_editor=lambda path: None)
    action_named(top_level_menu(window, "Edit"), "Edit startup file").trigger()
    assert window.startup_path.read_text(encoding="utf-8") == "MINE = 1\n"


def test_the_progress_line_returns_after_a_status_message_during_a_run(qtbot, make_window):
    def cannot_open(path):
        raise OSError("no editor")

    window = make_window(open_in_text_editor=cannot_open)
    window.prompt_box.setPlainText("import time\ntime.sleep(120)")
    window.run_prompt()
    assert window.output_box.toPlainText() == "/"
    action_named(top_level_menu(window, "Edit"), "Edit startup file").trigger()
    message = "[could not open the startup file: no editor]"
    assert window.output_box.toPlainText() == message
    window.poll_run()
    assert window.output_box.toPlainText() == message + "\n/"
    window.cancel_run()
    qtbot.waitUntil(lambda: not window.is_running, timeout=30000)


def test_a_failure_to_open_the_editor_is_reported_in_the_output_box(make_window):
    def cannot_open(path):
        raise OSError("no editor is installed")

    window = make_window(open_in_text_editor=cannot_open)
    action_named(top_level_menu(window, "Edit"), "Edit startup file").trigger()
    assert window.output_box.toPlainText() == "[could not open the startup file: no editor is installed]"


# ------------------------------------------------------------------------- settings

def test_edit_settings_is_always_enabled(window):
    menu = top_level_menu(window, "Edit")
    open_menu(menu)
    assert action_named(menu, "Edit settings").isEnabled()


def test_edit_settings_creates_the_settings_file_from_the_default_and_opens_it(make_window):
    opened = []
    window = make_window(open_in_text_editor=opened.append)
    assert not window.settings_path.exists()
    action_named(top_level_menu(window, "Edit"), "Edit settings").trigger()
    assert window.settings_path.name == "settings_python.toml"
    assert window.settings_path.read_text(encoding="utf-8") == PYTHON.default_settings_path.read_text(
        encoding="utf-8"
    )
    assert opened == [window.settings_path]


def test_edit_settings_does_not_touch_the_startup_file(make_window):
    opened = []
    window = make_window(startup_text="MINE = 1\n", open_in_text_editor=opened.append)
    action_named(top_level_menu(window, "Edit"), "Edit settings").trigger()
    assert opened != [window.startup_path]
    assert window.startup_path.read_text(encoding="utf-8") == "MINE = 1\n"


def test_edit_settings_leaves_an_existing_settings_file_alone(make_window):
    opened = []
    window = make_window(settings_text="# mine\n", open_in_text_editor=opened.append)
    action_named(top_level_menu(window, "Edit"), "Edit settings").trigger()
    assert window.settings_path.read_text(encoding="utf-8") == "# mine\n"
    assert opened == [window.settings_path]


def test_a_failure_to_open_the_settings_file_is_reported_in_the_output_box(make_window):
    def cannot_open(path):
        raise OSError("no editor is installed")

    window = make_window(open_in_text_editor=cannot_open)
    action_named(top_level_menu(window, "Edit"), "Edit settings").trigger()
    assert window.output_box.toPlainText() == "[could not open the settings file: no editor is installed]"
