"""The main window: a prompt box above an output box."""
import time
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCloseEvent, QGuiApplication, QKeySequence, QShortcut
from PySide6.QtWidgets import QMainWindow, QSplitter

from mathdoer import text_editor
from mathdoer.interface.edit_menu import EditMenu
from mathdoer.interface.focus_tracker import ActiveBoxTracker
from mathdoer.interface.fonts import DEFAULT_POINT_SIZE, clamp_point_size
from mathdoer.interface.output_display import OutputDisplay
from mathdoer.interface.find_bar import FindBar
from mathdoer.interface.prompt_editor import PromptEditor
from mathdoer.interface.prompt_pane import PromptPane
from mathdoer.interface.registry_menus import add_registry_menus
from mathdoer.interface.styling import apply_menu_theme, window_palette
from mathdoer.interface.theme import DARK_THEME, Theme
from mathdoer.output_buffer import DEFAULT_MAXIMUM_CHARACTER_COUNT, OutputBuffer
from mathdoer.output_text import normalize_output_text
from mathdoer.progress import progress_text
from mathdoer.registry import Registry, RegistryEntry, load_registry
from mathdoer.running import OutputText, Run, RunFinished, RunOutcome, RunSettings
from mathdoer.user_files import create_file_if_missing

WINDOW_TITLE = "mathdoer"
INITIAL_WINDOW_SIZE = (900, 700)
INITIAL_SPLITTER_SIZES = (280, 420)
SPLITTER_HANDLE_WIDTH = 5
POLL_INTERVAL_MILLISECONDS = 30

RUN_SHORTCUTS = ("Ctrl+Return", "Ctrl+Enter")  # Enter on the keypad is Ctrl+Enter
CANCEL_SHORTCUT = "Shift+Esc"
ZOOM_IN_SHORTCUTS = ("Ctrl++", "Ctrl+=")  # the second needs no Shift on most keyboards
ZOOM_OUT_SHORTCUT = "Ctrl+-"
ZOOM_RESET_SHORTCUT = "Ctrl+0"
WORD_WRAP_SHORTCUT = "Alt+Z"
FIND_SHORTCUT = "Ctrl+F"
REPLACE_SHORTCUT = "Ctrl+H"
FIND_NEXT_SHORTCUT = "F3"
FIND_PREVIOUS_SHORTCUT = "Shift+F3"

CANCELLED_MARKER = "[cancelled]"


def crashed_marker(exit_code: int) -> str:
    return f"[the worker stopped unexpectedly (exit code {exit_code})]"


class MainWindow(QMainWindow):
    def __init__(
        self,
        run_settings: RunSettings,
        theme: Theme = DARK_THEME,
        maximum_output_characters: int = DEFAULT_MAXIMUM_CHARACTER_COUNT,
        clock: Callable[[], float] = time.monotonic,
        registry: Registry | None = None,
        keyboard_modifiers: Callable[[], Qt.KeyboardModifier] = QGuiApplication.keyboardModifiers,
        open_in_text_editor: Callable[[Path], None] = text_editor.open_in_text_editor,
        parent=None,
    ):
        super().__init__(parent)
        self._run_settings = run_settings
        self._clock = clock
        self._keyboard_modifiers = keyboard_modifiers
        self._open_in_text_editor = open_in_text_editor
        self._output_buffer = OutputBuffer(maximum_output_characters)
        self._run: Run | None = None
        self._run_started_at = 0.0
        self._shown_progress_text: str | None = None
        self._font_size = DEFAULT_POINT_SIZE

        self.setWindowTitle(WINDOW_TITLE)
        self.resize(*INITIAL_WINDOW_SIZE)
        self.setPalette(window_palette(theme))

        self.prompt_box = PromptEditor(theme, run_settings.language)
        self.prompt_pane = PromptPane(self.prompt_box, theme)
        self.output_box = OutputDisplay(theme)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(self.prompt_pane)
        splitter.addWidget(self.output_box)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(SPLITTER_HANDLE_WIDTH)
        splitter.setSizes(list(INITIAL_SPLITTER_SIZES))
        splitter.setStyleSheet(f"QSplitter::handle {{ background: {theme.splitter_handle}; }}")
        self.setCentralWidget(splitter)

        self._active_box = ActiveBoxTracker((self.prompt_box, self.output_box))
        self._edit_menu = EditMenu(
            self.menuBar(),
            self.prompt_box,
            self.output_box,
            self._active_box,
            self._edit_startup_file,
            self._edit_settings,
        )
        add_registry_menus(
            self.menuBar(),
            registry if registry is not None else load_registry(run_settings.registry_path),
            self._insert_registry_entry,
        )
        apply_menu_theme(self.menuBar(), theme)

        for sequence in RUN_SHORTCUTS:
            QShortcut(QKeySequence(sequence), self, activated=self.run_prompt)
        QShortcut(QKeySequence(CANCEL_SHORTCUT), self, activated=self.cancel_run)
        for sequence in ZOOM_IN_SHORTCUTS:
            QShortcut(QKeySequence(sequence), self, activated=lambda: self.zoom_by(1))
        QShortcut(QKeySequence(ZOOM_OUT_SHORTCUT), self, activated=lambda: self.zoom_by(-1))
        QShortcut(QKeySequence(ZOOM_RESET_SHORTCUT), self, activated=lambda: self.set_font_size(DEFAULT_POINT_SIZE))
        QShortcut(QKeySequence(WORD_WRAP_SHORTCUT), self, activated=self.toggle_word_wrap)
        QShortcut(QKeySequence(FIND_SHORTCUT), self, activated=self.find_bar.show_find)
        QShortcut(QKeySequence(REPLACE_SHORTCUT), self, activated=self.find_bar.show_replace)
        QShortcut(QKeySequence(FIND_NEXT_SHORTCUT), self, activated=lambda: self.find_bar.step_from_shortcut(True))
        QShortcut(
            QKeySequence(FIND_PREVIOUS_SHORTCUT), self, activated=lambda: self.find_bar.step_from_shortcut(False)
        )
        for box in (self.prompt_box, self.output_box):
            box.zoom_requested.connect(self.zoom_by)

        self._timer = QTimer(self)
        self._timer.setInterval(POLL_INTERVAL_MILLISECONDS)
        self._timer.timeout.connect(self.poll_run)

        self.prompt_box.setFocus()

    @property
    def current_run(self) -> Run | None:
        return self._run

    @property
    def is_running(self) -> bool:
        return self._run is not None

    @property
    def startup_path(self) -> Path:
        return self._run_settings.startup_path

    @property
    def settings_path(self) -> Path:
        return self._run_settings.settings_path

    @property
    def find_bar(self) -> FindBar:
        return self.prompt_pane.find_bar

    @property
    def font_size(self) -> int:
        return self._font_size

    def set_font_size(self, point_size: int) -> None:
        """Both boxes always have the same font size."""
        self._font_size = clamp_point_size(point_size)
        for box in (self.prompt_box, self.output_box):
            box.set_font_size(self._font_size)

    def zoom_by(self, steps: int) -> None:
        self.set_font_size(self._font_size + steps)

    def toggle_word_wrap(self) -> None:
        """Turn word wrap on or off in the box that has the focus."""
        self._active_box.active_box().toggle_word_wrap()

    def _insert_registry_entry(self, entry: RegistryEntry) -> None:
        """Insert the entry's name, or its literal value when Shift is held."""
        language = self._run_settings.language
        shift_held = bool(self._keyboard_modifiers() & Qt.KeyboardModifier.ShiftModifier)
        text = language.format_literal(entry) if shift_held else language.format_name(entry)
        self.prompt_box.insertPlainText(text)
        self.prompt_box.setFocus()

    def _edit_startup_file(self) -> None:
        self._open_user_file(
            "startup file", self._run_settings.language.default_startup_path, self._run_settings.startup_path
        )

    def _edit_settings(self) -> None:
        self._open_user_file(
            "settings file", self._run_settings.language.default_settings_path, self._run_settings.settings_path
        )

    def _open_user_file(self, description: str, default_path: Path, path: Path) -> None:
        """Open the file in the text editor, first recreating it from the default if it is missing."""
        try:
            self._open_in_text_editor(create_file_if_missing(default_path, path))
        except OSError as error:
            self._show_status(f"[could not open the {description}: {error}]")

    def _show_status(self, message: str) -> None:
        self.output_box.append_marker(message)
        self._shown_progress_text = None  # the progress line was replaced; show it again

    def run_prompt(self) -> None:
        if self.is_running:
            return
        self._output_buffer.clear()
        self.output_box.clear_output()
        self._run_started_at = self._clock()
        self._run = self._run_settings.start(self.prompt_box.toPlainText())
        self._shown_progress_text = progress_text(0.0)
        self.output_box.apply_changes(progress_text=self._shown_progress_text)
        self._timer.start()

    def cancel_run(self) -> None:
        if self._run is not None:
            self._run.cancel()

    def poll_run(self) -> None:
        """Bring the output box up to date with the run. Called by a timer."""
        if self._run is None:
            return
        segments = []
        discarded_pieces = []
        finished = None
        for event in self._run.poll():
            if isinstance(event, OutputText):
                text = normalize_output_text(event.text)
                discarded_pieces.append(self._output_buffer.append(text, event.is_error))
                segments.append((text, event.is_error))
            elif isinstance(event, RunFinished):
                finished = event

        if finished is not None:
            self.output_box.apply_changes(
                segments, "".join(discarded_pieces), self._output_buffer.discarded_character_count
            )
            self._finish_run(finished)
            return

        progress = progress_text(self._clock() - self._run_started_at)
        if segments or progress != self._shown_progress_text:
            self._shown_progress_text = progress
            self.output_box.apply_changes(
                segments, "".join(discarded_pieces), self._output_buffer.discarded_character_count, progress
            )

    def _finish_run(self, finished: RunFinished) -> None:
        self._timer.stop()
        self._run = None
        self._shown_progress_text = None
        if finished.outcome is RunOutcome.CANCELLED:
            self.output_box.append_marker(CANCELLED_MARKER)
        elif finished.outcome is RunOutcome.CRASHED and finished.exit_code is not None:
            self.output_box.append_marker(crashed_marker(finished.exit_code))

    def closeEvent(self, event: QCloseEvent) -> None:
        self.cancel_run()
        self._timer.stop()
        super().closeEvent(event)
