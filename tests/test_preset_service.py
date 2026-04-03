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
