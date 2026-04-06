import stat
from pathlib import Path

from PySide6.QtWidgets import QApplication

from dos_machines.application.engine_registry import EngineRegistry
from dos_machines.application.preset_service import PresetService
from dos_machines.application.settings_service import SettingsService
from dos_machines.ui.host_config_dialog import HostConfigDialog


def _app() -> QApplication:
    app = QApplication.instance()
    return app if app is not None else QApplication([])


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


def test_host_config_dialog_loads_saved_sdl_defaults(tmp_path: Path) -> None:
    _app()
    settings_service = SettingsService(config_root=tmp_path / "config")
    settings_service.load()
    engine_registry = EngineRegistry(settings_service.app_paths)
    preset_service = PresetService(settings_service.app_paths)
    binary = _fake_binary(tmp_path / "bin" / "dosbox")
    cache = engine_registry.register(binary)
    preset_service.save_section_default(cache.ref.engine_id, "sdl", {"fullscreen": "true"})

    dialog = HostConfigDialog(settings_service, engine_registry, preset_service)
    dialog.engine_binary_edit.setText(str(binary))
    dialog._load_schema_if_possible()

    assert dialog._sdl_option_states["fullscreen"].value == "true"
    assert dialog._sdl_option_states["fullscreen"].checked is True


def test_host_config_dialog_falls_back_to_schema_defaults(tmp_path: Path) -> None:
    _app()
    settings_service = SettingsService(config_root=tmp_path / "config")
    settings_service.load()
    engine_registry = EngineRegistry(settings_service.app_paths)
    preset_service = PresetService(settings_service.app_paths)
    binary = _fake_binary(tmp_path / "bin" / "dosbox")
    cache = engine_registry.register(binary)
    schema = engine_registry.load_schema(cache.ref.engine_id)
    fullscreen = next(
        option for section in schema.sections if section.name == "sdl"
        for option in section.options if option.name == "fullscreen"
    )

    dialog = HostConfigDialog(settings_service, engine_registry, preset_service)
    dialog.engine_binary_edit.setText(str(binary))
    dialog._load_schema_if_possible()

    assert dialog._sdl_option_states["fullscreen"].value == fullscreen.default_value
    assert dialog._sdl_option_states["fullscreen"].checked is False


def test_host_config_dialog_saves_sdl_defaults(tmp_path: Path) -> None:
    _app()
    settings_service = SettingsService(config_root=tmp_path / "config")
    settings_service.load()
    engine_registry = EngineRegistry(settings_service.app_paths)
    preset_service = PresetService(settings_service.app_paths)
    binary = _fake_binary(tmp_path / "bin" / "dosbox")
    cache = engine_registry.register(binary)

    dialog = HostConfigDialog(settings_service, engine_registry, preset_service)
    dialog.engine_binary_edit.setText(str(binary))
    dialog._load_schema_if_possible()
    dialog._sdl_option_states["fullscreen"].value = "true"
    dialog._sdl_option_states["fullscreen"].checked = True
    dialog._save()

    assert preset_service.load_section_default(cache.ref.engine_id, "sdl") == {"fullscreen": "true"}
