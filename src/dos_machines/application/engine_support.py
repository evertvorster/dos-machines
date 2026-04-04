from __future__ import annotations

from pathlib import Path
import subprocess


MANAGED_CONFIG_FILENAME = "dosbox.conf"


def display_name_for_engine(version: str | None = None) -> str:
    version_text = version.lower() if version is not None else ""
    if "staging" in version_text:
        return "DOSBox Staging"
    return "DOSBox"


def engine_id_prefix(version: str | None = None) -> str:
    version_text = version.lower() if version is not None else ""
    if "staging" in version_text:
        return "staging"
    return "dosbox"


def bundled_default_config_path() -> Path | None:
    candidates = [
        Path.home() / ".config" / "dosbox" / "dosbox-staging.conf",
        Path.home() / ".config" / "dosbox" / "dosbox.conf",
        Path("/usr/share/dos-machines/dosbox-staging.conf"),
        Path(__file__).resolve().parents[3] / "share" / "dos-machines" / "dosbox-staging.conf",
        Path(__file__).resolve().parents[3] / "examples" / "dosbox-staging.conf",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def detect_engine_version(binary_path: Path) -> str | None:
    resolved = binary_path.expanduser().resolve()
    try:
        completed = subprocess.run(
            [str(resolved), "--version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    output = (completed.stdout or completed.stderr).strip().splitlines()
    return output[0].strip() if output else None
