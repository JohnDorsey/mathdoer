"""The settings window: the pages listed down the left, as in the preferences of Notepad++,
and the settings of the chosen page on the right.

A change takes effect as soon as it is made; the window announces the new settings and
whoever owns them applies and saves them. There is nothing to confirm, only Close.
"""
from collections.abc import Callable
from dataclasses import replace

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from mathdoer.interface.styling import window_palette
from mathdoer.interface.theme import Theme
from mathdoer.interface_settings import (
    DEFAULT_INTERFACE_SETTINGS,
    SETTING_DESCRIPTIONS,
    SETTINGS_PAGES,
    WINDOW_PAGE,
    InterfaceSettings,
    SettingDescription,
    SettingsPage,
    descriptions_on_page,
)

INITIAL_SIZE = (680, 440)
PAGE_LIST_WIDTH = 170
PAGE_MARGIN = 14
ROW_SPACING = 8


class SettingsWindow(QDialog):
    """Shows an InterfaceSettings and lets the user change any of it.

    The window does not close when a setting changes and does not block the main window.
    set_settings shows settings that were changed elsewhere, without announcing them.
    """

    settings_changed = Signal(object)  # the new InterfaceSettings, after the user changed one

    def __init__(
        self,
        settings: InterfaceSettings,
        theme: Theme,
        current_window_size: Callable[[], tuple[int, int]],
        parent=None,
    ):
        """current_window_size gives the width and height of the main window, for the Use
        current size button."""
        super().__init__(parent)
        self._settings = settings
        self._current_window_size = current_window_size
        self._checkboxes: dict[str, QCheckBox] = {}
        self._spin_boxes: dict[str, QSpinBox] = {}
        self._number_labels: dict[str, QLabel] = {}
        self._requirements = {d.name: d.requires for d in SETTING_DESCRIPTIONS if d.requires is not None}

        self.setWindowTitle("Settings")
        self.resize(*INITIAL_SIZE)
        self.setPalette(window_palette(theme))

        self.page_list = QListWidget()
        self.page_list.setFixedWidth(PAGE_LIST_WIDTH)
        self.page_list.setStyleSheet(
            f"QListWidget {{ background: {theme.panel_background}; border: 1px solid {theme.control_border}; outline: 0; }}"
            "QListWidget::item { padding: 6px 10px; }"
            f"QListWidget::item:selected {{ background: {theme.selection_background}; color: {theme.selection_text}; }}"
        )
        self._pages = QStackedWidget()
        for page in SETTINGS_PAGES:
            self.page_list.addItem(page.title)
            self._pages.addWidget(self._build_page(page))

        self.restore_defaults_button = QPushButton("Restore defaults")
        self.close_button = QPushButton("Close")
        for button in (self.restore_defaults_button, self.close_button):
            button.setAutoDefault(False)
        buttons = QHBoxLayout()
        buttons.addWidget(self.restore_defaults_button)
        buttons.addStretch(1)
        buttons.addWidget(self.close_button)

        body = QHBoxLayout()
        body.addWidget(self.page_list)
        body.addWidget(self._pages, 1)
        layout = QVBoxLayout(self)
        layout.addLayout(body, 1)
        layout.addLayout(buttons)

        self.page_list.currentRowChanged.connect(self._pages.setCurrentIndex)
        self.restore_defaults_button.clicked.connect(self._restore_defaults)
        self.close_button.clicked.connect(self.close)
        self.page_list.setCurrentRow(0)
        self.set_settings(settings)

    # ---------------------------------------------------------------------- the pages

    def page_titles(self) -> list[str]:
        return [self.page_list.item(row).text() for row in range(self.page_list.count())]

    @property
    def current_page_title(self) -> str:
        return self.page_list.currentItem().text()

    def show_page(self, title: str) -> None:
        self.page_list.setCurrentRow(self.page_titles().index(title))

    def _build_page(self, page: SettingsPage) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(PAGE_MARGIN, PAGE_MARGIN, PAGE_MARGIN, PAGE_MARGIN)
        layout.setSpacing(ROW_SPACING)
        if page.note:
            note = QLabel(page.note)
            note.setWordWrap(True)
            layout.addWidget(note)

        numbers = QFormLayout()
        for description in descriptions_on_page(page):
            if description.value_type is bool:
                layout.addWidget(self._build_checkbox(description))
            else:
                self._add_number_row(numbers, description)
        if numbers.rowCount():
            layout.addLayout(numbers)
        if page is WINDOW_PAGE:
            self.use_current_size_button = QPushButton("Use current size")
            self.use_current_size_button.setAutoDefault(False)
            self.use_current_size_button.clicked.connect(self._use_current_size)
            row = QHBoxLayout()
            row.addWidget(self.use_current_size_button)
            row.addStretch(1)
            layout.addLayout(row)
        layout.addStretch(1)
        return widget

    def _build_checkbox(self, description: SettingDescription) -> QCheckBox:
        checkbox = QCheckBox(description.label)
        checkbox.toggled.connect(self._widgets_changed)
        self._checkboxes[description.name] = checkbox
        return checkbox

    def _add_number_row(self, form: QFormLayout, description: SettingDescription) -> None:
        spin_box = QSpinBox()
        spin_box.setRange(description.minimum, description.maximum)
        spin_box.setKeyboardTracking(False)  # a number counts once it is finished, not at each digit
        spin_box.valueChanged.connect(self._widgets_changed)
        label = QLabel(description.label)
        form.addRow(label, spin_box)
        self._spin_boxes[description.name] = spin_box
        self._number_labels[description.name] = label

    # -------------------------------------------------------------------------- widgets

    def checkbox_for(self, name: str) -> QCheckBox:
        return self._checkboxes[name]

    def spin_box_for(self, name: str) -> QSpinBox:
        return self._spin_boxes[name]

    def label_for(self, name: str) -> str:
        """The text beside the box of a number setting."""
        return self._number_labels[name].text()

    # ------------------------------------------------------------------------- settings

    @property
    def settings(self) -> InterfaceSettings:
        return self._settings

    def set_settings(self, settings: InterfaceSettings) -> None:
        """Show these settings. Nothing is announced: they are not a change made here."""
        self._settings = settings
        for name, checkbox in self._checkboxes.items():
            self._show_value(checkbox, checkbox.setChecked, getattr(settings, name))
        for name, spin_box in self._spin_boxes.items():
            self._show_value(spin_box, spin_box.setValue, getattr(settings, name))
        self._update_requirements()

    @staticmethod
    def _show_value(widget: QWidget, show: Callable, value) -> None:
        blocked = widget.blockSignals(True)
        show(value)
        widget.blockSignals(blocked)

    def _update_requirements(self) -> None:
        """A setting that requires another is greyed while that one is off. It keeps its value."""
        for name, required in self._requirements.items():
            self._checkboxes[name].setEnabled(getattr(self._settings, required))

    def _widgets_changed(self) -> None:
        values = {name: checkbox.isChecked() for name, checkbox in self._checkboxes.items()}
        values.update({name: spin_box.value() for name, spin_box in self._spin_boxes.items()})
        settings = replace(self._settings, **values)
        if settings == self._settings:
            return
        self._settings = settings
        self._update_requirements()
        self.settings_changed.emit(settings)

    def _restore_defaults(self) -> None:
        """Announced even when the settings already are the defaults: it is also how a settings
        file that could not be read gets replaced."""
        self.set_settings(DEFAULT_INTERFACE_SETTINGS)
        self.settings_changed.emit(DEFAULT_INTERFACE_SETTINGS)

    def _use_current_size(self) -> None:
        width, height = self._current_window_size()
        for name, value in (("window_width", width), ("window_height", height)):
            self._show_value(self._spin_boxes[name], self._spin_boxes[name].setValue, value)  # clamped by its limits
        self._widgets_changed()
