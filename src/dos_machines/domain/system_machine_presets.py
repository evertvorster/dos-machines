from __future__ import annotations

from dos_machines.domain.models import MachinePreset


SYSTEM_MACHINE_PRESETS: list[MachinePreset] = [
    MachinePreset(
        preset_id="ibm_pc_1981_cga_speaker",
        title="1981 - IBM PC 5150 - CGA Mono - PC Speaker",
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
        preset_id="ibm_pc_1981_hercules",
        title="1981 - IBM PC - Hercules - PC Speaker",
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
        preset_id="ibm_xt_1983_cga_speaker",
        title="1983 - IBM PC/XT 5160 - CGA - PC Speaker",
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
        preset_id="ibm_pcjr_1983",
        title="1983 - IBM PCjr",
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
        title="1984 - Tandy 1000",
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
        title="1984 - IBM AT / 286 - EGA - PC Speaker",
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
        title="1987 - 286/386 - SVGA S3 - AdLib / OPL2 + MT-32",
        source="system",
        tier="Tier 4 - VGA Baseline",
        description="Late-1980s SVGA/VGA-compatible machine with AdLib-era FM sound and MT-32 MIDI support.",
        key_facts=[
            "CPU: 286/early 386 class",
            "Graphics: SVGA S3 / VGA-compatible",
            "Sound: AdLib / OPL2 FM plus Roland MT-32 MIDI",
        ],
        rationale=[
            "Fits the transition into VGA/SVGA with optional premium MIDI music.",
            "Useful for games where AdLib is the FM fallback and MT-32 is the preferred music target.",
        ],
        sources=[
            "IBM PS/2 VGA-era references",
            "AdLib support notes in late-1980s DOS games",
            "Roland MT-32 DOS compatibility references",
        ],
    ),
    MachinePreset(
        preset_id="386_vga_sb_1990",
        title="1987 - 386 - SVGA S3 - Sound Blaster + MT-32",
        source="system",
        tier="Tier 5 - Standard DOS",
        description="386-class DOS gaming setup with SVGA/VGA compatibility, Sound Blaster audio, and MT-32 MIDI support.",
        key_facts=[
            "CPU: 386-class",
            "Graphics: SVGA S3 / VGA-compatible",
            "Sound: Sound Blaster compatible digital audio plus Roland MT-32 MIDI",
        ],
        rationale=[
            "Represents the broad compatibility baseline for mainstream DOS gaming.",
            "Good default for VGA-era titles with Sound Blaster effects and MT-32 music.",
        ],
        sources=[
            "Common DOS game hardware requirements",
            "Sound Blaster compatibility references",
            "Roland MT-32 DOS compatibility references",
        ],
    ),
    MachinePreset(
        preset_id="486_vga_sb_mt32",
        title="1989 - 486 - SVGA S3 - Sound Blaster + MT-32",
        source="system",
        tier="Tier 6 - High-End DOS",
        description="Higher-end DOS setup with fast 486-class performance, SVGA/VGA compatibility, Sound Blaster effects, and MT-32 MIDI support.",
        key_facts=[
            "CPU: 486-class",
            "Graphics: SVGA S3 / VGA-compatible",
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
    MachinePreset(
        preset_id="586_vga_sb_midi",
        title="1993 - 586 / Pentium MMX - SVGA S3 - Sound Blaster + MIDI",
        source="system",
        tier="Tier 7 - Late DOS",
        description="Late DOS-era Pentium-class setup with SVGA/VGA compatibility, Sound Blaster 16 audio, and General MIDI through FluidSynth.",
        key_facts=[
            "CPU: Pentium MMX / 586-class",
            "Graphics: SVGA S3 / VGA-compatible",
            "Sound: Sound Blaster 16 plus General MIDI",
        ],
        rationale=[
            "Targets late DOS titles that benefit from Pentium-class performance and SB16-era digital audio.",
            "Useful for games where General MIDI is the preferred music path rather than MT-32.",
        ],
        sources=[
            "Intel Pentium processor release references",
            "Intel Pentium processor with MMX technology references",
            "Late DOS game hardware requirement references",
        ],
    ),
]
