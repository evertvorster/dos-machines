from pathlib import Path

from dos_machines.application.settings_service import SettingsService
from dos_machines.application.workspace_service import WorkspaceService


def _workspace_service(tmp_path: Path) -> WorkspaceService:
    settings_service = SettingsService(config_root=tmp_path / "config")
    settings = settings_service.load()
    return WorkspaceService(settings_service, settings)


def test_read_launcher_entry_marks_missing_profile_as_broken(tmp_path: Path) -> None:
    service = _workspace_service(tmp_path)
    launcher = service.workspace_path / "Broken.desktop"
    launcher.write_text(
        "\n".join(
            [
                "[Desktop Entry]",
                "Type=Application",
                "Name=Broken",
                'Exec="/usr/bin/dosbox" -conf "/tmp/test.conf"',
                f"X-DOSMachines-ProfilePath={tmp_path / 'missing' / '.dosmachines' / 'profile.json'}",
                "",
            ]
        ),
        encoding="utf-8",
    )

    entry = service.read_launcher_entry(launcher)

    assert entry.broken is True
    assert entry.title == "Broken"
    assert entry.exec_value == '"/usr/bin/dosbox" -conf "/tmp/test.conf"'


def test_read_launcher_entry_marks_missing_icon_path_as_broken(tmp_path: Path) -> None:
    service = _workspace_service(tmp_path)
    launcher = service.workspace_path / "Broken.desktop"
    profile_path = tmp_path / "game" / ".dosmachines" / "profile.json"
    profile_path.parent.mkdir(parents=True)
    profile_path.write_text("{}", encoding="utf-8")
    launcher.write_text(
        "\n".join(
            [
                "[Desktop Entry]",
                "Type=Application",
                "Name=Broken",
                f"X-DOSMachines-ProfilePath={profile_path}",
                f"Icon={tmp_path / 'missing-icon.png'}",
                f"Path={tmp_path / 'game' / '.dosmachines'}",
                "",
            ]
        ),
        encoding="utf-8",
    )

    entry = service.read_launcher_entry(launcher)

    assert entry.broken is True
    assert entry.working_dir == tmp_path / "game" / ".dosmachines"
    assert entry.icon_path == tmp_path / "missing-icon.png"
