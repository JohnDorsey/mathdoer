# PyInstaller spec: a folder holding mathdoer.exe (mathdoer on macOS and Linux) and what it needs.
# Build from the project folder with: uv run pyinstaller packaging/mathdoer.spec
# The result is dist/mathdoer/. Check it with: uv run python packaging/check_build.py
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files

project = Path(SPECPATH).parent
package = project / "src" / "mathdoer"
python_language_folder = "mathdoer/languages/python"

# The code finds these next to its own modules (Path(__file__)), and PyInstaller keeps that layout.
# The worker and the startup file are Python files that are read as data, never imported.
datas = collect_data_files("mathdoer")  # registry.toml and settings_python.toml
datas += [
    (str(package / "languages" / "python" / "worker.py"), python_language_folder),
    (str(package / "languages" / "python" / "startup_python.py"), python_language_folder),
]

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
)
COLLECT(executable, analysis.binaries, analysis.datas, name="mathdoer")
