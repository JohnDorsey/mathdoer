"""The icon of mathdoer: a square cut into two rectangles, the top one white with a black cursive
"m" and the bottom one black with a white cursive "dm". The file is drawn by packaging/make_icon.py
and holds the icon at every size that Windows asks for."""
from pathlib import Path

from PySide6.QtGui import QIcon

ICON_PATH = Path(__file__).with_name("icon.ico")


def application_icon() -> QIcon:
    return QIcon(str(ICON_PATH))
