"""Tests for packaging/fetch_embeddable_python.py, which downloads the Python that the packaged
program runs prompts on. Nothing here touches the network: the download is replaced."""
import hashlib
import importlib.util
import zipfile
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "packaging" / "fetch_embeddable_python.py"


@pytest.fixture
def fetch():
    specification = importlib.util.spec_from_file_location("fetch_embeddable_python", SCRIPT)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def make_zip(path: Path, files: dict[str, bytes]) -> bytes:
    with zipfile.ZipFile(path, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return path.read_bytes()


def test_the_pinned_download_is_a_python_org_embeddable_zip_with_a_sha256(fetch):
    assert fetch.DOWNLOAD_URL.startswith("https://www.python.org/ftp/python/")
    assert fetch.DOWNLOAD_URL.endswith("-embed-amd64.zip")
    assert fetch.VERSION in fetch.DOWNLOAD_URL
    assert len(fetch.SHA256) == 64 and set(fetch.SHA256) <= set("0123456789abcdef")


def test_the_zip_is_unpacked_into_a_folder_that_holds_python_exe(fetch, tmp_path):
    archive = tmp_path / "python.zip"
    content = make_zip(archive, {"python.exe": b"exe", "python313.zip": b"library"})
    folder = fetch.unpack(archive, hashlib.sha256(content).hexdigest(), tmp_path / "out")
    assert (folder / "python.exe").read_bytes() == b"exe"
    assert (folder / "python313.zip").read_bytes() == b"library"


def test_a_zip_with_the_wrong_checksum_is_refused_and_nothing_is_unpacked(fetch, tmp_path):
    archive = tmp_path / "python.zip"
    make_zip(archive, {"python.exe": b"exe"})
    with pytest.raises(fetch.ChecksumError, match="python.zip"):
        fetch.unpack(archive, "0" * 64, tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_a_zip_without_python_exe_is_refused(fetch, tmp_path):
    archive = tmp_path / "python.zip"
    content = make_zip(archive, {"readme.txt": b"no python here"})
    with pytest.raises(fetch.NotPythonError):
        fetch.unpack(archive, hashlib.sha256(content).hexdigest(), tmp_path / "out")


def test_an_old_unpacked_folder_is_replaced_not_mixed_with_the_new_one(fetch, tmp_path):
    archive = tmp_path / "python.zip"
    content = make_zip(archive, {"python.exe": b"new"})
    out = tmp_path / "out"
    out.mkdir()
    (out / "stale.txt").write_text("left over")
    fetch.unpack(archive, hashlib.sha256(content).hexdigest(), out)
    assert not (out / "stale.txt").exists()
    assert (out / "python.exe").read_bytes() == b"new"


def test_a_file_that_is_already_downloaded_and_checks_out_is_not_downloaded_again(fetch, tmp_path):
    archive = tmp_path / "python.zip"
    content = make_zip(archive, {"python.exe": b"exe"})
    downloads = []
    path = fetch.download(
        "https://example.invalid/python.zip", archive, hashlib.sha256(content).hexdigest(), downloads.append
    )
    assert path == archive and downloads == []


def test_a_missing_or_damaged_file_is_downloaded_and_checked(fetch, tmp_path):
    source = tmp_path / "source.zip"
    content = make_zip(source, {"python.exe": b"exe"})
    expected = hashlib.sha256(content).hexdigest()
    target = tmp_path / "cache" / "python.zip"

    def copy_the_source(url, destination):
        destination.write_bytes(source.read_bytes())

    assert fetch.download("https://example.invalid/python.zip", target, expected, copy_the_source) == target
    assert target.read_bytes() == content
    target.write_bytes(b"damaged")
    fetch.download("https://example.invalid/python.zip", target, expected, copy_the_source)
    assert target.read_bytes() == content


def test_a_download_that_does_not_match_is_refused_and_not_kept(fetch, tmp_path):
    target = tmp_path / "cache" / "python.zip"

    def deliver_something_else(url, destination):
        destination.write_bytes(b"something else")

    with pytest.raises(fetch.ChecksumError):
        fetch.download("https://example.invalid/python.zip", target, "0" * 64, deliver_something_else)
    assert not target.exists()
