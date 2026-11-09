"""Tests for how the prompt box looks: line numbers, indentation guides, zoom and word wrap."""
import pytest
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent

from mathdoer.interface.fonts import DEFAULT_POINT_SIZE, MAXIMUM_POINT_SIZE, MINIMUM_POINT_SIZE
from mathdoer.interface.output_display import OutputDisplay
from mathdoer.interface.prompt_editor import (
    GUTTER_PADDING,
    MINIMUM_GUTTER_DIGITS,
    PromptEditor,
)
from mathdoer.interface.theme import DARK_THEME
from mathdoer.languages.python import PYTHON

CONTROL = Qt.KeyboardModifier.ControlModifier
NONE = Qt.KeyboardModifier.NoModifier


@pytest.fixture
def editor(qtbot):
    widget = PromptEditor(DARK_THEME, PYTHON)
    qtbot.addWidget(widget)
    widget.resize(600, 300)
    widget.show()
    qtbot.waitExposed(widget)
    return widget


def digit_width(editor):
    return editor.fontMetrics().horizontalAdvance("9")


def numbered_lines(count):
    return "\n".join(f"line {number}" for number in range(1, count + 1))


# ------------------------------------------------------------------- line numbers

def test_the_font_has_a_width_to_measure_the_gutter_with(editor):
    assert digit_width(editor) > 0


def test_the_gutter_is_at_least_three_digits_wide(editor):
    assert MINIMUM_GUTTER_DIGITS == 3
    editor.setPlainText("a\nb")
    assert editor.gutter_width() == 2 * GUTTER_PADDING + 3 * digit_width(editor)


def test_the_gutter_grows_with_the_number_of_digits(editor):
    editor.setPlainText(numbered_lines(999))
    assert editor.gutter_width() == 2 * GUTTER_PADDING + 3 * digit_width(editor)
    editor.setPlainText(numbered_lines(1000))
    assert editor.gutter_width() == 2 * GUTTER_PADDING + 4 * digit_width(editor)
    editor.setPlainText("a")
    assert editor.gutter_width() == 2 * GUTTER_PADDING + 3 * digit_width(editor)


def test_the_text_starts_to_the_right_of_the_gutter(editor):
    editor.setPlainText(numbered_lines(1000))
    assert editor.viewportMargins().left() == editor.gutter_width()
    assert editor.gutter.geometry().left() == editor.contentsRect().left()
    assert editor.gutter.width() == editor.gutter_width()
    assert editor.gutter.geometry().right() < editor.viewport().geometry().left()


def test_the_gutter_is_as_tall_as_the_box(editor):
    assert editor.gutter.height() == editor.contentsRect().height()
    editor.resize(600, 400)
    assert editor.gutter.height() == editor.contentsRect().height()


def test_every_line_gets_one_number(editor):
    editor.setPlainText("a\nb\nc")
    assert editor.visible_line_numbers() == [1, 2, 3]


def test_a_wrapped_line_gets_only_one_number(qtbot, editor):
    editor.resize(220, 300)
    editor.setPlainText("word " * 12 + "\nsecond")
    qtbot.wait(50)
    assert editor.document().begin().layout().lineCount() > 1  # the first line did wrap
    assert editor.visible_line_numbers() == [1, 2]


def test_the_numbers_follow_the_scrolling(qtbot, editor):
    editor.setPlainText(numbered_lines(200))
    qtbot.waitUntil(lambda: editor.verticalScrollBar().maximum() > 50)
    editor.verticalScrollBar().setValue(50)
    numbers = editor.visible_line_numbers()
    assert numbers[0] in (51, 52)
    assert numbers == list(range(numbers[0], numbers[0] + len(numbers)))
    assert len(numbers) > 5


def test_the_gutter_is_painted_in_its_own_colors(editor):
    editor.setPlainText("a\nb\nc")
    image = editor.gutter.grab().toImage()
    background = DARK_THEME.line_number_background
    assert image.pixelColor(0, image.height() - 1).name() == background
    colors = {image.pixelColor(x, y).name() for x in range(image.width()) for y in range(0, 60)}
    assert background in colors
    assert len(colors) > 1  # the numbers themselves


def test_the_gutter_follows_the_font_size(editor):
    editor.setPlainText("a")
    before = editor.gutter_width()
    editor.set_font_size(DEFAULT_POINT_SIZE + 10)
    assert editor.gutter_width() > before
    assert editor.viewportMargins().left() == editor.gutter_width()
    assert editor.gutter.width() == editor.gutter_width()


# ------------------------------------------------------------ indentation guides

def guides_of(editor):
    return [(guide.line, guide.column) for guide in editor.visible_indentation_guides()]


def test_lines_get_a_guide_at_each_level_of_their_indentation(editor):
    editor.setPlainText("def f():\n    x = 1\n        y = 2\nz")
    assert guides_of(editor) == [(1, 0), (2, 0), (2, 4)]


def test_a_blank_line_continues_the_guides_around_it(editor):
    editor.setPlainText("def f():\n    x = 1\n\n    y = 2\n\nz")
    assert guides_of(editor) == [(1, 0), (2, 0), (3, 0), (4, 0)]


def test_guides_stand_in_the_columns_of_the_text(editor):
    editor.setPlainText("        x")
    space = editor.fontMetrics().horizontalAdvance(" ")
    first, second = editor.visible_indentation_guides()
    assert second.x - first.x == 4 * space
    assert first.x >= editor.document().documentMargin()


def test_guides_follow_the_font_size(editor):
    editor.setPlainText("        x")
    before = editor.visible_indentation_guides()
    editor.set_font_size(DEFAULT_POINT_SIZE + 10)
    after = editor.visible_indentation_guides()
    assert after[1].x - after[0].x > before[1].x - before[0].x


def test_a_guide_covers_the_row_of_its_line(editor):
    editor.setPlainText("a\n    b\n    c")
    first, second = editor.visible_indentation_guides()
    assert (first.line, second.line) == (1, 2)
    assert first.bottom == second.top  # the guides of neighbouring lines meet
    assert first.top < first.bottom


def test_on_a_wrapped_line_the_guide_covers_only_the_first_row(qtbot, editor):
    editor.resize(220, 300)
    editor.setPlainText("    " + "word " * 60)
    qtbot.wait(50)
    layout = editor.document().begin().layout()
    assert layout.lineCount() > 2  # it did wrap
    guide = editor.visible_indentation_guides()[0]
    assert guide.bottom - guide.top == round(layout.lineAt(0).height())


def test_the_guides_are_painted_in_the_theme_color(editor):
    editor.setPlainText("a\n        b\n        c")
    image = editor.viewport().grab().toImage()
    first, second = editor.visible_indentation_guides()[:2]
    middle = (first.top + first.bottom) // 2
    assert image.pixelColor(first.x, middle).name() == DARK_THEME.indentation_guide
    assert image.pixelColor(second.x, middle).name() == DARK_THEME.indentation_guide
    assert image.pixelColor(second.x + 2, middle).name() == DARK_THEME.text_background


def test_no_guide_is_painted_where_the_line_has_none(editor):
    editor.setPlainText("a\n    b")
    image = editor.viewport().grab().toImage()
    guide = editor.visible_indentation_guides()[0]
    row_of_a = 3
    assert image.pixelColor(guide.x, row_of_a).name() != DARK_THEME.indentation_guide


def test_only_the_visible_lines_have_guides(qtbot, editor):
    editor.setPlainText("\n".join("    x" for _ in range(500)))
    qtbot.waitUntil(lambda: editor.verticalScrollBar().maximum() > 100)
    assert 5 < len(editor.visible_indentation_guides()) < 100


# ------------------------------------------------------------------------ zoom

@pytest.fixture(params=["prompt", "output"])
def text_box(request, qtbot):
    widget = PromptEditor(DARK_THEME, PYTHON) if request.param == "prompt" else OutputDisplay(DARK_THEME)
    qtbot.addWidget(widget)
    widget.resize(600, 300)
    widget.show()
    return widget


def wheel(box, delta, modifiers):
    event = QWheelEvent(
        QPointF(10, 10), box.mapToGlobal(QPointF(10, 10)), QPoint(0, 0), QPoint(0, delta),
        Qt.MouseButton.NoButton, modifiers, Qt.ScrollPhase.NoScrollPhase, False,
    )
    box.wheelEvent(event)
    return event


def test_a_box_starts_at_the_default_font_size(text_box):
    assert text_box.font().pointSize() == DEFAULT_POINT_SIZE


def test_set_font_size_changes_the_font_and_keeps_it_monospace(text_box):
    text_box.set_font_size(15)
    assert text_box.font().pointSize() == 15
    assert text_box.font().fixedPitch()


def test_set_font_size_is_kept_within_limits(text_box):
    text_box.set_font_size(1)
    assert text_box.font().pointSize() == MINIMUM_POINT_SIZE
    text_box.set_font_size(1000)
    assert text_box.font().pointSize() == MAXIMUM_POINT_SIZE


def test_ctrl_wheel_up_asks_to_zoom_in_and_down_to_zoom_out(text_box):
    requests = []
    text_box.zoom_requested.connect(requests.append)
    event = wheel(text_box, 120, CONTROL)
    assert event.isAccepted()
    wheel(text_box, -120, CONTROL)
    wheel(text_box, 240, CONTROL)
    assert requests == [1, -1, 1, 1]


def test_small_wheel_steps_add_up_to_one_zoom_step(text_box):
    requests = []
    text_box.zoom_requested.connect(requests.append)
    for _ in range(4):
        wheel(text_box, 30, CONTROL)
    assert requests == [1]
    for _ in range(4):
        wheel(text_box, -30, CONTROL)
    assert requests == [1, -1]


def test_the_wheel_without_ctrl_does_not_zoom(text_box):
    requests = []
    text_box.zoom_requested.connect(requests.append)
    wheel(text_box, 120, NONE)
    assert requests == []


def test_the_wheel_without_ctrl_still_scrolls(qtbot, text_box):
    text_box.setPlainText(numbered_lines(300)) if isinstance(text_box, PromptEditor) else text_box.apply_changes(
        segments=[(numbered_lines(300), False)]
    )
    qtbot.waitUntil(lambda: text_box.verticalScrollBar().maximum() > 50)
    text_box.verticalScrollBar().setValue(100)
    wheel(text_box, -120, NONE)
    assert text_box.verticalScrollBar().value() > 100


# -------------------------------------------------------------------- word wrap

def test_word_wrap_is_on_by_default(text_box):
    assert text_box.word_wrap
    assert text_box.lineWrapMode() == text_box.LineWrapMode.WidgetWidth


def test_toggling_word_wrap_switches_between_wrapping_and_not(text_box):
    text_box.toggle_word_wrap()
    assert not text_box.word_wrap
    assert text_box.lineWrapMode() == text_box.LineWrapMode.NoWrap
    text_box.toggle_word_wrap()
    assert text_box.word_wrap
    assert text_box.lineWrapMode() == text_box.LineWrapMode.WidgetWidth


def test_without_word_wrap_a_long_line_makes_a_horizontal_scroll_bar(qtbot, editor):
    editor.setPlainText("x" * 500)
    qtbot.wait(50)
    assert editor.horizontalScrollBar().maximum() == 0
    editor.toggle_word_wrap()
    qtbot.waitUntil(lambda: editor.horizontalScrollBar().maximum() > 0)
