from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4
import json
import shutil

from dos_machines.application.config_renderer import ConfigRenderer
from dos_machines.application.engine_registry import EngineRegistry
from dos_machines.application.engine_support import MANAGED_CONFIG_FILENAME
from dos_machines.domain.models import AppPaths, GameTargets, MachineProfile, OptionState, Provenance, UiState


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
    remove_icon: bool = False
    option_states: dict[str, dict[str, OptionState]] | None = None
    autoexec_text: str | None = None
    raw_overrides: dict[str, dict[str, str]] | None = None
    import_source_path: Path | None = None
    existing_profile_path: Path | None = None
    overwrite_existing: bool = False


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
        managed_dir = self.managed_dir(game_dir)
        return managed_dir / MANAGED_CONFIG_FILENAME

    def existing_profile(self, game_dir: Path) -> MachineProfile | None:
        profile_path = self.profile_path_for_game(game_dir)
        return self.load(profile_path) if profile_path.exists() else None

    def create(self, request: CreateProfileRequest) -> MachineProfile:
        game_dir = request.game_dir.expanduser().resolve()
        game_dir.mkdir(parents=True, exist_ok=True)
        managed_dir = self.managed_dir(game_dir)
        managed_dir.mkdir(parents=True, exist_ok=True)
        profile_path = managed_dir / "profile.json"
        if profile_path.exists() and request.existing_profile_path is None and not request.overwrite_existing:
            raise FileExistsError(f"Game is already registered: {profile_path}")

        engine_cache = self._engine_registry.register(request.engine_binary)
        schema = self._engine_registry.load_schema(engine_cache.ref.engine_id)
        existing_profile_path = request.existing_profile_path
        if existing_profile_path is None and request.overwrite_existing and profile_path.exists():
            existing_profile_path = profile_path
        existing = self.load(existing_profile_path) if existing_profile_path else None
        machine_id = existing.identity.machine_id if existing is not None else uuid4().hex
        working_dir = game_dir
        ui_state = existing.ui if existing is not None else UiState()
        provenance = existing.provenance if existing is not None else Provenance()
        if request.import_source_path is not None:
            provenance.import_source_path = request.import_source_path.expanduser().resolve()
        game_targets = GameTargets(
            game_dir=game_dir,
            working_dir=working_dir,
            executable=request.executable,
            setup_executable=request.setup_executable,
        )
        profile = MachineProfile(
            identity=self._build_identity(machine_id, request.title, request.notes),
            engine=engine_cache.ref,
            preset=self._build_preset(request.preset_id, request.start_mode),
            game=game_targets,
            ui=ui_state,
            provenance=provenance,
            option_states=request.option_states or self._default_option_states(schema),
            autoexec_text=(
                request.autoexec_text
                if request.autoexec_text is not None
                else existing.autoexec_text if existing is not None and existing.autoexec_text
                else self._config_renderer.default_autoexec_text(game_targets, engine_cache.ref.binary_path)
            ),
            raw_overrides=request.raw_overrides or (existing.raw_overrides if existing is not None else {}),
        )
        if request.remove_icon:
            self._delete_managed_icon(managed_dir, existing.ui.icon_path if existing is not None else None)
            profile.ui.icon_path = None
        elif request.icon_source is not None:
            self._delete_managed_icon(managed_dir, existing.ui.icon_path if existing is not None else None)
            icon_target = managed_dir / f"icon{request.icon_source.suffix.lower() or '.png'}"
            shutil.copyfile(request.icon_source, icon_target)
            profile.ui.icon_path = icon_target
        elif existing is not None and existing.ui.icon_path is not None:
            profile.ui.icon_path = self._resolve_existing_icon_path(existing.ui.icon_path, managed_dir)

        self.save(profile)
        return profile

    def save(self, profile: MachineProfile) -> None:
        managed_dir = self.managed_dir(profile.game.game_dir)
        managed_dir.mkdir(parents=True, exist_ok=True)
        profile_path = managed_dir / "profile.json"
        config_path = managed_dir / MANAGED_CONFIG_FILENAME
        schema = self._engine_registry.load_schema(profile.engine.engine_id)
        profile_path.write_text(profile.dumps(), encoding="utf-8")
        config_path.write_text(self._config_renderer.render(profile, schema), encoding="utf-8")

    def load(self, profile_path: Path) -> MachineProfile:
        payload = json.loads(profile_path.read_text(encoding="utf-8"))
        return MachineProfile.from_json(payload)

    def delete(self, profile_path: Path) -> None:
        resolved_profile_path = profile_path.expanduser().resolve()
        managed_dir = resolved_profile_path.parent
        existing = self.load(resolved_profile_path) if resolved_profile_path.exists() else None
        if resolved_profile_path.exists():
            resolved_profile_path.unlink()
        if existing is not None and existing.ui.icon_path is not None and existing.ui.icon_path.exists():
            self._delete_managed_icon(managed_dir, existing.ui.icon_path)
        try:
            managed_dir.rmdir()
        except OSError:
            pass

    def _delete_managed_icon(self, managed_dir: Path, icon_path: Path | None) -> None:
        if icon_path is None:
            return
        resolved = icon_path.expanduser().resolve()
        if resolved.parent == managed_dir and resolved.exists():
            resolved.unlink()

    def _resolve_existing_icon_path(self, icon_path: Path, managed_dir: Path) -> Path | None:
        resolved = icon_path.expanduser()
        candidate = managed_dir / resolved.name
        if resolved.parent != managed_dir and candidate.exists():
            return candidate
        if resolved.exists():
            return resolved
        if candidate.exists():
            return candidate
        managed_icons = sorted(managed_dir.glob("icon.*"))
        if managed_icons:
            return managed_icons[0]
        return None

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
