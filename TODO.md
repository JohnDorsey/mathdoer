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
- [ ] Interface for running
  - [ ] Ctrl+Enter runs; Shift+Esc cancels a running prompt and marks the output as cancelled
  - [ ] The output box shows a truncation notice when the output buffer has discarded text
  - [ ] A spinner (`/ - \ |`) is shown in the output while running; after 5 seconds without a result it is followed by a counter of elapsed time: `00:05`, then `hh:mm:ss` from one hour, then `d:hh:mm:ss` from one day
  - [ ] Output is cleared when a new run starts; error text is shown in red
- [ ] Keep internals and names language-neutral (ongoing): everything specific to Python (startup file, literals, comment syntax, running the code) lives in a Python language module, so other languages can be added later; the interface stays Python
- [x] Startup file (Python's), created for the user from a bundled default
  - [x] `from math import *`, then `from builtins import pow` with a note explaining why (`math.pow` would otherwise turn `pow(2, 100)` into a float)
  - [x] Code that reads the registry and defines every constant and unit as a SCREAMING_SNAKE_CASE variable
  - [ ] Edit > Edit startup file opens it in the system's editor for `.txt` files
- [x] Registry of constants and units (TOML, language-neutral), the single source for the menus and the startup file
  - [x] Same items as preccalc; labels clarified where preccalc's are ambiguous; CODATA 2022 and exact definitions; names that carry their definition when the plain word is ambiguous
  - [x] Greatest correct precision: exact values as exact decimals or ratios; irrational values to 100 significant digits
- [ ] Menus: Edit, Constants, Units
  - [ ] Constants and Units: click inserts the name; Shift+click inserts the literal value (Alt+click was tried: Windows closes the menu when Alt is pressed)
  - [ ] Edit: Undo, Redo, Cut, Copy, Paste, Select all, Copy output, Edit startup file
- [ ] Prompt box (top, editable) and output box (bottom, read-only but selectable and copyable) with a draggable splitter; resizable window
- [ ] Dark, high-contrast theme
- [ ] Prompt box editing behaviors
  - [ ] Indentation guides
  - [ ] Tab inserts spaces; Shift+Tab dedents; Tab and Shift+Tab work on a selection
  - [ ] Auto-indent after a colon
  - [ ] Toggle comment (Ctrl+/)
  - [ ] Duplicate line (Ctrl+D)
  - [ ] Move line up and down (Alt+Up, Alt+Down)
  - [ ] Delete line (Ctrl+Shift+K)
  - [ ] Smart Home; Ctrl+Left/Right and Ctrl+Backspace/Delete by word
  - [ ] Undo and redo
  - [ ] Syntax highlighting; matching-bracket highlight
  - [ ] Line numbers
  - [ ] Find and replace as an inline bar (Ctrl+F, Ctrl+H, F3, Esc), prompt box only
  - [ ] Zoom
  - [ ] Monospace font; word wrap on, toggled with Alt+Z
  - [ ] No auto-closing brackets or quotes
- [x] GPL-3.0-or-later license
- [ ] Windows first, Python 3.11 or later

## Unscheduled

- [ ] Setting to control numeric behavior (plain Python numbers today; for example `Decimal` or `Fraction` literals, or higher precision)
  - [ ] With full precision on, constants and units use their full registry precision
  - [ ] Evaluate the irrational registry entries (Stefan-Boltzmann constant, parsec) from their formulas at any requested precision; the stored 100 digits are a floor, not the limit
  - [ ] Decide what Shift+click inserts for very long values (the two irrational entries have 100 digits)
- [ ] Languages other than Python (the interface always stays Python)
- [ ] Setting for a configurable interpreter that runs the prompt
- [ ] Reset the startup file to the bundled default
- [ ] Accept Notepad++ theme files; bundle Notepad++ themes (check the license of each theme first)
- [ ] `input()` opens a popup window with a text field (the worker protocol already has a closed standard input to extend)
- [ ] Package as an EXE (the interpreter that runs the prompt must be bundled or configured)
- [ ] Third box above the prompt box for definitions that persist between runs
- [ ] File menu and persistence of the prompt text
- [ ] History (not decided; leaning towards no persisted Python session between runs)
- [ ] macOS and Linux support, including opening the startup file in the system's `.txt` editor; the POSIX branches of cancelling a run have been written but never run
