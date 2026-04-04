from pathlib import Path
from unittest.mock import patch

from dos_machines.application.launcher_service import LauncherService
from dos_machines.domain.models import (
    EngineCapabilities,
    EngineRef,
    GameTargets,
    MachineProfile,
    PresetRef,
    ProfileIdentity,
    Provenance,
    UiState,
)


def _profile(tmp_path: Path, title: str) -> MachineProfile:
    game_dir = tmp_path / "games" / title.lower().replace(" ", "_")
    managed_dir = game_dir / ".dosmachines"
    managed_dir.mkdir(parents=True, exist_ok=True)
    return MachineProfile(
        identity=ProfileIdentity(machine_id="machine-1", title=title),
        engine=EngineRef(
            engine_id="engine-1",
            binary_path=Path("/usr/bin/dosbox"),
            display_name="DOSBox",
            capabilities=EngineCapabilities(),
        ),
        preset=PresetRef(preset_id="blank", start_mode="blank"),
        game=GameTargets(
            game_dir=game_dir,
            working_dir=game_dir,
            executable="GAME.EXE",
        ),
        ui=UiState(),
        provenance=Provenance(),
    )


def test_launch_launcher_runs_exec_in_desktop_entry_path(tmp_path: Path) -> None:
    launcher = tmp_path / "Test.desktop"
    workdir = tmp_path / "run"
    workdir.mkdir()
    launcher.write_text(
        "\n".join(
            [
                "[Desktop Entry]",
                "Type=Application",
                "Name=Test",
                'Exec="/usr/bin/dosbox" -conf "/tmp/test.conf"',
                f"Path={workdir}",
                "",
            ]
        ),
        encoding="utf-8",
    )

    service = LauncherService()
    with patch("subprocess.Popen") as popen:
        service.launch_launcher(launcher)

    args, kwargs = popen.call_args
    assert args[0] == ["/usr/bin/dosbox", "-conf", "/tmp/test.conf"]
    assert kwargs["cwd"] == str(workdir)


def test_launcher_without_exec_raises(tmp_path: Path) -> None:
    launcher = tmp_path / "Broken.desktop"
    launcher.write_text("[Desktop Entry]\nType=Application\nName=Broken\n", encoding="utf-8")
    service = LauncherService()
    try:
        service.launch_launcher(launcher)
    except ValueError as exc:
        assert "Exec" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Expected ValueError for missing Exec")


def test_sync_launcher_replaces_old_file_when_title_changes(tmp_path: Path) -> None:
    workspace_dir = tmp_path / "workspace"
    service = LauncherService()

    original = _profile(tmp_path, "Old Name")
    old_launcher = service.create_launcher(original, workspace_dir)

    renamed = _profile(tmp_path, "New Name")
    renamed.identity.machine_id = original.identity.machine_id
    renamed.game = original.game
    new_launcher = service.sync_launcher(renamed, workspace_dir, old_launcher)

    assert new_launcher == workspace_dir / "New Name.desktop"
    assert new_launcher.exists()
    assert not old_launcher.exists()
    assert "Name=New Name" in new_launcher.read_text(encoding="utf-8")


def test_launcher_uses_dosbox_x_config_name_for_dosbox_x_engines(tmp_path: Path) -> None:
    workspace_dir = tmp_path / "workspace"
    service = LauncherService()

    profile = _profile(tmp_path, "DOSBox X Game")
    profile.engine.binary_path = Path("/usr/bin/dosbox-x")

    launcher_path = service.create_launcher(profile, workspace_dir)

    assert '"/usr/bin/dosbox-x" -conf "' in launcher_path.read_text(encoding="utf-8")
    assert "dosbox-x.conf" in launcher_path.read_text(encoding="utf-8")
