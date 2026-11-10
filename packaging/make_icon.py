"""Draws the icon of mathdoer.

    uv run python packaging/make_icon.py

The icon is a square cut into two rectangles, one above the other: the top one white with a
black cursive "m", the bottom one black with a white cursive "dm". The script writes
src/mathdoer/interface/icon.ico, which holds the icon at every size Windows asks for; the
window and the packaged program both use that file. Run it only to change the icon: the file
is kept in the repository, so nobody needs the font to build mathdoer.

The letters are the outlines of a font (a cursive one that Windows ships), drawn at each size
as shapes rather than scaled down from one picture, and they are placed by the ink they cover,
not by the room the font gives them. The script needs the real platform, which has fonts; the
offscreen platform of the tests has none.
"""
import struct
import sys
from pathlib import Path

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontInfo, QGuiApplication, QImage, QPainter, QPainterPath, QTransform

ICON_PATH = Path(__file__).resolve().parent.parent / "src" / "mathdoer" / "interface" / "icon.ico"

ICON_SIZES = (16, 20, 24, 32, 40, 48, 64, 128, 256)
FONT_FAMILY = "Segoe Script"
TOP_TEXT = "m"
BOTTOM_TEXT = "dm"
TOP_BACKGROUND = QColor("white")
TOP_INK = QColor("black")
BOTTOM_BACKGROUND = QColor("black")
BOTTOM_INK = QColor("white")

REFERENCE_PIXEL_SIZE = 1000  # the letters are drawn big, then scaled as shapes
WIDTH_FRACTION = 0.80  # of the square, the most that the widest text may cover
HEIGHT_FRACTION = 0.74  # of one rectangle, the most that the text may cover
ICO_ENTRY_SIZE_LIMIT = 256  # an entry of 256 pixels is written as 0


def text_outline(text: str, family: str) -> QPainterPath:
    font = QFont(family)
    font.setPixelSize(REFERENCE_PIXEL_SIZE)
    font.setBold(True)  # thin strokes disappear at 16 pixels
    outline = QPainterPath()
    outline.addText(0, 0, font, text)
    return outline


def placed(outline: QPainterPath, scale: float, center: QPointF) -> QPainterPath:
    """The outline made smaller by the scale and moved so that its ink is centered on the point."""
    ink = outline.boundingRect()
    transform = QTransform()
    transform.translate(center.x(), center.y())
    transform.scale(scale, scale)
    transform.translate(-ink.center().x(), -ink.center().y())
    return transform.map(outline)


def draw_icon(size: int, family: str = FONT_FAMILY) -> QImage:
    top_outline = text_outline(TOP_TEXT, family)
    bottom_outline = text_outline(BOTTOM_TEXT, family)
    widest = max(top_outline.boundingRect().width(), bottom_outline.boundingRect().width())
    tallest = max(top_outline.boundingRect().height(), bottom_outline.boundingRect().height())
    half = size / 2
    scale = min(WIDTH_FRACTION * size / widest, HEIGHT_FRACTION * half / tallest)  # one scale for both texts

    image = QImage(size, size, QImage.Format.Format_RGB32)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.fillRect(QRectF(0, 0, size, half), TOP_BACKGROUND)
    painter.fillRect(QRectF(0, half, size, half), BOTTOM_BACKGROUND)
    painter.setBrush(TOP_INK)
    painter.drawPath(placed(top_outline, scale, QPointF(size / 2, half / 2)))
    painter.setBrush(BOTTOM_INK)
    painter.drawPath(placed(bottom_outline, scale, QPointF(size / 2, half + half / 2)))
    painter.end()
    return image


def png_bytes(image: QImage) -> bytes:
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    buffer.close()
    return bytes(data)


def ico_bytes(png_by_size: dict[int, bytes]) -> bytes:
    """An icon file holding one square image of each size, every one stored as a PNG."""
    sizes = sorted(png_by_size)
    header = struct.pack("<HHH", 0, 1, len(sizes))  # reserved, type 1 = icon, count
    offset = len(header) + 16 * len(sizes)
    directory = b""
    for size in sizes:
        side = 0 if size >= ICO_ENTRY_SIZE_LIMIT else size
        directory += struct.pack("<BBBBHHII", side, side, 0, 0, 1, 32, len(png_by_size[size]), offset)
        offset += len(png_by_size[size])
    return header + directory + b"".join(png_by_size[size] for size in sizes)


def main() -> int:
    application = QGuiApplication(sys.argv)
    if QFontInfo(QFont(FONT_FAMILY)).family() != FONT_FAMILY:
        print(f"The font {FONT_FAMILY} is not installed here, and the icon is drawn with it.")
        return 1
    icon = ico_bytes({size: png_bytes(draw_icon(size)) for size in ICON_SIZES})
    ICON_PATH.write_bytes(icon)
    print(f"Wrote {ICON_PATH} ({len(icon)} bytes, sizes {', '.join(map(str, ICON_SIZES))}).")
    del application
    return 0


if __name__ == "__main__":
    sys.exit(main())
