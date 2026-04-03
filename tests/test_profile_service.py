from pathlib import Path
import stat

from dos_machines.application.config_renderer import ConfigRenderer
from dos_machines.application.engine_registry import EngineRegistry
from dos_machines.application.launcher_service import LauncherService
from dos_machines.application.profile_service import CreateProfileRequest, ProfileService
from dos_machines.application.settings_service import SettingsService
from dos_machines.domain.models import OptionState


def _fake_binary(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = \"--list-glshaders\" ]; then\n"
        "  echo crt-auto\n"
        "  echo sharp\n"
        "  exit 0\n"
        "fi\n"
        "echo 'dosbox staging 0.81.0'\n",
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return path


def test_create_profile_writes_managed_files_and_launcher(tmp_path: Path) -> None:
    settings_service = SettingsService(config_root=tmp_path / "config")
    settings_service.load()
    engine_registry = EngineRegistry(settings_service.app_paths)
    profile_service = ProfileService(settings_service.app_paths, engine_registry, ConfigRenderer())
    launcher_service = LauncherService()

    game_dir = tmp_path / "games" / "keen4"
    workspace_dir = tmp_path / "workspace"
    binary = _fake_binary(tmp_path / "bin" / "dosbox")
    cache = engine_registry.register(binary)
    schema = engine_registry.load_schema(cache.ref.engine_id)
    option_states = {
        section.name: {
            option.name: OptionState(value=option.default_value, checked=True, origin="default")
            for option in section.options
        }
        for section in schema.sections
        if section.name != "autoexec"
    }

    request = CreateProfileRequest(
        title="Commander Keen 4",
        game_dir=game_dir,
        executable="KEEN4E.EXE",
        engine_binary=binary,
        workspace_dir=workspace_dir,
        option_states=option_states,
    )

    profile = profile_service.create(request)
    launcher = launcher_service.create_launcher(profile, workspace_dir)

    assert (game_dir / ".dosmachines" / "profile.json").exists()
    assert (game_dir / ".dosmachines" / "dosbox.conf").exists()
    assert launcher.exists()
    text = launcher.read_text(encoding="utf-8")
    assert "X-DOSMachines-ProfilePath" in text
    config_text = (game_dir / ".dosmachines" / "dosbox.conf").read_text(encoding="utf-8")
    assert "[sdl]" in config_text
    assert "KEEN4E.EXE" in config_text


def test_existing_profile_is_detected(tmp_path: Path) -> None:
    settings_service = SettingsService(config_root=tmp_path / "config")
    settings_service.load()
    engine_registry = EngineRegistry(settings_service.app_paths)
    profile_service = ProfileService(settings_service.app_paths, engine_registry, ConfigRenderer())
    binary = tmp_path / "dosbox"
    _fake_binary(binary)
    cache = engine_registry.register(binary)
    schema = engine_registry.load_schema(cache.ref.engine_id)

    request = CreateProfileRequest(
        title="DOOM",
        game_dir=tmp_path / "doom",
        executable="DOOM.EXE",
        engine_binary=binary,
        workspace_dir=tmp_path / "workspace",
        option_states={
            section.name: {
                option.name: OptionState(value=option.default_value, checked=True, origin="default")
                for option in section.options
            }
            for section in schema.sections
            if section.name != "autoexec"
        },
    )
    profile_service.create(request)

    existing = profile_service.existing_profile(tmp_path / "doom")
    assert existing is not None
    assert existing.identity.title == "DOOM"
