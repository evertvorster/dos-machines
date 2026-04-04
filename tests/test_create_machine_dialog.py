from pathlib import Path
import stat

from PySide6.QtWidgets import QApplication

from dos_machines.application.config_renderer import ConfigRenderer
from dos_machines.application.engine_registry import EngineRegistry
from dos_machines.application.profile_service import CreateProfileRequest, ProfileService
from dos_machines.application.preset_service import PresetService
from dos_machines.application.settings_service import SettingsService
from dos_machines.domain.models import OptionState
from dos_machines.ui.create_machine_dialog import CreateMachineDialog


def _fake_binary(path: Path, version_output: str = "dosbox-staging, version 0.82.2") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = \"--list-glshaders\" ]; then\n"
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
    preset_service.save_section_default(cache.ref.engine_id, "sdl", {"fullscreen": "true"})
    preset_service.save_section_default(cache.ref.engine_id, "autoexec", {"__text__": "mount c \".\"\nc:"})

    dialog = CreateMachineDialog(tmp_path / "workspace", settings_service, engine_registry, preset_service)
    dialog.engine_binary_edit.setText(str(binary))
    dialog.game_dir_edit.setText(str(tmp_path / "game"))
    dialog._load_schema_if_possible()

    assert dialog._option_states["sdl"]["fullscreen"].value == "true"
    assert dialog._option_states["sdl"]["fullscreen"].origin == "default-preset"
    assert dialog._autoexec_text == 'mount c "."\nc:'


def test_existing_machine_does_not_apply_engine_scoped_section_defaults(tmp_path: Path) -> None:
    _app()
    settings_service = SettingsService(config_root=tmp_path / "config")
    settings_service.load()
    preset_service = PresetService(settings_service.app_paths)
    engine_registry = EngineRegistry(settings_service.app_paths)
    profile_service = ProfileService(settings_service.app_paths, engine_registry, ConfigRenderer())
    binary = _fake_binary(tmp_path / "bin" / "dosbox")
    cache = engine_registry.register(binary)
    schema = engine_registry.load_schema(cache.ref.engine_id)
    preset_service.save_section_default(cache.ref.engine_id, "sdl", {"fullscreen": "true"})

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
                        value="false" if section.name == "sdl" and option.name == "fullscreen" else option.default_value,
                        checked=section.name == "sdl" and option.name == "fullscreen",
                        origin="user" if section.name == "sdl" and option.name == "fullscreen" else "default",
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
    dialog = CreateMachineDialog(tmp_path / "workspace", settings_service, engine_registry, preset_service)

    game_dir = tmp_path / "game"
    capture_dir = game_dir / ".dosmachines" / "capture"
    capture_dir.mkdir(parents=True)
    dialog.game_dir_edit.setText(str(game_dir))

    assert dialog._icon_start_dir() == capture_dir
