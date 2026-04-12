from __future__ import annotations

from dos_machines.domain.models import MachinePreset


SYSTEM_MACHINE_PRESETS: list[MachinePreset] = [
    MachinePreset(
        preset_id="ibm_pc_1981_cga_speaker",
        title="IBM PC 5150 (1981)",
        source="system",
        tier="Tier 1 - Early PC",
        description="Baseline IBM PC configuration for the earliest CGA-era DOS software.",
        key_facts=[
            "CPU: Intel 8088 at 4.77 MHz",
            "Graphics: CGA, 320x200 4-color baseline",
            "Sound: PC speaker only",
        ],
        rationale=[
            "Targets software that depends on original IBM PC timing.",
            "Useful when composite/CGA-era color behavior is part of the experience.",
        ],
        sources=[
            "IBM Personal Computer 5150 technical specifications",
            "Period IBM PC/CGA compatibility references",
        ],
    ),
    MachinePreset(
        preset_id="ibm_xt_1983_cga_speaker",
        title="IBM PC/XT 5160 (1983)",
        source="system",
        tier="Tier 1 - Early PC",
        description="IBM XT-class CGA machine for early hard-disk-era DOS titles and utilities.",
        key_facts=[
            "CPU: Intel 8088 at 4.77 MHz",
            "Graphics: CGA or MDA class, CGA-focused preset",
            "Sound: PC speaker only",
        ],
        rationale=[
            "Represents the common CGA + speaker baseline before PCjr/Tandy and EGA adoption.",
            "Best for software tuned for XT-era CPU speed without later audio hardware.",
        ],
        sources=[
            "IBM Personal Computer XT 5160 specifications",
            "DOS compatibility notes for XT-class systems",
        ],
    ),
    MachinePreset(
        preset_id="ibm_pc_1981_hercules",
        title="IBM PC Hercules (1981)",
        source="system",
        tier="Tier 1 - Early PC",
        description="Early IBM PC-class monochrome machine for software that expects Hercules graphics or business-PC display behavior.",
        key_facts=[
            "CPU: Intel 8088 at 4.77 MHz",
            "Graphics: Hercules monochrome, 720x348 high-resolution text/graphics",
            "Sound: PC speaker only",
        ],
        rationale=[
            "Targets titles and utilities with native Hercules support.",
            "Represents the common monochrome business-PC branch alongside CGA-era XT systems.",
        ],
        sources=[
            "Hercules Graphics Card technical references",
            "DOS compatibility notes for Hercules-capable software",
        ],
    ),
    MachinePreset(
        preset_id="ibm_pcjr_1983",
        title="IBM PCjr (1983)",
        source="system",
        tier="Tier 2 - Home PC Variants",
        description="PCjr-compatible preset for software that expects PCjr graphics and audio behavior.",
        key_facts=[
            "CPU: Intel 8088 class",
            "Graphics: PCjr/Tandy video modes",
            "Sound: 3-voice PCjr audio plus speaker behavior",
        ],
        rationale=[
            "Intended for titles with explicit PCjr support.",
            "Covers software that needs PCjr graphics or enhanced home-PC audio.",
        ],
        sources=[
            "IBM PCjr hardware references",
            "DOSBox machine-type compatibility notes",
        ],
    ),
    MachinePreset(
        preset_id="tandy_1000_1984",
        title="Tandy 1000 (1984)",
        source="system",
        tier="Tier 2 - Home PC Variants",
        description="Tandy 1000-style preset for titles that benefit from Tandy graphics and 3-voice sound.",
        key_facts=[
            "CPU: 8088-class home PC",
            "Graphics: Tandy/PCjr compatible video modes",
            "Sound: Tandy 3-voice audio",
        ],
        rationale=[
            "Useful for games with native Tandy enhancements.",
            "Captures the common home-PC branch distinct from IBM business machines.",
        ],
        sources=[
            "Tandy 1000 family references",
            "DOS game Tandy support documentation",
        ],
    ),
    MachinePreset(
        preset_id="ibm_at_1984_ega",
        title="IBM AT EGA (1984)",
        source="system",
        tier="Tier 3 - 16-bit Transition",
        description="Early 16-bit AT-class machine with EGA graphics and speaker-era audio baseline.",
        key_facts=[
            "CPU: 80286-class system",
            "Graphics: EGA",
            "Sound: PC speaker baseline",
        ],
        rationale=[
            "Targets the transition period before VGA and Sound Blaster became standard.",
            "Fits software that benefits from EGA while remaining pre-AdLib/SB focused.",
        ],
        sources=[
            "IBM Personal Computer AT references",
            "EGA-era DOS hardware compatibility notes",
        ],
    ),
    MachinePreset(
        preset_id="vga_adlib_1987",
        title="VGA + AdLib (1987)",
        source="system",
        tier="Tier 4 - VGA Baseline",
        description="Late-1980s VGA machine with AdLib-era FM sound and no Sound Blaster digitized audio.",
        key_facts=[
            "CPU: 286/early 386 class",
            "Graphics: VGA",
            "Sound: AdLib / OPL2 FM",
        ],
        rationale=[
            "Fits the transition into VGA before Sound Blaster became the common denominator.",
            "Useful for games where AdLib is the intended music target.",
        ],
        sources=[
            "IBM PS/2 VGA-era references",
            "AdLib support notes in late-1980s DOS games",
        ],
    ),
    MachinePreset(
        preset_id="386_vga_sb_1990",
        title="386 VGA Sound Blaster (1990)",
        source="system",
        tier="Tier 5 - Standard DOS",
        description="Conventional early-1990s DOS gaming baseline with 386-class performance, VGA, and Sound Blaster audio.",
        key_facts=[
            "CPU: 386-class",
            "Graphics: VGA",
            "Sound: Sound Blaster compatible digital + FM audio",
        ],
        rationale=[
            "Represents the broad compatibility baseline for mainstream DOS gaming.",
            "Good default for many VGA-era titles when no special hardware target is known.",
        ],
        sources=[
            "Common 1990 DOS game hardware requirements",
            "Sound Blaster compatibility references",
        ],
    ),
    MachinePreset(
        preset_id="486_vga_sb_mt32",
        title="486 VGA Sound Blaster + MT-32",
        source="system",
        tier="Tier 6 - High-End DOS",
        description="Higher-end DOS setup with fast 486-class performance, VGA, Sound Blaster effects, and MT-32 MIDI support.",
        key_facts=[
            "CPU: 486-class",
            "Graphics: VGA",
            "Sound: Sound Blaster plus Roland MT-32 MIDI",
        ],
        rationale=[
            "Targets premium DOS setups used for late adventure, simulation, and multi-device audio support.",
            "Useful when MT-32 is the preferred music path alongside SB effects.",
        ],
        sources=[
            "Roland MT-32 DOS compatibility references",
            "Typical high-end DOS gaming hardware guides",
        ],
    ),
]
