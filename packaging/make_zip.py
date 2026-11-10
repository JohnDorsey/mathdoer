"""Packs the packaged program into the zip that users get.

    uv run python packaging/make_zip.py [folder]          (the folder is dist/mathdoer by default)

The zip is dist/mathdoer-<version>-windows-x64.zip. It holds one folder, mathdoer-<version>,
with the program (mathdoer.exe and the folder it needs beside it) and the license and the
readme of the project, so unzipping it anywhere gives one tidy folder. Check the zip itself
with check_build.py, which unzips it into a folder of its own and checks that.
"""
import platform
import sys
import zipfile
from pathlib import Path

from project_information import PROJECT, read_version

EXECUTABLE_NAME = "mathdoer.exe"
EXTRA_FILE_NAMES = ("LICENSE", "README.md")  # beside the program, from the project folder


class PackageError(Exception):
    pass


class UnsupportedSystemError(PackageError):
    pass


def platform_label(platform_name: str = sys.platform, machine: str = platform.machine()) -> str:
    """The part of the file name that says which system the package is for."""
    if (platform_name, machine) == ("win32", "AMD64"):
        return "windows-x64"
    raise UnsupportedSystemError(
        f"There is no zip package for {platform_name} on {machine}; only Windows on AMD64 has one so far."
    )


def folder_name(version: str) -> str:
    return f"mathdoer-{version}"


def zip_name(version: str, label: str) -> str:
    return f"mathdoer-{version}-{label}.zip"


def make_zip(program_folder: Path, extra_files: list[Path], destination: Path, folder_inside: str) -> Path:
    """Write the zip: every file of the program folder and every extra file, all inside one folder
    of the given name. The files are in a fixed order, so the same files make the same zip. The zip
    is written under another name and moved into place, so a failure leaves nothing half done."""
    if not (program_folder / EXECUTABLE_NAME).is_file():
        raise PackageError(f"There is no {EXECUTABLE_NAME} in {program_folder}. Build it first (see mathdoer.spec).")
    for extra_file in extra_files:
        if not extra_file.is_file():
            raise PackageError(f"There is no {extra_file.name} to put in the zip: {extra_file} is not a file.")
    entries = {f"{folder_inside}/{path.relative_to(program_folder).as_posix()}": path
               for path in program_folder.rglob("*") if path.is_file()}
    entries.update({f"{folder_inside}/{extra_file.name}": extra_file for extra_file in extra_files})
    destination.parent.mkdir(parents=True, exist_ok=True)
    unfinished = destination.with_name(destination.name + ".unfinished")
    try:
        with zipfile.ZipFile(unfinished, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for name in sorted(entries):
                information = zipfile.ZipInfo.from_file(entries[name], name)  # keeps the date of the file
                information.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(information, entries[name].read_bytes(), compresslevel=9)
        unfinished.replace(destination)
    finally:
        unfinished.unlink(missing_ok=True)
    return destination


def main() -> int:
    program_folder = Path(sys.argv[1]) if len(sys.argv) > 1 else PROJECT / "dist" / "mathdoer"
    version = read_version()
    destination = program_folder.parent / zip_name(version, platform_label())
    try:
        make_zip(program_folder, [PROJECT / name for name in EXTRA_FILE_NAMES], destination, folder_name(version))
    except PackageError as error:
        print(error)
        return 1
    print(f"Wrote {destination} ({destination.stat().st_size / 1_000_000:.1f} MB).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
