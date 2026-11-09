"""Tests for the registry of named constants and units."""
import math
from decimal import Decimal, localcontext
from fractions import Fraction

import pytest

from mathdoer.registry import (
    ConstantEntry,
    RegistryError,
    UnitEntry,
    load_registry,
    parse_registry_text,
    parse_value_text,
    shipped_registry_path,
)

# Labels and unit texts copied from the PrecCalc64 menus (constants.cns, units.unt),
# with the one label that has a stray double space normalized.
PRECCALC_CONSTANTS = [
    ("Speed of light", "m/s"),
    ("g", "m/s^2"),
    ("Gravitational", "m^3/s^2.kg"),
    ("Avogadro", "1/mol"),
    ("Universal gas", "J/mol.K"),
    ("Molar volume of gas", "m^3/mol"),
    ("Permittivity of vacuum", "F/m"),
    ("Permeability of vacuum", "H/m"),
    ("Faraday", "C/mol"),
    ("Elementary charge", "C"),
    ("Atomic mass", "kg"),
    ("Electron mass", "kg"),
    ("Proton mass", "kg"),
    ("Neutron mass", "kg"),
    ("Rydberg", "1/m"),
    ("Planck", "J.s"),
    ("Boltzmann", "J/K"),
    ("Stefan-Boltzmann", "W/m^2.K^4"),
    ("Bohr magneton", "J/T"),
    ("Nuclear magneton", "J/T"),
]

PRECCALC_UNITS = {
    "Length": [
        "angstrom", "inch", "foot", "yard", "mile", "nautical mile",
        "astronomical unit", "light-year", "parsec",
    ],
    "Area": ["inch squared", "foot squared", "yard squared", "acre", "mile squared"],
    "Volume": [
        "fluid ounce (UK)", "fluid ounce (US)", "pint (UK)", "gallon (UK)",
        "gallon (US)", "barrel",
    ],
    "Mass": ["ounce", "pound"],
    "Energy": ["erg", "calorie"],
    "Power": ["horse", "horse power"],
    "Pressure": ["atmosphere", "Torr (mm of Hg)", "mm of water"],
    "Speed": ["km/h", "knot"],
    "Time": [
        "sidereal day", "calendar day", "sidereal month", "synodic month",
        "sidereal year", "tropical year",
    ],
}

# The items, their order and their units match PrecCalc64. Where its label is ambiguous
# or incomplete the label is replaced by an unambiguous one: PrecCalc64 label -> label.
CLARIFIED_LABELS = {
    "g": "Standard gravity",
    "Gravitational": "Gravitational constant",
    "Avogadro": "Avogadro constant",
    "Universal gas": "Molar gas constant (universal gas constant)",
    "Molar volume of gas": "Molar volume of ideal gas (273.15 K, 100 kPa)",
    "Faraday": "Faraday constant",
    "Atomic mass": "Atomic mass constant (unified atomic mass unit)",
    "Rydberg": "Rydberg constant",
    "Planck": "Planck constant",
    "Boltzmann": "Boltzmann constant",
    "Stefan-Boltzmann": "Stefan-Boltzmann constant",
    "inch squared": "square inch",
    "foot squared": "square foot",
    "yard squared": "square yard",
    "mile squared": "square mile",
    "barrel": "barrel (petroleum, 42 US gallons)",
    "ounce": "ounce (avoirdupois)",
    "pound": "pound (avoirdupois)",
    "calorie": "calorie (International Table)",
    "horse": "horsepower (metric)",
    "horse power": "horsepower (mechanical)",
    "atmosphere": "standard atmosphere",
    "Torr (mm of Hg)": "Torr (1/760 of a standard atmosphere)",
    "mm of water": "millimeter of water (conventional)",
    "km/h": "kilometer per hour",
    "knot": "knot (nautical mile per hour)",
}


def clarified(preccalc_label):
    return CLARIFIED_LABELS.get(preccalc_label, preccalc_label)


# Names that carry their definition when the plain word has several meanings.
EXPECTED_CONSTANT_NAMES = {
    "Speed of light": "SPEED_OF_LIGHT",
    "g": "STANDARD_GRAVITY",
    "Gravitational": "GRAVITATIONAL_CONSTANT",
    "Avogadro": "AVOGADRO_CONSTANT",
    "Universal gas": "MOLAR_GAS_CONSTANT",
    "Molar volume of gas": "MOLAR_VOLUME_OF_IDEAL_GAS_273_15_KELVIN_100_KILOPASCAL",
    "Permittivity of vacuum": "VACUUM_PERMITTIVITY",
    "Permeability of vacuum": "VACUUM_PERMEABILITY",
    "Faraday": "FARADAY_CONSTANT",
    "Elementary charge": "ELEMENTARY_CHARGE",
    "Atomic mass": "ATOMIC_MASS_CONSTANT",
    "Electron mass": "ELECTRON_MASS",
    "Proton mass": "PROTON_MASS",
    "Neutron mass": "NEUTRON_MASS",
    "Rydberg": "RYDBERG_CONSTANT",
    "Planck": "PLANCK_CONSTANT",
    "Boltzmann": "BOLTZMANN_CONSTANT",
    "Stefan-Boltzmann": "STEFAN_BOLTZMANN_CONSTANT",
    "Bohr magneton": "BOHR_MAGNETON",
    "Nuclear magneton": "NUCLEAR_MAGNETON",
}

EXPECTED_UNIT_NAMES = {
    "angstrom": "ANGSTROM",
    "inch": "INCH",
    "foot": "FOOT",
    "yard": "YARD",
    "mile": "MILE",
    "nautical mile": "NAUTICAL_MILE",
    "astronomical unit": "ASTRONOMICAL_UNIT",
    "light-year": "LIGHT_YEAR",
    "parsec": "PARSEC",
    "inch squared": "SQUARE_INCH",
    "foot squared": "SQUARE_FOOT",
    "yard squared": "SQUARE_YARD",
    "acre": "ACRE",
    "mile squared": "SQUARE_MILE",
    "fluid ounce (UK)": "UK_FLUID_OUNCE",
    "fluid ounce (US)": "US_FLUID_OUNCE",
    "pint (UK)": "UK_PINT",
    "gallon (UK)": "UK_GALLON",
    "gallon (US)": "US_GALLON",
    "barrel": "OIL_BARREL",
    "ounce": "AVOIRDUPOIS_OUNCE",
    "pound": "AVOIRDUPOIS_POUND",
    "erg": "ERG",
    "calorie": "INTERNATIONAL_TABLE_CALORIE",
    "horse": "METRIC_HORSEPOWER",
    "horse power": "MECHANICAL_HORSEPOWER",
    "atmosphere": "STANDARD_ATMOSPHERE",
    "Torr (mm of Hg)": "TORR",
    "mm of water": "CONVENTIONAL_MILLIMETER_OF_WATER",
    "km/h": "KILOMETER_PER_HOUR",
    "knot": "KNOT",
    "sidereal day": "SIDEREAL_DAY",
    "calendar day": "CALENDAR_DAY",
    "sidereal month": "SIDEREAL_MONTH",
    "synodic month": "SYNODIC_MONTH",
    "sidereal year": "SIDEREAL_YEAR",
    "tropical year": "TROPICAL_YEAR",
}

# Measured values carry an uncertainty; rounded values are exactly defined but not
# representable as a finite decimal, so the stored digits are rounded.
MEASURED_NAMES = {
    "GRAVITATIONAL_CONSTANT", "VACUUM_PERMITTIVITY", "VACUUM_PERMEABILITY",
    "ATOMIC_MASS_CONSTANT", "ELECTRON_MASS", "PROTON_MASS", "NEUTRON_MASS",
    "RYDBERG_CONSTANT", "BOHR_MAGNETON", "NUCLEAR_MAGNETON",
    "SIDEREAL_MONTH", "SYNODIC_MONTH", "SIDEREAL_YEAR", "TROPICAL_YEAR",
}
ROUNDED_NAMES = {"STEFAN_BOLTZMANN_CONSTANT", "PARSEC"}

# Rounded values keep at least this many significant digits, correctly rounded.
ROUNDED_SIGNIFICANT_DIGIT_COUNT = 100


@pytest.fixture(scope="module")
def shipped_registry():
    return load_registry()


@pytest.fixture(scope="module")
def value_of(shipped_registry):
    return lambda name: shipped_registry.entry_named(name).value


# ---------------------------------------------------------------- value text

@pytest.mark.parametrize(
    "text, expected",
    [
        ("299792458", Fraction(299792458)),
        ("0", Fraction(0)),
        ("-5", Fraction(-5)),
        ("0.0254", Fraction(254, 10000)),
        ("6.62607015e-34", Fraction(662607015, 10**42)),
        ("6.02214076E23", Fraction(602214076 * 10**15)),
        ("1e-10", Fraction(1, 10**10)),
        ("1852/3600", Fraction(1852, 3600)),
        ("101325/760", Fraction(101325, 760)),
        ("1.5/3e1", Fraction(1, 20)),
    ],
)
def test_parse_value_text_is_exact(text, expected):
    assert parse_value_text(text) == expected


@pytest.mark.parametrize(
    "text",
    ["", " ", "abc", "1/0", "1/0.0", "1/2/3", "/2", "1/", " 5", "5 ", "5\n", "0x10",
     "1e", "e5", "--1", "+1", "nan", "inf", "1_000", "1,5", ".5", "5.", "1.e5",
     "١٢", "1 / 2", "2**3"],
)
def test_parse_value_text_rejects_everything_outside_the_grammar(text):
    with pytest.raises(RegistryError):
        parse_value_text(text)


# ------------------------------------------------------------ shipped registry

def test_shipped_registry_path_is_a_real_toml_file():
    path = shipped_registry_path()
    assert path.is_file()
    assert path.suffix == ".toml"


def test_loading_the_default_equals_loading_the_shipped_path(shipped_registry):
    assert load_registry(shipped_registry_path()) == shipped_registry


def test_constants_match_the_preccalc_menu_in_order(shipped_registry):
    actual = [(entry.label, entry.unit) for entry in shipped_registry.constants]
    expected = [(clarified(label), unit) for label, unit in PRECCALC_CONSTANTS]
    assert actual == expected


def test_units_match_the_preccalc_menu_in_order(shipped_registry):
    assert shipped_registry.unit_categories() == tuple(PRECCALC_UNITS)
    for category, labels in PRECCALC_UNITS.items():
        actual = [unit.label for unit in shipped_registry.units_in_category(category)]
        assert actual == [clarified(label) for label in labels], category


def test_every_clarified_label_replaces_a_preccalc_label():
    preccalc_labels = {label for label, _ in PRECCALC_CONSTANTS}
    for labels in PRECCALC_UNITS.values():
        preccalc_labels.update(labels)
    assert set(CLARIFIED_LABELS) <= preccalc_labels


def test_labels_are_unique_so_every_menu_item_is_unambiguous(shipped_registry):
    labels = [entry.label for entry in shipped_registry.entries()]
    assert len(labels) == len(set(labels))


def test_constant_names_are_as_decided(shipped_registry):
    actual = {entry.label: entry.name for entry in shipped_registry.constants}
    assert actual == {clarified(label): name for label, name in EXPECTED_CONSTANT_NAMES.items()}


def test_unit_names_are_as_decided(shipped_registry):
    actual = {entry.label: entry.name for entry in shipped_registry.units}
    assert actual == {clarified(label): name for label, name in EXPECTED_UNIT_NAMES.items()}


def test_names_are_unique_across_constants_and_units(shipped_registry):
    names = [entry.name for entry in shipped_registry.entries()]
    assert len(names) == len(set(names)) == 57


def test_every_value_is_positive(shipped_registry):
    for entry in shipped_registry.entries():
        assert entry.value > 0, entry.name


def test_value_text_parses_to_the_stored_value(shipped_registry):
    for entry in shipped_registry.entries():
        assert parse_value_text(entry.value_text) == entry.value, entry.name


def test_basis_classification_is_as_decided(shipped_registry):
    by_basis = {"measured": set(), "rounded": set(), "exact": set()}
    for entry in shipped_registry.entries():
        by_basis[entry.basis].add(entry.name)
    assert by_basis["measured"] == MEASURED_NAMES
    assert by_basis["rounded"] == ROUNDED_NAMES
    assert not by_basis["exact"] & (MEASURED_NAMES | ROUNDED_NAMES)


def test_entry_named_raises_key_error_for_unknown_names(shipped_registry):
    with pytest.raises(KeyError):
        shipped_registry.entry_named("NOT_A_NAME")


def test_entries_lists_constants_then_units(shipped_registry):
    assert shipped_registry.entries() == shipped_registry.constants + shipped_registry.units
    assert isinstance(shipped_registry.constants[0], ConstantEntry)
    assert isinstance(shipped_registry.units[0], UnitEntry)


# Values that must agree exactly with each other, so a typo in one is caught.
EXACT_RELATIONS = [
    ("molar gas constant is Avogadro times Boltzmann",
     lambda v: v("MOLAR_GAS_CONSTANT") == v("AVOGADRO_CONSTANT") * v("BOLTZMANN_CONSTANT")),
    ("Faraday constant is Avogadro times elementary charge",
     lambda v: v("FARADAY_CONSTANT") == v("AVOGADRO_CONSTANT") * v("ELEMENTARY_CHARGE")),
    ("molar volume is R * 273.15 K / 100 kPa",
     lambda v: v("MOLAR_VOLUME_OF_IDEAL_GAS_273_15_KELVIN_100_KILOPASCAL")
     == v("MOLAR_GAS_CONSTANT") * Fraction("273.15") / 100000),
    ("foot is 12 inches", lambda v: v("FOOT") == 12 * v("INCH")),
    ("yard is 3 feet", lambda v: v("YARD") == 3 * v("FOOT")),
    ("mile is 1760 yards", lambda v: v("MILE") == 1760 * v("YARD")),
    ("square inch", lambda v: v("SQUARE_INCH") == v("INCH") ** 2),
    ("square foot", lambda v: v("SQUARE_FOOT") == v("FOOT") ** 2),
    ("square yard", lambda v: v("SQUARE_YARD") == v("YARD") ** 2),
    ("square mile", lambda v: v("SQUARE_MILE") == v("MILE") ** 2),
    ("acre is 43560 square feet", lambda v: v("ACRE") == 43560 * v("SQUARE_FOOT")),
    ("US gallon is 231 cubic inches", lambda v: v("US_GALLON") == 231 * v("INCH") ** 3),
    ("US fluid ounce is 1/128 US gallon", lambda v: v("US_FLUID_OUNCE") == v("US_GALLON") / 128),
    ("oil barrel is 42 US gallons", lambda v: v("OIL_BARREL") == 42 * v("US_GALLON")),
    ("UK fluid ounce is 1/160 UK gallon", lambda v: v("UK_FLUID_OUNCE") == v("UK_GALLON") / 160),
    ("UK pint is 1/8 UK gallon", lambda v: v("UK_PINT") == v("UK_GALLON") / 8),
    ("ounce is 1/16 pound", lambda v: v("AVOIRDUPOIS_OUNCE") == v("AVOIRDUPOIS_POUND") / 16),
    ("light-year is a Julian year of light travel",
     lambda v: v("LIGHT_YEAR") == Fraction("365.25") * 86400 * v("SPEED_OF_LIGHT")),
    ("metric horsepower is 75 kgf*m/s", lambda v: v("METRIC_HORSEPOWER") == 75 * v("STANDARD_GRAVITY")),
    ("mechanical horsepower is 550 ft*lbf/s",
     lambda v: v("MECHANICAL_HORSEPOWER")
     == 550 * v("FOOT") * v("AVOIRDUPOIS_POUND") * v("STANDARD_GRAVITY")),
    ("atmosphere is 101325 pascals", lambda v: v("STANDARD_ATMOSPHERE") == 101325),
    ("Torr is 1/760 atmosphere", lambda v: v("TORR") == v("STANDARD_ATMOSPHERE") / 760),
    ("conventional mm of water is 1 kgf/m^2", lambda v: v("CONVENTIONAL_MILLIMETER_OF_WATER") == v("STANDARD_GRAVITY")),
    ("knot is a nautical mile per hour", lambda v: v("KNOT") == v("NAUTICAL_MILE") / 3600),
    ("kilometer per hour", lambda v: v("KILOMETER_PER_HOUR") == Fraction(1000, 3600)),
    ("calendar day is 86400 seconds", lambda v: v("CALENDAR_DAY") == 86400),
    ("sidereal day is 86400 s over the exact Earth rotation ratio 1.002737909350795 (IERS)",
     lambda v: v("SIDEREAL_DAY") == Fraction(86400) / Fraction("1.002737909350795")),
    ("sidereal month is 27.32166155 days (IERS Conventions 2003)",
     lambda v: v("SIDEREAL_MONTH") == Fraction("27.32166155") * 86400),
    ("synodic month is 29.530588861 days (Meeus)",
     lambda v: v("SYNODIC_MONTH") == Fraction("29.530588861") * 86400),
    ("sidereal year is 365.256363004 days (Simon et al. 1994)",
     lambda v: v("SIDEREAL_YEAR") == Fraction("365.256363004") * 86400),
    ("tropical year is 365.242190402 days (Simon et al. 1994)",
     lambda v: v("TROPICAL_YEAR") == Fraction("365.242190402") * 86400),
]


@pytest.mark.parametrize(
    "holds", [relation for _, relation in EXACT_RELATIONS], ids=[name for name, _ in EXACT_RELATIONS]
)
def test_exact_relations_between_entries(value_of, holds):
    assert holds(value_of)


# Relations that involve an irrational number or a published rounding.
def test_parsec_is_648000_over_pi_astronomical_units(value_of):
    expected = 648000 / math.pi * float(value_of("ASTRONOMICAL_UNIT"))
    assert math.isclose(float(value_of("PARSEC")), expected, rel_tol=1e-14)


def test_stefan_boltzmann_follows_from_the_exact_constants(value_of):
    k = float(value_of("BOLTZMANN_CONSTANT"))
    h = float(value_of("PLANCK_CONSTANT"))
    c = float(value_of("SPEED_OF_LIGHT"))
    expected = 2 * math.pi**5 * k**4 / (15 * h**3 * c**2)
    assert math.isclose(float(value_of("STEFAN_BOLTZMANN_CONSTANT")), expected, rel_tol=1e-12)


def pi_as_fraction(significant_digit_count):
    """Machin's formula, pi = 16 arctan(1/5) - 4 arctan(1/239), in exact decimal arithmetic."""
    with localcontext() as context:
        context.prec = significant_digit_count + 20
        tolerance = Decimal(10) ** -context.prec

        def arctangent_of_reciprocal(n):
            term = Decimal(1) / n
            total = term
            k = 1
            while term > tolerance:
                term /= n * n
                total += term / (2 * k + 1) * (-1 if k % 2 else 1)
                k += 1
            return total

        return Fraction(16 * arctangent_of_reciprocal(5) - 4 * arctangent_of_reciprocal(239))


def test_the_pi_helper_agrees_with_math_pi():
    assert math.isclose(float(pi_as_fraction(30)), math.pi, rel_tol=1e-15)
    assert str(float(pi_as_fraction(30))) == "3.141592653589793"


def significant_digit_count_and_unit_in_last_place(value_text):
    """The number of significant digits written, and the size of the last digit."""
    number = Decimal(value_text)
    digit_count = len(number.as_tuple().digits)
    return digit_count, Fraction(10) ** (number.adjusted() - (digit_count - 1))


def exact_irrational_values(value_of):
    pi = pi_as_fraction(ROUNDED_SIGNIFICANT_DIGIT_COUNT + 30)
    k, h, c = (value_of(n) for n in ("BOLTZMANN_CONSTANT", "PLANCK_CONSTANT", "SPEED_OF_LIGHT"))
    return {
        "STEFAN_BOLTZMANN_CONSTANT": 2 * pi**5 * k**4 / (15 * h**3 * c**2),
        "PARSEC": 648000 / pi * value_of("ASTRONOMICAL_UNIT"),
    }


@pytest.mark.parametrize("name", sorted(ROUNDED_NAMES))
def test_rounded_values_keep_at_least_100_significant_digits(shipped_registry, name):
    digit_count, _ = significant_digit_count_and_unit_in_last_place(
        shipped_registry.entry_named(name).value_text
    )
    assert digit_count >= ROUNDED_SIGNIFICANT_DIGIT_COUNT


@pytest.mark.parametrize("name", sorted(ROUNDED_NAMES))
def test_rounded_values_are_correctly_rounded_to_their_last_stored_digit(
    shipped_registry, value_of, name
):
    entry = shipped_registry.entry_named(name)
    _, unit_in_last_place = significant_digit_count_and_unit_in_last_place(entry.value_text)
    error = abs(entry.value - exact_irrational_values(value_of)[name])
    assert error <= unit_in_last_place / 2


def test_vacuum_permittivity_and_permeability_agree_with_the_speed_of_light(value_of):
    product = (
        float(value_of("VACUUM_PERMITTIVITY"))
        * float(value_of("VACUUM_PERMEABILITY"))
        * float(value_of("SPEED_OF_LIGHT")) ** 2
    )
    assert math.isclose(product, 1.0, rel_tol=1e-9)


# ------------------------------------------------------------------- loading

CONSTANT_FIELDS = {
    "name": "SPEED_OF_LIGHT",
    "label": "Speed of light",
    "unit": "m/s",
    "value": "299792458",
    "basis": "exact",
    "source": "SI definition of the metre",
}
UNIT_FIELDS = {
    "name": "INCH",
    "label": "inch",
    "category": "Length",
    "value": "0.0254",
    "basis": "exact",
    "source": "International yard and pound agreement",
}


def table_text(table_name, fields):
    lines = [f"[[{table_name}]]"] + [f'{key} = "{value}"' for key, value in fields.items()]
    return "\n".join(lines)


def registry_text(constants=(CONSTANT_FIELDS,), units=(UNIT_FIELDS,), header="format_version = 1"):
    parts = [header]
    parts += [table_text("constants", fields) for fields in constants]
    parts += [table_text("units", fields) for fields in units]
    return "\n\n".join(parts) + "\n"


def without(fields, field_name):
    return {key: value for key, value in fields.items() if key != field_name}


def test_a_minimal_registry_loads():
    registry = parse_registry_text(registry_text())
    assert registry.constants == (
        ConstantEntry(
            name="SPEED_OF_LIGHT", label="Speed of light", value_text="299792458",
            value=Fraction(299792458), basis="exact", source="SI definition of the metre",
            unit="m/s",
        ),
    )
    assert registry.units == (
        UnitEntry(
            name="INCH", label="inch", value_text="0.0254", value=Fraction(254, 10000),
            basis="exact", source="International yard and pound agreement", category="Length",
        ),
    )


def test_a_registry_may_have_no_constants_or_no_units():
    assert parse_registry_text(registry_text(constants=())).constants == ()
    assert parse_registry_text(registry_text(units=())).units == ()


def test_units_are_grouped_by_category_in_order_of_first_appearance():
    units = [
        {**UNIT_FIELDS, "name": "INCH", "label": "inch", "category": "Length"},
        {**UNIT_FIELDS, "name": "ACRE", "label": "acre", "category": "Area", "value": "4046.8564224"},
        {**UNIT_FIELDS, "name": "FOOT", "label": "foot", "category": "Length", "value": "0.3048"},
    ]
    registry = parse_registry_text(registry_text(units=units))
    assert registry.unit_categories() == ("Length", "Area")
    assert [unit.name for unit in registry.units_in_category("Length")] == ["INCH", "FOOT"]
    assert registry.units_in_category("Nothing") == ()


def test_loading_a_missing_file_raises_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_registry(tmp_path / "missing.toml")


def test_loading_a_file_reports_the_path_in_errors(tmp_path):
    path = tmp_path / "broken.toml"
    path.write_text("format_version = 2\n", encoding="utf-8")
    with pytest.raises(RegistryError, match="broken.toml"):
        load_registry(path)


@pytest.mark.parametrize(
    "header, expected_message",
    [("format_version = 2", "format_version"), ("", "format_version"),
     ('format_version = "1"', "format_version")],
)
def test_rejects_a_missing_or_unsupported_format_version(header, expected_message):
    with pytest.raises(RegistryError, match=expected_message):
        parse_registry_text(registry_text(header=header))


def test_rejects_unknown_top_level_keys():
    with pytest.raises(RegistryError, match="colour"):
        parse_registry_text(registry_text(header='format_version = 1\ncolour = "red"'))


def test_rejects_text_that_is_not_toml():
    with pytest.raises(RegistryError, match="TOML"):
        parse_registry_text("format_version = ")


@pytest.mark.parametrize("table_name", ["constants", "units"])
@pytest.mark.parametrize("wrong_form", ['[{name}]\nname = "X"', "{name} = [1]", '{name} = "text"'])
def test_rejects_entries_that_are_not_an_array_of_tables(table_name, wrong_form):
    text = "format_version = 1\n\n" + wrong_form.format(name=table_name) + "\n"
    with pytest.raises(RegistryError, match=f"{table_name} must be an array of tables"):
        parse_registry_text(text)


@pytest.mark.parametrize("field_name", list(CONSTANT_FIELDS))
def test_rejects_a_constant_missing_a_field(field_name):
    with pytest.raises(RegistryError, match=field_name):
        parse_registry_text(registry_text(constants=[without(CONSTANT_FIELDS, field_name)]))


@pytest.mark.parametrize("field_name", list(UNIT_FIELDS))
def test_rejects_a_unit_missing_a_field(field_name):
    with pytest.raises(RegistryError, match=field_name):
        parse_registry_text(registry_text(units=[without(UNIT_FIELDS, field_name)]))


@pytest.mark.parametrize("field_name", list(CONSTANT_FIELDS))
def test_rejects_a_blank_constant_field(field_name):
    with pytest.raises(RegistryError, match=field_name):
        parse_registry_text(registry_text(constants=[{**CONSTANT_FIELDS, field_name: "  "}]))


def test_rejects_a_field_that_is_not_text():
    text = registry_text().replace('value = "299792458"', "value = 299792458")
    with pytest.raises(RegistryError, match="value"):
        parse_registry_text(text)


def test_rejects_unknown_fields_in_entries():
    with pytest.raises(RegistryError, match="colour"):
        parse_registry_text(registry_text(constants=[{**CONSTANT_FIELDS, "colour": "red"}]))
    with pytest.raises(RegistryError, match="colour"):
        parse_registry_text(registry_text(units=[{**UNIT_FIELDS, "colour": "red"}]))


@pytest.mark.parametrize(
    "name",
    ["speed_of_light", "Speed_Of_Light", "1ABC", "A__B", "A_", "_A", "A-B", "A B", "ÄB"],
)
def test_rejects_names_that_are_not_screaming_snake_case(name):
    with pytest.raises(RegistryError, match="name"):
        parse_registry_text(registry_text(constants=[{**CONSTANT_FIELDS, "name": name}]))


@pytest.mark.parametrize("name", ["A", "AB", "A1", "A_1", "MOLAR_VOLUME_273_15_KELVIN"])
def test_accepts_screaming_snake_case_names(name):
    parse_registry_text(registry_text(constants=[{**CONSTANT_FIELDS, "name": name}]))


def test_rejects_duplicate_names_within_constants():
    with pytest.raises(RegistryError, match="duplicate.*SPEED_OF_LIGHT"):
        parse_registry_text(registry_text(constants=[CONSTANT_FIELDS, CONSTANT_FIELDS]))


def test_rejects_a_name_shared_by_a_constant_and_a_unit():
    clashing_unit = {**UNIT_FIELDS, "name": "SPEED_OF_LIGHT"}
    with pytest.raises(RegistryError, match="duplicate.*SPEED_OF_LIGHT"):
        parse_registry_text(registry_text(units=[clashing_unit]))


@pytest.mark.parametrize("value", ["", "abc", "1/0", "1/2/3", "0x10", "nan", "1_000", ".5"])
def test_rejects_invalid_values_naming_the_entry(value):
    with pytest.raises(RegistryError, match="SPEED_OF_LIGHT"):
        parse_registry_text(registry_text(constants=[{**CONSTANT_FIELDS, "value": value}]))


def test_rejects_an_unknown_basis():
    with pytest.raises(RegistryError, match="basis"):
        parse_registry_text(registry_text(constants=[{**CONSTANT_FIELDS, "basis": "guess"}]))
