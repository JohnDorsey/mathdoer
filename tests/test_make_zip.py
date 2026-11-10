"""Tests for packaging/make_zip.py, which packs the packaged program into the zip that users get."""
import zipfile
from pathlib import Path

import pytest

import make_zip


@pytest.fixture
def program_folder(tmp_path):
    folder = tmp_path / "dist" / "mathdoer"
    (folder / "_internal" / "deep" / "er").mkdir(parents=True)
    (folder / "mathdoer.exe").write_bytes(b"MZ\x00\x01 binary \xff\xfe")
    (folder / "_internal" / "base_library.zip").write_bytes(bytes(range(256)) * 10)
    (folder / "_internal" / "deep" / "er" / "file.txt").write_bytes(b"deeply nested\n")
    return folder


@pytest.fixture
def extra_files(tmp_path):
    folder = tmp_path / "project"
    folder.mkdir()
    (folder / "LICENSE").write_bytes(b"license text\n")
    (folder / "README.md").write_bytes(b"# readme\n")
    return [folder / "LICENSE", folder / "README.md"]


def pack(program_folder, extra_files, tmp_path, name="mathdoer-9.8.7"):
    return make_zip.make_zip(program_folder, extra_files, tmp_path / "out" / "package.zip", name)


def names_in(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as archive:
        return archive.namelist()


def test_the_file_name_has_the_program_the_version_and_the_system():
    assert make_zip.zip_name("1.0.0", "windows-x64") == "mathdoer-1.0.0-windows-x64.zip"


def test_the_folder_inside_has_the_program_and_the_version():
    assert make_zip.folder_name("1.0.0") == "mathdoer-1.0.0"


@pytest.mark.parametrize("platform_name, machine, label", [("win32", "AMD64", "windows-x64")])
def test_the_label_names_the_system_the_package_was_built_for(platform_name, machine, label):
    assert make_zip.platform_label(platform_name, machine) == label


@pytest.mark.parametrize(
    "platform_name, machine",
    [("win32", "ARM64"), ("win32", "x86"), ("linux", "x86_64"), ("darwin", "arm64")],
)
def test_a_system_without_a_package_is_refused_by_name(platform_name, machine):
    with pytest.raises(make_zip.UnsupportedSystemError, match=f"{platform_name}.*{machine}"):
        make_zip.platform_label(platform_name, machine)


def test_the_zip_holds_one_folder_with_the_program_and_the_extra_files(program_folder, extra_files, tmp_path):
    path = pack(program_folder, extra_files, tmp_path)
    assert sorted(names_in(path)) == sorted(
        [
            "mathdoer-9.8.7/mathdoer.exe",
            "mathdoer-9.8.7/_internal/base_library.zip",
            "mathdoer-9.8.7/_internal/deep/er/file.txt",
            "mathdoer-9.8.7/LICENSE",
            "mathdoer-9.8.7/README.md",
        ]
    )


def test_every_file_comes_out_as_it_went_in(program_folder, extra_files, tmp_path):
    path = pack(program_folder, extra_files, tmp_path)
    with zipfile.ZipFile(path) as archive:
        assert archive.testzip() is None
        assert archive.read("mathdoer-9.8.7/mathdoer.exe") == (program_folder / "mathdoer.exe").read_bytes()
        assert archive.read("mathdoer-9.8.7/_internal/base_library.zip") == bytes(range(256)) * 10
        assert archive.read("mathdoer-9.8.7/_internal/deep/er/file.txt") == b"deeply nested\n"
        assert archive.read("mathdoer-9.8.7/LICENSE") == b"license text\n"


def test_the_files_are_compressed(program_folder, extra_files, tmp_path):
    with zipfile.ZipFile(pack(program_folder, extra_files, tmp_path)) as archive:
        assert {info.compress_type for info in archive.infolist()} == {zipfile.ZIP_DEFLATED}


def test_the_names_use_forward_slashes_and_come_in_a_fixed_order(program_folder, extra_files, tmp_path):
    names = names_in(pack(program_folder, extra_files, tmp_path))
    assert all("\\" not in name for name in names)
    assert names == sorted(names)


def test_the_same_files_make_the_same_zip(program_folder, extra_files, tmp_path):
    first = pack(program_folder, extra_files, tmp_path, "mathdoer-1.0.0").read_bytes()
    second = pack(program_folder, extra_files, tmp_path, "mathdoer-1.0.0").read_bytes()
    assert first == second


def test_an_old_zip_is_replaced_and_no_unfinished_file_is_left(program_folder, extra_files, tmp_path):
    destination = tmp_path / "out" / "package.zip"
    destination.parent.mkdir()
    destination.write_bytes(b"an older package")
    make_zip.make_zip(program_folder, extra_files, destination, "mathdoer-9.8.7")
    assert zipfile.is_zipfile(destination)
    assert [path.name for path in destination.parent.iterdir()] == ["package.zip"]


def test_a_folder_without_the_program_is_refused(tmp_path, extra_files):
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(make_zip.PackageError, match=r"mathdoer\.exe"):
        make_zip.make_zip(empty, extra_files, tmp_path / "package.zip", "mathdoer-9.8.7")
    assert not (tmp_path / "package.zip").exists()


def test_a_missing_extra_file_is_refused_and_no_zip_is_left(program_folder, extra_files, tmp_path):
    with pytest.raises(make_zip.PackageError, match="NOTICE"):
        make_zip.make_zip(
            program_folder, [*extra_files, tmp_path / "NOTICE"], tmp_path / "out" / "package.zip", "mathdoer-9.8.7"
        )
    assert not list((tmp_path / "out").glob("*"))  # neither a zip nor an unfinished one


def test_the_extra_files_of_the_project_exist():
    for name in make_zip.EXTRA_FILE_NAMES:
        assert (make_zip.PROJECT / name).is_file()
