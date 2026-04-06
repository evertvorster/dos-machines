from pathlib import Path

from dos_machines.application.preset_service import PresetService
from dos_machines.application.settings_service import SettingsService


def test_section_and_machine_presets_round_trip(tmp_path: Path) -> None:
    settings_service = SettingsService(config_root=tmp_path / "config")
    settings_service.load()
    preset_service = PresetService(settings_service.app_paths)

    section = preset_service.save_section_preset(
        "Roland MIDI",
        "midi",
        {"mididevice": "mt32", "mpu401": "intelligent"},
    )
    machine = preset_service.save_machine_preset(
        "MT-32 Adventure",
        {
            "render": {"glshader": "crt-auto"},
            "midi": {"mididevice": "mt32", "mpu401": "intelligent"},
        },
    )

    sections = preset_service.load_section_presets()
    machines = preset_service.load_machine_presets()
    resolved = preset_service.resolve_machine_preset(machine.preset_id)

    assert any(item.preset_id == section.preset_id for item in sections)
    assert any(item.preset_id == machine.preset_id for item in machines)
    assert resolved["midi"]["mididevice"] == "mt32"


def test_engine_scoped_section_defaults_round_trip(tmp_path: Path) -> None:
    settings_service = SettingsService(config_root=tmp_path / "config")
    settings_service.load()
    preset_service = PresetService(settings_service.app_paths)

    preset_service.save_section_default("staging-a", "sdl", {"fullscreen": "true"})
    preset_service.save_section_default("staging-b", "sdl", {"fullscreen": "false"})

    assert preset_service.load_section_default("staging-a", "sdl") == {"fullscreen": "true"}
    assert preset_service.load_section_default("staging-b", "sdl") == {"fullscreen": "false"}
    assert preset_service.load_section_default("missing", "sdl") is None


def test_saving_section_preset_with_existing_title_updates_it(tmp_path: Path) -> None:
    settings_service = SettingsService(config_root=tmp_path / "config")
    settings_service.load()
    preset_service = PresetService(settings_service.app_paths)

    original = preset_service.save_section_preset("Roland MIDI", "midi", {"mididevice": "mt32"})
    updated = preset_service.save_section_preset("Roland MIDI", "midi", {"mididevice": "default"})

    presets = [preset for preset in preset_service.load_section_presets() if preset.section_name == "midi"]

    assert len(presets) == 1
    assert updated.preset_id == original.preset_id
    assert presets[0].sections["midi"]["mididevice"] == "default"


def test_saving_machine_preset_with_existing_title_updates_it(tmp_path: Path) -> None:
    settings_service = SettingsService(config_root=tmp_path / "config")
    settings_service.load()
    preset_service = PresetService(settings_service.app_paths)

    original = preset_service.save_machine_preset(
        "Adventure",
        {"midi": {"mididevice": "mt32"}},
    )
    updated = preset_service.save_machine_preset(
        "Adventure",
        {"midi": {"mididevice": "default"}, "render": {"glshader": "sharp"}},
    )

    machines = preset_service.load_machine_presets()
    sections = preset_service.load_section_presets()
    resolved = preset_service.resolve_machine_preset(updated.preset_id)

    assert len(machines) == 1
    assert updated.preset_id == original.preset_id
    assert resolved["midi"]["mididevice"] == "default"
    assert resolved["render"]["glshader"] == "sharp"
    assert all(not preset.title.startswith("Adventure / midi") or preset.sections["midi"]["mididevice"] == "default" for preset in sections)


def test_system_machine_presets_are_available_with_metadata(tmp_path: Path) -> None:
    settings_service = SettingsService(config_root=tmp_path / "config")
    settings_service.load()
    preset_service = PresetService(settings_service.app_paths)

    presets = preset_service.load_system_machine_presets()

    ids = {preset.preset_id for preset in presets}
    assert "ibm_pc_1981_cga_speaker" in ids
    assert "486_vga_sb_mt32" in ids
    assert all(preset.source == "system" for preset in presets)
    assert any(preset.key_facts for preset in presets)
    assert any(preset.description for preset in presets)


def test_saving_machine_preset_omits_sdl_section(tmp_path: Path) -> None:
    settings_service = SettingsService(config_root=tmp_path / "config")
    settings_service.load()
    preset_service = PresetService(settings_service.app_paths)

    preset = preset_service.save_machine_preset(
        "No SDL",
        {"sdl": {"fullscreen": "true"}, "midi": {"mididevice": "mt32"}},
    )

    resolved = preset_service.resolve_machine_preset(preset.preset_id)

    assert "sdl" not in resolved
    assert resolved["midi"]["mididevice"] == "mt32"


def test_resolving_legacy_machine_preset_ignores_sdl_section(tmp_path: Path) -> None:
    settings_service = SettingsService(config_root=tmp_path / "config")
    settings_service.load()
    preset_service = PresetService(settings_service.app_paths)

    preset_service._persist(
        {
            "section_defaults": {},
            "section_presets": [
                {
                    "preset_id": "section-a",
                    "title": "Legacy / sdl",
                    "section_name": "sdl",
                    "sections": {"sdl": {"fullscreen": "true"}},
                },
                {
                    "preset_id": "section-b",
                    "title": "Legacy / midi",
                    "section_name": "midi",
                    "sections": {"midi": {"mididevice": "default"}},
                },
            ],
            "machine_presets": [
                {
                    "preset_id": "machine-a",
                    "title": "Legacy",
                    "section_preset_ids": ["section-a", "section-b"],
                }
            ],
        }
    )

    resolved = preset_service.resolve_machine_preset("machine-a")

    assert "sdl" not in resolved
    assert resolved["midi"]["mididevice"] == "default"
