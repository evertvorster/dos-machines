from pathlib import Path

from PySide6.QtWidgets import QApplication

from dos_machines.application.config_renderer import ConfigRenderer
from dos_machines.application.engine_registry import EngineRegistry
from dos_machines.application.import_service import ImportService
from dos_machines.application.launcher_service import LauncherService
from dos_machines.application.preset_service import PresetService
from dos_machines.application.profile_service import ProfileService
from dos_machines.application.settings_service import SettingsService
from dos_machines.application.workspace_service import WorkspaceService
from dos_machines.ui.main_window import MainWindow


def _app() -> QApplication:
    app = QApplication.instance()
    return app if app is not None else QApplication([])


def _main_window(tmp_path: Path) -> tuple[MainWindow, SettingsService]:
    _app()
    settings_service = SettingsService(config_root=tmp_path / "config")
    settings = settings_service.load()
    workspace_service = WorkspaceService(settings_service, settings)
    engine_registry = EngineRegistry(settings_service.app_paths)
    preset_service = PresetService(settings_service.app_paths)
    config_renderer = ConfigRenderer()
    profile_service = ProfileService(settings_service.app_paths, engine_registry, config_renderer)
    import_service = ImportService(engine_registry, profile_service)
    launcher_service = LauncherService()
    window = MainWindow(
        settings_service=settings_service,
        workspace_service=workspace_service,
        profile_service=profile_service,
        import_service=import_service,
        launcher_service=launcher_service,
        engine_registry=engine_registry,
        preset_service=preset_service,
    )
    return window, settings_service


def test_main_window_restores_persisted_icon_size(tmp_path: Path) -> None:
    settings_service = SettingsService(config_root=tmp_path / "config")
    settings = settings_service.load()
    settings.workspace_icon_size = 96
    settings_service.save(settings)

    window, _ = _main_window(tmp_path)

    assert window._view.iconSize().width() == 96


def test_main_window_resize_icons_persists_setting(tmp_path: Path) -> None:
    window, settings_service = _main_window(tmp_path)

    window._resize_icons(120)

    assert window._view.iconSize().width() == 72
    assert settings_service.load().workspace_icon_size == 72
