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
- [ ] Prompt box editing behaviors
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
  - [ ] Find and replace as an inline bar (Ctrl+F, Ctrl+H, F3, Esc), prompt box only
  - [x] Zoom (Ctrl with +, - and 0, and Ctrl with the mouse wheel; both boxes together)
  - [x] Monospace font; word wrap on, toggled with Alt+Z in the box that has the focus
  - [x] No auto-closing brackets or quotes
- [x] GPL-3.0-or-later license
- [ ] Windows first, Python 3.11 or later

## Unscheduled

- [ ] Setting to control numeric behavior (plain Python numbers today; for example `Decimal` or `Fraction` literals, or higher precision)
  - [ ] With full precision on, constants and units use their full registry precision
  - [ ] Evaluate the irrational registry entries (Stefan-Boltzmann constant, parsec) from their formulas at any requested precision; the stored 100 digits are a floor, not the limit
  - [ ] Decide what Shift+click inserts for very long values (the two irrational entries have 100 digits)
- [ ] Make the separators between menu groups easier to see in the dark theme (they are almost invisible; Fusion draws them faintly)
- [ ] Auto-indent after an opening bracket (today only a colon adds a level)
- [ ] Make Enter quicker on very large prompts (it lexes every earlier line; 45 ms at 4,300 lines)
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
