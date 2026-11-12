"""The files of PySide6 that mathdoer never uses, which the package leaves out (about a quarter of
its size). packaging/mathdoer.spec drops them and packaging/check_build.py checks that they are gone.

mathdoer draws widgets with Qt's own painter, so it needs no OpenGL; it reads no network, no SVG and
no image except its .ico icon; and its text is English.
"""
from pathlib import PurePosixPath

# files by the start of their names (Qt6Network.dll, QtNetwork.pyd, and the names on other systems)
UNNEEDED_NAME_PREFIXES = ("opengl32sw", "Qt6Network", "QtNetwork", "Qt6Svg", "QtSvg")
UNNEEDED_PLUGIN_FOLDERS = ("tls", "networkinformation", "iconengines")
IMAGE_READER_FOLDER = "imageformats"
IMAGE_READER_KEPT = "qico"  # the icon is an .ico file
TRANSLATIONS_FOLDER = "translations"


def is_unneeded(path: str) -> bool:
    """Whether a file of the package, named by its path inside the package (with / or \\), is one
    that mathdoer never uses."""
    parts = PurePosixPath(path.replace("\\", "/")).parts
    if "PySide6" not in parts:
        return False
    inside = parts[parts.index("PySide6") + 1 :]
    if not inside:
        return False
    name = inside[-1]
    if inside[0] == TRANSLATIONS_FOLDER:
        return True
    if inside[0] == "plugins" and len(inside) >= 3:
        if inside[1] in UNNEEDED_PLUGIN_FOLDERS:
            return True
        if inside[1] == IMAGE_READER_FOLDER:
            return IMAGE_READER_KEPT not in name
    return len(inside) == 1 and name.startswith(UNNEEDED_NAME_PREFIXES)
