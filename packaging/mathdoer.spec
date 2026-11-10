# PyInstaller spec: a folder holding mathdoer.exe (mathdoer on macOS and Linux) and what it needs.
# Build from the project folder with:
#     uv run python packaging/fetch_embeddable_python.py      (once; Windows)
#     uv run pyinstaller packaging/mathdoer.spec
# The result is dist/mathdoer/. Check it with: uv run python packaging/check_build.py
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files

sys.path.insert(0, SPECPATH)  # the scripts beside this file
from project_information import read_version
from windows_version_information import version_information

project = Path(SPECPATH).parent
package = project / "src" / "mathdoer"
python_language_folder = "mathdoer/languages/python"

# The code finds these next to its own modules (Path(__file__)), and PyInstaller keeps that layout.
# The worker and the startup file are Python files that are read as data, never imported.
datas = collect_data_files("mathdoer")  # registry.toml, settings_python.toml and icon.ico
datas += [
    (str(package / "languages" / "python" / "worker.py"), python_language_folder),
    (str(package / "languages" / "python" / "startup_python.py"), python_language_folder),
]

# The Python that the packaged program runs prompts on, next to the other data (see
# mathdoer.application.default_interpreter_path). Only Windows has an embeddable Python.
if sys.platform == "win32":
    embeddable_python = project / "build" / "embeddable_python" / "python"
    if not (embeddable_python / "python.exe").is_file():
        raise SystemExit("Run packaging/fetch_embeddable_python.py first: there is no " + str(embeddable_python))
    datas += [(str(embeddable_python), "python")]

analysis = Analysis(
    [str(package / "__main__.py")],
    pathex=[str(project / "src")],
    datas=datas,
    excludes=["pytest", "pytestqt", "tkinter"],
)
archive = PYZ(analysis.pure)
executable = EXE(
    archive,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="mathdoer",
    console=False,  # a window program: no console window behind it
    # The icon of the file, which is also the icon of the window until Qt sets the same file on it,
    # and the version shown in its properties. Only Windows takes an .ico file and a version resource.
    icon=str(package / "interface" / "icon.ico") if sys.platform == "win32" else None,
    version=version_information(read_version()) if sys.platform == "win32" else None,
)
COLLECT(executable, analysis.binaries, analysis.datas, name="mathdoer")
