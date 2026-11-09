"""The main window: a prompt box above an output box."""
import time
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCloseEvent, QGuiApplication, QKeySequence, QShortcut
from PySide6.QtWidgets import QMainWindow, QPlainTextEdit, QSplitter

from mathdoer import text_editor
from mathdoer.interface.edit_menu import EditMenu
from mathdoer.interface.fonts import monospace_font
from mathdoer.interface.output_display import OutputDisplay
from mathdoer.interface.registry_menus import add_registry_menus
from mathdoer.interface.styling import apply_menu_theme, text_box_palette, window_palette
from mathdoer.interface.theme import DARK_THEME, Theme
from mathdoer.output_buffer import DEFAULT_MAXIMUM_CHARACTER_COUNT, OutputBuffer
from mathdoer.output_text import normalize_output_text
from mathdoer.progress import progress_text
from mathdoer.registry import Registry, RegistryEntry, load_registry
from mathdoer.running import OutputText, Run, RunFinished, RunOutcome, RunSettings
from mathdoer.startup_files import create_startup_file_if_missing

WINDOW_TITLE = "mathdoer"
INITIAL_WINDOW_SIZE = (900, 700)
INITIAL_SPLITTER_SIZES = (280, 420)
SPLITTER_HANDLE_WIDTH = 5
POLL_INTERVAL_MILLISECONDS = 30

RUN_SHORTCUTS = ("Ctrl+Return", "Ctrl+Enter")  # Enter on the keypad is Ctrl+Enter
CANCEL_SHORTCUT = "Shift+Esc"

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

        self.setWindowTitle(WINDOW_TITLE)
        self.resize(*INITIAL_WINDOW_SIZE)
        self.setPalette(window_palette(theme))

        self.prompt_box = QPlainTextEdit()
        self.prompt_box.setFont(monospace_font())
        self.prompt_box.setPalette(text_box_palette(self.prompt_box.palette(), theme))
        self.prompt_box.setFrameShape(QPlainTextEdit.Shape.NoFrame)
        self.output_box = OutputDisplay(theme)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(self.prompt_box)
        splitter.addWidget(self.output_box)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(SPLITTER_HANDLE_WIDTH)
        splitter.setSizes(list(INITIAL_SPLITTER_SIZES))
        splitter.setStyleSheet(f"QSplitter::handle {{ background: {theme.splitter_handle}; }}")
        self.setCentralWidget(splitter)

        self._edit_menu = EditMenu(
            self.menuBar(), self.prompt_box, self.output_box, self._edit_startup_file
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

    def _insert_registry_entry(self, entry: RegistryEntry) -> None:
        """Insert the entry's name, or its literal value when Shift is held."""
        language = self._run_settings.language
        shift_held = bool(self._keyboard_modifiers() & Qt.KeyboardModifier.ShiftModifier)
        text = language.format_literal(entry) if shift_held else language.format_name(entry)
        self.prompt_box.insertPlainText(text)
        self.prompt_box.setFocus()

    def _edit_startup_file(self) -> None:
        try:
            path = create_startup_file_if_missing(
                self._run_settings.language, self._run_settings.startup_path
            )
            self._open_in_text_editor(path)
        except OSError as error:
            self._show_status(f"[could not open the startup file: {error}]")

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
