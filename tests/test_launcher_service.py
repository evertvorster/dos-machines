from pathlib import Path
from unittest.mock import patch

from dos_machines.application.launcher_service import LauncherService


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
