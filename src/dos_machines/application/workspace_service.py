from __future__ import annotations

import configparser
from pathlib import Path

from dos_machines.application.settings_service import SettingsService
from dos_machines.domain.models import Settings, WorkspaceEntry


class WorkspaceService:
    def __init__(self, settings_service: SettingsService, settings: Settings) -> None:
        self._settings_service = settings_service
        self._settings = settings

    @property
    def workspace_path(self) -> Path:
        return self._settings.workspace_path

    def ensure_workspace(self) -> Path:
        self.workspace_path.mkdir(parents=True, exist_ok=True)
        return self.workspace_path

    def set_workspace(self, path: Path) -> None:
        workspace = path.expanduser().resolve()
        workspace.mkdir(parents=True, exist_ok=True)
        recents = [workspace] + [item for item in self._settings.recent_workspaces if item != workspace]
        self._settings.workspace_path = workspace
        self._settings.recent_workspaces = recents[:10]
        self._settings_service.save(self._settings)

    def create_folder(self, parent: Path, name: str) -> Path:
        folder = parent / name
        folder.mkdir(parents=True, exist_ok=False)
        return folder

    def scan_launchers(self) -> list[WorkspaceEntry]:
        self.ensure_workspace()
        entries: list[WorkspaceEntry] = []
        for launcher in self.workspace_path.rglob("*.desktop"):
            entries.append(self.read_launcher_entry(launcher))
        return sorted(entries, key=lambda item: item.title.lower())

    def read_launcher_entry(self, launcher_path: Path) -> WorkspaceEntry:
        parser = configparser.ConfigParser(interpolation=None)
        parser.read(launcher_path, encoding="utf-8")
        section = parser["Desktop Entry"] if parser.has_section("Desktop Entry") else {}
        title = section.get("Name", launcher_path.stem)
        profile_value = section.get("X-DOSMachines-ProfilePath")
        machine_id = section.get("X-DOSMachines-MachineId")
        icon_value = section.get("Icon")
        profile_path = Path(profile_value) if profile_value else None
        icon_path = None
        if icon_value and "/" in icon_value:
            icon_path = Path(icon_value).expanduser()
        broken = profile_path is not None and not profile_path.exists()
        return WorkspaceEntry(
            launcher_path=launcher_path,
            title=title,
            profile_path=profile_path,
            machine_id=machine_id,
            icon_path=icon_path,
            broken=broken,
        )
