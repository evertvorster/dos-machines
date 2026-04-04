from pathlib import Path
import stat

from dos_machines.application.engine_registry import EngineRegistry
from dos_machines.application.settings_service import SettingsService


def _fake_binary(path: Path, version_output: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = \"--list-glshaders\" ]; then\n"
        "  echo crt-auto\n"
        "  echo sharp\n"
        "  exit 0\n"
        "fi\n"
        f"echo '{version_output}'\n",
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return path


def test_register_dosbox_staging_keeps_cli_shader_probe(tmp_path: Path) -> None:
    settings_service = SettingsService(config_root=tmp_path / "config")
    settings_service.load()
    engine_registry = EngineRegistry(settings_service.app_paths)
    binary = _fake_binary(tmp_path / "bin" / "dosbox", "dosbox-staging, version 0.82.2")

    cache = engine_registry.register(binary)

    assert cache.ref.display_name == "DOSBox Staging"
    assert cache.ref.engine_id.startswith("staging-")
    assert cache.ref.capabilities.glshaders == ["crt-auto", "sharp"]
    assert cache.default_conf_path.read_text(encoding="utf-8").startswith("# This is the configuration file for DOSBox Staging")
