from pathlib import Path

from dos_machines.application.settings_service import SettingsService


def test_settings_service_creates_default_workspace(tmp_path: Path) -> None:
    service = SettingsService(config_root=tmp_path)
    settings = service.load()

    assert settings.workspace_path == tmp_path / "dos-machines" / "workspace"
    assert settings.workspace_path.exists()
    assert service.app_paths.settings_path.exists()


def test_settings_service_persists_last_engine_binary_path(tmp_path: Path) -> None:
    service = SettingsService(config_root=tmp_path)
    settings = service.load()
    settings.last_engine_binary_path = Path("/usr/bin/dosbox")

    service.save(settings)
    reloaded = service.load()

    assert reloaded.last_engine_binary_path == Path("/usr/bin/dosbox")
