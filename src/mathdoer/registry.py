"""Registry of named constants and units, shared by the menus and the startup files.

The registry is language-neutral data (registry.toml). Nothing here depends on the
language the prompt is written in; each language turns an entry's name and value into
its own variable names and literals.

A value is written as text, either a decimal number or a ratio of two decimal numbers:
``299792458``, ``6.62607015e-34``, ``1852/3600``. Text keeps exact definitions exact.
"""
import re
import tomllib
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

SUPPORTED_FORMAT_VERSION = 1

# exact: stored text is the exact value. rounded: exactly defined, but not a finite
# decimal, so the stored digits are rounded. measured: carries an uncertainty.
ENTRY_BASES = ("exact", "rounded", "measured")

NAME_PATTERN = re.compile(r"[A-Z][A-Z0-9]*(_[A-Z0-9]+)*")
DECIMAL_NUMBER_PATTERN = re.compile(r"-?[0-9]+(\.[0-9]+)?([eE][+-]?[0-9]+)?")

COMMON_FIELD_NAMES = ("name", "label", "value", "basis", "source")
CONSTANT_FIELD_NAMES = COMMON_FIELD_NAMES + ("unit",)
UNIT_FIELD_NAMES = COMMON_FIELD_NAMES + ("category",)
TOP_LEVEL_KEYS = ("format_version", "constants", "units")


class RegistryError(ValueError):
    """The registry data is malformed."""


@dataclass(frozen=True)
class RegistryEntry:
    name: str
    label: str
    value_text: str
    value: Fraction
    basis: str
    source: str


@dataclass(frozen=True)
class ConstantEntry(RegistryEntry):
    unit: str


@dataclass(frozen=True)
class UnitEntry(RegistryEntry):
    category: str


@dataclass(frozen=True)
class Registry:
    constants: tuple[ConstantEntry, ...]
    units: tuple[UnitEntry, ...]

    def unit_categories(self) -> tuple[str, ...]:
        """Category labels in order of first appearance."""
        return tuple(dict.fromkeys(unit.category for unit in self.units))

    def units_in_category(self, category: str) -> tuple[UnitEntry, ...]:
        return tuple(unit for unit in self.units if unit.category == category)

    def entries(self) -> tuple[RegistryEntry, ...]:
        return self.constants + self.units

    def entry_named(self, name: str) -> RegistryEntry:
        for entry in self.entries():
            if entry.name == name:
                return entry
        raise KeyError(name)


def parse_value_text(text: str) -> Fraction:
    parts = text.split("/")
    if len(parts) > 2 or not all(DECIMAL_NUMBER_PATTERN.fullmatch(part) for part in parts):
        raise RegistryError(
            f"invalid value {text!r}: expected a decimal number or a ratio of two decimal numbers"
        )
    numerator = Fraction(parts[0])
    if len(parts) == 1:
        return numerator
    denominator = Fraction(parts[1])
    if denominator == 0:
        raise RegistryError(f"invalid value {text!r}: the denominator is zero")
    return numerator / denominator


def shipped_registry_path() -> Path:
    return Path(__file__).with_name("registry.toml")


def load_registry(path: Path | str | None = None) -> Registry:
    path = shipped_registry_path() if path is None else Path(path)
    try:
        return parse_registry_text(path.read_text(encoding="utf-8"))
    except RegistryError as error:
        raise RegistryError(f"{path}: {error}") from error


def parse_registry_text(text: str) -> Registry:
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        raise RegistryError(f"invalid TOML: {error}") from error

    if data.get("format_version") != SUPPORTED_FORMAT_VERSION:
        raise RegistryError(
            f"format_version must be {SUPPORTED_FORMAT_VERSION}, found {data.get('format_version')!r}"
        )
    unknown_keys = sorted(set(data) - set(TOP_LEVEL_KEYS))
    if unknown_keys:
        raise RegistryError(f"unknown top-level key(s): {', '.join(unknown_keys)}")

    constants = tuple(
        ConstantEntry(**_read_entry("constants", index, raw_entry, CONSTANT_FIELD_NAMES))
        for index, raw_entry in enumerate(_entry_tables(data, "constants"))
    )
    units = tuple(
        UnitEntry(**_read_entry("units", index, raw_entry, UNIT_FIELD_NAMES))
        for index, raw_entry in enumerate(_entry_tables(data, "units"))
    )
    _reject_duplicate_names(constants + units)
    return Registry(constants=constants, units=units)


def _entry_tables(data: dict, table_name: str) -> list[dict]:
    tables = data.get(table_name, [])
    if not isinstance(tables, list) or not all(isinstance(table, dict) for table in tables):
        raise RegistryError(f"{table_name} must be an array of tables, written [[{table_name}]]")
    return tables


def _read_entry(table_name: str, index: int, raw_entry: dict, field_names: tuple[str, ...]) -> dict:
    """Validate one table entry and return the keyword arguments for its entry class."""
    raw_name = raw_entry.get("name")
    description = f"[[{table_name}]] entry {index + 1}"
    if isinstance(raw_name, str) and raw_name:
        description += f" ({raw_name})"

    unknown_fields = sorted(set(raw_entry) - set(field_names))
    if unknown_fields:
        raise RegistryError(f"{description}: unknown field(s) {', '.join(unknown_fields)}")
    for field_name in field_names:
        field_value = raw_entry.get(field_name)
        if not isinstance(field_value, str) or not field_value.strip():
            raise RegistryError(f"{description}: field {field_name!r} must be a non-empty string")

    if not NAME_PATTERN.fullmatch(raw_entry["name"]):
        raise RegistryError(f"{description}: name must be SCREAMING_SNAKE_CASE")
    if raw_entry["basis"] not in ENTRY_BASES:
        raise RegistryError(f"{description}: basis must be one of {', '.join(ENTRY_BASES)}")
    try:
        value = parse_value_text(raw_entry["value"])
    except RegistryError as error:
        raise RegistryError(f"{description}: {error}") from error

    fields = {field_name: raw_entry[field_name] for field_name in field_names}
    fields["value_text"] = fields.pop("value")
    fields["value"] = value
    return fields


def _reject_duplicate_names(entries: tuple[RegistryEntry, ...]) -> None:
    seen_names = set()
    for entry in entries:
        if entry.name in seen_names:
            raise RegistryError(f"duplicate name {entry.name}")
        seen_names.add(entry.name)
