from __future__ import annotations

import configparser
from pathlib import Path
import shlex
import subprocess

from dos_machines.application.engine_support import MANAGED_CONFIG_FILENAME
from dos_machines.domain.models import MachineProfile


class LauncherService:
    def __init__(self) -> None:
        self._current_process: subprocess.Popen | None = None

    def create_launcher(self, profile: MachineProfile, workspace_dir: Path) -> Path:
        workspace_dir.mkdir(parents=True, exist_ok=True)
        launcher_path = workspace_dir / f"{profile.identity.title}.desktop"
        return self._write_launcher(profile, launcher_path)

    def sync_launcher(
        self,
        profile: MachineProfile,
        workspace_dir: Path,
        previous_launcher_path: Path | None = None,
    ) -> Path:
        workspace_dir.mkdir(parents=True, exist_ok=True)
        launcher_path = workspace_dir / f"{profile.identity.title}.desktop"
        if previous_launcher_path is not None:
            previous_launcher_path = previous_launcher_path.expanduser().resolve()
        if (
            previous_launcher_path is not None
            and previous_launcher_path.exists()
            and previous_launcher_path != launcher_path
            and launcher_path.exists()
        ):
            raise FileExistsError(f"Launcher already exists: {launcher_path}")
        written_path = self._write_launcher(profile, launcher_path)
        if (
            previous_launcher_path is not None
            and previous_launcher_path.exists()
            and previous_launcher_path != written_path
        ):
            previous_launcher_path.unlink()
        return written_path

    def _write_launcher(self, profile: MachineProfile, launcher_path: Path) -> Path:
        config_path = profile.game.game_dir / ".dosmachines" / MANAGED_CONFIG_FILENAME
        working_dir = profile.game.game_dir / ".dosmachines"
        icon_path = profile.ui.icon_path
        icon_value = str(icon_path) if icon_path is not None else "applications-games"
        launcher_path.write_text(
            self._desktop_entry(profile, config_path, working_dir, icon_value),
            encoding="utf-8",
        )
        launcher_path.chmod(0o755)
        return launcher_path

    def _desktop_entry(
        self,
        profile: MachineProfile,
        config_path: Path,
        working_dir: Path,
        icon_value: str,
    ) -> str:
        exec_value = f'"{profile.engine.binary_path}" -conf "{config_path}"'
        lines = [
            "[Desktop Entry]",
            "Type=Application",
            f"Name={profile.identity.title}",
            f"Exec={exec_value}",
            f"Path={working_dir}",
            f"Icon={icon_value}",
            "Terminal=false",
            "Categories=Game;Emulator;",
            f"X-DOSMachines-ProfilePath={profile.game.game_dir / '.dosmachines' / 'profile.json'}",
            f"X-DOSMachines-MachineId={profile.identity.machine_id}",
            "",
        ]
        return "\n".join(lines)

    def launch_launcher(self, launcher_path: Path) -> subprocess.Popen:
        parser = configparser.ConfigParser(interpolation=None)
        parser.read(launcher_path, encoding="utf-8")
        if not parser.has_section("Desktop Entry"):
            raise ValueError(f"Invalid desktop entry: {launcher_path}")
        section = parser["Desktop Entry"]
        exec_value = section.get("Exec", "").strip()
        if not exec_value:
            raise ValueError(f"Desktop entry has no Exec line: {launcher_path}")
        working_dir = section.get("Path", "").strip() or None
        self._current_process = subprocess.Popen(
            shlex.split(exec_value),
            cwd=working_dir,
            start_new_session=True,
        )
        return self._current_process
