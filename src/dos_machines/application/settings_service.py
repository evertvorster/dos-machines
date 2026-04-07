from __future__ import annotations

from pathlib import Path
import json
import os

from dos_machines.domain.models import AppPaths, Settings


class SettingsService:
    def __init__(self, config_root: Path | None = None) -> None:
        base_root = config_root or Path(
            os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")
        )
        config_dir = base_root / "dos-machines"
        self.app_paths = AppPaths(
            config_root=config_dir,
            settings_path=config_dir / "settings.json",
            engines_root=config_dir / "engines",
            presets_root=config_dir / "presets",
            default_workspace=config_dir / "workspace",
        )

    def ensure_layout(self) -> None:
        self.app_paths.config_root.mkdir(parents=True, exist_ok=True)
        self.app_paths.engines_root.mkdir(parents=True, exist_ok=True)
        self.app_paths.presets_root.mkdir(parents=True, exist_ok=True)
        self.app_paths.default_workspace.mkdir(parents=True, exist_ok=True)

    def load(self) -> Settings:
        self.ensure_layout()
        if not self.app_paths.settings_path.exists():
            settings = Settings(workspace_path=self.app_paths.default_workspace)
            self.save(settings)
            return settings

        payload = json.loads(self.app_paths.settings_path.read_text(encoding="utf-8"))
        settings = Settings.from_json(payload, self.app_paths.default_workspace)
        settings.workspace_path.mkdir(parents=True, exist_ok=True)
        return settings

    def save(self, settings: Settings) -> None:
        self.ensure_layout()
        settings.workspace_path.mkdir(parents=True, exist_ok=True)
        self.app_paths.settings_path.write_text(
            json.dumps(settings.to_json(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
