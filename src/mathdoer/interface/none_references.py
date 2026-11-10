"""A workaround for a bug in PySide6 6.12.0 on Linux.

Calls from Python into some protected Qt methods that return nothing (QSyntaxHighlighter's
setFormat, setCurrentBlockState and currentBlockUserData, measured) release one reference to
None each, which they never took. Before Python 3.12 the count of references to None is real,
and once the highlighter has made a few thousand such calls it reaches zero and the interpreter
aborts with "none_dealloc: deallocating None". From Python 3.12 on None is immortal and the bug
does nothing. Windows and macOS were not affected in the measurements.

Remove this module, and its use, once a PySide6 release is measured to be free of the bug (the
tests in test_none_references.py measure it).
"""
import ctypes
import sys
from collections.abc import Iterator
from contextlib import contextmanager


def _none_is_counted() -> bool:
    return sys.version_info < (3, 12)


@contextmanager
def balanced_none_references() -> Iterator[None]:
    """Take back the references to None that the code inside the block lost. Taking too many
    is harmless, so a reference the block gained is kept."""
    if not _none_is_counted():
        yield
        return
    before = sys.getrefcount(None)
    try:
        yield
    finally:
        for _ in range(before - sys.getrefcount(None)):
            ctypes.pythonapi.Py_IncRef(ctypes.py_object(None))
