from __future__ import annotations

from pathlib import Path
import subprocess


ENGINE_FAMILY_DOSBOX_X = "dosbox_x"
ENGINE_FAMILY_DOSBOX = "dosbox"


def detect_engine_family(binary_path: Path) -> str:
    resolved = binary_path.expanduser().resolve()
    name = resolved.name.lower()
    if "dosbox-x" in name:
        return ENGINE_FAMILY_DOSBOX_X
    version = detect_engine_version(resolved, detect_engine_family_from_name(resolved))
    if version is not None and "dosbox-x" in version.lower():
        return ENGINE_FAMILY_DOSBOX_X
    return ENGINE_FAMILY_DOSBOX


def detect_engine_family_from_name(binary_path: Path) -> str:
    return ENGINE_FAMILY_DOSBOX_X if "dosbox-x" in binary_path.name.lower() else ENGINE_FAMILY_DOSBOX


def display_name_for_engine(binary_path: Path, version: str | None = None) -> str:
    family = detect_engine_family_from_name(binary_path)
    version_text = version.lower() if version is not None else ""
    if family == ENGINE_FAMILY_DOSBOX_X or "dosbox-x" in version_text:
        return "DOSBox-X"
    if "staging" in version_text:
        return "DOSBox Staging"
    return "DOSBox"


def engine_id_prefix(binary_path: Path, version: str | None = None) -> str:
    family = detect_engine_family_from_name(binary_path)
    version_text = version.lower() if version is not None else ""
    if family == ENGINE_FAMILY_DOSBOX_X or "dosbox-x" in version_text:
        return "dosbox-x"
    if "staging" in version_text:
        return "staging"
    return "dosbox"


def managed_config_filename(binary_path: Path) -> str:
    return "dosbox-x.conf" if detect_engine_family_from_name(binary_path) == ENGINE_FAMILY_DOSBOX_X else "dosbox.conf"


def bundled_default_config_path(binary_path: Path) -> Path:
    examples_dir = Path(__file__).resolve().parents[3] / "examples"
    if detect_engine_family_from_name(binary_path) == ENGINE_FAMILY_DOSBOX_X:
        candidates = sorted(examples_dir.glob("dosbox-x*.conf"))
        if candidates:
            return candidates[-1]
        return examples_dir / "dosbox-x.conf"
    return examples_dir / "dosbox-staging.conf"


def detect_engine_version(binary_path: Path, family: str | None = None) -> str | None:
    resolved = binary_path.expanduser().resolve()
    selected_family = family or detect_engine_family_from_name(resolved)
    args = [str(resolved), "-version"] if selected_family == ENGINE_FAMILY_DOSBOX_X else [str(resolved), "--version"]
    try:
        completed = subprocess.run(
            args,
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    output = (completed.stdout or completed.stderr).strip().splitlines()
    return output[0].strip() if output else None


def dosbox_x_glshader_dir(binary_path: Path) -> Path | None:
    resolved = binary_path.expanduser().resolve()
    candidates = [
        resolved.parent.parent / "share" / "dosbox-x" / "glshaders",
        Path("/usr/share/dosbox-x/glshaders"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None
