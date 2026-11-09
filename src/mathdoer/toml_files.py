"""Reading the TOML files that mathdoer's settings are kept in."""
import tomllib
from pathlib import Path


def read_toml_file(path: Path) -> dict:
    """The contents of the TOML file. A byte-order mark at the start, which some editors add
    to a UTF-8 file, is skipped instead of being taken for part of the first line.

    Raises FileNotFoundError when there is no file, OSError when it cannot be read,
    UnicodeDecodeError when it is not UTF-8 and tomllib.TOMLDecodeError when it is not TOML.
    """
    return tomllib.loads(Path(path).read_bytes().decode("utf-8-sig"))
