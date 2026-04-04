from pathlib import Path

from dos_machines.application import engine_support


def test_bundled_default_config_path_exists_in_repo() -> None:
    path = engine_support.bundled_default_config_path()

    assert path is not None
    assert path.name == "dosbox-staging.conf"
    assert path.exists()


def test_bundled_default_config_path_prefers_user_config(monkeypatch, tmp_path: Path) -> None:
    home = tmp_path / "home"
    user_config = home / ".config" / "dosbox" / "dosbox-staging.conf"
    user_config.parent.mkdir(parents=True)
    user_config.write_text("# user config\n", encoding="utf-8")

    monkeypatch.setattr(engine_support.Path, "home", lambda: home)

    path = engine_support.bundled_default_config_path()

    assert path == user_config
