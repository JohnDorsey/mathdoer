# mathdoer

A calculator that executes the Python code you type.

Type code in the top box and press Ctrl+Enter. The value of the last expression, and anything you print, appears in the bottom box. Every run starts from a clean slate in a separate process, so nothing is remembered between runs except what the startup file defines.

## Running

```
uv run mathdoer
uv run pytest
```

## Keys

| Keys | Does |
| --- | --- |
| Ctrl+Enter | Run the prompt (in single-line mode, Enter runs it too) |
| Shift+Esc | Cancel a running prompt |
| Tab, Shift+Tab | Indent, dedent (every selected line) |
| Enter | New line, indented like the line above and one level more after a colon (in single-line mode, Alt+Enter does this and Enter runs the prompt) |
| Ctrl+/ | Comment or uncomment the lines |
| Ctrl+D | Duplicate the lines |
| Alt+Up, Alt+Down | Move the lines |
| Ctrl+Shift+K | Delete the lines |
| Home | First character of the line, then the start of the line |
| Ctrl+Left, Ctrl+Right, Ctrl+Backspace, Ctrl+Delete | By word |
| Ctrl+Z, Ctrl+Y or Ctrl+Shift+Z | Undo, redo |
| Ctrl+F, Ctrl+H | Find, find and replace |
| Enter, Shift+Enter, F3, Shift+F3 | Next, previous match |
| Esc | Close the find bar |
| Ctrl+`+`, Ctrl+`=`, Ctrl+`-`, Ctrl+`0`, Ctrl+mouse wheel | Zoom in, zoom out, reset |
| Alt+Z | Turn word wrap on or off in the box that has the focus |

Every one of these can be turned off in the settings window (see below).

In the Constants and Units menus, a click inserts the name of the constant or unit and Shift+click inserts its value.

## The startup file

Before every prompt, mathdoer runs your startup file in the same namespace. On Windows it is `%APPDATA%\mathdoer\startup_python.py`; Edit > Edit startup file opens it in your editor for text files. It starts out with `from math import *` and code that defines every constant and unit from the registry, such as `SPEED_OF_LIGHT` and `INCH`. mathdoer never overwrites your changes.

## The settings window

Edit > Settings… opens a window with the pages listed down the left and the settings of the chosen page on the right. A change takes effect at once and is saved; there is nothing to confirm. The buttons are Use current size, which copies the size of the open window into the window size setting, Restore defaults, and Close.

- **Window:** the width and height the window has when mathdoer starts. A window larger than the screen is made to fit it.
- **Display:** line numbers, colors for keywords, strings, comments and numbers, the highlight of the matching bracket, indentation guides, wrapping of long lines in each box (Alt+Z changes this one too), and zooming with the keys and with the mouse wheel.
- **Fonts:** the font and the size, in points, of the prompt box and of the output box, each on its own. Pick a font from the list of monospace fonts or type the name of any font; one that is not installed is replaced by Consolas or, failing that, another monospace font. Zooming moves each box a point at a time from its own size, and Ctrl+0 puts both back to the sizes set here. Choosing another font or size for a box replaces its zoom.
- **Editing:** the width of a tab, in characters (4 to match Python's convention, which is the default), which is how far apart the tab stops and the indentation guides are and how many spaces one level of indentation takes; single-line mode, in which Enter runs the prompt and Alt+Enter starts a new line (Ctrl+Enter still runs, Shift+Enter still starts a new line); whether Tab inserts spaces or a tab character, whether Tab indents every selected line, Shift+Tab, whether Enter keeps the indentation and adds a level after a line that opens a block, and the Home key going to the first character before the start of the line.
- **Line commands:** comment, duplicate, move and delete lines.
- **Find:** the find and replace bar.

Every feature starts out on. Turn them all off and the prompt box is a plain text editor, like Notepad. A feature that is off is not handled by mathdoer at all, so its keys do whatever Qt does with them; only Shift+Tab is swallowed, so that the focus does not leave the box.

The settings are kept in `%APPDATA%\mathdoer\interface_settings.toml` on Windows. The window writes the whole file whenever a setting changes, so comments you add to it are lost, and mathdoer reads it only when it starts. A file that cannot be read does not stop mathdoer: it starts with the default settings and says why in the output box, and the first change in the settings window, or Restore defaults, replaces the file.

## The Python settings file

Edit > Edit Python settings file opens the settings file, `%APPDATA%\mathdoer\settings_python.toml` on Windows, in your editor for text files, creating it first if it is missing. mathdoer reads it before every run, so a change takes effect on the next run. A mistake in it is reported in the output box and the prompt is not run.

The one setting is `interpreter`, the Python that runs your prompts (3.11 or later). Without it prompts run on the Python that mathdoer itself runs on, which has no extra packages. Point it at a Python that has the packages you want:

```toml
interpreter = 'C:\Python311\python.exe'
```

Give the full path of the program, or the name of one on your PATH, such as `py`. Use single quotes around a Windows path so its backslashes are taken literally. A run does not inherit the virtual environment that mathdoer itself runs in (`uv run` activates one), so `py`, `python` and the Windows `python3.exe` alias reach the Python they stand for.

## Building a package

```
uv run python packaging/fetch_embeddable_python.py
uv run pyinstaller packaging/mathdoer.spec
uv run python packaging/make_zip.py
uv run python packaging/check_build.py dist/mathdoer-1.0.0-windows-x64.zip
```

The first downloads python.org's embeddable Python (3.13, about 11 MB, once; the file is checked against a pinned checksum). The second builds `dist/mathdoer/`, a folder with `mathdoer.exe` in it, and the third packs it, with `LICENSE` and `README.md`, into `dist/mathdoer-1.0.0-windows-x64.zip`: the file to hand out, which unzips into one folder, `mathdoer-1.0.0`. The fourth unzips that zip into a temporary folder and checks what a user would get: that the files the program reads are in it, that the executable has the icon and the version of the project, that a prompt runs on the Python it carries, and that it starts, with a configuration folder of its own, and keeps running. `check_build.py` also takes the folder `dist/mathdoer` instead of the zip.

The version, 1.0.0, is written in `pyproject.toml` and nowhere else; the version information of `mathdoer.exe` (shown in its properties) and the name of the zip are made from it. The icon, `src/mathdoer/interface/icon.ico`, is drawn by `packaging/make_icon.py` (run it only to change the icon; it needs the font Segoe Script, which Windows ships).

The packaged program runs prompts on that Python, which has the standard library and nothing else, as the unpackaged program does on its own Python. Name another in `settings_python.toml` (Edit > Edit Python settings file) to use packages. The embeddable Python exists for Windows only; a package built elsewhere has none, and a run without an `interpreter` setting says so.

## License

Copyright (C) 2026 John Dorsey

mathdoer is free software, licensed under the GNU General Public License, version 3 or (at your option) any later version. See [LICENSE](LICENSE).
