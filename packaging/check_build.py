"""Checks a packaged mathdoer: the folder that packaging/mathdoer.spec builds, or the zip that
packaging/make_zip.py makes from it.

    uv run python packaging/check_build.py [folder or zip]      (the folder dist/mathdoer by default)

It checks that every file the code reads next to its own modules is in the package, and that
the executable carries the icon and the version of the project. It then starts the program with
an empty configuration folder of its own, never the user's, and checks that it stays running and
creates its startup file there. Where the package carries a Python, it also runs a prompt on it,
with the packaged worker, startup file and registry, the way the program does. Given a zip, it
also checks the zip itself (its name, its folder, the license and readme beside the program) and
unpacks it into a temporary folder to run all of that on what the user would get. It exits with
1 and says why when a check fails.
"""
import json
import os
import struct
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

import mathdoer
from mathdoer.application import BUNDLED_INTERPRETER_PATH
from mathdoer.interface.icon import ICON_PATH
from mathdoer.languages.python import PYTHON, WORKER_PATH
from mathdoer.registry import shipped_registry_path
from mathdoer.running import (
    MESSAGE_KIND_KEY,
    MESSAGE_KIND_OUTPUT,
    MESSAGE_TEXT_KEY,
    REGISTRY_ENVIRONMENT_VARIABLE,
    REQUEST_PROMPT_TEXT_KEY,
    REQUEST_STARTUP_PATH_KEY,
)
from mathdoer.user_files import startup_file_path, user_configuration_directory

from make_zip import EXTRA_FILE_NAMES, UnsupportedSystemError, folder_name, platform_label, zip_name
from project_information import PROJECT, read_version

SOURCE_ROOT = Path(mathdoer.__file__).resolve().parent.parent
STARTUP_TIMEOUT_SECONDS = 30
SECONDS_IT_MUST_KEEP_RUNNING = 3


def executable_in(folder: Path) -> Path:
    return folder / ("mathdoer.exe" if sys.platform == "win32" else "mathdoer")


def files_the_code_reads_next_to_its_modules() -> list[Path]:
    """Their paths relative to the folder that holds the mathdoer package."""
    paths = [
        shipped_registry_path(),
        PYTHON.default_startup_path,
        PYTHON.default_settings_path,
        WORKER_PATH,
        ICON_PATH,
    ]
    return [Path(path).resolve().relative_to(SOURCE_ROOT) for path in paths]


def files_the_package_must_carry() -> list[Path]:
    """The same, and the Python that the program runs prompts on where it has one."""
    paths = files_the_code_reads_next_to_its_modules()
    return [*paths, BUNDLED_INTERPRETER_PATH] if sys.platform == "win32" else paths


def find_bundled(folder: Path, relative_path: Path) -> Path | None:
    """PyInstaller 6 keeps the files in a subfolder (_internal) unless the spec says otherwise."""
    for candidate in (folder / "_internal" / relative_path, folder / relative_path):
        if candidate.is_file():
            return candidate
    return None


def check_files(folder: Path) -> list[str]:
    problems = [
        f"{relative_path} is not in the package"
        for relative_path in files_the_package_must_carry()
        if find_bundled(folder, relative_path) is None
    ]
    # the icon is an .ico file, which Qt reads with a plugin of its own
    reader_folder = Path("PySide6") / "plugins" / "imageformats"
    if not any(list((base / reader_folder).glob("*qico*")) for base in (folder / "_internal", folder)):
        problems.append(f"Qt's reader for .ico files is not in the package (looked in {reader_folder})")
    return problems


def images_in_icon_file(path: Path) -> list[bytes]:
    """The image of each entry of an icon file, in the order of the entries."""
    data = path.read_bytes()
    count = struct.unpack_from("<H", data, 4)[0]
    images = []
    for index in range(count):
        length, offset = struct.unpack_from("<II", data, 6 + 16 * index + 8)
        images.append(data[offset : offset + length])
    return images


def images_in_executable(path: Path) -> list[bytes]:
    """The images of the first icon group of an executable, in the order of the group; none when
    it has no icon."""
    import pefile

    executable = pefile.PE(str(path), fast_load=True)
    executable.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_RESOURCE"]])
    directory = getattr(executable, "DIRECTORY_ENTRY_RESOURCE", None)  # missing when there are no resources
    resources = {entry.id: entry for entry in directory.entries} if directory else {}
    groups = resources.get(pefile.RESOURCE_TYPE["RT_GROUP_ICON"])
    icons = resources.get(pefile.RESOURCE_TYPE["RT_ICON"])
    if groups is None or icons is None:
        return []

    def data_of(named_entry) -> bytes:
        leaf = named_entry.directory.entries[0].data.struct  # the first language of the resource
        return executable.get_data(leaf.OffsetToData, leaf.Size)

    group = data_of(groups.directory.entries[0])
    count = struct.unpack_from("<H", group, 4)[0]
    icons_by_identifier = {entry.id: entry for entry in icons.directory.entries}
    identifiers = [struct.unpack_from("<H", group, 6 + 14 * index + 12)[0] for index in range(count)]
    return [data_of(icons_by_identifier[identifier]) for identifier in identifiers]


def check_executable_resources(folder: Path) -> list[str]:
    """The icon and the version information that the spec asked for are in the executable (Windows)."""
    from PyInstaller.utils.win32.versioninfo import read_version_info_from_executable

    from windows_version_information import version_information

    executable = executable_in(folder)
    problems = []
    if images_in_executable(executable) != images_in_icon_file(ICON_PATH):
        problems.append(f"the icon of {executable.name} is not the icon of mathdoer ({ICON_PATH.name})")
    found = read_version_info_from_executable(str(executable))
    expected = version_information(read_version())
    if found is None or found.toRaw() != expected.toRaw():
        problems.append(f"the version information of {executable.name} is not that of mathdoer {read_version()}")
    return problems


def startup_file_is_the_packaged_default(startup_path: Path, folder: Path) -> bool:
    """The program copies the default startup file that it carries. The reference is that file in
    the package, not the one in this source tree: a package built elsewhere has other line endings."""
    return startup_path.read_bytes() == packaged(folder, PYTHON.default_startup_path).read_bytes()


def check_it_starts_and_keeps_running(folder: Path) -> list[str]:
    with tempfile.TemporaryDirectory() as home:
        environment = {
            **os.environ,
            "HOME": home,
            "USERPROFILE": home,
            "APPDATA": home,
            "XDG_CONFIG_HOME": home,
        }
        previous = {name: os.environ.get(name) for name in environment}
        os.environ.update(environment)
        try:
            startup_path = startup_file_path(PYTHON, user_configuration_directory())
        finally:
            for name, value in previous.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value
        process = subprocess.Popen([str(executable_in(folder))], env=environment, cwd=home)
        try:
            deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
            while not startup_path.exists():
                if process.poll() is not None:
                    return [f"the program stopped with exit code {process.returncode} before it started"]
                if time.monotonic() > deadline:
                    return [f"the program did not create {startup_path} within {STARTUP_TIMEOUT_SECONDS} seconds"]
                time.sleep(0.2)
            time.sleep(SECONDS_IT_MUST_KEEP_RUNNING)
            if process.poll() is not None:
                return [f"the program stopped with exit code {process.returncode} just after it started"]
            if not startup_file_is_the_packaged_default(startup_path, folder):
                return ["the startup file it created is not a copy of the default in the package"]
            return []
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=30)


def packaged(folder: Path, source_path: Path) -> Path | None:
    return find_bundled(folder, Path(source_path).resolve().relative_to(SOURCE_ROOT))


def check_a_prompt_runs_on_the_packaged_python(folder: Path) -> list[str]:
    """The program starts the worker like this: its interpreter, the worker script, one line of
    JSON on standard input. The prompt uses the startup file, which reads the registry."""
    python = find_bundled(folder, BUNDLED_INTERPRETER_PATH)
    worker = packaged(folder, WORKER_PATH)
    startup = packaged(folder, PYTHON.default_startup_path)
    registry = packaged(folder, shipped_registry_path())
    prompt = "import sys\nprint(sys.version_info[:2])\nSPEED_OF_LIGHT * 2"
    request = json.dumps({REQUEST_PROMPT_TEXT_KEY: prompt, REQUEST_STARTUP_PATH_KEY: str(startup)})
    command = PYTHON.build_worker_command(python)
    command[-1] = str(worker)  # the last item is the worker in the source; use the packaged one
    environment = {**os.environ, REGISTRY_ENVIRONMENT_VARIABLE: str(registry)}
    try:
        finished = subprocess.run(
            command, input=request, capture_output=True, text=True, timeout=60, env=environment, cwd=folder
        )
    except subprocess.TimeoutExpired:
        return ["the packaged Python did not finish a prompt within 60 seconds"]
    messages = [json.loads(line) for line in finished.stdout.splitlines() if line.startswith("{")]
    output = "".join(m[MESSAGE_TEXT_KEY] for m in messages if m[MESSAGE_KIND_KEY] == MESSAGE_KIND_OUTPUT)
    if finished.returncode != 0 or "599584916" not in output:
        errors = finished.stderr.strip()[:300]
        return [f"a prompt did not run on the packaged Python: exit code {finished.returncode}, "
                f"output {output!r}, errors {errors!r}"]
    print("The packaged Python ran a prompt:", output.strip().replace("\n", "; "))
    return []


def check_folder(folder: Path) -> list[str]:
    """The checks that need only the folder; each runs only when the ones before it passed."""
    if not executable_in(folder).is_file():
        return [f"there is no {executable_in(folder)}; build it first (see packaging/mathdoer.spec)"]
    checks = [check_files]
    if sys.platform == "win32":
        checks.append(check_executable_resources)
    checks.append(check_it_starts_and_keeps_running)
    if sys.platform == "win32":
        checks.append(check_a_prompt_runs_on_the_packaged_python)
    for check in checks:
        problems = check(folder)
        if problems:
            return problems
    return []


def check_zip_contents(archive: zipfile.ZipFile, zip_path: Path) -> list[str]:
    """The name of the zip, the single folder in it and the files beside the program."""
    version = read_version()
    try:
        expected_name = zip_name(version, platform_label())
    except UnsupportedSystemError as error:
        return [str(error)]
    problems = []
    if zip_path.name != expected_name:
        problems.append(f"the zip is called {zip_path.name}, not {expected_name}")
    broken = archive.testzip()
    if broken is not None:
        problems.append(f"{broken} in the zip does not match its checksum")
    names = archive.namelist()
    top_level = {name.split("/")[0] for name in names}
    if top_level != {folder_name(version)}:
        problems.append(f"the zip holds {sorted(top_level)} at its top, not only {folder_name(version)}")
    problems += [
        f"{name} is not in the zip, beside the program"
        for name in EXTRA_FILE_NAMES
        if f"{folder_name(version)}/{name}" not in names
    ]
    return problems


def check_zip(zip_path: Path) -> list[str]:
    with zipfile.ZipFile(zip_path) as archive:
        problems = check_zip_contents(archive, zip_path)
        if problems:
            return problems
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as unpacked:
            archive.extractall(unpacked)
            return check_folder(Path(unpacked) / folder_name(read_version()))


def main() -> int:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else PROJECT / "dist" / "mathdoer"
    if target.suffix == ".zip":
        problems = check_zip(target) if target.is_file() else [f"there is no {target}"]
    else:
        problems = check_folder(target)
    for problem in problems:
        print("FAILED:", problem)
    if not problems:
        print(f"OK: {target} passed every check.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
