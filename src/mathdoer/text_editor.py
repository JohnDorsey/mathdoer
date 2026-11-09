"""Opening a file in the system's editor for text files."""
import ntpath
import re
import subprocess
import sys
from pathlib import Path

ASSOCSTR_COMMAND = 1
FALLBACK_WINDOWS_EDITOR = "notepad.exe"

# %1 and %L stand for the file. %* and %2 to %9 stand for other arguments, which we have none of.
FILE_PLACEHOLDER = re.compile(r'(?P<opening>"?)%[1lL](?P<closing>"?)')
OTHER_PLACEHOLDER = re.compile(r" ?%[*2-9]")


def build_command_line(command_template: str, path: Path) -> str:
    """Fill in a Windows file-association command such as `"C:\\npp.exe" "%1"` or `NOTEPAD.EXE %1`."""
    found_file_placeholder = False

    def substitute(match: re.Match) -> str:
        nonlocal found_file_placeholder
        found_file_placeholder = True
        opening, closing = match["opening"], match["closing"]
        if bool(opening) == bool(closing):
            return f'"{path}"'  # already quoted, or not quoted and needs it
        return f"{opening}{path}{closing}"

    command = ntpath.expandvars(command_template)
    command = FILE_PLACEHOLDER.sub(substitute, command)
    command = OTHER_PLACEHOLDER.sub("", command).strip()
    return command if found_file_placeholder else f'{command} "{path}"'


def windows_text_editor_command() -> str:
    """The command Windows runs to open a .txt file: the user's default text editor."""
    import ctypes
    from ctypes import wintypes

    query = ctypes.windll.shlwapi.AssocQueryStringW
    query.argtypes = [
        wintypes.DWORD, wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR,
        wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD),
    ]
    query.restype = ctypes.HRESULT  # a failure raises OSError
    size = wintypes.DWORD(0)
    query(0, ASSOCSTR_COMMAND, ".txt", "open", None, ctypes.byref(size))
    buffer = ctypes.create_unicode_buffer(size.value)
    query(0, ASSOCSTR_COMMAND, ".txt", "open", buffer, ctypes.byref(size))
    return buffer.value


def open_in_text_editor(path: Path) -> None:
    """Start the editor and return at once. Raises OSError if it cannot be started."""
    if sys.platform == "win32":
        try:
            command_template = windows_text_editor_command()
        except OSError:
            command_template = FALLBACK_WINDOWS_EDITOR
        subprocess.Popen(build_command_line(command_template, path))
    elif sys.platform == "darwin":
        subprocess.Popen(["open", "-t", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])
