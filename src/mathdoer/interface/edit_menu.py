"""The Edit menu."""
from collections.abc import Callable

from PySide6.QtGui import QAction, QGuiApplication
from PySide6.QtWidgets import QMenuBar, QPlainTextEdit

from mathdoer.interface.focus_tracker import ActiveBoxTracker


class EditMenu:
    """Undo, redo, cut and paste act on the prompt box, the only box that can be edited.
    Copy and select all act on the box the tracker says is active."""

    def __init__(
        self,
        menu_bar: QMenuBar,
        prompt_box: QPlainTextEdit,
        output_box: QPlainTextEdit,
        tracker: ActiveBoxTracker,
        open_settings_window: Callable[[], None],
        edit_startup_file: Callable[[], None],
        edit_language_settings_file: Callable[[], None],
        language_name: str,
    ):
        self._prompt_box = prompt_box
        self._output_box = output_box
        self._tracker = tracker

        self.menu = menu_bar.addMenu("Edit")
        self._undo = self._add("Undo", "Ctrl+Z", self._undo_in_prompt)
        self._redo = self._add("Redo", "Ctrl+Y", self._redo_in_prompt)
        self.menu.addSeparator()
        self._cut = self._add("Cut", "Ctrl+X", self._cut_from_prompt)
        self._copy = self._add("Copy", "Ctrl+C", self._copy_from_active_box)
        self._paste = self._add("Paste", "Ctrl+V", self._paste_into_prompt)
        self._select_all = self._add("Select all", "Ctrl+A", self._select_all_in_active_box)
        self.menu.addSeparator()
        self._copy_output = self._add("Copy output", None, self._copy_the_output)
        self.menu.addSeparator()
        self._add("Settings…", None, open_settings_window)
        self._add("Edit startup file", None, edit_startup_file)
        self._add(f"Edit {language_name} settings file", None, edit_language_settings_file)
        self.menu.aboutToShow.connect(self._update_enabled_states)

    def _add(self, text: str, shortcut_hint: str | None, handler: Callable[[], None]) -> QAction:
        # The hint after the tab is only shown. The text boxes handle these keys themselves,
        # and a real shortcut would also fire while the other box has the focus.
        action = QAction(f"{text}\t{shortcut_hint}" if shortcut_hint else text, self.menu)
        action.triggered.connect(lambda checked=False: handler())
        self.menu.addAction(action)
        return action

    def _update_enabled_states(self) -> None:
        active = self._tracker.active_box()
        document = self._prompt_box.document()
        self._undo.setEnabled(document.isUndoAvailable())
        self._redo.setEnabled(document.isRedoAvailable())
        self._cut.setEnabled(self._prompt_box.textCursor().hasSelection())
        self._copy.setEnabled(active.textCursor().hasSelection())
        self._paste.setEnabled(self._prompt_box.canPaste())
        self._select_all.setEnabled(not active.document().isEmpty())
        self._copy_output.setEnabled(bool(self._output_box.output_text()))

    def _undo_in_prompt(self) -> None:
        self._prompt_box.undo()
        self._prompt_box.setFocus()

    def _redo_in_prompt(self) -> None:
        self._prompt_box.redo()
        self._prompt_box.setFocus()

    def _cut_from_prompt(self) -> None:
        self._prompt_box.cut()
        self._prompt_box.setFocus()

    def _copy_from_active_box(self) -> None:
        box = self._tracker.active_box()
        box.copy()
        box.setFocus()

    def _paste_into_prompt(self) -> None:
        self._prompt_box.paste()
        self._prompt_box.setFocus()

    def _select_all_in_active_box(self) -> None:
        box = self._tracker.active_box()
        box.selectAll()
        box.setFocus()

    def _copy_the_output(self) -> None:
        QGuiApplication.clipboard().setText(self._output_box.output_text())
