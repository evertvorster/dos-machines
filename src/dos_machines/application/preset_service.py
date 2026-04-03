from __future__ import annotations

from pathlib import Path
from uuid import uuid4
import json

from dos_machines.domain.models import AppPaths, GraphicsPreset


GRAPHICS_SECTIONS = {"sdl", "render"}


class PresetService:
    def __init__(self, app_paths: AppPaths) -> None:
        self._app_paths = app_paths
        self._user_presets_path = self._app_paths.presets_root / "user-presets.json"

    def load_graphics_presets(self) -> list[GraphicsPreset]:
        if not self._user_presets_path.exists():
            return []
        payload = json.loads(self._user_presets_path.read_text(encoding="utf-8"))
        return [GraphicsPreset.from_json(item) for item in payload.get("graphics_presets", [])]

    def save_graphics_preset(self, title: str, option_states: dict[str, dict[str, str]]) -> GraphicsPreset:
        presets = self.load_graphics_presets()
        preset = GraphicsPreset(
            preset_id=f"graphics-{uuid4().hex[:12]}",
            title=title,
            sections={
                section: dict(values)
                for section, values in option_states.items()
                if section in GRAPHICS_SECTIONS
            },
        )
        presets.append(preset)
        self._persist(presets)
        return preset

    def _persist(self, presets: list[GraphicsPreset]) -> None:
        self._app_paths.presets_root.mkdir(parents=True, exist_ok=True)
        self._user_presets_path.write_text(
            json.dumps(
                {"graphics_presets": [preset.to_json() for preset in presets]},
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
