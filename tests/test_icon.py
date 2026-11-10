"""Tests for the icon: the file in the repository (what the window and the package use) and the
drawing code that made it (packaging/make_icon.py). The offscreen platform has no fonts, so the
drawing is tested with letters replaced by plain rectangles of known size."""
import struct

import pytest
from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QIcon, QImage, QPainterPath

import make_icon
from mathdoer.interface.icon import ICON_PATH, application_icon

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
DARK = 96  # a pixel below this red value is ink on white, or background of the black half
LIGHT = 160


def read_icon_entries(data: bytes) -> list[tuple[int, int, bytes]]:
    """(width, height, image data) of every entry of an icon file."""
    reserved, kind, count = struct.unpack_from("<HHH", data, 0)
    assert (reserved, kind) == (0, 1)
    entries = []
    for index in range(count):
        width, height, _, _, planes, bits, length, offset = struct.unpack_from("<BBBBHHII", data, 6 + 16 * index)
        entries.append((width or 256, height or 256, data[offset : offset + length]))
    return entries


def pixel_rows(image: QImage) -> list[list[int]]:
    return [[image.pixel(x, y) & 0xFFFFFF for x in range(image.width())] for y in range(image.height())]


def red_values(image: QImage) -> list[list[int]]:
    """The red value of each pixel, by row."""
    return [[pixel >> 16 for pixel in row] for row in pixel_rows(image)]


def is_gray(pixel: int) -> bool:
    return pixel >> 16 == (pixel >> 8) & 0xFF == pixel & 0xFF


def ink_box(values: list[list[int]], rows: range, is_ink) -> tuple[int, int, int, int] | None:
    """(left, top, right, bottom) of the pixels in the rows that satisfy is_ink, edges included."""
    found = [(x, y) for y in rows for x, value in enumerate(values[y]) if is_ink(value)]
    if not found:
        return None
    xs, ys = [x for x, _ in found], [y for _, y in found]
    return min(xs), min(ys), max(xs), max(ys)


@pytest.fixture(scope="module")
def committed_entries():
    return read_icon_entries(ICON_PATH.read_bytes())


def test_the_icon_file_holds_every_size_windows_asks_for(committed_entries):
    assert [(width, height) for width, height, _ in committed_entries] == [(s, s) for s in make_icon.ICON_SIZES]
    assert {16, 24, 32, 48, 256} <= set(make_icon.ICON_SIZES)


def test_every_entry_is_a_png_of_the_size_in_the_directory(committed_entries):
    for width, height, data in committed_entries:
        assert data.startswith(PNG_SIGNATURE)
        image = QImage.fromData(data)
        assert (image.width(), image.height()) == (width, height)


def test_qt_loads_the_icon_with_all_its_sizes(qapp):
    icon = application_icon()
    assert not icon.isNull()
    assert sorted(size.width() for size in icon.availableSizes()) == list(make_icon.ICON_SIZES)


def test_a_missing_icon_file_would_give_a_null_icon(qapp, tmp_path):
    assert QIcon(str(tmp_path / "nothing.ico")).isNull()  # why the other tests check the real file


@pytest.mark.parametrize("size", make_icon.ICON_SIZES)
def test_the_square_is_white_above_and_black_below_with_nothing_but_gray(committed_entries, size):
    image = QImage.fromData(next(data for width, _, data in committed_entries if width == size))
    assert all(is_gray(pixel) for row in pixel_rows(image) for pixel in row)
    values = red_values(image)
    half = size // 2
    assert [values[0][0], values[0][size - 1], values[half - 1][0], values[half - 1][size - 1]] == [255] * 4
    assert [values[half][0], values[half][size - 1], values[size - 1][0], values[size - 1][size - 1]] == [0] * 4


@pytest.mark.parametrize("size", make_icon.ICON_SIZES)
def test_black_letters_on_the_white_half_and_white_letters_on_the_black_half(committed_entries, size):
    data = next(data for width, _, data in committed_entries if width == size)
    values = red_values(QImage.fromData(data))
    half = size // 2
    top_ink = ink_box(values, range(half), lambda value: value < DARK)
    bottom_ink = ink_box(values, range(half, size), lambda value: value > LIGHT)
    assert top_ink is not None and bottom_ink is not None
    # the letters stay clear of the edges of their rectangle, and of the cut between the two
    margin = max(1, size // 20)
    assert top_ink[0] >= margin and top_ink[2] <= size - 1 - margin
    assert top_ink[1] >= margin and top_ink[3] <= half - 1 - margin
    assert bottom_ink[0] >= margin and bottom_ink[2] <= size - 1 - margin
    assert bottom_ink[1] >= half + margin and bottom_ink[3] <= size - 1 - margin


def test_dm_is_wider_than_m_and_both_are_centered(committed_entries):
    data = next(data for width, _, data in committed_entries if width == 256)
    values = red_values(QImage.fromData(data))
    top = ink_box(values, range(128), lambda value: value < DARK)
    bottom = ink_box(values, range(128, 256), lambda value: value > LIGHT)
    assert bottom[2] - bottom[0] > 1.4 * (top[2] - top[0])
    for left, _, right, _ in (top, bottom):
        assert abs((left + right) / 2 - 127.5) <= 6
    for box, middle in ((top, 64), (bottom, 192)):
        assert abs((box[1] + box[3]) / 2 - middle) <= 6


def test_the_icon_is_the_icon_that_the_package_data_carries():
    assert ICON_PATH.parent.name == "interface" and ICON_PATH.name == "icon.ico"
    assert make_icon.ICON_PATH == ICON_PATH


class TestIcoFile:
    def test_the_directory_describes_each_png_in_order_of_size(self):
        png_by_size = {32: PNG_SIGNATURE + b"thirty-two", 16: PNG_SIGNATURE + b"sixteen", 256: PNG_SIGNATURE + b"big"}
        entries = read_icon_entries(make_icon.ico_bytes(png_by_size))
        assert entries == [(16, 16, png_by_size[16]), (32, 32, png_by_size[32]), (256, 256, png_by_size[256])]

    def test_an_entry_of_256_pixels_is_written_as_0_and_the_smaller_ones_as_themselves(self):
        data = make_icon.ico_bytes({255: b"a", 256: b"b"})
        assert [data[6], data[6 + 16]] == [255, 0]


class TestDrawing:
    """The letters become rectangles: 40 by 10 for the top text and 80 by 20 for the bottom text.
    In a square of 100 pixels the bottom text is as wide as it may be (80) at scale 1, so every
    edge falls on a pixel boundary and the ink can be measured exactly."""

    @pytest.fixture(autouse=True)
    def rectangles_for_letters(self, qapp, monkeypatch):
        def outline(text, family):
            path = QPainterPath()
            width, height = {make_icon.TOP_TEXT: (40, 10), make_icon.BOTTOM_TEXT: (80, 20)}[text]
            path.addRect(QRectF(5, -height, width, height))  # off the origin, as letters are
            return path

        monkeypatch.setattr(make_icon, "text_outline", outline)

    def drawn(self, size=100):
        values = red_values(make_icon.draw_icon(size))
        half = size // 2
        top = ink_box(values, range(half), lambda value: value < 128)
        bottom = ink_box(values, range(half, size), lambda value: value > 128)
        return values, top, bottom

    def test_the_texts_are_centered_in_their_rectangles_by_the_ink(self):
        _, top, bottom = self.drawn()
        assert top == (30, 20, 69, 29)  # centered on (50, 25)
        assert bottom == (10, 65, 89, 84)  # centered on (50, 75)

    def test_both_texts_have_one_scale_and_the_wider_one_fills_four_fifths_of_the_width(self):
        _, top, bottom = self.drawn()
        assert bottom[2] - bottom[0] + 1 == round(make_icon.WIDTH_FRACTION * 100)
        assert (top[2] - top[0] + 1, top[3] - top[1] + 1) == (40, 10)
        assert (bottom[2] - bottom[0] + 1, bottom[3] - bottom[1] + 1) == (80, 20)

    def test_text_that_is_tall_and_narrow_is_limited_by_its_height_instead(self, monkeypatch):
        def tall(text, family):
            path = QPainterPath()
            path.addRect(QRectF(0, -100, 10, 100))
            return path

        monkeypatch.setattr(make_icon, "text_outline", tall)
        values, _, _ = self.drawn()
        column = 50 - 1  # inside the ink, which is 3.7 pixels wide around x = 50
        covered = sum((255 - values[y][column]) / 255 for y in range(50))
        # the two rows at the ends are partly covered and have 8 bits to say how much: off by 1/255 at most each
        assert covered == pytest.approx(make_icon.HEIGHT_FRACTION * 50, abs=2 / 255)

    def test_the_square_is_cut_into_two_equal_halves_of_one_color_each(self):
        values, _, _ = self.drawn()
        for row in (0, 19, 49):  # the first row, the row above the top text, the last row of the half
            assert all(value == 255 for value in values[row])
        for row in (50, 64, 99):  # the first row of the other half, the row above the bottom text, the last row
            assert all(value == 0 for value in values[row])

    def test_the_colors_are_black_ink_above_and_white_ink_below(self):
        values, _, _ = self.drawn()
        assert values[25][50] == 0  # the top text covers the center of the top half
        assert values[75][50] == 255  # and the bottom text the center of the bottom half

    def test_the_center_of_a_text_is_placed_exactly_where_asked(self):
        outline = make_icon.text_outline(make_icon.BOTTOM_TEXT, "any")
        moved = make_icon.placed(outline, 0.5, QPointF(100, 200))
        assert moved.boundingRect().center() == QPointF(100, 200)
        assert moved.boundingRect().width() == 40
