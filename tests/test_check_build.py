"""Tests for the parts of packaging/check_build.py that need no built program: what it compares
the startup file with, and what it requires of a zip."""
import zipfile
from pathlib import Path

import pytest

import check_build
from mathdoer.languages.python import PYTHON

VERSION = "1.0.0"
FOLDER = f"mathdoer-{VERSION}"
ZIP_NAME = f"mathdoer-{VERSION}-windows-x64.zip"
PACKAGED_STARTUP = Path("_internal") / "mathdoer" / "languages" / "python" / "startup_python.py"


@pytest.fixture
def package_folder(tmp_path):
    folder = tmp_path / "package"
    (folder / PACKAGED_STARTUP).parent.mkdir(parents=True)
    return folder


def package_startup(folder, content: bytes):
    (folder / PACKAGED_STARTUP).write_bytes(content)


class TestTheStartupFileIsTheDefaultOfThePackage:
    def test_a_copy_of_the_packaged_file_is_the_default(self, package_folder, tmp_path):
        package_startup(package_folder, b"import math\r\n")
        created = tmp_path / "startup_python.py"
        created.write_bytes(b"import math\r\n")
        assert check_build.startup_file_is_the_packaged_default(created, package_folder)

    def test_a_file_that_differs_is_not(self, package_folder, tmp_path):
        package_startup(package_folder, b"import math\r\n")
        created = tmp_path / "startup_python.py"
        created.write_bytes(b"import cmath\r\n")
        assert not check_build.startup_file_is_the_packaged_default(created, package_folder)

    def test_the_source_tree_is_not_the_reference_even_when_only_its_line_endings_differ(
        self, package_folder, tmp_path
    ):
        # a package built on another machine can have other line endings than the files checked out
        # here (the CI runner makes them \r\n); the program copies what it carries, so the copy is right
        source = PYTHON.default_startup_path.read_bytes()
        other_endings = source.replace(b"\r\n", b"\n") if b"\r\n" in source else source.replace(b"\n", b"\r\n")
        assert other_endings != source
        package_startup(package_folder, other_endings)
        created = tmp_path / "startup_python.py"
        created.write_bytes(other_endings)
        assert check_build.startup_file_is_the_packaged_default(created, package_folder)


class TestTheContentsOfAZip:
    @pytest.fixture(autouse=True)
    def a_windows_package_at_version_1_0_0(self, monkeypatch):
        monkeypatch.setattr(check_build, "platform_label", lambda: "windows-x64")
        monkeypatch.setattr(check_build, "read_version", lambda: VERSION)

    def problems_in(self, tmp_path, names, zip_name=ZIP_NAME):
        path = tmp_path / zip_name
        with zipfile.ZipFile(path, "w") as archive:
            for name in names:
                archive.writestr(name, b"content")
        with zipfile.ZipFile(path) as archive:
            return check_build.check_zip_contents(archive, path)

    def test_the_folder_with_the_program_and_the_extra_files_is_right(self, tmp_path):
        names = [f"{FOLDER}/mathdoer.exe", f"{FOLDER}/LICENSE", f"{FOLDER}/README.md", f"{FOLDER}/_internal/a.dll"]
        assert self.problems_in(tmp_path, names) == []

    def test_another_name_for_the_zip_is_a_problem(self, tmp_path):
        names = [f"{FOLDER}/mathdoer.exe", f"{FOLDER}/LICENSE", f"{FOLDER}/README.md"]
        (problem,) = self.problems_in(tmp_path, names, zip_name="mathdoer-1.0.0-linux.zip")
        assert ZIP_NAME in problem

    def test_a_file_beside_the_folder_is_a_problem(self, tmp_path):
        names = [f"{FOLDER}/mathdoer.exe", f"{FOLDER}/LICENSE", f"{FOLDER}/README.md", "stray.txt"]
        (problem,) = self.problems_in(tmp_path, names)
        assert "stray.txt" in problem

    def test_a_folder_of_another_version_is_a_problem(self, tmp_path):
        names = ["mathdoer-0.9.0/mathdoer.exe", "mathdoer-0.9.0/LICENSE", "mathdoer-0.9.0/README.md"]
        problems = self.problems_in(tmp_path, names)
        assert any("mathdoer-0.9.0" in problem for problem in problems)
        assert any("LICENSE" in problem for problem in problems)  # none inside the right folder

    @pytest.mark.parametrize("missing", ["LICENSE", "README.md"])
    def test_a_missing_extra_file_is_named(self, tmp_path, missing):
        names = [f"{FOLDER}/{name}" for name in ("mathdoer.exe", "LICENSE", "README.md") if name != missing]
        (problem,) = self.problems_in(tmp_path, names)
        assert missing in problem

    def test_a_system_without_a_zip_package_is_one_problem_that_says_so(self, tmp_path, monkeypatch):
        def refuse():
            raise check_build.UnsupportedSystemError("There is no zip package for this system.")

        monkeypatch.setattr(check_build, "platform_label", refuse)
        assert self.problems_in(tmp_path, [f"{FOLDER}/mathdoer.exe"]) == ["There is no zip package for this system."]
