from __future__ import annotations

from importlib import resources
from uuid import uuid4
import json

from dos_machines.application.config_text import parse_config_text
from dos_machines.domain.models import AppPaths, MachinePreset, SectionPreset
from dos_machines.domain.system_machine_presets import SYSTEM_MACHINE_PRESETS


EXCLUDED_MACHINE_PRESET_SECTIONS = {"sdl"}


class PresetService:
    def __init__(self, app_paths: AppPaths) -> None:
        self._app_paths = app_paths
        self._user_presets_path = self._app_paths.presets_root / "user-presets.json"

    def load_section_presets(self) -> list[SectionPreset]:
        payload = self._load_payload()
        return [SectionPreset.from_json(item) for item in payload.get("section_presets", [])]

    def load_machine_presets(self) -> list[MachinePreset]:
        payload = self._load_payload()
        return [self._normalize_machine_preset(MachinePreset.from_json(item)) for item in payload.get("machine_presets", [])]

    def load_user_machine_presets(self) -> list[MachinePreset]:
        return self.load_machine_presets()

    def load_system_machine_presets(self) -> list[MachinePreset]:
        return [self._normalize_machine_preset(preset) for preset in SYSTEM_MACHINE_PRESETS]

    def load_section_default(self, engine_id: str, section_name: str) -> dict[str, str] | None:
        payload = self._load_payload()
        defaults = payload.get("section_defaults", {})
        engine_defaults = defaults.get(engine_id, {})
        values = engine_defaults.get(section_name)
        return {key: str(value) for key, value in values.items()} if isinstance(values, dict) else None

    def save_section_default(self, engine_id: str, section_name: str, values: dict[str, str]) -> dict[str, str]:
        payload = self._load_payload()
        defaults = payload.setdefault("section_defaults", {})
        engine_defaults = defaults.setdefault(engine_id, {})
        engine_defaults[section_name] = dict(values)
        self._persist(payload)
        return dict(values)

    def save_section_preset(self, title: str, section_name: str, values: dict[str, str]) -> SectionPreset:
        payload = self._load_payload()
        presets = [SectionPreset.from_json(item) for item in payload.get("section_presets", [])]
        existing = next(
            (preset for preset in presets if preset.title == title and preset.section_name == section_name),
            None,
        )
        preset = SectionPreset(
            preset_id=existing.preset_id if existing is not None else f"section-{uuid4().hex[:12]}",
            title=title,
            section_name=section_name,
            sections={section_name: dict(values)},
        )
        if existing is not None:
            presets = [item for item in presets if item.preset_id != existing.preset_id]
        presets.append(preset)
        payload["section_presets"] = [item.to_json() for item in presets]
        self._persist(payload)
        return preset

    def save_machine_preset(
        self,
        title: str,
        section_values: dict[str, dict[str, str]],
    ) -> MachinePreset:
        payload = self._load_payload()
        section_presets = [SectionPreset.from_json(item) for item in payload.get("section_presets", [])]
        machine_presets = [MachinePreset.from_json(item) for item in payload.get("machine_presets", [])]
        existing_machine = next((preset for preset in machine_presets if preset.title == title), None)
        if existing_machine is not None:
            section_presets = [
                preset for preset in section_presets
                if preset.preset_id not in existing_machine.section_preset_ids
            ]
            machine_presets = [
                preset for preset in machine_presets
                if preset.preset_id != existing_machine.preset_id
            ]
        section_preset_ids: list[str] = []
        for section_name, values in section_values.items():
            if section_name in EXCLUDED_MACHINE_PRESET_SECTIONS:
                continue
            section_preset = SectionPreset(
                preset_id=f"section-{uuid4().hex[:12]}",
                title=f"{title} / {section_name}",
                section_name=section_name,
                sections={section_name: dict(values)},
            )
            section_presets.append(section_preset)
            section_preset_ids.append(section_preset.preset_id)

        machine_preset = MachinePreset(
            preset_id=existing_machine.preset_id if existing_machine is not None else f"machine-{uuid4().hex[:12]}",
            title=title,
            section_preset_ids=section_preset_ids,
            source="user",
        )
        machine_presets.append(machine_preset)
        payload["section_presets"] = [item.to_json() for item in section_presets]
        payload["machine_presets"] = [item.to_json() for item in machine_presets]
        self._persist(payload)
        return machine_preset

    def resolve_machine_preset(self, preset_id: str) -> dict[str, dict[str, str]]:
        section_presets = {preset.preset_id: preset for preset in self.load_section_presets()}
        machine_preset = self.get_machine_preset(preset_id)
        resolved: dict[str, dict[str, str]] = {}
        if machine_preset.source == "system":
            for section_name, values in self._load_system_machine_preset_sections(machine_preset.preset_id).items():
                resolved.setdefault(section_name, {}).update(values)
            return resolved
        if machine_preset.sections:
            for section_name, values in machine_preset.sections.items():
                if section_name in EXCLUDED_MACHINE_PRESET_SECTIONS:
                    continue
                resolved.setdefault(section_name, {}).update(values)
            return resolved
        for section_preset_id in machine_preset.section_preset_ids:
            section_preset = section_presets.get(section_preset_id)
            if section_preset is None:
                continue
            for section_name, values in section_preset.sections.items():
                if section_name in EXCLUDED_MACHINE_PRESET_SECTIONS:
                    continue
                resolved.setdefault(section_name, {}).update(values)
        return resolved

    def get_machine_preset(self, preset_id: str) -> MachinePreset:
        for preset in self.load_system_machine_presets():
            if preset.preset_id == preset_id:
                return preset
        for preset in self.load_user_machine_presets():
            if preset.preset_id == preset_id:
                return preset
        raise StopIteration(preset_id)

    def _load_payload(self) -> dict[str, object]:
        if not self._user_presets_path.exists():
            return {"section_presets": [], "machine_presets": [], "section_defaults": {}}
        return json.loads(self._user_presets_path.read_text(encoding="utf-8"))

    def _persist(self, payload: dict[str, object]) -> None:
        self._app_paths.presets_root.mkdir(parents=True, exist_ok=True)
        self._user_presets_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def _normalize_machine_preset(self, preset: MachinePreset) -> MachinePreset:
        return MachinePreset(
            preset_id=preset.preset_id,
            title=preset.title,
            section_preset_ids=list(preset.section_preset_ids),
            source=preset.source,
            tier=preset.tier,
            description=preset.description,
            key_facts=list(preset.key_facts),
            rationale=list(preset.rationale),
            sources=list(preset.sources),
            sections={
                section_name: dict(values)
                for section_name, values in preset.sections.items()
                if section_name not in EXCLUDED_MACHINE_PRESET_SECTIONS
            },
        )

    def _load_system_machine_preset_sections(self, preset_id: str) -> dict[str, dict[str, str]]:
        asset = resources.files("dos_machines").joinpath("assets", "system-presets", f"{preset_id}.conf")
        parsed_sections, _ = parse_config_text(asset.read_text(encoding="utf-8"))
        return {
            section_name: dict(values)
            for section_name, values in parsed_sections.items()
            if section_name not in EXCLUDED_MACHINE_PRESET_SECTIONS
        }
