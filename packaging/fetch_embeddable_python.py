"""Fetches the Python that the packaged program runs prompts on (Windows only for now).

    uv run python packaging/fetch_embeddable_python.py

It downloads python.org's embeddable Python, checks it against the checksum pinned below, and
unpacks it into build/embeddable_python/python, where packaging/mathdoer.spec picks it up. A file
that was downloaded before and still checks out is not downloaded again. The embeddable Python
has the standard library and nothing else, like the Python that mathdoer itself runs on.

To change the version, change VERSION and SHA256 together; python.org lists the files at
https://www.python.org/ftp/python/<version>/ and publishes signatures beside them, which the
checksum below does not replace: it was computed from the file as downloaded over HTTPS.
"""
import hashlib
import shutil
import sys
import urllib.request
import zipfile
from collections.abc import Callable
from pathlib import Path

VERSION = "3.13.14"
FILE_NAME = f"python-{VERSION}-embed-amd64.zip"
DOWNLOAD_URL = f"https://www.python.org/ftp/python/{VERSION}/{FILE_NAME}"
SHA256 = "90b4e5b9898b72d744650524bff92377c367f44bd5fbd09e3148656c080ad907"

PROJECT = Path(__file__).resolve().parent.parent
WORK_FOLDER = PROJECT / "build" / "embeddable_python"
UNPACKED_FOLDER = WORK_FOLDER / "python"


class ChecksumError(Exception):
    pass


class NotPythonError(Exception):
    pass


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_file(url: str, destination: Path) -> None:
    with urllib.request.urlopen(url, timeout=60) as response, open(destination, "wb") as stream:
        shutil.copyfileobj(response, stream)


def download(
    url: str, path: Path, sha256: str, fetch_file: Callable[[str, Path], None] = download_file
) -> Path:
    """The file at the path, downloaded first unless it is there and matches the checksum.
    A download that does not match is deleted and refused."""
    if path.is_file() and sha256_of(path) == sha256:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.unlink(missing_ok=True)
    fetch_file(url, path)
    if sha256_of(path) != sha256:
        found = sha256_of(path)
        path.unlink()
        raise ChecksumError(f"{path.name} from {url} has the checksum {found}, not the pinned {sha256}")
    return path


def unpack(archive: Path, sha256: str, destination: Path) -> Path:
    """Replace the destination folder with the contents of the zip, after checking its checksum
    and that it holds python.exe."""
    if sha256_of(archive) != sha256:
        raise ChecksumError(f"{archive.name} does not have the pinned checksum {sha256}")
    with zipfile.ZipFile(archive) as zipped:
        if "python.exe" not in zipped.namelist():
            raise NotPythonError(f"{archive.name} holds no python.exe")
        unfinished = destination.with_name(destination.name + ".unfinished")
        shutil.rmtree(unfinished, ignore_errors=True)
        zipped.extractall(unfinished)
    shutil.rmtree(destination, ignore_errors=True)
    unfinished.rename(destination)
    return destination


def main() -> int:
    if sys.platform != "win32":
        print("The embeddable Python exists for Windows only; there is nothing to fetch here.")
        return 1
    archive = download(DOWNLOAD_URL, WORK_FOLDER / FILE_NAME, SHA256)
    folder = unpack(archive, SHA256, UNPACKED_FOLDER)
    print(f"Python {VERSION} is in {folder}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
