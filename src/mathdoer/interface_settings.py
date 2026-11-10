"""The user's choices about the interface: which editor features are on, the size the window
opens at, the font of each box and the width of a tab.

Each setting is a field of InterfaceSettings, and the field says everything else about it too:
the page of the settings window it is on, its label there, and its limits. The window, the
file and the checks on both are made from these fields, so a new setting is one line here.

The settings are kept in a TOML file that the settings window rewrites whenever one changes.
Every feature is on by default, so nothing changes until the user turns one off.
"""
import os
import tomllib
from dataclasses import dataclass, field, fields
from pathlib import Path

from mathdoer.toml_files import read_toml_file

DEFAULT_WINDOW_WIDTH = 900
DEFAULT_WINDOW_HEIGHT = 700
MINIMUM_WINDOW_WIDTH = 400
MINIMUM_WINDOW_HEIGHT = 300
MAXIMUM_WINDOW_SIZE = 10000  # pixels; a window larger than the screen is fitted to it when it opens
DEFAULT_FONT_FAMILY = "Consolas"  # where it is not installed, the fonts that interface.fonts falls back to
DEFAULT_POINT_SIZE = 11
MINIMUM_POINT_SIZE = 6
MAXIMUM_POINT_SIZE = 72
DEFAULT_TAB_WIDTH = 4
MINIMUM_TAB_WIDTH = 1
MAXIMUM_TAB_WIDTH = 16  # characters

FILE_HEADER = (
    "# mathdoer interface settings.\n"
    "#\n"
    "# The Settings window (Edit > Settings) writes this file whenever a setting changes and replaces\n"
    "# all of it, so comments added here are lost. mathdoer reads the file when it starts.\n"
)


class InterfaceSettingsError(Exception):
    """The settings file cannot be used. The message is for the user: it names the file
    and says what is wrong."""


@dataclass(frozen=True)
class SettingsPage:
    """A page of the settings window. The note is shown at the top of the page."""

    title: str
    note: str = ""


WINDOW_PAGE = SettingsPage(
    "Window",
    "The size the window has when mathdoer starts. A change applies the next time mathdoer starts.",
)
DISPLAY_PAGE = SettingsPage("Display")
FONTS_PAGE = SettingsPage(
    "Fonts",
    "Pick a font from the list or type the name of one. A font that is not installed is replaced by "
    "Consolas or, failing that, another monospace font. Zooming (Ctrl and + or -) changes the size until "
    "Ctrl+0 puts it back to the size set here.",
)
EDITING_PAGE = SettingsPage("Editing")
LINE_COMMANDS_PAGE = SettingsPage("Line commands")
FIND_PAGE = SettingsPage("Find")
SETTINGS_PAGES = (WINDOW_PAGE, DISPLAY_PAGE, FONTS_PAGE, EDITING_PAGE, LINE_COMMANDS_PAGE, FIND_PAGE)


def _setting(default, page, label, *, requires=None, minimum=None, maximum=None):
    """The field of a setting. A setting that requires another has no effect while that one is off."""
    return field(
        default=default,
        metadata={"page": page, "label": label, "requires": requires, "minimum": minimum, "maximum": maximum},
    )


@dataclass(frozen=True)
class InterfaceSettings:
    """The names of the fields are the keys of the settings file."""

    window_width: int = _setting(
        DEFAULT_WINDOW_WIDTH, WINDOW_PAGE, "Width in pixels",
        minimum=MINIMUM_WINDOW_WIDTH, maximum=MAXIMUM_WINDOW_SIZE,
    )
    window_height: int = _setting(
        DEFAULT_WINDOW_HEIGHT, WINDOW_PAGE, "Height in pixels",
        minimum=MINIMUM_WINDOW_HEIGHT, maximum=MAXIMUM_WINDOW_SIZE,
    )

    show_line_numbers: bool = _setting(True, DISPLAY_PAGE, "Show line numbers")
    highlight_syntax: bool = _setting(True, DISPLAY_PAGE, "Color keywords, strings, comments and numbers")
    highlight_matching_brackets: bool = _setting(
        True, DISPLAY_PAGE, "Highlight the bracket that matches the one next to the caret"
    )
    show_indentation_guides: bool = _setting(True, DISPLAY_PAGE, "Show a vertical guide at each level of indentation")
    wrap_prompt_box_lines: bool = _setting(True, DISPLAY_PAGE, "Wrap long lines in the prompt box (Alt+Z)")
    wrap_output_box_lines: bool = _setting(True, DISPLAY_PAGE, "Wrap long lines in the output box (Alt+Z)")
    zoom_with_keys: bool = _setting(True, DISPLAY_PAGE, "Zoom with Ctrl and +, - or 0")
    zoom_with_mouse_wheel: bool = _setting(True, DISPLAY_PAGE, "Zoom with Ctrl and the mouse wheel")

    prompt_box_font_family: str = _setting(DEFAULT_FONT_FAMILY, FONTS_PAGE, "Prompt box font")
    prompt_box_font_size: int = _setting(
        DEFAULT_POINT_SIZE, FONTS_PAGE, "Prompt box font size in points",
        minimum=MINIMUM_POINT_SIZE, maximum=MAXIMUM_POINT_SIZE,
    )
    output_box_font_family: str = _setting(DEFAULT_FONT_FAMILY, FONTS_PAGE, "Output box font")
    output_box_font_size: int = _setting(
        DEFAULT_POINT_SIZE, FONTS_PAGE, "Output box font size in points",
        minimum=MINIMUM_POINT_SIZE, maximum=MAXIMUM_POINT_SIZE,
    )

    tab_width: int = _setting(
        DEFAULT_TAB_WIDTH, EDITING_PAGE, "Tab width in characters (the width of one level of indentation)",
        minimum=MINIMUM_TAB_WIDTH, maximum=MAXIMUM_TAB_WIDTH,
    )
    single_line_mode: bool = _setting(
        False, EDITING_PAGE,
        "Single-line mode: Enter runs, Alt+Enter starts a new line (off: Ctrl+Enter runs)",
    )
    tab_key_inserts_spaces: bool = _setting(
        True, EDITING_PAGE, "Tab inserts spaces (turned off, Tab inserts a tab character)"
    )
    tab_indents_selected_lines: bool = _setting(True, EDITING_PAGE, "Tab indents every selected line")
    shift_tab_removes_indentation: bool = _setting(
        True, EDITING_PAGE, "Shift+Tab removes one level of indentation"
    )
    enter_keeps_indentation: bool = _setting(True, EDITING_PAGE, "Enter keeps the indentation of the line above")
    indent_after_block_opening: bool = _setting(
        True, EDITING_PAGE, "Enter adds one level after a line that opens a block",
        requires="enter_keeps_indentation",
    )
    home_key_goes_to_first_character: bool = _setting(
        True, EDITING_PAGE, "Home goes to the first character of the line, then to its start"
    )

    toggle_comment_command: bool = _setting(True, LINE_COMMANDS_PAGE, "Comment or uncomment the lines (Ctrl+/)")
    duplicate_lines_command: bool = _setting(True, LINE_COMMANDS_PAGE, "Duplicate the lines (Ctrl+D)")
    move_lines_command: bool = _setting(True, LINE_COMMANDS_PAGE, "Move the lines up or down (Alt+Up, Alt+Down)")
    delete_lines_command: bool = _setting(True, LINE_COMMANDS_PAGE, "Delete the lines (Ctrl+Shift+K)")

    find_and_replace_bar: bool = _setting(
        True, FIND_PAGE, "Find and replace bar (Ctrl+F, Ctrl+H, F3, Shift+F3)"
    )

    def __post_init__(self):
        for description in SETTING_DESCRIPTIONS:
            value = getattr(self, description.name)
            problem = description.problem_with(value)
            if problem:
                raise ValueError(f"{description.name} {problem}, not {value!r}")


@dataclass(frozen=True)
class SettingDescription:
    """What a setting is, for the settings window and the file: read from the field."""

    name: str
    value_type: type  # bool for a feature that is on or off, int for a number, str for a font name
    default: bool | int | str
    page: SettingsPage
    label: str
    requires: str | None
    minimum: int | None
    maximum: int | None

    def problem_with(self, value: object) -> str | None:
        """Why the value cannot be this setting's, or None if it can."""
        if self.value_type is bool:
            return None if isinstance(value, bool) else "must be true or false"
        if self.value_type is str:
            return None if isinstance(value, str) and value else "must be the name of a font, in quotes"
        is_a_whole_number = isinstance(value, int) and not isinstance(value, bool)
        if is_a_whole_number and self.minimum <= value <= self.maximum:
            return None
        return f"must be a whole number from {self.minimum} to {self.maximum}"


def _describe(setting_field) -> SettingDescription:
    metadata = setting_field.metadata
    return SettingDescription(
        name=setting_field.name,
        value_type=setting_field.type,
        default=setting_field.default,
        page=metadata["page"],
        label=metadata["label"],
        requires=metadata["requires"],
        minimum=metadata["minimum"],
        maximum=metadata["maximum"],
    )


SETTING_DESCRIPTIONS = tuple(_describe(setting_field) for setting_field in fields(InterfaceSettings))
DEFAULT_INTERFACE_SETTINGS = InterfaceSettings()


def descriptions_on_page(page: SettingsPage) -> tuple[SettingDescription, ...]:
    return tuple(description for description in SETTING_DESCRIPTIONS if description.page == page)


# ----------------------------------------------------------------------------- the file

def read_interface_settings(path: Path) -> InterfaceSettings:
    """The settings in the file; the defaults for those it does not mention, and for all of
    them when there is no file. Raises InterfaceSettingsError."""
    try:
        contents = read_toml_file(path)
    except FileNotFoundError:
        return DEFAULT_INTERFACE_SETTINGS
    except (tomllib.TOMLDecodeError, OSError, UnicodeDecodeError) as error:
        raise InterfaceSettingsError(f"Cannot read the interface settings file {path}: {error}.") from error

    descriptions = {description.name: description for description in SETTING_DESCRIPTIONS}
    unknown_names = [name for name in contents if name not in descriptions]
    if unknown_names:
        names = ", ".join(f"'{name}'" for name in sorted(unknown_names))
        raise InterfaceSettingsError(
            f"Unknown setting {names} in {path}. The settings are: {', '.join(descriptions)}."
        )
    for name, value in contents.items():
        problem = descriptions[name].problem_with(value)
        if problem:
            raise InterfaceSettingsError(f"The setting '{name}' in {path} {problem}, not {value!r}.")
    return InterfaceSettings(**contents)


def render_interface_settings(settings: InterfaceSettings) -> str:
    """The text of the settings file: every setting, under a heading for its page."""
    sections = [FILE_HEADER]
    for page in SETTINGS_PAGES:
        lines = [f"# {page.title}"]
        for description in descriptions_on_page(page):
            lines.append(f"{description.name} = {_toml_value(getattr(settings, description.name))}")
        sections.append("\n".join(lines) + "\n")
    return "\n".join(sections)


def write_interface_settings(path: Path, settings: InterfaceSettings) -> None:
    """Replace the file with the settings, making its folder if need be. The old file stays
    as it was if the write fails. Raises OSError."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_name(path.name + ".tmp")
    try:
        temporary_path.write_bytes(render_interface_settings(settings).encode("utf-8"))
        os.replace(temporary_path, path)
    except OSError:
        try:
            temporary_path.unlink(missing_ok=True)
        except OSError:
            pass  # the error that matters is the one being raised
        raise


def _toml_value(value: bool | int | str) -> str:
    if isinstance(value, str):
        return _toml_string(value)
    return ("true" if value else "false") if isinstance(value, bool) else str(value)


def _toml_string(text: str) -> str:
    """A TOML basic string: quotes and backslashes escaped, control characters written as
    unicode escapes. The rest, such as accented letters, stays as it is; the file is UTF-8."""
    escaped = []
    for character in text:
        if character in ('"', "\\"):
            escaped.append("\\" + character)
        elif ord(character) < 0x20 or ord(character) == 0x7F:
            escaped.append(f"\\u{ord(character):04x}")
        else:
            escaped.append(character)
    return '"' + "".join(escaped) + '"'
