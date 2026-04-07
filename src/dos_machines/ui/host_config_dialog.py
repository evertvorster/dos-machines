from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from dos_machines.application.engine_registry import EngineRegistry
from dos_machines.application.preset_service import PresetService
from dos_machines.application.settings_service import SettingsService
from dos_machines.domain.models import EngineSchema, OptionState
from dos_machines.ui.create_machine_dialog import SectionEditorDialog


class HostConfigDialog(QDialog):
    def __init__(
        self,
        settings_service: SettingsService,
        engine_registry: EngineRegistry,
        preset_service: PresetService,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Configure Host")
        self.resize(760, 520)
        self._settings_service = settings_service
        self._engine_registry = engine_registry
        self._preset_service = preset_service
        self._schema: EngineSchema | None = None
        self._engine_id: str | None = None
        self._sdl_option_states: dict[str, OptionState] = {}

        settings = self._settings_service.load()
        self.engine_binary_edit = QLineEdit(
            str(settings.last_engine_binary_path)
            if settings.last_engine_binary_path is not None
            else ""
        )
        self.engine_binary_edit.editingFinished.connect(self._load_schema_if_possible)

        self._edit_sdl_button = QPushButton("Edit SDL Settings")
        self._edit_sdl_button.clicked.connect(self._edit_sdl_settings)
        self._status_label = QLabel()
        self._status_label.setWordWrap(True)
        self._summary = QTextEdit()
        self._summary.setReadOnly(True)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)

        form = QFormLayout()
        form.addRow(
            "Engine Binary",
            self._with_browse(self.engine_binary_edit, self._browse_engine_binary),
        )

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self._edit_sdl_button)
        layout.addWidget(self._status_label)
        layout.addWidget(QLabel("Current SDL engine defaults"))
        layout.addWidget(self._summary)
        layout.addWidget(buttons)

        self._load_schema_if_possible(silent=True)
        self._sync_ui()

    def _with_browse(self, line_edit: QLineEdit, callback) -> QHBoxLayout:
        button = QPushButton("Browse…")
        button.clicked.connect(callback)
        layout = QHBoxLayout()
        layout.addWidget(line_edit)
        layout.addWidget(button)
        return layout

    def _browse_engine_binary(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select DOSBox Binary", self.engine_binary_edit.text().strip()
        )
        if not path:
            return
        self.engine_binary_edit.setText(path)
        self._load_schema_if_possible()

    def _load_schema_if_possible(self, silent: bool = False) -> None:
        binary_path = Path(self.engine_binary_edit.text().strip()).expanduser()
        if not binary_path:
            self._schema = None
            self._engine_id = None
            self._sdl_option_states = {}
            self._sync_ui()
            return
        try:
            cache = self._engine_registry.register(binary_path)
            self._schema = self._engine_registry.load_schema(cache.ref.engine_id)
            self._engine_id = cache.ref.engine_id
            self._load_sdl_defaults()
            settings = self._settings_service.load()
            settings.last_engine_binary_path = binary_path
            self._settings_service.save(settings)
        except Exception as exc:
            self._schema = None
            self._engine_id = None
            self._sdl_option_states = {}
            if not silent:
                QMessageBox.critical(self, "Engine Load Failed", str(exc))
        self._sync_ui()

    def _load_sdl_defaults(self) -> None:
        assert self._schema is not None
        sdl_section = next(
            (section for section in self._schema.sections if section.name == "sdl"),
            None,
        )
        if sdl_section is None:
            self._sdl_option_states = {}
            return
        saved = (
            self._preset_service.load_section_default(self._engine_id, "sdl")
            if self._engine_id is not None
            else None
        )
        self._sdl_option_states = {
            option.name: OptionState(
                value=saved[option.name]
                if saved and option.name in saved
                else option.default_value,
                checked=saved is not None and option.name in saved,
                origin="default-preset"
                if saved is not None and option.name in saved
                else "default",
            )
            for option in sdl_section.options
        }

    def _sync_ui(self) -> None:
        has_schema = (
            self._schema is not None
            and self._engine_id is not None
            and bool(self._sdl_option_states)
        )
        self._edit_sdl_button.setEnabled(has_schema)
        if not self.engine_binary_edit.text().strip():
            self._status_label.setText(
                "Choose a DOSBox engine binary to configure SDL engine defaults."
            )
        elif not has_schema:
            self._status_label.setText(
                "Load a DOSBox engine schema before editing SDL engine defaults."
            )
        else:
            self._status_label.setText(
                "These SDL engine defaults are used when creating a new machine."
            )
        self._summary.setPlainText(self._summary_text())

    def _summary_text(self) -> str:
        if not self._sdl_option_states:
            return ""
        lines = []
        for option_name, state in self._sdl_option_states.items():
            if not state.checked:
                continue
            lines.append(f"{option_name} = {state.value}")
        return "\n".join(lines) if lines else "Using engine defaults for SDL."

    def _edit_sdl_settings(self) -> None:
        if self._schema is None or self._engine_id is None:
            return
        sdl_section = next(
            (section for section in self._schema.sections if section.name == "sdl"),
            None,
        )
        if sdl_section is None:
            QMessageBox.warning(
                self,
                "Section Missing",
                "The loaded engine schema does not define an SDL section.",
            )
            return
        dialog = SectionEditorDialog(
            sdl_section,
            self._sdl_option_states,
            self._preset_service,
            engine_id=self._engine_id,
            parent=self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self._sync_ui()

    def _save(self) -> None:
        if self._engine_id is None or self._schema is None:
            QMessageBox.warning(
                self,
                "Schema Not Loaded",
                "Load an engine schema before saving SDL engine defaults.",
            )
            return
        values = {
            option_name: state.value
            for option_name, state in self._sdl_option_states.items()
            if state.checked
        }
        self._preset_service.save_section_default(self._engine_id, "sdl", values)
        self.accept()
