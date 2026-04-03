from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from dos_machines.application.engine_registry import EngineRegistry
from dos_machines.application.preset_service import GRAPHICS_SECTIONS, PresetService
from dos_machines.application.profile_service import CreateProfileRequest
from dos_machines.domain.models import EngineSchema, OptionState, SchemaOption


class CreateMachineDialog(QDialog):
    def __init__(
        self,
        workspace_dir: Path,
        engine_registry: EngineRegistry,
        preset_service: PresetService,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add New Machine")
        self.resize(860, 720)
        self._workspace_dir = workspace_dir
        self._engine_registry = engine_registry
        self._preset_service = preset_service
        self._schema: EngineSchema | None = None
        self._current_index = 0
        self._ordered_options: list[tuple[str, SchemaOption]] = []
        self._option_states: dict[str, dict[str, OptionState]] = {}
        self._value_widget: QWidget | None = None

        self.title_edit = QLineEdit()
        self.game_dir_edit = QLineEdit()
        self.executable_edit = QLineEdit()
        self.engine_binary_edit = QLineEdit("/usr/bin/dosbox")

        self._load_engine_button = QPushButton("Load Engine Schema")
        self._load_engine_button.clicked.connect(self._load_schema)

        self._section_label = QLabel("No engine loaded")
        self._option_label = QLabel("Choose a DOSBox binary to begin")
        self._help_text = QTextEdit()
        self._help_text.setReadOnly(True)
        self._explicit_check = QCheckBox("Mark this option as set")
        self._explicit_check.toggled.connect(self._explicit_toggled)
        self._previous_button = QPushButton("Previous")
        self._previous_button.clicked.connect(self._go_previous)
        self._next_button = QPushButton("Next")
        self._next_button.clicked.connect(self._go_next)
        self._save_preset_button = QPushButton("Save Graphics Preset")
        self._save_preset_button.clicked.connect(self._save_graphics_preset)
        self._apply_preset_button = QPushButton("Apply Graphics Preset")
        self._apply_preset_button.clicked.connect(self._apply_graphics_preset)

        metadata_form = QFormLayout()
        metadata_form.addRow("Title", self.title_edit)
        metadata_form.addRow("Game Directory", self._with_browse(self.game_dir_edit, self._browse_game_dir))
        metadata_form.addRow("Executable", self._with_browse(self.executable_edit, self._browse_executable))
        metadata_form.addRow("Engine Binary", self._with_browse(self.engine_binary_edit, self._browse_engine_binary))
        metadata_form.addRow("", self._load_engine_button)

        option_box = QGroupBox("Guided Config Editor")
        self._option_layout = QVBoxLayout()
        self._option_layout.addWidget(self._section_label)
        self._option_layout.addWidget(self._option_label)
        self._editor_host = QVBoxLayout()
        self._option_layout.addLayout(self._editor_host)
        self._option_layout.addWidget(self._explicit_check)
        self._option_layout.addWidget(self._help_text)
        nav_row = QHBoxLayout()
        nav_row.addWidget(self._previous_button)
        nav_row.addWidget(self._next_button)
        nav_row.addStretch(1)
        nav_row.addWidget(self._apply_preset_button)
        nav_row.addWidget(self._save_preset_button)
        self._option_layout.addLayout(nav_row)
        option_box.setLayout(self._option_layout)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._validate_before_accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(metadata_form)
        layout.addWidget(option_box)
        layout.addWidget(buttons)
        self.setLayout(layout)
        self._refresh_navigation()

    def build_request(self) -> CreateProfileRequest:
        return CreateProfileRequest(
            title=self.title_edit.text().strip(),
            game_dir=Path(self.game_dir_edit.text().strip()).expanduser(),
            executable=self.executable_edit.text().strip(),
            engine_binary=Path(self.engine_binary_edit.text().strip()).expanduser(),
            workspace_dir=self._workspace_dir,
            option_states=self._option_states,
        )

    def _with_browse(self, line_edit: QLineEdit, callback) -> QHBoxLayout:
        button = QPushButton("Browse…")
        button.clicked.connect(callback)
        layout = QHBoxLayout()
        layout.addWidget(line_edit)
        layout.addWidget(button)
        return layout

    def _browse_game_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select Game Directory")
        if path:
            self.game_dir_edit.setText(path)

    def _browse_engine_binary(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select DOSBox Binary")
        if path:
            self.engine_binary_edit.setText(path)

    def _browse_executable(self) -> None:
        start_dir = self.game_dir_edit.text().strip() or str(Path.home())
        path, _ = QFileDialog.getOpenFileName(self, "Select Game Executable", start_dir)
        if path:
            selected = Path(path)
            game_dir = self.game_dir_edit.text().strip()
            if game_dir:
                try:
                    relative = selected.relative_to(Path(game_dir))
                    self.executable_edit.setText(str(relative).replace("/", "\\"))
                    return
                except ValueError:
                    pass
            self.executable_edit.setText(selected.name)

    def _load_schema(self) -> None:
        binary_path = Path(self.engine_binary_edit.text().strip()).expanduser()
        if not binary_path:
            QMessageBox.warning(self, "Missing Binary", "Choose a DOSBox binary first.")
            return
        try:
            cache = self._engine_registry.register(binary_path)
            self._schema = self._engine_registry.load_schema(cache.ref.engine_id)
        except Exception as exc:
            QMessageBox.critical(self, "Engine Load Failed", str(exc))
            return

        self._option_states = {
            section.name: {
                option.name: OptionState(value=option.default_value, checked=False, origin="default")
                for option in section.options
            }
            for section in self._schema.sections
            if section.name != "autoexec"
        }
        self._ordered_options = [
            (section.name, option)
            for section in self._schema.sections
            if section.name != "autoexec"
            for option in section.options
        ]
        self._current_index = 0
        self._show_current_option()

    def _show_current_option(self) -> None:
        if not self._ordered_options:
            self._section_label.setText("No schema options loaded")
            self._option_label.setText("Choose a DOSBox binary to begin")
            self._help_text.clear()
            self._clear_editor_host()
            self._refresh_navigation()
            return

        section_name, option = self._ordered_options[self._current_index]
        state = self._option_states[section_name][option.name]
        self._section_label.setText(f"[{section_name}]")
        self._option_label.setText(option.name)
        self._option_label.setToolTip(option.help_text)
        self._help_text.setPlainText(option.help_text)
        self._explicit_check.blockSignals(True)
        self._explicit_check.setChecked(state.checked)
        self._explicit_check.blockSignals(False)

        self._clear_editor_host()
        widget = self._build_editor(option, state)
        self._value_widget = widget
        self._editor_host.addWidget(widget)
        self._refresh_navigation()

    def _build_editor(self, option: SchemaOption, state: OptionState) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        description = QLabel(option.description)
        description.setWordWrap(True)
        layout.addWidget(description)

        if option.value_type == "boolean":
            editor = QComboBox()
            editor.addItems(["true", "false"])
            editor.setCurrentText(state.value.lower())
            editor.currentTextChanged.connect(self._value_changed)
        elif option.value_type in {"enum", "dynamic"}:
            editor = QComboBox()
            editor.addItems(option.choices or [state.value])
            editor.setEditable(option.value_type == "dynamic")
            if state.value not in option.choices:
                editor.addItem(state.value)
            editor.setCurrentText(state.value)
            editor.currentTextChanged.connect(self._value_changed)
        else:
            editor = QLineEdit(state.value)
            editor.textChanged.connect(self._value_changed)
        editor.setToolTip(option.help_text)
        layout.addWidget(editor)

        if option.choices:
            choices_label = QLabel("Options: " + ", ".join(option.choices))
            choices_label.setWordWrap(True)
            layout.addWidget(choices_label)

        return container

    def _clear_editor_host(self) -> None:
        while self._editor_host.count():
            item = self._editor_host.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _current_state(self) -> OptionState:
        section_name, option = self._ordered_options[self._current_index]
        return self._option_states[section_name][option.name]

    def _current_option(self) -> tuple[str, SchemaOption]:
        return self._ordered_options[self._current_index]

    def _value_changed(self, value: str) -> None:
        state = self._current_state()
        state.value = value

    def _explicit_toggled(self, checked: bool) -> None:
        state = self._current_state()
        state.checked = checked
        state.origin = "user" if checked else "default"
        self._refresh_navigation()

    def _go_previous(self) -> None:
        if self._current_index == 0:
            return
        self._current_index -= 1
        self._show_current_option()

    def _go_next(self) -> None:
        if not self._ordered_options:
            return
        if not self._current_state().checked:
            QMessageBox.information(self, "Option Not Marked", "Check the option before moving on.")
            return
        if self._current_index >= len(self._ordered_options) - 1:
            return
        self._current_index += 1
        self._show_current_option()

    def _refresh_navigation(self) -> None:
        has_options = bool(self._ordered_options)
        self._previous_button.setEnabled(has_options and self._current_index > 0)
        self._next_button.setEnabled(has_options and self._current_state().checked if has_options else False)
        self._save_preset_button.setEnabled(has_options)
        self._apply_preset_button.setEnabled(has_options)

    def _save_graphics_preset(self) -> None:
        if not self._option_states:
            return
        title, accepted = QInputDialog.getText(self, "Save Graphics Preset", "Preset name")
        if not accepted or not title.strip():
            return
        values = {
            section: {
                name: state.value
                for name, state in options.items()
                if state.checked
            }
            for section, options in self._option_states.items()
            if section in GRAPHICS_SECTIONS
        }
        self._preset_service.save_graphics_preset(title.strip(), values)
        QMessageBox.information(self, "Preset Saved", f"Saved graphics preset '{title.strip()}'.")

    def _apply_graphics_preset(self) -> None:
        presets = self._preset_service.load_graphics_presets()
        if not presets:
            QMessageBox.information(self, "No Presets", "No graphics presets have been saved yet.")
            return
        titles = [preset.title for preset in presets]
        title, accepted = QInputDialog.getItem(self, "Apply Graphics Preset", "Preset", titles, 0, False)
        if not accepted or not title:
            return
        preset = next(preset for preset in presets if preset.title == title)
        for section, options in preset.sections.items():
            for name, value in options.items():
                if section not in self._option_states or name not in self._option_states[section]:
                    continue
                state = self._option_states[section][name]
                state.value = value
                state.checked = True
                state.origin = "preset"
        self._show_current_option()

    def _validate_before_accept(self) -> None:
        if not self.title_edit.text().strip() or not self.game_dir_edit.text().strip():
            QMessageBox.warning(self, "Missing Fields", "Title and game directory are required.")
            return
        if self._schema is None or not self._ordered_options:
            QMessageBox.warning(self, "Schema Not Loaded", "Load the engine schema before creating a machine.")
            return
        unchecked = [
            f"{section}.{option.name}"
            for section, option in self._ordered_options
            if not self._option_states[section][option.name].checked
        ]
        if unchecked:
            QMessageBox.warning(
                self,
                "Incomplete Config",
                f"Review and mark all options before finishing.\nFirst remaining: {unchecked[0]}",
            )
            return
        self.accept()
