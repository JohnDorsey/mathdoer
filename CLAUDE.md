# mathdoer

A desktop calculator that executes the Python code the user types. The interface is modeled on PrecCalc64 (https://preccalc.sourceforge.net/): an editable prompt box on top, a read-only output box below, Ctrl+Enter runs. The code editing experience should feel as good as a text editor (Notepad++ is the reference).

Reference install of PrecCalc64: `E:\data-game-win10pro2\lock\portable\preccalc64\`. Its `constants.cns` and `units.unt` list the contents of its Constants and Units menus.

## Rules

- Ask the user before adding any interface feature, and before adding any PrecCalc64 feature, that they have not approved. The interface stays small; few buttons.
- Prefer descriptive names to shortened ones. No abbreviations unless very common (ctrl). No acronyms unless very common (ui).
- Expect the project to grow. Avoid technical debt; keep code simple, maintainable and extensible.
- Keep this file under 10 KB and do not use it to explain how the code works; that is the job of the code and its documentation.
- `TODO.md` holds the plan: a scheduled section and an unscheduled section. Keep it current.

## Decisions not visible in the code

- Registry labels and names must be unambiguous and descriptive, even where PrecCalc64's are not. Registry values keep the greatest precision that is definitely correct and are never rounded to fit a number type (a future setting may give users full precision).
- Files that could be duplicated or confused across languages carry the language name, for example `startup_python.py`.
- User settings live in one TOML file per language (`settings_python.toml`), read before every run. A mistake in it is an error shown in the output box, never silently ignored (unknown settings are errors too).
- Every run is a clean slate in a separate process. No persisted Python session between runs.
- The first version has no file menu and does not persist the prompt text.
- Dark theme with high contrast; text is never dim.
- Licensed GPL-3.0-or-later; copyright John Dorsey.
- Other languages besides Python will come later, but the interface always stays Python. Keep everything outside a language's own module language-neutral, and keep Python-specific names out of neutral modules.
- Menu items insert a name on click and the literal value on Shift+click (Alt+click closes the menu on Windows).
- Windows first, Python 3.11 or later. macOS, Linux and an EXE package come later.

## Commands

- `uv run pytest` runs the tests.
- `uv run mathdoer` starts the program.
- Interface tests run on Qt's offscreen platform, which has no fonts and shows nothing. Check how the window really looks with a screenshot taken on the real platform.
