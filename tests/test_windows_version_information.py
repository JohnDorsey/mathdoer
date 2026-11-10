"""Tests for packaging/windows_version_information.py: the version resource of mathdoer.exe,
which Windows shows in the properties of the file and Task Manager shows as the name."""
import pytest

# PyInstaller's code for version resources needs pefile, which PyInstaller installs on Windows only,
# and only a Windows program has a version resource
pytest.importorskip("pefile", reason="the version resource is made on Windows only")

from PyInstaller.utils.win32.versioninfo import VSVersionInfo

import windows_version_information as information


def strings_of(version_information: VSVersionInfo) -> dict[str, str]:
    (table,) = version_information.kids[0].kids
    return {string.name: string.val for string in table.kids}


def numbers_of(most_significant_word: int, least_significant_word: int) -> tuple[int, int, int, int]:
    """The four numbers of a version, which the resource keeps as two 32-bit words."""
    return (
        most_significant_word >> 16,
        most_significant_word & 0xFFFF,
        least_significant_word >> 16,
        least_significant_word & 0xFFFF,
    )


def test_the_numbers_are_the_version_and_a_zero_in_the_last_place():
    fixed = information.version_information("1.2.3").ffi
    assert numbers_of(fixed.fileVersionMS, fixed.fileVersionLS) == (1, 2, 3, 0)
    assert numbers_of(fixed.productVersionMS, fixed.productVersionLS) == (1, 2, 3, 0)


def test_the_strings_name_the_program_its_version_and_its_license():
    strings = strings_of(information.version_information("1.2.3"))
    assert strings["ProductName"] == "mathdoer"
    assert strings["FileDescription"] == "mathdoer"
    assert strings["OriginalFilename"] == "mathdoer.exe"
    assert strings["InternalName"] == "mathdoer"
    assert strings["FileVersion"] == strings["ProductVersion"] == "1.2.3"
    assert "John Dorsey" in strings["LegalCopyright"] and "GPL-3.0-or-later" in strings["LegalCopyright"]
    assert strings["Comments"] == "A calculator that executes the Python code you type"


def test_the_language_is_american_english_in_unicode():
    result = information.version_information("1.0.0")
    (table,) = result.kids[0].kids
    assert table.name == "040904B0"
    assert result.kids[1].kids[0].name == "Translation"
    assert result.kids[1].kids[0].kids == [0x409, 1200]


def test_the_description_is_the_one_in_pyproject_toml():
    import project_information

    assert information.DESCRIPTION == project_information.read_project_table()["description"]


def test_a_version_that_is_not_three_numbers_is_refused():
    with pytest.raises(ValueError, match="major.minor.patch"):
        information.version_information("1.0")


def test_it_becomes_the_binary_resource_that_the_executable_gets():
    raw = information.version_information("4.5.6").toRaw()
    assert "4.5.6".encode("utf-16-le") in raw
    assert "mathdoer.exe".encode("utf-16-le") in raw
