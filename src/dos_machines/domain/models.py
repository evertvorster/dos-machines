from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
import json


def _path_to_str(value: Path | None) -> str | None:
    return None if value is None else str(value)


def _path_from_str(value: str | None) -> Path | None:
    return None if value is None else Path(value)


@dataclass(slots=True)
class AppPaths:
    config_root: Path
    settings_path: Path
    engines_root: Path
    presets_root: Path
    icons_root: Path
    default_workspace: Path


@dataclass(slots=True)
class Settings:
    workspace_path: Path
    recent_workspaces: list[Path] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        return {
            "workspace_path": str(self.workspace_path),
            "recent_workspaces": [str(path) for path in self.recent_workspaces],
        }

    @classmethod
    def from_json(cls, payload: dict[str, Any], default_workspace: Path) -> "Settings":
        workspace_path = Path(payload.get("workspace_path", default_workspace))
        recent = [Path(path) for path in payload.get("recent_workspaces", [])]
        return cls(workspace_path=workspace_path, recent_workspaces=recent)


@dataclass(slots=True)
class EngineRef:
    engine_id: str
    binary_path: Path
    display_name: str
    version: str | None = None
    probe_status: str = "cached"

    def to_json(self) -> dict[str, Any]:
        return {
            "engine_id": self.engine_id,
            "binary_path": str(self.binary_path),
            "display_name": self.display_name,
            "version": self.version,
            "probe_status": self.probe_status,
        }

    @classmethod
    def from_json(cls, payload: dict[str, Any]) -> "EngineRef":
        return cls(
            engine_id=payload["engine_id"],
            binary_path=Path(payload["binary_path"]),
            display_name=payload["display_name"],
            version=payload.get("version"),
            probe_status=payload.get("probe_status", "cached"),
        )


@dataclass(slots=True)
class ProfileIdentity:
    machine_id: str
    title: str
    year: int | None = None
    notes: str = ""

    def to_json(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_json(cls, payload: dict[str, Any]) -> "ProfileIdentity":
        return cls(
            machine_id=payload["machine_id"],
            title=payload["title"],
            year=payload.get("year"),
            notes=payload.get("notes", ""),
        )


@dataclass(slots=True)
class PresetRef:
    preset_id: str
    start_mode: str

    def to_json(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_json(cls, payload: dict[str, Any]) -> "PresetRef":
        return cls(
            preset_id=payload["preset_id"],
            start_mode=payload["start_mode"],
        )


@dataclass(slots=True)
class GameTargets:
    game_dir: Path
    working_dir: Path
    executable: str
    setup_executable: str | None = None

    def to_json(self) -> dict[str, Any]:
        return {
            "game_dir": str(self.game_dir),
            "working_dir": str(self.working_dir),
            "executable": self.executable,
            "setup_executable": self.setup_executable,
        }

    @classmethod
    def from_json(cls, payload: dict[str, Any]) -> "GameTargets":
        return cls(
            game_dir=Path(payload["game_dir"]),
            working_dir=Path(payload["working_dir"]),
            executable=payload["executable"],
            setup_executable=payload.get("setup_executable"),
        )


@dataclass(slots=True)
class UiState:
    icon_path: Path | None = None
    advanced_mode: bool = False

    def to_json(self) -> dict[str, Any]:
        return {
            "icon_path": _path_to_str(self.icon_path),
            "advanced_mode": self.advanced_mode,
        }

    @classmethod
    def from_json(cls, payload: dict[str, Any]) -> "UiState":
        return cls(
            icon_path=_path_from_str(payload.get("icon_path")),
            advanced_mode=payload.get("advanced_mode", False),
        )


@dataclass(slots=True)
class Provenance:
    import_source_path: Path | None = None

    def to_json(self) -> dict[str, Any]:
        return {"import_source_path": _path_to_str(self.import_source_path)}

    @classmethod
    def from_json(cls, payload: dict[str, Any]) -> "Provenance":
        return cls(import_source_path=_path_from_str(payload.get("import_source_path")))


@dataclass(slots=True)
class MachineProfile:
    identity: ProfileIdentity
    engine: EngineRef
    preset: PresetRef
    game: GameTargets
    ui: UiState = field(default_factory=UiState)
    machine_overrides: dict[str, dict[str, Any]] = field(default_factory=dict)
    raw_overrides: dict[str, dict[str, str]] = field(default_factory=dict)
    provenance: Provenance = field(default_factory=Provenance)

    def to_json(self) -> dict[str, Any]:
        return {
            "identity": self.identity.to_json(),
            "engine": self.engine.to_json(),
            "preset": self.preset.to_json(),
            "game": self.game.to_json(),
            "ui": self.ui.to_json(),
            "machine_overrides": self.machine_overrides,
            "raw_overrides": self.raw_overrides,
            "provenance": self.provenance.to_json(),
        }

    @classmethod
    def from_json(cls, payload: dict[str, Any]) -> "MachineProfile":
        return cls(
            identity=ProfileIdentity.from_json(payload["identity"]),
            engine=EngineRef.from_json(payload["engine"]),
            preset=PresetRef.from_json(payload["preset"]),
            game=GameTargets.from_json(payload["game"]),
            ui=UiState.from_json(payload.get("ui", {})),
            machine_overrides=payload.get("machine_overrides", {}),
            raw_overrides=payload.get("raw_overrides", {}),
            provenance=Provenance.from_json(payload.get("provenance", {})),
        )

    def dumps(self) -> str:
        return json.dumps(self.to_json(), indent=2, sort_keys=True) + "\n"


@dataclass(slots=True)
class WorkspaceEntry:
    launcher_path: Path
    title: str
    profile_path: Path | None
    machine_id: str | None
    broken: bool = False
