# mathdoer todo

## Scheduled

First version.

- [x] Run the prompt in a separate process with a clean namespace on every run (no interface yet)
  - [x] Run the startup file first, in the same namespace
  - [x] Show the value of the last expression, as a REPL does; `print` also works
  - [x] Show errors as a trimmed traceback with line numbers matching the prompt; errors in the startup file are labelled as such and the prompt is not run
  - [x] Output streams live; cancelling stops the run and everything it started
  - [x] Output buffer with a size cap: when it overflows the oldest text is discarded
  - [x] `input()` fails with a clear message
- [x] Interface for running
  - [x] Ctrl+Enter runs; Shift+Esc cancels a running prompt and marks the output as cancelled
  - [x] The output box shows a truncation notice when the output buffer has discarded text
  - [x] A spinner (`/ - \ |`) is shown in the output while running; after 5 seconds without a result it is followed by a counter of elapsed time: `00:05`, then `hh:mm:ss` from one hour, then `d:hh:mm:ss` from one day
  - [x] Output is cleared when a new run starts; error text is shown in red
- [ ] Keep internals and names language-neutral (ongoing): everything specific to Python (startup file, literals, comment syntax, running the code) lives in a Python language module, so other languages can be added later; the interface stays Python
- [x] Startup file (Python's), created for the user from a bundled default
  - [x] `from math import *`, then `from builtins import pow` with a note explaining why (`math.pow` would otherwise turn `pow(2, 100)` into a float)
  - [x] Code that reads the registry and defines every constant and unit as a SCREAMING_SNAKE_CASE variable
  - [x] Edit > Edit startup file opens it in the system's editor for `.txt` files (recreated from the default if missing)
- [x] Registry of constants and units (TOML, language-neutral), the single source for the menus and the startup file
  - [x] Same items as preccalc; labels clarified where preccalc's are ambiguous; CODATA 2022 and exact definitions; names that carry their definition when the plain word is ambiguous
  - [x] Greatest correct precision: exact values as exact decimals or ratios; irrational values to 100 significant digits
- [x] Menus: Edit, Constants, Units
  - [x] Constants and Units: click inserts the name; Shift+click inserts the literal value (Alt+click was tried: Windows closes the menu when Alt is pressed)
  - [x] Edit: Undo, Redo, Cut, Copy, Paste, Select all, Copy output, Edit startup file
- [x] Prompt box (top, editable) and output box (bottom, read-only but selectable and copyable) with a draggable splitter; resizable window
- [x] Dark, high-contrast theme (every text color is tested for at least 7:1 contrast; the syntax colors await approval)
- [x] Prompt box editing behaviors
  - [x] Indentation guides (they run through blank lines and cover only the first row of a wrapped line)
  - [x] Tab inserts spaces; Shift+Tab dedents; Tab and Shift+Tab work on a selection
  - [x] Auto-indent after a colon
  - [x] Toggle comment (Ctrl+/)
  - [x] Duplicate line (Ctrl+D)
  - [x] Move line up and down (Alt+Up, Alt+Down)
  - [x] Delete line (Ctrl+Shift+K)
  - [x] Smart Home; Ctrl+Left/Right and Ctrl+Backspace/Delete by word
  - [x] Undo and redo
  - [x] Syntax highlighting; matching-bracket highlight
  - [x] Line numbers
  - [x] Find and replace as an inline bar above the prompt box (Ctrl+F, Ctrl+H, Enter and Shift+Enter, F3 and Shift+F3, Esc or the close button), prompt box only; Match case, a match counter, every match highlighted, Replace and Replace all (one undo step)
  - [x] Zoom (Ctrl with +, - and 0, and Ctrl with the mouse wheel; both boxes together)
  - [x] Monospace font; word wrap on, toggled with Alt+Z in the box that has the focus
  - [x] No auto-closing brackets or quotes
- [x] GPL-3.0-or-later license
- [ ] Windows first; mathdoer itself needs Python 3.12 or later, the Python that runs prompts 3.11 or later

Interpreter setting.

- [x] Settings file per language (`settings_python.toml`, TOML, created from a bundled default by Edit > Edit Python settings file, read before every run); unknown settings and bad values are errors that are explained in the output box
  - [x] `interpreter`: the program that runs the prompt, as a full path or a name on the PATH

Settings window.

- [x] Edit > Settings… opens a window with vertical tabs on the left, as in the preferences of Notepad++; a change applies and is saved at once, and the buttons are Use current size, Restore defaults and Close
  - [x] Every editor feature can be turned off, down to a plain text editor: line numbers, syntax colors, bracket highlight, indentation guides, wrapping in each box, zoom with the keys and the wheel, Tab inserting spaces or a tab character, Tab on selected lines, Shift+Tab, Enter keeping the indentation, a level after a block opening, Home, the four line commands, and the find bar
  - [x] Default window size (applies at the next start; a size larger than the screen is fitted to it)
  - [x] `interface_settings.toml`, written by the window and read at launch; a file that cannot be read gives the defaults and a red message
  - [x] Edit settings renamed Edit Python settings file; Alt+Z keeps its choice as the wrapping setting
  - [x] Single-line mode (Editing page, off by default): Enter runs the prompt and Alt+Enter starts a new line; off, Enter starts a new line and Ctrl+Enter runs
  - [x] Tab width (Editing page) and a Fonts page: family and size for the prompt box and the output box separately; zooming moves each box from its own size and Ctrl+0 returns to the sizes in the settings

Continuous integration and packaging.

- [x] GitHub Actions run the tests on Linux, macOS and Windows, all on Python 3.12
  - [x] mathdoer needs Python 3.12 because PySide6 6.12.0 on Linux loses a reference to None on every call to some protected Qt methods (`QSyntaxHighlighter.setFormat`, a resize, a key press), and before Python 3.12 that count is real, so the interpreter aborts after a few thousand calls. Measured on CI; macOS and Windows are clean
- [x] A first packaged program: `uv run pyinstaller packaging/mathdoer.spec` builds `dist/mathdoer/mathdoer.exe`, `uv run python packaging/check_build.py` checks it (files present, starts with its own empty configuration folder, keeps running), and CI does both on Windows
- [x] The packaged program carries python.org's embeddable Python 3.13 (Windows) and runs prompts on it by default; `check_build.py` runs a prompt on it with the packaged worker, startup file and registry
  - [ ] Other systems have no embeddable Python: a macOS or Linux package would need its own plan (python-build-standalone is the likely source)
  - [ ] The checksum was computed from the download over HTTPS; python.org's PGP signature was not checked (the key could not be fetched in a usable form)
- [x] Version 1.0.0, written in `pyproject.toml` only; the packaging scripts read it
- [x] Icon: a square in two rectangles, the top white with a black cursive "m", the bottom black with a white cursive "dm" (`packaging/make_icon.py` draws `src/mathdoer/interface/icon.ico`; the window wears it and the executable carries it)
- [x] Version information in `mathdoer.exe` (the Details tab of its properties)
- [x] The package is a zip, `dist/mathdoer-1.0.0-windows-x64.zip`, holding the folder `mathdoer-1.0.0` with the program, `LICENSE` and `README.md`; `check_build.py` unzips it and checks what is in it; a manual run of the package workflow keeps it as an artifact
  - [ ] The icon was drawn with Segoe Script, a font of Microsoft's. The font file is not in the repository or the package, only a picture of two groups of letters; I believe that is allowed but did not check Microsoft's license terms. A font with an open license (the SIL Open Font License, for example) would leave no question, and the script needs only a new `FONT_FAMILY`
  - [ ] Nothing is signed: Windows SmartScreen warns about an unknown program when the zip comes from the internet (see code signing below)

## Unscheduled

- [ ] Setting to control numeric behavior (plain Python numbers today; for example `Decimal` or `Fraction` literals, or higher precision)
  - [ ] With full precision on, constants and units use their full registry precision
  - [ ] Evaluate the irrational registry entries (Stefan-Boltzmann constant, parsec) from their formulas at any requested precision; the stored 100 digits are a floor, not the limit
  - [ ] Decide what Shift+click inserts for very long values (the two irrational entries have 100 digits)
- [ ] Make the separators between menu groups easier to see in the dark theme (they are almost invisible; Fusion draws them faintly)
- [ ] Find options: whole word and regular expressions (only Match case today; they would go on the Find page of the settings window)
- [ ] More settings, each needing approval first: the interpreter (it stays in the Python settings file for now)
- [ ] The tab width is one setting for every language (default 4); when a second language comes, decide whether each language keeps its own
- [ ] Auto-indent after an opening bracket (today only a colon adds a level)
- [ ] Make Enter quicker on very large prompts (it lexes every earlier line; 45 ms at 4,300 lines)
- [ ] Languages other than Python (the interface always stays Python)
- [ ] Reset the startup file to the bundled default
- [ ] Accept Notepad++ theme files; bundle Notepad++ themes (check the license of each theme first)
- [ ] `input()` opens a popup window with a text field (the worker protocol already has a closed standard input to extend)
- [ ] Finish the package: a smaller size (127 MB, 54 MB zipped; `opengl32sw.dll`, Qt6Network and Qt6Svg are probably unneeded), a macOS app bundle (needs an .icns icon) and a Linux build (PyInstaller sets `LD_LIBRARY_PATH` for child processes on Linux, which the worker must not inherit: restore `LD_LIBRARY_PATH_ORIG`), code signing
- [ ] Publish version 1.0.0: a GitHub release with the zip (a tag `v1.0.0`; not done, since a release is public)
- [ ] An About window or some other place that shows the version (the version is in the properties of `mathdoer.exe` only; a new interface feature, so it needs approval)
- [ ] Third box above the prompt box for definitions that persist between runs
- [ ] File menu and persistence of the prompt text
- [ ] History (not decided; leaning towards no persisted Python session between runs)
- [ ] macOS and Linux support, including opening the startup file in the system's `.txt` editor; the POSIX branches of cancelling a run have been written but never run, and with the find bar turned off Ctrl+H is left to Qt, which may delete a character on Linux and macOS (checked on Windows only)
