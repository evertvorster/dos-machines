from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from dos_machines.application.config_renderer import ConfigRenderer
from dos_machines.application.engine_registry import EngineRegistry
from dos_machines.application.launcher_service import LauncherService
from dos_machines.application.preset_service import PresetService
from dos_machines.application.profile_service import ProfileService
from dos_machines.application.settings_service import SettingsService
from dos_machines.application.workspace_service import WorkspaceService
from dos_machines.ui.main_window import MainWindow


def build_main_window() -> MainWindow:
    settings_service = SettingsService()
    settings = settings_service.load()
    workspace_service = WorkspaceService(settings_service, settings)
    engine_registry = EngineRegistry(settings_service.app_paths)
    preset_service = PresetService(settings_service.app_paths)
    config_renderer = ConfigRenderer()
    profile_service = ProfileService(settings_service.app_paths, engine_registry, config_renderer)
    launcher_service = LauncherService()
    return MainWindow(
        settings_service=settings_service,
        workspace_service=workspace_service,
        profile_service=profile_service,
        launcher_service=launcher_service,
        engine_registry=engine_registry,
        preset_service=preset_service,
    )


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("DOS Machines")
    window = build_main_window()
    window.show()
    return app.exec()
