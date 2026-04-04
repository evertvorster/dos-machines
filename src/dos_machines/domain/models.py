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
    last_engine_binary_path: Path | None = None
    workspace_icon_size: int = 64

    def to_json(self) -> dict[str, Any]:
        return {
            "workspace_path": str(self.workspace_path),
            "recent_workspaces": [str(path) for path in self.recent_workspaces],
            "last_engine_binary_path": _path_to_str(self.last_engine_binary_path),
            "workspace_icon_size": self.workspace_icon_size,
        }

    @classmethod
    def from_json(cls, payload: dict[str, Any], default_workspace: Path) -> "Settings":
        workspace_path = Path(payload.get("workspace_path", default_workspace))
        recent = [Path(path) for path in payload.get("recent_workspaces", [])]
        return cls(
            workspace_path=workspace_path,
            recent_workspaces=recent,
            last_engine_binary_path=_path_from_str(payload.get("last_engine_binary_path")),
            workspace_icon_size=int(payload.get("workspace_icon_size", 64)),
        )


@dataclass(slots=True)
class EngineCapabilities:
    munt_available: bool = False
    fluidsynth_available: bool = False
    glshader_support: bool = False
    glshaders: list[str] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_json(cls, payload: dict[str, Any]) -> "EngineCapabilities":
        return cls(
            munt_available=payload.get("munt_available", False),
            fluidsynth_available=payload.get("fluidsynth_available", False),
            glshader_support=payload.get("glshader_support", False),
            glshaders=list(payload.get("glshaders", [])),
        )


@dataclass(slots=True)
class EngineRef:
    engine_id: str
    binary_path: Path
    display_name: str
    version: str | None = None
    probe_status: str = "cached"
    capabilities: EngineCapabilities = field(default_factory=EngineCapabilities)

    def to_json(self) -> dict[str, Any]:
        return {
            "engine_id": self.engine_id,
            "binary_path": str(self.binary_path),
            "display_name": self.display_name,
            "version": self.version,
            "probe_status": self.probe_status,
            "capabilities": self.capabilities.to_json(),
        }

    @classmethod
    def from_json(cls, payload: dict[str, Any]) -> "EngineRef":
        return cls(
            engine_id=payload["engine_id"],
            binary_path=Path(payload["binary_path"]),
            display_name=payload["display_name"],
            version=payload.get("version"),
            probe_status=payload.get("probe_status", "cached"),
            capabilities=EngineCapabilities.from_json(payload.get("capabilities", {})),
        )


@dataclass(slots=True)
class SchemaOption:
    section: str
    name: str
    default_value: str
    value_type: str
    description: str
    help_text: str
    comment_lines: list[str] = field(default_factory=list)
    choices: list[str] = field(default_factory=list)
    choice_help: dict[str, str] = field(default_factory=dict)
    runtime_dependent: bool = False

    def to_json(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_json(cls, payload: dict[str, Any]) -> "SchemaOption":
        return cls(
            section=payload["section"],
            name=payload["name"],
            default_value=payload["default_value"],
            value_type=payload["value_type"],
            description=payload.get("description", ""),
            help_text=payload.get("help_text", ""),
            comment_lines=list(payload.get("comment_lines", [])),
            choices=list(payload.get("choices", [])),
            choice_help=dict(payload.get("choice_help", {})),
            runtime_dependent=payload.get("runtime_dependent", False),
        )


@dataclass(slots=True)
class SchemaSection:
    name: str
    options: list[SchemaOption] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "options": [option.to_json() for option in self.options],
        }

    @classmethod
    def from_json(cls, payload: dict[str, Any]) -> "SchemaSection":
        return cls(
            name=payload["name"],
            options=[SchemaOption.from_json(item) for item in payload.get("options", [])],
        )


@dataclass(slots=True)
class EngineSchema:
    engine_id: str
    display_name: str
    sections: list[SchemaSection] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        return {
            "engine_id": self.engine_id,
            "display_name": self.display_name,
            "sections": [section.to_json() for section in self.sections],
        }

    @classmethod
    def from_json(cls, payload: dict[str, Any]) -> "EngineSchema":
        return cls(
            engine_id=payload["engine_id"],
            display_name=payload["display_name"],
            sections=[SchemaSection.from_json(item) for item in payload.get("sections", [])],
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
class OptionState:
    value: str
    checked: bool = False
    origin: str = "default"

    def to_json(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_json(cls, payload: dict[str, Any]) -> "OptionState":
        return cls(
            value=str(payload.get("value", "")),
            checked=payload.get("checked", False),
            origin=payload.get("origin", "default"),
        )


@dataclass(slots=True)
class MachineProfile:
    identity: ProfileIdentity
    engine: EngineRef
    preset: PresetRef
    game: GameTargets
    ui: UiState = field(default_factory=UiState)
    option_states: dict[str, dict[str, OptionState]] = field(default_factory=dict)
    autoexec_text: str = ""
    raw_overrides: dict[str, dict[str, str]] = field(default_factory=dict)
    provenance: Provenance = field(default_factory=Provenance)

    def to_json(self) -> dict[str, Any]:
        return {
            "identity": self.identity.to_json(),
            "engine": self.engine.to_json(),
            "preset": self.preset.to_json(),
            "game": self.game.to_json(),
            "ui": self.ui.to_json(),
            "option_states": {
                section: {name: state.to_json() for name, state in options.items()}
                for section, options in self.option_states.items()
            },
            "autoexec_text": self.autoexec_text,
            "raw_overrides": self.raw_overrides,
            "provenance": self.provenance.to_json(),
        }

    @classmethod
    def from_json(cls, payload: dict[str, Any]) -> "MachineProfile":
        option_states = {
            section: {
                name: OptionState.from_json(state_payload)
                for name, state_payload in options.items()
            }
            for section, options in payload.get("option_states", {}).items()
        }
        if not option_states and "machine_overrides" in payload:
            option_states = {
                section: {
                    name: OptionState(value=str(value), checked=True, origin="legacy")
                    for name, value in options.items()
                }
                for section, options in payload.get("machine_overrides", {}).items()
            }
        return cls(
            identity=ProfileIdentity.from_json(payload["identity"]),
            engine=EngineRef.from_json(payload["engine"]),
            preset=PresetRef.from_json(payload["preset"]),
            game=GameTargets.from_json(payload["game"]),
            ui=UiState.from_json(payload.get("ui", {})),
            option_states=option_states,
            autoexec_text=payload.get("autoexec_text", ""),
            raw_overrides=payload.get("raw_overrides", {}),
            provenance=Provenance.from_json(payload.get("provenance", {})),
        )

    def dumps(self) -> str:
        return json.dumps(self.to_json(), indent=2, sort_keys=True) + "\n"


@dataclass(slots=True)
class SectionPreset:
    preset_id: str
    title: str
    section_name: str
    sections: dict[str, dict[str, str]]

    def to_json(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_json(cls, payload: dict[str, Any]) -> "SectionPreset":
        return cls(
            preset_id=payload["preset_id"],
            title=payload["title"],
            section_name=payload["section_name"],
            sections={
                section: {name: str(value) for name, value in options.items()}
                for section, options in payload.get("sections", {}).items()
            },
        )


@dataclass(slots=True)
class MachinePreset:
    preset_id: str
    title: str
    section_preset_ids: list[str]

    def to_json(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_json(cls, payload: dict[str, Any]) -> "MachinePreset":
        return cls(
            preset_id=payload["preset_id"],
            title=payload["title"],
            section_preset_ids=list(payload.get("section_preset_ids", [])),
        )


@dataclass(slots=True)
class WorkspaceEntry:
    launcher_path: Path
    title: str
    profile_path: Path | None
    machine_id: str | None
    broken: bool = False
