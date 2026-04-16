from __future__ import annotations

from pathlib import Path
import shutil
import subprocess


def launch_media_manager(media_dir: Path, game_dir: Path) -> None:
    dolphin = shutil.which("dolphin")
    if dolphin:
        subprocess.Popen(
            [dolphin, "--new-window", "--split", str(media_dir), str(game_dir)],
            start_new_session=True,
        )
        return
    opener = shutil.which("xdg-open")
    if opener:
        subprocess.Popen([opener, str(media_dir)], start_new_session=True)
        return
    raise FileNotFoundError(
        "Could not find Dolphin or xdg-open to open the media folder."
    )
