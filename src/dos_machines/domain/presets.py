from __future__ import annotations

from typing import Any


BUILTIN_PRESETS: list[dict[str, Any]] = [
    {
        "preset_id": "blank",
        "title": "Blank Machine",
        "description": "Start from the engine defaults without a hardware preset.",
        "machine_defaults": {},
    },
    {
        "preset_id": "386-vga",
        "title": "386 VGA Machine",
        "description": "A practical baseline for many DOS VGA games.",
        "machine_defaults": {
            "cpu": {"core": "auto", "cycles": "auto"},
            "dosbox": {"machine": "svga_s3"},
            "sblaster": {"sbtype": "sb16"},
            "midi": {"mpu401": "intelligent", "mididevice": "default"},
        },
    },
    {
        "preset_id": "mt32-adventure",
        "title": "MT-32 Adventure Machine",
        "description": "Adventure-focused machine with MT-32 style defaults.",
        "machine_defaults": {
            "cpu": {"core": "auto", "cycles": "auto"},
            "dosbox": {"machine": "svga_s3"},
            "midi": {"mpu401": "intelligent", "mididevice": "mt32"},
            "sblaster": {"sbtype": "sbpro2"},
        },
    },
]
