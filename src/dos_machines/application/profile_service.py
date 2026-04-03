from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4
import json
import shutil

from dos_machines.application.config_renderer import ConfigRenderer
from dos_machines.application.engine_registry import EngineRegistry
from dos_machines.domain.models import AppPaths, GameTargets, MachineProfile, OptionState


@dataclass(slots=True)
class CreateProfileRequest:
    title: str
    game_dir: Path
    executable: str
    engine_binary: Path
    workspace_dir: Path
    preset_id: str = "blank"
    start_mode: str = "blank"
    setup_executable: str | None = None
    notes: str = ""
    icon_source: Path | None = None
    option_states: dict[str, dict[str, OptionState]] | None = None


class ProfileService:
    def __init__(
        self,
        app_paths: AppPaths,
        engine_registry: EngineRegistry,
        config_renderer: ConfigRenderer,
    ) -> None:
        self._app_paths = app_paths
        self._engine_registry = engine_registry
        self._config_renderer = config_renderer

    def managed_dir(self, game_dir: Path) -> Path:
        return game_dir / ".dosmachines"

    def profile_path_for_game(self, game_dir: Path) -> Path:
        return self.managed_dir(game_dir) / "profile.json"

    def config_path_for_game(self, game_dir: Path) -> Path:
        return self.managed_dir(game_dir) / "dosbox.conf"

    def existing_profile(self, game_dir: Path) -> MachineProfile | None:
        profile_path = self.profile_path_for_game(game_dir)
        return self.load(profile_path) if profile_path.exists() else None

    def create(self, request: CreateProfileRequest) -> MachineProfile:
        game_dir = request.game_dir.expanduser().resolve()
        game_dir.mkdir(parents=True, exist_ok=True)
        managed_dir = self.managed_dir(game_dir)
        managed_dir.mkdir(parents=True, exist_ok=True)
        profile_path = managed_dir / "profile.json"
        if profile_path.exists():
            raise FileExistsError(f"Game is already registered: {profile_path}")

        engine_cache = self._engine_registry.register(request.engine_binary)
        schema = self._engine_registry.load_schema(engine_cache.ref.engine_id)
        machine_id = uuid4().hex
        working_dir = game_dir
        profile = MachineProfile(
            identity=self._build_identity(machine_id, request.title, request.notes),
            engine=engine_cache.ref,
            preset=self._build_preset(request.preset_id, request.start_mode),
            game=GameTargets(
                game_dir=game_dir,
                working_dir=working_dir,
                executable=request.executable,
                setup_executable=request.setup_executable,
            ),
            option_states=request.option_states or self._default_option_states(schema),
        )
        if request.icon_source is not None:
            icon_target = managed_dir / "icon.png"
            shutil.copyfile(request.icon_source, icon_target)
            profile.ui.icon_path = icon_target

        self.save(profile)
        return profile

    def save(self, profile: MachineProfile) -> None:
        managed_dir = self.managed_dir(profile.game.game_dir)
        managed_dir.mkdir(parents=True, exist_ok=True)
        profile_path = managed_dir / "profile.json"
        config_path = managed_dir / "dosbox.conf"
        schema = self._engine_registry.load_schema(profile.engine.engine_id)
        profile_path.write_text(profile.dumps(), encoding="utf-8")
        config_path.write_text(self._config_renderer.render(profile, schema), encoding="utf-8")

    def load(self, profile_path: Path) -> MachineProfile:
        payload = json.loads(profile_path.read_text(encoding="utf-8"))
        return MachineProfile.from_json(payload)

    def _build_identity(self, machine_id: str, title: str, notes: str):
        from dos_machines.domain.models import ProfileIdentity

        return ProfileIdentity(machine_id=machine_id, title=title, notes=notes)

    def _build_preset(self, preset_id: str, start_mode: str):
        from dos_machines.domain.models import PresetRef

        return PresetRef(preset_id=preset_id, start_mode=start_mode)

    def _default_option_states(self, schema) -> dict[str, dict[str, OptionState]]:
        return {
            section.name: {
                option.name: OptionState(value=option.default_value, checked=False, origin="default")
                for option in section.options
            }
            for section in schema.sections
            if section.name != "autoexec"
        }
