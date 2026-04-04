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
        autoexec_text='mount c "C:\\GAMES\\KEEN4"\nc:\ncd \\',
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
    assert 'mount c "C:\\GAMES\\KEEN4"' in config_text
    assert "#              output:" in config_text
    profile_path = game_dir / ".dosmachines" / "profile.json"
    assert '"autoexec_text"' in profile_path.read_text(encoding="utf-8")


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


def test_autoexec_defaults_are_backfilled_for_existing_profiles(tmp_path: Path) -> None:
    settings_service = SettingsService(config_root=tmp_path / "config")
    settings_service.load()
    engine_registry = EngineRegistry(settings_service.app_paths)
    profile_service = ProfileService(settings_service.app_paths, engine_registry, ConfigRenderer())
    binary = _fake_binary(tmp_path / "bin" / "dosbox")
    cache = engine_registry.register(binary)
    schema = engine_registry.load_schema(cache.ref.engine_id)

    request = CreateProfileRequest(
        title="Prince of Persia",
        game_dir=tmp_path / "pop",
        executable="PRINCE.EXE",
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
    profile = profile_service.create(request)
    assert "PRINCE.EXE" in profile.autoexec_text


def test_updating_existing_profile_changes_title_without_new_machine_id(tmp_path: Path) -> None:
    settings_service = SettingsService(config_root=tmp_path / "config")
    settings_service.load()
    engine_registry = EngineRegistry(settings_service.app_paths)
    profile_service = ProfileService(settings_service.app_paths, engine_registry, ConfigRenderer())
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

    original = profile_service.create(
        CreateProfileRequest(
            title="Old Name",
            game_dir=tmp_path / "rename-me",
            executable="GAME.EXE",
            engine_binary=binary,
            workspace_dir=tmp_path / "workspace",
            option_states=option_states,
        )
    )

    updated = profile_service.create(
        CreateProfileRequest(
            title="New Name",
            game_dir=original.game.game_dir,
            executable=original.game.executable,
            engine_binary=original.engine.binary_path,
            workspace_dir=tmp_path / "workspace",
            option_states=original.option_states,
            autoexec_text=original.autoexec_text,
            existing_profile_path=original.game.game_dir / ".dosmachines" / "profile.json",
        )
    )

    assert updated.identity.title == "New Name"
    assert updated.identity.machine_id == original.identity.machine_id
    reloaded = profile_service.load(original.game.game_dir / ".dosmachines" / "profile.json")
    assert reloaded.identity.title == "New Name"


def test_delete_profile_keeps_generated_config(tmp_path: Path) -> None:
    settings_service = SettingsService(config_root=tmp_path / "config")
    settings_service.load()
    engine_registry = EngineRegistry(settings_service.app_paths)
    profile_service = ProfileService(settings_service.app_paths, engine_registry, ConfigRenderer())
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

    profile = profile_service.create(
        CreateProfileRequest(
            title="Delete Me",
            game_dir=tmp_path / "delete-me",
            executable="GAME.EXE",
            engine_binary=binary,
            workspace_dir=tmp_path / "workspace",
            option_states=option_states,
        )
    )

    managed_dir = profile.game.game_dir / ".dosmachines"
    profile_path = managed_dir / "profile.json"
    config_path = managed_dir / "dosbox.conf"

    profile_service.delete(profile_path)

    assert not profile_path.exists()
    assert config_path.exists()
    assert managed_dir.exists()
