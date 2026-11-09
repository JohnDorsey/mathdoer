"""Tests for the language description and the Python language."""
import re
from fractions import Fraction
from pathlib import Path

import pytest

from mathdoer.languages import EditingRules, Language
from mathdoer.languages.python import PYTHON
from mathdoer.languages.python.lexer import lex_line
from mathdoer.registry import load_registry
from mathdoer.syntax import LexedLine


def make_language(**overrides):
    fields = dict(
        identifier="example",
        display_name="Example",
        file_extension=".ex",
        default_startup_path=Path("startup_example.ex"),
        build_worker_command=lambda interpreter_path: [str(interpreter_path), "worker"],
        format_name=lambda entry: entry.name.lower(),
        format_literal=lambda entry: entry.value_text,
        editing=EditingRules(
            comment_prefix="//",
            opens_indented_block=lambda lines, line, column: False,
            bracket_pairs=(("(", ")"),),
        ),
        lex_line=lambda text, state: LexedLine((), 0),
    )
    fields.update(overrides)
    return Language(**fields)


def test_python_is_described_as_decided():
    assert PYTHON.identifier == "python"
    assert PYTHON.display_name == "Python"
    assert PYTHON.file_extension == ".py"


def test_the_startup_file_name_carries_the_language_name():
    assert PYTHON.startup_file_name == "startup_python.py"
    assert make_language().startup_file_name == "startup_example.ex"


def test_languages_that_share_an_extension_get_different_startup_file_names():
    first = make_language(identifier="first", file_extension=".py")
    second = make_language(identifier="second", file_extension=".py")
    assert first.startup_file_name != second.startup_file_name


def test_the_bundled_default_startup_file_follows_the_naming_convention():
    assert PYTHON.default_startup_path.is_file()
    assert PYTHON.default_startup_path.name == PYTHON.startup_file_name


@pytest.mark.parametrize("identifier", ["", "Python", "py thon", "py-thon", "1python", "python!"])
def test_rejects_identifiers_that_are_not_lowercase_words(identifier):
    with pytest.raises(ValueError, match="identifier"):
        make_language(identifier=identifier)


@pytest.mark.parametrize("extension", ["", "py", ".", "..py", ".p y"])
def test_rejects_file_extensions_that_are_not_a_dot_and_a_word(extension):
    with pytest.raises(ValueError, match="extension"):
        make_language(file_extension=extension)


def test_a_language_decides_how_its_names_and_literals_are_written():
    entry = load_registry().entry_named("INCH")
    language = make_language()
    assert language.format_name(entry) == "inch"
    assert language.format_literal(entry) == "0.0254"


def test_a_language_describes_how_to_edit_and_lex_its_code():
    language = make_language()
    assert language.editing.comment_prefix == "//"
    assert language.editing.indent_width == 4
    assert language.lex_line("anything", 0) == LexedLine((), 0)


def test_python_lexes_with_its_own_lexer():
    assert PYTHON.lex_line is lex_line


def test_python_names_are_the_registry_names():
    for entry in load_registry().entries():
        assert PYTHON.format_name(entry) == entry.name


@pytest.mark.parametrize(
    "name, expected_literal",
    [
        ("SPEED_OF_LIGHT", "299792458"),
        ("PLANCK_CONSTANT", "6.62607015e-34"),
        ("MOLAR_VOLUME_OF_IDEAL_GAS_273_15_KELVIN_100_KILOPASCAL", "0.02271095464148557506"),
        ("KNOT", "(1852/3600)"),
        ("KILOMETER_PER_HOUR", "(1000/3600)"),
        ("TORR", "(101325/760)"),
    ],
)
def test_python_literals_are_the_stored_text_with_integer_ratios_in_parentheses(
    name, expected_literal
):
    assert PYTHON.format_literal(load_registry().entry_named(name)) == expected_literal


def test_python_keeps_every_digit_of_a_long_value():
    entry = load_registry().entry_named("PARSEC")
    assert PYTHON.format_literal(entry) == entry.value_text
    assert len(entry.value_text) > 100


def test_a_ratio_with_decimals_becomes_an_exact_integer_ratio():
    entry = load_registry().entry_named("SIDEREAL_DAY")
    literal = PYTHON.format_literal(entry)
    match = re.fullmatch(r"\((\d+)/(\d+)\)", literal)
    assert match, literal
    assert Fraction(int(match[1]), int(match[2])) == entry.value


def test_every_python_literal_is_exactly_the_value_the_named_constant_has(startup_value_of):
    for entry in load_registry().entries():
        literal = PYTHON.format_literal(entry)
        value = eval(literal)
        assert value == startup_value_of(entry), entry.name
        assert type(value) is type(startup_value_of(entry)), entry.name


def test_every_python_literal_can_follow_an_operator_without_changing_meaning(startup_value_of):
    for entry in load_registry().entries():
        assert eval("1 / " + PYTHON.format_literal(entry)) == 1 / startup_value_of(entry), entry.name


def test_the_python_worker_command_runs_the_worker_script_in_utf8_mode():
    interpreter_path = Path("some") / "python.exe"
    command = PYTHON.build_worker_command(interpreter_path)
    assert command[:3] == [str(interpreter_path), "-X", "utf8"]
    assert Path(command[3]).name == "worker.py"
    assert Path(command[3]).is_file()
    assert len(command) == 4
