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


def _none_is_counted() -> bool:
    return sys.version_info < (3, 12)


def take_back_none_references(count: int) -> None:
    """Take back references to None that Qt calls lost. The count is how many fewer the code
    sees now than before the calls, read as sys.getrefcount(None) in the same function (a
    context manager cannot do it: its own machinery moves the count by a few). Taking too many
    back is harmless, so a count of zero or less does nothing."""
    if _none_is_counted():
        for _ in range(count):
            ctypes.pythonapi.Py_IncRef(ctypes.py_object(None))
