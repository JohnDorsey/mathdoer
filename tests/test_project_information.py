"""Tests for packaging/project_information.py: the version, which is written in pyproject.toml
only and read from there by every packaging script."""
import importlib.metadata

import pytest

import project_information


def write_pyproject(tmp_path, version):
    path = tmp_path / "pyproject.toml"
    path.write_text(f'[project]\nname = "example"\nversion = "{version}"\n', encoding="utf-8")
    return path


def test_the_version_is_read_from_the_project_table(tmp_path):
    assert project_information.read_version(write_pyproject(tmp_path, "3.14.15")) == "3.14.15"


def test_the_version_of_the_project_is_the_version_the_installed_package_reports():
    # the installed metadata is rebuilt from pyproject.toml, so this catches a stale environment
    assert project_information.read_version() == importlib.metadata.version("mathdoer")


def test_the_version_of_the_project_has_three_numbers():
    numbers = project_information.version_numbers(project_information.read_version())
    assert len(numbers) == 3 and all(isinstance(number, int) for number in numbers)


def test_version_numbers_are_major_minor_and_patch():
    assert project_information.version_numbers("1.0.0") == (1, 0, 0)
    assert project_information.version_numbers("12.345.6") == (12, 345, 6)


@pytest.mark.parametrize("text", ["1.0", "1", "1.0.0.0", "1.0.0rc1", "v1.0.0", "1.0.x", "", "1.0.0 "])
def test_a_version_that_is_not_three_numbers_is_refused(text):
    with pytest.raises(ValueError, match="major.minor.patch"):
        project_information.version_numbers(text)
