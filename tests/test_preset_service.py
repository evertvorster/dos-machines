from pathlib import Path

from dos_machines.application.preset_service import PresetService
from dos_machines.application.settings_service import SettingsService


def test_machine_presets_round_trip(tmp_path: Path) -> None:
    settings_service = SettingsService(config_root=tmp_path / "config")
    settings_service.load()
    preset_service = PresetService(settings_service.app_paths)

    machine = preset_service.save_machine_preset(
        "MT-32 Adventure",
        {
            "render": {"glshader": "crt-auto"},
            "midi": {"mididevice": "mt32", "mpu401": "intelligent"},
        },
    )

    machines = preset_service.load_machine_presets()
    resolved = preset_service.resolve_machine_preset(machine.preset_id)

    assert any(item.preset_id == machine.preset_id for item in machines)
    assert resolved["midi"]["mididevice"] == "mt32"


def test_engine_scoped_section_defaults_round_trip(tmp_path: Path) -> None:
    settings_service = SettingsService(config_root=tmp_path / "config")
    settings_service.load()
    preset_service = PresetService(settings_service.app_paths)

    preset_service.save_section_default("staging-a", "sdl", {"fullscreen": "true"})
    preset_service.save_section_default("staging-b", "sdl", {"fullscreen": "false"})

    assert preset_service.load_section_default("staging-a", "sdl") == {
        "fullscreen": "true"
    }
    assert preset_service.load_section_default("staging-b", "sdl") == {
        "fullscreen": "false"
    }
    assert preset_service.load_section_default("missing", "sdl") is None


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
    resolved = preset_service.resolve_machine_preset(updated.preset_id)

    assert len(machines) == 1
    assert updated.preset_id == original.preset_id
    assert resolved["midi"]["mididevice"] == "default"
    assert resolved["render"]["glshader"] == "sharp"
    assert machines[0].sections == {
        "midi": {"mididevice": "default"},
        "render": {"glshader": "sharp"},
    }


def test_system_machine_presets_are_available_with_metadata(tmp_path: Path) -> None:
    settings_service = SettingsService(config_root=tmp_path / "config")
    settings_service.load()
    preset_service = PresetService(settings_service.app_paths)

    presets = preset_service.load_system_machine_presets()

    ids = {preset.preset_id for preset in presets}
    assert "ibm_pc_1981_cga_speaker" in ids
    assert "ibm_pc_1981_hercules" in ids
    assert "vga_adlib_1987" in ids
    assert "386_vga_sb_1990" in ids
    assert "486_vga_sb_mt32" in ids
    assert "586_vga_sb_midi" in ids
    titles = {preset.preset_id: preset.title for preset in presets}
    assert titles["ibm_pc_1981_cga_speaker"] == (
        "1981 - IBM PC 5150 - CGA Mono - PC Speaker"
    )
    assert titles["vga_adlib_1987"] == (
        "1987 - 286/386 - SVGA S3 - AdLib / OPL2 + MT-32"
    )
    assert titles["586_vga_sb_midi"] == (
        "1993 - 586 / Pentium MMX - SVGA S3 - Sound Blaster + MIDI"
    )
    assert all(preset.source == "system" for preset in presets)
    assert any(preset.key_facts for preset in presets)
    assert any(preset.description for preset in presets)
    hercules = preset_service.resolve_machine_preset("ibm_pc_1981_hercules")
    assert hercules["dosbox"]["machine"] == "hercules"
    assert hercules["speaker"]["pcspeaker"] == "true"
    vga_adlib = preset_service.resolve_machine_preset("vga_adlib_1987")
    assert vga_adlib["midi"]["mpu401"] == "intelligent"
    assert vga_adlib["midi"]["mididevice"] == "mt32"
    standard_386 = preset_service.resolve_machine_preset("386_vga_sb_1990")
    assert standard_386["midi"]["mpu401"] == "intelligent"
    assert standard_386["midi"]["mididevice"] == "mt32"
    resolved = preset_service.resolve_machine_preset("486_vga_sb_mt32")
    assert resolved["cpu"]["cputype"] == "486"
    assert resolved["cpu"]["cpu_cycles"] == "25000"
    late_dos = preset_service.resolve_machine_preset("586_vga_sb_midi")
    assert late_dos["cpu"]["cputype"] == "pentium_mmx"
    assert late_dos["dosbox"]["machine"] == "svga_s3"
    assert late_dos["sblaster"]["sbtype"] == "sb16"
    assert late_dos["midi"]["mididevice"] == "fluidsynth"


def test_saving_machine_preset_omits_sdl_and_autoexec_sections(tmp_path: Path) -> None:
    settings_service = SettingsService(config_root=tmp_path / "config")
    settings_service.load()
    preset_service = PresetService(settings_service.app_paths)

    preset = preset_service.save_machine_preset(
        "No SDL",
        {
            "sdl": {"fullscreen": "true"},
            "autoexec": {"__text__": "mount c .\nc:"},
            "midi": {"mididevice": "mt32"},
        },
    )

    resolved = preset_service.resolve_machine_preset(preset.preset_id)

    assert "sdl" not in resolved
    assert "autoexec" not in resolved
    assert resolved["midi"]["mididevice"] == "mt32"
