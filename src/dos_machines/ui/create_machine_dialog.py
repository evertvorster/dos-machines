from __future__ import annotations

from html import escape
from pathlib import Path

from PySide6.QtCore import QPoint, QRect, QSize, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLayout,
    QLayoutItem,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from dos_machines.application.config_renderer import ConfigRenderer
from dos_machines.application.engine_registry import EngineRegistry
from dos_machines.application.import_service import ImportAnalysis, ImportIssue, ImportService
from dos_machines.application.preset_service import PresetService
from dos_machines.application.profile_service import CreateProfileRequest
from dos_machines.domain.models import EngineSchema, MachineProfile, OptionState, SchemaOption, SchemaSection


class NoWheelMixin:
    def wheelEvent(self, event) -> None:
        if self.hasFocus():
            super().wheelEvent(event)
            return
        event.ignore()


class NoWheelComboBox(NoWheelMixin, QComboBox):
    pass


class NoWheelSpinBox(NoWheelMixin, QSpinBox):
    pass


class NoWheelDoubleSpinBox(NoWheelMixin, QDoubleSpinBox):
    pass


class FlowLayout(QLayout):
    def __init__(self, parent=None, margin: int = 0, hspacing: int = 12, vspacing: int = 12) -> None:
        super().__init__(parent)
        self._items: list[QLayoutItem] = []
        self._hspacing = hspacing
        self._vspacing = vspacing
        self.setContentsMargins(margin, margin, margin, margin)

    def addItem(self, item) -> None:
        self._items.append(item)

    def addWidget(self, widget) -> None:
        super().addWidget(widget)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index: int):
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index: int):
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return self._do_layout(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect: QRect) -> None:
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self) -> QSize:
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size

    def _do_layout(self, rect: QRect, test_only: bool) -> int:
        margins = self.contentsMargins()
        effective = rect.adjusted(
            +margins.left(),
            +margins.top(),
            -margins.right(),
            -margins.bottom(),
        )
        x = effective.x()
        y = effective.y()
        line_height = 0
        max_right = effective.right()

        for item in self._items:
            size = item.sizeHint()
            next_x = x + size.width() + self._hspacing
            if line_height > 0 and next_x - self._hspacing > max_right:
                x = effective.x()
                y += line_height + self._vspacing
                next_x = x + size.width() + self._hspacing
                line_height = 0

            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), size))

            x = next_x
            line_height = max(line_height, size.height())

        return y + line_height - rect.y() + margins.bottom()


class SectionEditorDialog(QDialog):
    def __init__(
        self,
        section: SchemaSection,
        option_states: dict[str, OptionState],
        preset_service: PresetService,
        issues: list[ImportIssue] | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Section: {section.name}")
        self.resize(760, 720)
        self._section = section
        self._option_states = option_states
        self._preset_service = preset_service
        self._issues = issues or []
        self._field_widgets: dict[str, QWidget] = {}

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._scroll.setWidget(self._content)

        toolbar = QHBoxLayout()
        self._apply_preset_button = QPushButton("Apply Section Preset")
        self._apply_preset_button.clicked.connect(self._apply_section_preset)
        self._save_preset_button = QPushButton("Save Section Preset")
        self._save_preset_button.clicked.connect(self._save_section_preset)
        toolbar.addWidget(self._apply_preset_button)
        toolbar.addWidget(self._save_preset_button)
        toolbar.addStretch(1)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(toolbar)
        layout.addWidget(self._scroll)
        layout.addWidget(buttons)
        self.setLayout(layout)

        self._rebuild_cards()

    def _rebuild_cards(self) -> None:
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._field_widgets.clear()

        section_only_issues = [issue for issue in self._issues if issue.option_name is None]
        if section_only_issues:
            warning = QLabel("\n".join(issue.message for issue in section_only_issues))
            warning.setWordWrap(True)
            warning.setStyleSheet("color: #a16207;")
            self._content_layout.addWidget(warning)

        for option in self._section.options:
            self._content_layout.addWidget(self._build_option_card(option))
        self._content_layout.addStretch(1)

    def _build_option_card(self, option: SchemaOption) -> QWidget:
        state = self._option_states[option.name]
        box = QGroupBox(option.name)
        layout = QVBoxLayout(box)

        option_issues = [issue for issue in self._issues if issue.option_name == option.name]
        if option_issues:
            warning = QLabel("\n".join(issue.message for issue in option_issues))
            warning.setWordWrap(True)
            warning.setStyleSheet("color: #a16207;")
            layout.addWidget(warning)

        editor = self._build_editor(option, state, option_issues)
        self._field_widgets[option.name] = editor
        layout.addWidget(editor)

        if option.help_text:
            help_label = QLabel(option.help_text)
            help_label.setWordWrap(True)
            help_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            help_label.setTextFormat(Qt.TextFormat.RichText)
            help_label.setText(self._format_help_text(option.help_text))
            layout.addWidget(help_label)

        return box

    def _build_editor(self, option: SchemaOption, state: OptionState, option_issues: list[ImportIssue]) -> QWidget:
        has_invalid_issue = bool(option_issues)
        if option.value_type == "boolean":
            editor = NoWheelComboBox()
            editor.addItems(["true", "false"])
            current_value = state.value.lower() if not has_invalid_issue else option.default_value.lower()
            editor.setCurrentText(current_value)
            editor.currentTextChanged.connect(lambda value, name=option.name: self._set_value(name, value))
            return editor
        if option.value_type in {"enum", "dynamic"} and option.choices:
            editor = NoWheelComboBox()
            editor.addItems(option.choices)
            editor.setEditable(option.value_type == "dynamic")
            if state.value not in option.choices and not has_invalid_issue:
                editor.addItem(state.value)
            editor.setCurrentText(state.value if not has_invalid_issue else option.default_value)
            editor.currentTextChanged.connect(lambda value, name=option.name: self._set_value(name, value))
            return editor
        editor = QLineEdit(state.value)
        editor.textChanged.connect(lambda value, name=option.name: self._set_value(name, value))
        return editor

    def _set_value(self, option_name: str, value: str) -> None:
        state = self._option_states[option_name]
        state.value = value
        state.checked = True
        state.origin = "user"

    def _reset_option(self, option: SchemaOption) -> None:
        state = self._option_states[option.name]
        state.value = option.default_value
        state.checked = False
        state.origin = "default"
        widget = self._field_widgets[option.name]
        if isinstance(widget, QComboBox):
            widget.setCurrentText(option.default_value)
        elif isinstance(widget, QLineEdit):
            widget.setText(option.default_value)
        self._rebuild_cards()

    def _apply_section_preset(self) -> None:
        presets = [preset for preset in self._preset_service.load_section_presets() if preset.section_name == self._section.name]
        if not presets:
            QMessageBox.information(self, "No Presets", f"No presets saved for section '{self._section.name}'.")
            return
        titles = [preset.title for preset in presets]
        title, accepted = QInputDialog.getItem(self, "Apply Section Preset", "Preset", titles, 0, False)
        if not accepted or not title:
            return
        preset = next(item for item in presets if item.title == title)
        for option_name, value in preset.sections.get(self._section.name, {}).items():
            if option_name not in self._option_states:
                continue
            self._option_states[option_name].value = value
            self._option_states[option_name].checked = True
            self._option_states[option_name].origin = "preset"
        self._rebuild_cards()

    def _save_section_preset(self) -> None:
        title, accepted = QInputDialog.getText(self, "Save Section Preset", "Preset name")
        if not accepted or not title.strip():
            return
        values = {
            option_name: state.value
            for option_name, state in self._option_states.items()
            if state.checked
        }
        self._preset_service.save_section_preset(title.strip(), self._section.name, values)
        QMessageBox.information(self, "Preset Saved", f"Saved section preset '{title.strip()}'.")

    def _format_help_text(self, text: str) -> str:
        lines: list[str] = []
        for index, raw_line in enumerate(text.splitlines()):
            stripped = raw_line.strip()
            if not stripped:
                lines.append("")
                continue
            if self._looks_like_option_line(stripped):
                prefix, suffix = stripped.split(":", 1)
                escaped = f"<b>{escape(prefix)}:</b>{escape(suffix)}"
            else:
                escaped = escape(stripped)
                if index > 0:
                    escaped = f"{'&nbsp;' * 4}{escaped}"
            lines.append(escaped)
        return "<br>".join(lines)

    def _looks_like_option_line(self, line: str) -> bool:
        if line.startswith(("Possible values:", "Deprecated values:", "Notes:", "Note:")):
            return True
        if ":" not in line:
            return False
        prefix = line.split(":", 1)[0].strip()
        return bool(prefix) and all(character.isalnum() or character in "_-+<>./%, " for character in prefix)


class AutoexecEditorDialog(QDialog):
    def __init__(self, autoexec_text: str, preset_service: PresetService, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Section: autoexec")
        self.resize(760, 600)
        self._preset_service = preset_service
        self._editor = QTextEdit()
        self._editor.setPlainText(autoexec_text)

        toolbar = QHBoxLayout()
        apply_button = QPushButton("Apply Section Preset")
        apply_button.clicked.connect(self._apply_section_preset)
        save_button = QPushButton("Save Section Preset")
        save_button.clicked.connect(self._save_section_preset)
        toolbar.addWidget(apply_button)
        toolbar.addWidget(save_button)
        toolbar.addStretch(1)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(toolbar)
        layout.addWidget(self._editor)
        layout.addWidget(buttons)
        self.setLayout(layout)

    @property
    def autoexec_text(self) -> str:
        return self._editor.toPlainText().strip()

    def _apply_section_preset(self) -> None:
        presets = [preset for preset in self._preset_service.load_section_presets() if preset.section_name == "autoexec"]
        if not presets:
            QMessageBox.information(self, "No Presets", "No presets saved for section 'autoexec'.")
            return
        titles = [preset.title for preset in presets]
        title, accepted = QInputDialog.getItem(self, "Apply Section Preset", "Preset", titles, 0, False)
        if not accepted or not title:
            return
        preset = next(item for item in presets if item.title == title)
        self._editor.setPlainText(preset.sections.get("autoexec", {}).get("__text__", ""))

    def _save_section_preset(self) -> None:
        title, accepted = QInputDialog.getText(self, "Save Section Preset", "Preset name")
        if not accepted or not title.strip():
            return
        self._preset_service.save_section_preset(title.strip(), "autoexec", {"__text__": self.autoexec_text})
        QMessageBox.information(self, "Preset Saved", f"Saved section preset '{title.strip()}'.")


class CreateMachineDialog(QDialog):
    def __init__(
        self,
        workspace_dir: Path,
        engine_registry: EngineRegistry,
        preset_service: PresetService,
        profile: MachineProfile | None = None,
        import_service: ImportService | None = None,
        import_analysis: ImportAnalysis | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Configure Imported Machine" if import_analysis is not None else "Configure Machine" if profile is not None else "Add New Machine")
        self.resize(980, 760)
        self._workspace_dir = workspace_dir
        self._engine_registry = engine_registry
        self._preset_service = preset_service
        self._import_service = import_service
        self._import_analysis = import_analysis
        self._renderer = ConfigRenderer()
        self._profile = profile
        self._schema: EngineSchema | None = None
        self._option_states: dict[str, dict[str, OptionState]] = {}
        self._section_buttons: dict[str, QPushButton] = {}
        self._autoexec_text = profile.autoexec_text if profile is not None else ""
        self._import_issues: list[ImportIssue] = list(import_analysis.issues) if import_analysis is not None else []
        self._raw_import_text = import_analysis.raw_text if import_analysis is not None else ""
        self._last_reanalysed_raw_text = self._raw_import_text
        self._raw_import_edit = QTextEdit()
        self._raw_import_edit.setPlainText(self._raw_import_text)

        self.title_edit = QLineEdit(profile.identity.title if profile else import_analysis.title if import_analysis else "")
        self.game_dir_edit = QLineEdit(str(profile.game.game_dir) if profile else str(import_analysis.game_dir) if import_analysis else "")
        self.executable_edit = QLineEdit(profile.game.executable if profile else import_analysis.executable if import_analysis else "")
        self.engine_binary_edit = QLineEdit(str(profile.engine.binary_path) if profile else str(import_analysis.engine_binary) if import_analysis else "/usr/bin/dosbox")
        self.setup_executable_edit = QLineEdit(profile.game.setup_executable or "" if profile else "")

        self._load_engine_button = QPushButton("Load Engine Schema")
        self._load_engine_button.clicked.connect(self._load_schema)
        self._save_machine_preset_button = QPushButton("Save Machine Preset")
        self._save_machine_preset_button.clicked.connect(self._save_machine_preset)
        self._apply_machine_preset_button = QPushButton("Apply Machine Preset")
        self._apply_machine_preset_button.clicked.connect(self._apply_machine_preset)
        self._config_preview = QTextEdit()
        self._config_preview.setReadOnly(True)

        self._tabs = QTabWidget()
        self._tabs.addTab(self._build_metadata_tab(), "Machine")
        self._tabs.addTab(self._build_sections_tab(), "Sections")
        self._tabs.addTab(self._build_preview_tab(), "Config Preview")
        if import_analysis is not None:
            self._tabs.addTab(self._build_raw_import_tab(), "Imported Raw Config")

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._validate_before_accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addWidget(self._tabs)
        layout.addWidget(buttons)
        self.setLayout(layout)

        if profile is not None:
            self._load_schema_from_profile()
        elif import_analysis is not None:
            self._load_schema_from_import()
        self._sync_buttons()

    def build_request(self) -> CreateProfileRequest:
        if self._import_analysis is not None and self._import_service is not None:
            self._reanalyse_raw_import()
        existing_profile_path = None
        notes = ""
        if self._profile is not None:
            existing_profile_path = self._profile.game.game_dir / ".dosmachines" / "profile.json"
            notes = self._profile.identity.notes
        return CreateProfileRequest(
            title=self.title_edit.text().strip(),
            game_dir=Path(self.game_dir_edit.text().strip()).expanduser(),
            executable=self.executable_edit.text().strip(),
            engine_binary=Path(self.engine_binary_edit.text().strip()).expanduser(),
            workspace_dir=self._workspace_dir,
            setup_executable=self.setup_executable_edit.text().strip() or None,
            notes=notes,
            option_states=self._option_states,
            autoexec_text=self._autoexec_text,
            raw_overrides=self._import_analysis.raw_overrides if self._import_analysis is not None else None,
            import_source_path=self._import_analysis.config_path if self._import_analysis is not None else None,
            existing_profile_path=existing_profile_path,
        )

    def _build_metadata_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        form = QFormLayout()
        form.addRow("Title", self.title_edit)
        form.addRow("Game Directory", self._with_browse(self.game_dir_edit, self._browse_game_dir))
        form.addRow("Executable", self._with_browse(self.executable_edit, self._browse_executable))
        form.addRow("Setup Executable", self._with_browse(self.setup_executable_edit, self._browse_setup_executable))
        form.addRow("Engine Binary", self._with_browse(self.engine_binary_edit, self._browse_engine_binary))
        form.addRow("", self._load_engine_button)
        layout.addLayout(form)
        layout.addStretch(1)
        return tab

    def _build_sections_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        toolbar = QHBoxLayout()
        toolbar.addWidget(self._apply_machine_preset_button)
        toolbar.addWidget(self._save_machine_preset_button)
        toolbar.addStretch(1)
        layout.addLayout(toolbar)
        self._sections_warning_label = QLabel()
        self._sections_warning_label.setWordWrap(True)
        self._sections_warning_label.setStyleSheet("color: #a16207;")
        self._sections_warning_label.hide()
        layout.addWidget(self._sections_warning_label)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        self._sections_host = QWidget()
        self._sections_flow = FlowLayout(self._sections_host, margin=8, hspacing=12, vspacing=12)
        self._sections_host.setLayout(self._sections_flow)
        scroll_area.setWidget(self._sections_host)
        layout.addWidget(scroll_area)
        return tab

    def _build_preview_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.addWidget(QLabel("Generated config preview"))
        layout.addWidget(self._config_preview)
        return tab

    def _build_raw_import_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.addWidget(QLabel("Imported raw config"))
        layout.addWidget(self._raw_import_edit)
        return tab

    def _with_browse(self, line_edit: QLineEdit, callback) -> QHBoxLayout:
        button = QPushButton("Browse…")
        button.clicked.connect(callback)
        layout = QHBoxLayout()
        layout.addWidget(line_edit)
        layout.addWidget(button)
        return layout

    def _browse_game_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select Game Directory", self.game_dir_edit.text().strip())
        if path:
            self.game_dir_edit.setText(path)
            self._update_preview()

    def _browse_engine_binary(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select DOSBox Binary", self.engine_binary_edit.text().strip())
        if path:
            self.engine_binary_edit.setText(path)

    def _browse_executable(self) -> None:
        self._browse_relative_file(self.executable_edit, "Select Game Executable")

    def _browse_setup_executable(self) -> None:
        self._browse_relative_file(self.setup_executable_edit, "Select Setup Executable")

    def _browse_relative_file(self, target_edit: QLineEdit, title: str) -> None:
        start_dir = self.game_dir_edit.text().strip() or str(Path.home())
        path, _ = QFileDialog.getOpenFileName(self, title, start_dir)
        if not path:
            return
        selected = Path(path)
        game_dir = self.game_dir_edit.text().strip()
        if game_dir:
            try:
                relative = selected.relative_to(Path(game_dir))
                target_edit.setText(str(relative).replace("/", "\\"))
                self._update_preview()
                return
            except ValueError:
                pass
        target_edit.setText(selected.name)
        self._update_preview()

    def _load_schema_from_profile(self) -> None:
        assert self._profile is not None
        cache = self._engine_registry.register(self._profile.engine.binary_path)
        self._schema = self._engine_registry.load_schema(cache.ref.engine_id)
        self._option_states = {
            section.name: {
                option.name: self._profile.option_states.get(section.name, {}).get(
                    option.name,
                    OptionState(value=option.default_value, checked=False, origin="default"),
                )
                for option in section.options
            }
            for section in self._schema.sections
        }
        self._autoexec_text = self._profile.autoexec_text or self._renderer.default_autoexec_text(
            self._profile.game,
            self._profile.engine.binary_path,
        )
        self._rebuild_sections_overview()

    def _load_schema_from_import(self) -> None:
        assert self._import_analysis is not None
        cache = self._engine_registry.register(self._import_analysis.engine_binary)
        self._schema = self._engine_registry.load_schema(cache.ref.engine_id)
        self._option_states = {
            section.name: {
                option.name: self._import_analysis.option_states.get(section.name, {}).get(
                    option.name,
                    OptionState(value=option.default_value, checked=False, origin="default"),
                )
                for option in section.options
            }
            for section in self._schema.sections
        }
        self._autoexec_text = self._import_analysis.autoexec_text
        self._rebuild_sections_overview()

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

        existing_option_states = self._option_states
        self._option_states = {
            section.name: {
                option.name: existing_option_states.get(section.name, {}).get(
                    option.name,
                    OptionState(value=option.default_value, checked=False, origin="default"),
                )
                for option in section.options
            }
            for section in self._schema.sections
        }
        if not self._autoexec_text:
            from dos_machines.domain.models import GameTargets

            game_dir = Path(self.game_dir_edit.text().strip() or ".").expanduser()
            self._autoexec_text = self._renderer.default_autoexec_text(
                GameTargets(
                    game_dir=game_dir,
                    working_dir=game_dir,
                    executable=self.executable_edit.text().strip(),
                    setup_executable=self.setup_executable_edit.text().strip() or None,
                ),
                binary_path,
            )
        self._rebuild_sections_overview()

    def _rebuild_sections_overview(self) -> None:
        while self._sections_flow.count():
            item = self._sections_flow.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._section_buttons.clear()
        if self._schema is None:
            self._update_preview()
            self._sync_buttons()
            return

        sectionless_issues = [
            issue.message
            for issue in self._import_issues
            if issue.section_name not in {section.name for section in self._schema.sections}
        ]
        if sectionless_issues:
            self._sections_warning_label.setText("\n".join(sectionless_issues))
            self._sections_warning_label.show()
        else:
            self._sections_warning_label.hide()

        for section in self._schema.sections:
            button = QPushButton(self._section_button_text(section.name))
            if any(issue.section_name == section.name for issue in self._import_issues):
                button.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_MessageBoxWarning))
                button.setStyleSheet("color: #a16207;")
            button.clicked.connect(lambda _=False, name=section.name: self._open_section_dialog(name))
            self._section_buttons[section.name] = button
            self._sections_flow.addWidget(button)

        self._update_preview()
        self._sync_buttons()

    def _open_section_dialog(self, section_name: str) -> None:
        if section_name == "autoexec":
            dialog = AutoexecEditorDialog(self._autoexec_text, self._preset_service, self)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            self._autoexec_text = dialog.autoexec_text
            self._update_preview()
            return
        if self._schema is None:
            return
        section = next((item for item in self._schema.sections if item.name == section_name), None)
        if section is None:
            return
        dialog = SectionEditorDialog(
            section=section,
            option_states=self._option_states[section_name],
            preset_service=self._preset_service,
            issues=[issue for issue in self._import_issues if issue.section_name == section_name],
            parent=self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self._refresh_import_issues_for_section(section)
        self._update_preview()

    def _sync_buttons(self) -> None:
        enabled = self._schema is not None
        self._save_machine_preset_button.setEnabled(enabled)
        self._apply_machine_preset_button.setEnabled(enabled)

    def _save_machine_preset(self) -> None:
        if self._schema is None:
            return
        title, accepted = QInputDialog.getText(self, "Save Machine Preset", "Preset name")
        if not accepted or not title.strip():
            return
        values = {
            section_name: {
                option_name: state.value
                for option_name, state in options.items()
                if state.checked
            }
            for section_name, options in self._option_states.items()
            if section_name != "autoexec"
        }
        if self._autoexec_text.strip():
            values["autoexec"] = {"__text__": self._autoexec_text.strip()}
        self._preset_service.save_machine_preset(title.strip(), values)
        QMessageBox.information(self, "Preset Saved", f"Saved machine preset '{title.strip()}'.")

    def _apply_machine_preset(self) -> None:
        presets = self._preset_service.load_machine_presets()
        if not presets:
            QMessageBox.information(self, "No Presets", "No machine presets have been saved yet.")
            return
        titles = [preset.title for preset in presets]
        title, accepted = QInputDialog.getItem(self, "Apply Machine Preset", "Preset", titles, 0, False)
        if not accepted or not title:
            return
        preset = next(item for item in presets if item.title == title)
        resolved = self._preset_service.resolve_machine_preset(preset.preset_id)
        for section_name, values in resolved.items():
            if section_name == "autoexec":
                self._autoexec_text = values.get("__text__", self._autoexec_text)
                continue
            if section_name not in self._option_states:
                continue
            for name, value in values.items():
                state = self._option_states[section_name].get(name)
                if state is None:
                    continue
                state.value = value
                state.checked = True
                state.origin = "preset"
        self._update_preview()

    def _preview_profile(self) -> MachineProfile | None:
        if self._schema is None:
            return None
        engine_binary = Path(self.engine_binary_edit.text().strip()).expanduser()
        try:
            cache = self._engine_registry.register(engine_binary)
        except Exception:
            return None
        if self._profile is not None:
            machine_id = self._profile.identity.machine_id
            ui_state = self._profile.ui
            provenance = self._profile.provenance
        else:
            machine_id = "preview"
            from dos_machines.domain.models import UiState, Provenance
            ui_state = UiState()
            provenance = Provenance()
        from dos_machines.domain.models import GameTargets, PresetRef, ProfileIdentity

        game_dir = Path(self.game_dir_edit.text().strip() or ".").expanduser()
        return MachineProfile(
            identity=ProfileIdentity(machine_id=machine_id, title=self.title_edit.text().strip() or "Preview"),
            engine=cache.ref,
            preset=PresetRef(preset_id="manual", start_mode="manual"),
            game=GameTargets(
                game_dir=game_dir,
                working_dir=game_dir,
                executable=self.executable_edit.text().strip(),
                setup_executable=self.setup_executable_edit.text().strip() or None,
            ),
            ui=ui_state,
            option_states=self._option_states,
            autoexec_text=self._autoexec_text,
            provenance=provenance,
        )

    def _update_preview(self) -> None:
        preview_profile = self._preview_profile()
        if preview_profile is None or self._schema is None:
            self._config_preview.clear()
            return
        self._config_preview.setPlainText(self._renderer.render(preview_profile, self._schema))

    def _validate_before_accept(self) -> None:
        if not self.title_edit.text().strip() or not self.game_dir_edit.text().strip():
            QMessageBox.warning(self, "Missing Fields", "Title and game directory are required.")
            return
        if self._schema is None:
            QMessageBox.warning(self, "Schema Not Loaded", "Load the engine schema before saving.")
            return
        if self._import_analysis is not None and self._import_service is not None:
            self._reanalyse_raw_import()
            if self._import_issues:
                QMessageBox.warning(
                    self,
                    "Import Issues",
                    "Resolve the highlighted import issues or repair the raw config before saving.",
                )
                return
        self.accept()

    def _reanalyse_raw_import(self) -> None:
        assert self._import_analysis is not None
        assert self._import_service is not None
        current_raw_text = self._raw_import_edit.toPlainText()
        if current_raw_text == self._last_reanalysed_raw_text:
            return
        latest = self._import_service.analyse_text(current_raw_text, self._import_analysis.config_path)
        self._import_analysis = latest
        self._import_issues = list(latest.issues)
        self._last_reanalysed_raw_text = current_raw_text
        self._autoexec_text = latest.autoexec_text
        self._option_states = latest.option_states
        self.title_edit.setText(latest.title)
        self.game_dir_edit.setText(str(latest.game_dir))
        self.executable_edit.setText(latest.executable)
        self.engine_binary_edit.setText(str(latest.engine_binary))
        self._rebuild_sections_overview()

    def _section_button_text(self, section_name: str) -> str:
        issue_count = sum(1 for issue in self._import_issues if issue.section_name == section_name)
        if issue_count:
            return f"{section_name} ({issue_count})"
        return section_name

    def _refresh_import_issues_for_section(self, section: SchemaSection) -> None:
        if self._schema is None:
            return
        remaining: list[ImportIssue] = []
        for issue in self._import_issues:
            if issue.section_name != section.name or issue.option_name is None:
                remaining.append(issue)
                continue
            option = next((item for item in section.options if item.name == issue.option_name), None)
            state = self._option_states.get(section.name, {}).get(issue.option_name)
            if option is None or state is None:
                remaining.append(issue)
                continue
            if option.value_type == "boolean" and state.value.lower() not in {"true", "false", "1", "0"}:
                remaining.append(issue)
                continue
            if option.choices and state.value not in option.choices:
                remaining.append(issue)
                continue
        self._import_issues = remaining
        self._rebuild_sections_overview()
