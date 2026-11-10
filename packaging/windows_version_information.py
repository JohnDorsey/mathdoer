"""The version resource of mathdoer.exe: what Windows shows in the properties of the file (the
Details tab) and what Task Manager shows as the name of the program."""
from PyInstaller.utils.win32.versioninfo import (
    FixedFileInfo,
    StringFileInfo,
    StringStruct,
    StringTable,
    VarFileInfo,
    VarStruct,
    VSVersionInfo,
)

from project_information import read_project_table, version_numbers

PROGRAM_NAME = "mathdoer"
EXECUTABLE_NAME = "mathdoer.exe"
COPYRIGHT_NOTICE = "Copyright (C) 2026 John Dorsey. GPL-3.0-or-later."
DESCRIPTION = read_project_table()["description"]

LANGUAGE_AMERICAN_ENGLISH = 0x409
CODE_PAGE_UNICODE = 1200
STRING_TABLE_NAME = "040904B0"  # the language and the code page, as eight hexadecimal digits


def version_information(version: str) -> VSVersionInfo:
    major, minor, patch = version_numbers(version)
    numbers = (major, minor, patch, 0)  # a version resource has four numbers
    strings = {
        "CompanyName": "John Dorsey",
        "FileDescription": PROGRAM_NAME,
        "FileVersion": version,
        "InternalName": PROGRAM_NAME,
        "LegalCopyright": COPYRIGHT_NOTICE,
        "OriginalFilename": EXECUTABLE_NAME,
        "ProductName": PROGRAM_NAME,
        "ProductVersion": version,
        "Comments": DESCRIPTION,
    }
    return VSVersionInfo(
        ffi=FixedFileInfo(
            filevers=numbers,
            prodvers=numbers,
            mask=0x3F,
            flags=0x0,
            OS=0x40004,  # Windows NT, a Win32 program
            fileType=0x1,  # an application
            subtype=0x0,
            date=(0, 0),
        ),
        kids=[
            StringFileInfo([StringTable(STRING_TABLE_NAME, [StringStruct(*item) for item in strings.items()])]),
            VarFileInfo([VarStruct("Translation", [LANGUAGE_AMERICAN_ENGLISH, CODE_PAGE_UNICODE])]),
        ],
    )
