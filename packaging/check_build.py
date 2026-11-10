"""Checks a packaged mathdoer (the folder that packaging/mathdoer.spec builds).

    uv run python packaging/check_build.py [folder]       (the folder is dist/mathdoer by default)

It checks that every file the code reads next to its own modules is in the package, then starts
the program with an empty configuration folder of its own, never the user's, and checks that it
stays running and creates its startup file there. Where the package carries a Python, it also
runs a prompt on it, with the packaged worker, startup file and registry, the way the program
does. It exits with 1 and says why when a check fails.
"""
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import mathdoer
from mathdoer.application import BUNDLED_INTERPRETER_PATH
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

PROJECT = Path(__file__).resolve().parent.parent
SOURCE_ROOT = Path(mathdoer.__file__).resolve().parent.parent
STARTUP_TIMEOUT_SECONDS = 30
SECONDS_IT_MUST_KEEP_RUNNING = 3


def executable_in(folder: Path) -> Path:
    return folder / ("mathdoer.exe" if sys.platform == "win32" else "mathdoer")


def files_the_code_reads_next_to_its_modules() -> list[Path]:
    """Their paths relative to the folder that holds the mathdoer package."""
    paths = [shipped_registry_path(), PYTHON.default_startup_path, PYTHON.default_settings_path, WORKER_PATH]
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
    return [
        f"{relative_path} is not in the package"
        for relative_path in files_the_package_must_carry()
        if find_bundled(folder, relative_path) is None
    ]


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
            expected = PYTHON.default_startup_path.read_bytes()
            if startup_path.read_bytes() != expected:
                return ["the startup file it created is not a copy of the bundled default"]
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


def main() -> int:
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else PROJECT / "dist" / "mathdoer"
    if not executable_in(folder).is_file():
        print(f"There is no {executable_in(folder)}. Build it first (see packaging/mathdoer.spec).")
        return 1
    problems = check_files(folder)
    if not problems:
        problems = check_it_starts_and_keeps_running(folder)
    if not problems and sys.platform == "win32":
        problems = check_a_prompt_runs_on_the_packaged_python(folder)
    for problem in problems:
        print("FAILED:", problem)
    if not problems:
        print(f"OK: {executable_in(folder)} has its files, starts, and keeps running.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
