import os
from pathlib import Path
import stat
from types import MethodType

from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QApplication, QLabel, QToolButton

from dos_machines.application.config_renderer import ConfigRenderer
from dos_machines.application.engine_registry import EngineRegistry
from dos_machines.application.import_service import ImportService
from dos_machines.application.profile_service import (
    CreateProfileRequest,
    ProfileService,
)
from dos_machines.application.preset_service import PresetService
from dos_machines.application.settings_service import SettingsService
from dos_machines.domain.models import OptionState, SchemaOption, SchemaSection
from dos_machines.ui.create_machine_dialog import (
    CollapsibleHelpWidget,
    CreateMachineDialog,
    NoWheelComboBox,
    SectionEditorDialog,
    SystemPresetBrowserDialog,
)


def _fake_binary(
    path: Path, version_output: str = "dosbox-staging, version 0.82.2"
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "#!/bin/sh\n"
        'if [ "$1" = "--list-glshaders" ]; then\n'
        "  echo crt-auto\n"
        "  echo sharp\n"
        "  exit 0\n"
        "fi\n"
        f"echo '{version_output}'\n",
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return path


def _app() -> QApplication:
    app = QApplication.instance()
    return app if app is not None else QApplication([])


def test_new_machine_applies_engine_scoped_section_defaults(tmp_path: Path) -> None:
    _app()
    settings_service = SettingsService(config_root=tmp_path / "config")
    settings_service.load()
    preset_service = PresetService(settings_service.app_paths)
    engine_registry = EngineRegistry(settings_service.app_paths)
    binary = _fake_binary(tmp_path / "bin" / "dosbox")
    cache = engine_registry.register(binary)
    preset_service.save_section_default(
        cache.ref.engine_id, "sdl", {"fullscreen": "true"}
    )
    preset_service.save_section_default(
        cache.ref.engine_id, "autoexec", {"__text__": 'mount c "."\nc:'}
    )

    dialog = CreateMachineDialog(
        tmp_path / "workspace", settings_service, engine_registry, preset_service
    )
    dialog.engine_binary_edit.setText(str(binary))
    dialog.game_dir_edit.setText(str(tmp_path / "game"))
    dialog._load_schema_if_possible()

    assert dialog._option_states["sdl"]["fullscreen"].value == "true"
    assert dialog._option_states["sdl"]["fullscreen"].origin == "default-preset"
    assert dialog._autoexec_text == 'mount c "."\nc:'


def test_existing_machine_does_not_apply_engine_scoped_section_defaults(
    tmp_path: Path,
) -> None:
    _app()
    settings_service = SettingsService(config_root=tmp_path / "config")
    settings_service.load()
    preset_service = PresetService(settings_service.app_paths)
    engine_registry = EngineRegistry(settings_service.app_paths)
    profile_service = ProfileService(
        settings_service.app_paths, engine_registry, ConfigRenderer()
    )
    binary = _fake_binary(tmp_path / "bin" / "dosbox")
    cache = engine_registry.register(binary)
    schema = engine_registry.load_schema(cache.ref.engine_id)
    preset_service.save_section_default(
        cache.ref.engine_id, "sdl", {"fullscreen": "true"}
    )

    profile = profile_service.create(
        CreateProfileRequest(
            title="Existing",
            game_dir=tmp_path / "game",
            executable="GAME.EXE",
            engine_binary=binary,
            workspace_dir=tmp_path / "workspace",
            option_states={
                section.name: {
                    option.name: OptionState(
                        value="false"
                        if section.name == "sdl" and option.name == "fullscreen"
                        else option.default_value,
                        checked=section.name == "sdl" and option.name == "fullscreen",
                        origin="user"
                        if section.name == "sdl" and option.name == "fullscreen"
                        else "default",
                    )
                    for option in section.options
                }
                for section in schema.sections
                if section.name != "autoexec"
            },
        )
    )

    configured = CreateMachineDialog(
        tmp_path / "workspace",
        settings_service,
        engine_registry,
        preset_service,
        profile=profile,
    )

    assert configured._option_states["sdl"]["fullscreen"].value == "false"
    assert configured._option_states["sdl"]["fullscreen"].origin == "user"


def test_icon_selection_prefers_capture_directory(tmp_path: Path) -> None:
    _app()
    settings_service = SettingsService(config_root=tmp_path / "config")
    settings_service.load()
    preset_service = PresetService(settings_service.app_paths)
    engine_registry = EngineRegistry(settings_service.app_paths)
    dialog = CreateMachineDialog(
        tmp_path / "workspace", settings_service, engine_registry, preset_service
    )

    game_dir = tmp_path / "game"
    capture_dir = game_dir / ".dosmachines" / "capture"
    capture_dir.mkdir(parents=True)
    dialog.game_dir_edit.setText(str(game_dir))

    assert dialog._icon_start_dir() == capture_dir


def test_existing_profile_does_not_resubmit_current_icon_as_new_source(
    tmp_path: Path,
) -> None:
    _app()
    settings_service = SettingsService(config_root=tmp_path / "config")
    settings_service.load()
    preset_service = PresetService(settings_service.app_paths)
    engine_registry = EngineRegistry(settings_service.app_paths)
    profile_service = ProfileService(
        settings_service.app_paths, engine_registry, ConfigRenderer()
    )
    binary = _fake_binary(tmp_path / "bin" / "dosbox")
    cache = engine_registry.register(binary)
    schema = engine_registry.load_schema(cache.ref.engine_id)
    managed_icon = tmp_path / "game" / ".dosmachines" / "image0001.png"
    managed_icon.parent.mkdir(parents=True)
    managed_icon.write_text("icon", encoding="utf-8")

    profile = profile_service.create(
        CreateProfileRequest(
            title="Icon Game",
            game_dir=tmp_path / "game",
            executable="",
            engine_binary=binary,
            workspace_dir=tmp_path / "workspace",
            option_states={
                section.name: {
                    option.name: OptionState(
                        value=option.default_value, checked=True, origin="default"
                    )
                    for option in section.options
                }
                for section in schema.sections
                if section.name != "autoexec"
            },
        )
    )
    profile.ui.icon_path = managed_icon

    dialog = CreateMachineDialog(
        tmp_path / "workspace",
        settings_service,
        engine_registry,
        preset_service,
        profile=profile,
    )
    request = dialog.build_request()

    assert request.icon_source is None
    assert request.remove_icon is False


def test_section_editor_collapses_multiline_help_by_default(tmp_path: Path) -> None:
    _app()
    settings_service = SettingsService(config_root=tmp_path / "config")
    settings_service.load()
    preset_service = PresetService(settings_service.app_paths)
    section = SchemaSection(
        name="cpu",
        options=[
            SchemaOption(
                section="cpu",
                name="core",
                default_value="auto",
                value_type="enum",
                description="",
                help_text="Type of CPU emulation core to use.\nauto: The default mode.\nPossible values: auto, dynamic",
                choices=["auto", "dynamic"],
            )
        ],
    )
    option_states = {"core": OptionState(value="auto", checked=False, origin="default")}

    dialog = SectionEditorDialog(section, option_states, preset_service)

    widgets = dialog.findChildren(CollapsibleHelpWidget)

    assert len(widgets) == 1
    assert widgets[0]._preview_label.text() == "Type of CPU emulation core to use."
    assert widgets[0]._details_label.isHidden()
    assert widgets[0]._toggle_button.arrowType() == Qt.ArrowType.RightArrow


def test_section_editor_expands_and_collapses_multiline_help(tmp_path: Path) -> None:
    _app()
    settings_service = SettingsService(config_root=tmp_path / "config")
    settings_service.load()
    preset_service = PresetService(settings_service.app_paths)
    section = SchemaSection(
        name="cpu",
        options=[
            SchemaOption(
                section="cpu",
                name="core",
                default_value="auto",
                value_type="enum",
                description="",
                help_text="Type of CPU emulation core to use.\nauto: The default mode.\nPossible values: auto, dynamic",
                choices=["auto", "dynamic"],
            )
        ],
    )
    option_states = {"core": OptionState(value="auto", checked=False, origin="default")}

    dialog = SectionEditorDialog(section, option_states, preset_service)
    widget = dialog.findChildren(CollapsibleHelpWidget)[0]

    widget._toggle_button.click()

    assert not widget._details_label.isHidden()
    assert widget._toggle_button.arrowType() == Qt.ArrowType.DownArrow
    assert (
        widget._details_label.text()
        == "<b>auto:</b> The default mode.<br><b>Possible values:</b> auto, dynamic"
    )

    widget._toggle_button.click()

    assert widget._details_label.isHidden()
    assert widget._toggle_button.arrowType() == Qt.ArrowType.RightArrow


def test_section_editor_keeps_single_line_help_expanded(tmp_path: Path) -> None:
    _app()
    settings_service = SettingsService(config_root=tmp_path / "config")
    settings_service.load()
    preset_service = PresetService(settings_service.app_paths)
    section = SchemaSection(
        name="cpu",
        options=[
            SchemaOption(
                section="cpu",
                name="core",
                default_value="auto",
                value_type="enum",
                description="",
                help_text="Type of CPU emulation core to use.",
                choices=["auto", "dynamic"],
            )
        ],
    )
    option_states = {"core": OptionState(value="auto", checked=False, origin="default")}

    dialog = SectionEditorDialog(section, option_states, preset_service)

    assert dialog.findChildren(CollapsibleHelpWidget) == []
    assert dialog.findChildren(QToolButton) == []
    assert "Type of CPU emulation core to use." in [
        label.text() for label in dialog.findChildren(QLabel)
    ]


def test_no_wheel_combo_box_never_changes_value() -> None:
    app = _app()
    combo = NoWheelComboBox()
    combo.addItems(["auto", "dynamic", "normal"])
    combo.setCurrentText("dynamic")
    combo.setFocus()

    event = QWheelEvent(
        QPointF(5, 5),
        QPointF(5, 5),
        QPoint(0, 0),
        QPoint(0, 120),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.ScrollUpdate,
        False,
    )
    QApplication.sendEvent(combo, event)

    assert combo.currentText() == "dynamic"
    assert not event.isAccepted()


def test_recovery_dialog_hydrates_existing_profile_when_game_dir_is_corrected(
    tmp_path: Path,
) -> None:
    _app()
    settings_service = SettingsService(config_root=tmp_path / "config")
    settings_service.load()
    preset_service = PresetService(settings_service.app_paths)
    engine_registry = EngineRegistry(settings_service.app_paths)
    profile_service = ProfileService(
        settings_service.app_paths, engine_registry, ConfigRenderer()
    )
    binary = _fake_binary(tmp_path / "bin" / "dosbox")
    cache = engine_registry.register(binary)
    schema = engine_registry.load_schema(cache.ref.engine_id)
    game_dir = tmp_path / "moved-game"
    profile = profile_service.create(
        CreateProfileRequest(
            title="Recovered Machine",
            game_dir=game_dir,
            executable="GAME.EXE",
            engine_binary=binary,
            workspace_dir=tmp_path / "workspace",
            option_states={
                section.name: {
                    option.name: OptionState(
                        value=option.default_value, checked=True, origin="default"
                    )
                    for option in section.options
                }
                for section in schema.sections
                if section.name != "autoexec"
            },
        )
    )

    dialog = CreateMachineDialog(
        tmp_path / "workspace",
        settings_service,
        engine_registry,
        preset_service,
        profile_service=profile_service,
        recovery_mode=True,
    )

    dialog.game_dir_edit.setText(str(game_dir))
    request = dialog.build_request()

    assert dialog.title_edit.text() == "Recovered Machine"
    assert dialog.engine_binary_edit.text() == str(binary)
    assert (
        request.existing_profile_path
        == profile.game.game_dir / ".dosmachines" / "profile.json"
    )


def test_recovery_dialog_normalizes_loaded_profile_to_selected_directory(
    tmp_path: Path,
) -> None:
    _app()
    settings_service = SettingsService(config_root=tmp_path / "config")
    settings_service.load()
    preset_service = PresetService(settings_service.app_paths)
    engine_registry = EngineRegistry(settings_service.app_paths)
    profile_service = ProfileService(
        settings_service.app_paths, engine_registry, ConfigRenderer()
    )
    binary = _fake_binary(tmp_path / "bin" / "dosbox")
    cache = engine_registry.register(binary)
    schema = engine_registry.load_schema(cache.ref.engine_id)
    original_dir = tmp_path / "original-game"
    moved_dir = tmp_path / "moved-game"
    profile = profile_service.create(
        CreateProfileRequest(
            title="Recovered Machine",
            game_dir=original_dir,
            executable="GAME.EXE",
            engine_binary=binary,
            workspace_dir=tmp_path / "workspace",
            option_states={
                section.name: {
                    option.name: OptionState(
                        value=option.default_value, checked=True, origin="default"
                    )
                    for option in section.options
                }
                for section in schema.sections
                if section.name != "autoexec"
            },
        )
    )
    moved_profile_path = moved_dir / ".dosmachines" / "profile.json"
    moved_profile_path.parent.mkdir(parents=True)
    moved_profile_path.write_text(
        (original_dir / ".dosmachines" / "profile.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    dialog = CreateMachineDialog(
        tmp_path / "workspace",
        settings_service,
        engine_registry,
        preset_service,
        profile_service=profile_service,
        recovery_mode=True,
    )

    dialog.game_dir_edit.setText(str(moved_dir))
    request = dialog.build_request()

    assert dialog.game_dir_edit.text() == str(moved_dir)
    assert request.game_dir == moved_dir
    assert request.existing_profile_path == moved_profile_path


def test_recovery_dialog_reloads_managed_config_when_profile_is_missing(
    tmp_path: Path, monkeypatch
) -> None:
    _app()
    settings_service = SettingsService(config_root=tmp_path / "config")
    settings_service.load()
    preset_service = PresetService(settings_service.app_paths)
    engine_registry = EngineRegistry(settings_service.app_paths)
    profile_service = ProfileService(
        settings_service.app_paths, engine_registry, ConfigRenderer()
    )
    import_service = ImportService(engine_registry, profile_service)
    binary = _fake_binary(tmp_path / "bin" / "dosbox")
    engine_registry.register(binary)
    monkeypatch.setenv("PATH", f"{binary.parent}:{os.environ.get('PATH', '')}")

    game_dir = tmp_path / "moved-game"
    managed_dir = game_dir / ".dosmachines"
    managed_dir.mkdir(parents=True)
    config_path = managed_dir / "dosbox.conf"
    config_path.write_text(
        "\n".join(
            [
                "# Generated by DOS Machines",
                "# Machine: Recovered Config",
                "",
                "[cpu]",
                "core = auto",
                "",
                "[autoexec]",
                'mount c ".."',
                "c:",
                "",
            ]
        ),
        encoding="utf-8",
    )

    dialog = CreateMachineDialog(
        tmp_path / "workspace",
        settings_service,
        engine_registry,
        preset_service,
        import_service=import_service,
        profile_service=profile_service,
        recovery_mode=True,
    )

    dialog.game_dir_edit.setText(str(game_dir))
    request = dialog.build_request()

    assert dialog.game_dir_edit.text() == str(game_dir)
    assert dialog.engine_binary_edit.text().endswith("dosbox")
    assert request.import_source_path == config_path
    assert request.existing_profile_path is None


def test_import_dialog_allows_save_with_only_non_blocking_issues(
    tmp_path: Path, monkeypatch
) -> None:
    _app()
    settings_service = SettingsService(config_root=tmp_path / "config")
    settings_service.load()
    preset_service = PresetService(settings_service.app_paths)
    engine_registry = EngineRegistry(settings_service.app_paths)
    profile_service = ProfileService(
        settings_service.app_paths, engine_registry, ConfigRenderer()
    )
    import_service = ImportService(engine_registry, profile_service)
    binary = _fake_binary(tmp_path / "bin" / "dosbox")
    monkeypatch.setenv("PATH", f"{binary.parent}:{os.environ.get('PATH', '')}")

    config_path = tmp_path / "game" / "dosbox.conf"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        "[sdl]\nfullscreen = true\n\n[soundcanvas]\nfoo = bar\n",
        encoding="utf-8",
    )
    analysis = import_service.analyse_config(config_path)
    dialog = CreateMachineDialog(
        tmp_path / "workspace",
        settings_service,
        engine_registry,
        preset_service,
        import_service=import_service,
        import_analysis=analysis,
    )
    accepted = {"called": False}

    def _accept(self):
        accepted["called"] = True

    dialog.accept = MethodType(_accept, dialog)
    dialog._validate_before_accept()

    assert accepted["called"] is True


def test_import_dialog_sets_engine_id_and_preserves_imported_values(
    tmp_path: Path, monkeypatch
) -> None:
    _app()
    settings_service = SettingsService(config_root=tmp_path / "config")
    settings_service.load()
    preset_service = PresetService(settings_service.app_paths)
    engine_registry = EngineRegistry(settings_service.app_paths)
    profile_service = ProfileService(
        settings_service.app_paths, engine_registry, ConfigRenderer()
    )
    import_service = ImportService(engine_registry, profile_service)
    binary = _fake_binary(tmp_path / "bin" / "dosbox")
    cache = engine_registry.register(binary)
    preset_service.save_section_default(
        cache.ref.engine_id, "sdl", {"fullscreen": "false"}
    )
    monkeypatch.setenv("PATH", f"{binary.parent}:{os.environ.get('PATH', '')}")

    config_path = tmp_path / "game" / "dosbox.conf"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        "[sdl]\nfullscreen = true\n\n[autoexec]\nmount c .\nc:\n",
        encoding="utf-8",
    )
    analysis = import_service.analyse_config(config_path)

    dialog = CreateMachineDialog(
        tmp_path / "workspace",
        settings_service,
        engine_registry,
        preset_service,
        import_service=import_service,
        import_analysis=analysis,
    )

    assert dialog._engine_id == cache.ref.engine_id
    assert dialog._option_states["sdl"]["fullscreen"].value == "true"
    assert dialog._option_states["sdl"]["fullscreen"].origin == "imported"


def test_import_dialog_section_default_save_uses_loaded_engine_id(
    tmp_path: Path, monkeypatch
) -> None:
    _app()
    settings_service = SettingsService(config_root=tmp_path / "config")
    settings_service.load()
    preset_service = PresetService(settings_service.app_paths)
    engine_registry = EngineRegistry(settings_service.app_paths)
    profile_service = ProfileService(
        settings_service.app_paths, engine_registry, ConfigRenderer()
    )
    import_service = ImportService(engine_registry, profile_service)
    binary = _fake_binary(tmp_path / "bin" / "dosbox")
    cache = engine_registry.register(binary)
    monkeypatch.setenv("PATH", f"{binary.parent}:{os.environ.get('PATH', '')}")

    config_path = tmp_path / "game" / "dosbox.conf"
    config_path.parent.mkdir(parents=True)
    config_path.write_text("[sdl]\nfullscreen = true\n", encoding="utf-8")
    analysis = import_service.analyse_config(config_path)
    dialog = CreateMachineDialog(
        tmp_path / "workspace",
        settings_service,
        engine_registry,
        preset_service,
        import_service=import_service,
        import_analysis=analysis,
    )

    monkeypatch.setattr(
        "dos_machines.ui.create_machine_dialog.QMessageBox.information",
        lambda *args, **kwargs: None,
    )

    section = next(
        section for section in dialog._schema.sections if section.name == "sdl"
    )
    section_dialog = SectionEditorDialog(
        section,
        dialog._option_states["sdl"],
        preset_service,
        engine_id=dialog._engine_id,
    )
    section_dialog._save_section_default()

    assert preset_service.load_section_default(cache.ref.engine_id, "sdl") == {
        "fullscreen": "true"
    }


def test_build_request_uses_edited_config_preview_text(tmp_path: Path) -> None:
    _app()
    settings_service = SettingsService(config_root=tmp_path / "config")
    settings_service.load()
    preset_service = PresetService(settings_service.app_paths)
    engine_registry = EngineRegistry(settings_service.app_paths)
    binary = _fake_binary(tmp_path / "bin" / "dosbox")
    cache = engine_registry.register(binary)
    schema = engine_registry.load_schema(cache.ref.engine_id)
    dialog = CreateMachineDialog(
        tmp_path / "workspace",
        settings_service,
        engine_registry,
        preset_service,
    )
    dialog.engine_binary_edit.setText(str(binary))
    dialog.game_dir_edit.setText(str(tmp_path / "game"))
    dialog._load_schema_if_possible()

    edited_config = "[sdl]\nfullscreen = false\n"
    dialog._config_preview.setPlainText(edited_config)
    request = dialog.build_request()

    assert request.raw_config_text == edited_config


def test_saving_machine_preset_from_dialog_omits_sdl_and_autoexec(
    tmp_path: Path, monkeypatch
) -> None:
    _app()
    settings_service = SettingsService(config_root=tmp_path / "config")
    settings_service.load()
    preset_service = PresetService(settings_service.app_paths)
    engine_registry = EngineRegistry(settings_service.app_paths)
    binary = _fake_binary(tmp_path / "bin" / "dosbox")
    dialog = CreateMachineDialog(
        tmp_path / "workspace",
        settings_service,
        engine_registry,
        preset_service,
    )
    dialog.engine_binary_edit.setText(str(binary))
    dialog.game_dir_edit.setText(str(tmp_path / "game"))
    dialog._load_schema_if_possible()
    dialog._option_states["sdl"]["fullscreen"].value = "true"
    dialog._option_states["sdl"]["fullscreen"].checked = True
    dialog._option_states["midi"]["mididevice"].value = "mt32"
    dialog._option_states["midi"]["mididevice"].checked = True
    dialog._autoexec_text = "mount c .\nc:"

    monkeypatch.setattr(
        "dos_machines.ui.create_machine_dialog.QInputDialog.getItem",
        lambda *args, **kwargs: ("Preset A", True),
    )
    monkeypatch.setattr(
        "dos_machines.ui.create_machine_dialog.QMessageBox.information",
        lambda *args, **kwargs: None,
    )
    dialog._save_machine_preset()

    preset = preset_service.load_user_machine_presets()[0]
    resolved = preset_service.resolve_machine_preset(preset.preset_id)

    assert "sdl" not in resolved
    assert "autoexec" not in resolved
    assert resolved["midi"]["mididevice"] == "mt32"


def test_applying_user_machine_preset_keeps_current_sdl(
    tmp_path: Path, monkeypatch
) -> None:
    _app()
    settings_service = SettingsService(config_root=tmp_path / "config")
    settings_service.load()
    preset_service = PresetService(settings_service.app_paths)
    engine_registry = EngineRegistry(settings_service.app_paths)
    binary = _fake_binary(tmp_path / "bin" / "dosbox")
    dialog = CreateMachineDialog(
        tmp_path / "workspace",
        settings_service,
        engine_registry,
        preset_service,
    )
    dialog.engine_binary_edit.setText(str(binary))
    dialog.game_dir_edit.setText(str(tmp_path / "game"))
    dialog._load_schema_if_possible()
    dialog._option_states["sdl"]["fullscreen"].value = "false"
    dialog._option_states["sdl"]["fullscreen"].checked = True
    preset_service.save_machine_preset(
        "Preset A", {"sdl": {"fullscreen": "true"}, "midi": {"mididevice": "mt32"}}
    )

    monkeypatch.setattr(
        "dos_machines.ui.create_machine_dialog.QInputDialog.getItem",
        lambda *args, **kwargs: ("Preset A", True),
    )
    dialog._apply_user_machine_preset()

    assert dialog._option_states["sdl"]["fullscreen"].value == "false"
    assert dialog._option_states["midi"]["mididevice"].value == "mt32"


def test_applying_user_machine_preset_keeps_current_autoexec(
    tmp_path: Path, monkeypatch
) -> None:
    _app()
    settings_service = SettingsService(config_root=tmp_path / "config")
    settings_service.load()
    preset_service = PresetService(settings_service.app_paths)
    engine_registry = EngineRegistry(settings_service.app_paths)
    binary = _fake_binary(tmp_path / "bin" / "dosbox")
    dialog = CreateMachineDialog(
        tmp_path / "workspace",
        settings_service,
        engine_registry,
        preset_service,
    )
    dialog.engine_binary_edit.setText(str(binary))
    dialog.game_dir_edit.setText(str(tmp_path / "game"))
    dialog._load_schema_if_possible()
    dialog._autoexec_text = "mount c current\nc:"
    preset_service.save_machine_preset(
        "Preset A",
        {
            "autoexec": {"__text__": "mount c preset\nc:"},
            "midi": {"mididevice": "mt32"},
        },
    )

    monkeypatch.setattr(
        "dos_machines.ui.create_machine_dialog.QInputDialog.getItem",
        lambda *args, **kwargs: ("Preset A", True),
    )
    dialog._apply_user_machine_preset()

    assert dialog._autoexec_text == "mount c current\nc:"
    assert dialog._option_states["midi"]["mididevice"].value == "mt32"


def test_system_preset_browser_renders_details(tmp_path: Path) -> None:
    _app()
    settings_service = SettingsService(config_root=tmp_path / "config")
    settings_service.load()
    preset_service = PresetService(settings_service.app_paths)

    dialog = SystemPresetBrowserDialog(preset_service.load_system_machine_presets())

    assert dialog.selected_preset is not None
    assert "Hardware profile" in dialog._details.toPlainText()
    assert dialog.selected_preset.preset_id in dialog._details.toPlainText()


def test_applying_system_machine_preset_keeps_current_sdl(tmp_path: Path) -> None:
    _app()
    settings_service = SettingsService(config_root=tmp_path / "config")
    settings_service.load()
    preset_service = PresetService(settings_service.app_paths)
    engine_registry = EngineRegistry(settings_service.app_paths)
    binary = _fake_binary(tmp_path / "bin" / "dosbox")
    dialog = CreateMachineDialog(
        tmp_path / "workspace",
        settings_service,
        engine_registry,
        preset_service,
    )
    dialog.engine_binary_edit.setText(str(binary))
    dialog.game_dir_edit.setText(str(tmp_path / "game"))
    dialog._load_schema_if_possible()
    dialog._option_states["sdl"]["fullscreen"].value = "false"
    dialog._option_states["sdl"]["fullscreen"].checked = True

    preset = next(
        item
        for item in preset_service.load_system_machine_presets()
        if item.preset_id == "486_vga_sb_mt32"
    )
    dialog._apply_machine_preset_values(preset)

    assert dialog._option_states["sdl"]["fullscreen"].value == "false"
    assert dialog._option_states["midi"]["mididevice"].value == "mt32"
    assert dialog._option_states["cpu"]["cputype"].value == "486"
    assert dialog._option_states["cpu"]["cpu_cycles"].value == "25000"


def test_applying_system_machine_preset_keeps_current_autoexec(tmp_path: Path) -> None:
    _app()
    settings_service = SettingsService(config_root=tmp_path / "config")
    settings_service.load()
    preset_service = PresetService(settings_service.app_paths)
    engine_registry = EngineRegistry(settings_service.app_paths)
    binary = _fake_binary(tmp_path / "bin" / "dosbox")
    dialog = CreateMachineDialog(
        tmp_path / "workspace",
        settings_service,
        engine_registry,
        preset_service,
    )
    dialog.engine_binary_edit.setText(str(binary))
    dialog.game_dir_edit.setText(str(tmp_path / "game"))
    dialog._load_schema_if_possible()
    dialog._autoexec_text = "mount c current\nc:"

    preset = next(
        item
        for item in preset_service.load_system_machine_presets()
        if item.preset_id == "486_vga_sb_mt32"
    )
    dialog._apply_machine_preset_values(preset)

    assert dialog._autoexec_text == "mount c current\nc:"
