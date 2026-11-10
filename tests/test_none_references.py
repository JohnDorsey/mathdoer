"""Tests for the workaround for PySide6 6.12.0 on Linux, whose calls from Python into a few
protected Qt methods (QSyntaxHighlighter.setFormat, setCurrentBlockState and the like) release
one reference to None each time. Before Python 3.12 that count is real, and when it reaches zero
the interpreter aborts with "none_dealloc: deallocating None". From 3.12 on None is immortal and
nothing is wrong. Windows and macOS are not affected, so these tests only prove their point on
Linux, where they fail without the workaround; the first group proves the workaround itself."""
import ctypes
import gc
import sys

import pytest

from mathdoer.interface.none_references import balanced_none_references
from mathdoer.interface.prompt_editor import PromptEditor
from mathdoer.interface.syntax_highlighter import SyntaxHighlighter
from mathdoer.interface.theme import DARK_THEME
from mathdoer.languages.python import PYTHON

NONE_IS_COUNTED = sys.version_info < (3, 12)
needs_counted_none = pytest.mark.skipif(not NONE_IS_COUNTED, reason="None is immortal from Python 3.12 on")
TOLERANCE = 20  # references that the test machinery itself may take or give back
SMALL_TOLERANCE = 5  # the same, where the test makes no calls into Qt
RELEASED = 50  # far more than the tolerance, so that a block that did not take them back is caught


def none_count():
    gc.collect()
    return sys.getrefcount(None)


def release_none(times):
    """What the buggy calls do: give back a reference to None that was never taken."""
    for _ in range(times):
        ctypes.pythonapi.Py_DecRef(ctypes.py_object(None))


# ---------------------------------------------------------------------- the workaround itself

@needs_counted_none
def test_references_released_inside_the_block_are_taken_back():
    before = sys.getrefcount(None)
    with balanced_none_references():
        release_none(RELEASED)
    assert sys.getrefcount(None) >= before - SMALL_TOLERANCE


@needs_counted_none
def test_a_block_that_releases_nothing_changes_nothing():
    before = sys.getrefcount(None)
    with balanced_none_references():
        pass
    assert abs(sys.getrefcount(None) - before) <= SMALL_TOLERANCE


@needs_counted_none
def test_references_taken_inside_the_block_are_left_alone():
    """More references to None is harmless; fewer is what kills the interpreter."""
    before = sys.getrefcount(None)
    keep = [None] * 7
    with balanced_none_references():
        keep.extend([None] * RELEASED)
    assert sys.getrefcount(None) >= before + 7 + RELEASED - SMALL_TOLERANCE
    del keep


@needs_counted_none
def test_references_are_taken_back_when_the_block_raises():
    before = sys.getrefcount(None)
    with pytest.raises(ValueError):
        with balanced_none_references():
            release_none(RELEASED)
            raise ValueError("inside")
    assert sys.getrefcount(None) >= before - SMALL_TOLERANCE


def test_the_block_does_nothing_where_none_is_immortal(monkeypatch):
    monkeypatch.setattr(sys, "version_info", (3, 12, 0, "final", 0))
    with balanced_none_references():
        pass  # no reading of the count, no change


# --------------------------------------------------------------------- the interface code

@needs_counted_none
def test_highlighting_lines_does_not_use_up_references_to_none(qtbot):
    editor = PromptEditor(DARK_THEME, PYTHON)
    qtbot.addWidget(editor)
    editor.show()
    text = "total = (1 + 2) * 3  # a comment\nname = 'text'\n" * 100
    editor.setPlainText(text)
    before = none_count()
    for _ in range(5):
        editor.setPlainText(text)
    assert none_count() >= before - TOLERANCE


@needs_counted_none
def test_a_highlighter_on_its_own_does_not_use_up_references_to_none(qtbot):
    from PySide6.QtGui import QTextDocument

    document = QTextDocument()
    highlighter = SyntaxHighlighter(document, PYTHON, DARK_THEME)
    document.setPlainText("x = 1\n" * 50)
    before = none_count()
    highlighter.rehighlight()
    highlighter.set_coloring(False)
    highlighter.set_coloring(True)
    assert none_count() >= before - TOLERANCE


@needs_counted_none
def test_editing_and_drawing_the_prompt_box_does_not_use_up_references_to_none(qtbot):
    from PySide6.QtCore import Qt

    editor = PromptEditor(DARK_THEME, PYTHON)
    qtbot.addWidget(editor)
    editor.resize(600, 300)
    editor.show()
    qtbot.waitExposed(editor)
    before = none_count()
    for index in range(300):
        qtbot.keyClicks(editor, "x = (1,")
        qtbot.keyClick(editor, Qt.Key.Key_Return)
        editor.resize(600 + index % 5, 300)
        editor.set_font_size(11 + index % 3)
        editor.viewport().repaint()
    assert none_count() >= before - TOLERANCE
