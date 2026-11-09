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
| Ctrl+Enter | Run the prompt |
| Shift+Esc | Cancel a running prompt |
| Tab, Shift+Tab | Indent, dedent (every selected line) |
| Enter | New line, indented like the line above and one level more after a colon |
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

In the Constants and Units menus, a click inserts the name of the constant or unit and Shift+click inserts its value.

## The startup file

Before every prompt, mathdoer runs your startup file in the same namespace. On Windows it is `%APPDATA%\mathdoer\startup_python.py`; Edit > Edit startup file opens it in your editor for text files. It starts out with `from math import *` and code that defines every constant and unit from the registry, such as `SPEED_OF_LIGHT` and `INCH`. mathdoer never overwrites your changes.

## Settings

Edit > Edit settings opens the settings file, `%APPDATA%\mathdoer\settings_python.toml` on Windows, in your editor for text files, creating it first if it is missing. mathdoer reads it before every run, so a change takes effect on the next run. A mistake in it is reported in the output box and the prompt is not run.

The one setting is `interpreter`, the Python that runs your prompts (3.11 or later). Without it prompts run on the Python that mathdoer itself runs on, which has no extra packages. Point it at a Python that has the packages you want:

```toml
interpreter = 'C:\Python311\python.exe'
```

Use single quotes around a Windows path so its backslashes are taken literally. Give the full path: a bare name such as `py` is looked up on the PATH that mathdoer was started with, and `uv run` puts the project's own environment first on that PATH.

## License

Copyright (C) 2026 John Dorsey

mathdoer is free software, licensed under the GNU General Public License, version 3 or (at your option) any later version. See [LICENSE](LICENSE).
