"""What the packaging scripts know about the project, read from pyproject.toml, the one place
where the version is written."""
import re
import tomllib
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
PYPROJECT_PATH = PROJECT / "pyproject.toml"

VERSION_PATTERN = re.compile(r"(\d+)\.(\d+)\.(\d+)")


def read_project_table(pyproject_path: Path = PYPROJECT_PATH) -> dict:
    with open(pyproject_path, "rb") as stream:
        return tomllib.load(stream)["project"]


def read_version(pyproject_path: Path = PYPROJECT_PATH) -> str:
    return read_project_table(pyproject_path)["version"]


def version_numbers(version: str) -> tuple[int, int, int]:
    """The major, minor and patch numbers of a version such as 1.0.0. Anything else is refused,
    because the Windows version information holds numbers only."""
    match = VERSION_PATTERN.fullmatch(version)
    if match is None:
        raise ValueError(f"the version {version!r} is not three numbers, major.minor.patch")
    major, minor, patch = match.groups()
    return int(major), int(minor), int(patch)
