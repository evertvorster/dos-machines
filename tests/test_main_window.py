from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication

from dos_machines.application.config_renderer import ConfigRenderer
from dos_machines.application.engine_registry import EngineRegistry
from dos_machines.application.import_service import ImportService
from dos_machines.application.launcher_service import LauncherService
from dos_machines.application.preset_service import PresetService
from dos_machines.application.profile_service import CreateProfileRequest, ProfileService
from dos_machines.application.settings_service import SettingsService
from dos_machines.application.workspace_service import WorkspaceService
from dos_machines.domain.models import OptionState
from dos_machines.ui.main_window import MainWindow


def _app() -> QApplication:
    app = QApplication.instance()
    return app if app is not None else QApplication([])


def _main_window(tmp_path: Path) -> tuple[MainWindow, SettingsService]:
    _app()
    settings_service = SettingsService(config_root=tmp_path / "config")
    settings = settings_service.load()
    workspace_service = WorkspaceService(settings_service, settings)
    engine_registry = EngineRegistry(settings_service.app_paths)
    preset_service = PresetService(settings_service.app_paths)
    config_renderer = ConfigRenderer()
    profile_service = ProfileService(settings_service.app_paths, engine_registry, config_renderer)
    import_service = ImportService(engine_registry, profile_service)
    launcher_service = LauncherService()
    window = MainWindow(
        settings_service=settings_service,
        workspace_service=workspace_service,
        profile_service=profile_service,
        import_service=import_service,
        launcher_service=launcher_service,
        engine_registry=engine_registry,
        preset_service=preset_service,
    )
    return window, settings_service


def test_main_window_restores_persisted_icon_size(tmp_path: Path) -> None:
    settings_service = SettingsService(config_root=tmp_path / "config")
    settings = settings_service.load()
    settings.workspace_icon_size = 96
    settings_service.save(settings)

    window, _ = _main_window(tmp_path)

    assert window._view.iconSize().width() == 96


def test_main_window_resize_icons_persists_setting(tmp_path: Path) -> None:
    window, settings_service = _main_window(tmp_path)

    window._resize_icons(120)

    assert window._view.iconSize().width() == 72
    assert settings_service.load().workspace_icon_size == 72


def test_main_window_resize_icons_clamps_to_new_maximum(tmp_path: Path) -> None:
    window, settings_service = _main_window(tmp_path)

    for _ in range(40):
        window._resize_icons(120)

    assert window._view.iconSize().width() == 256
    assert settings_service.load().workspace_icon_size == 256


def test_main_window_inherits_application_icon(tmp_path: Path) -> None:
    app = _app()
    original_icon = app.windowIcon()
    test_icon = app.style().standardIcon(app.style().StandardPixmap.SP_ComputerIcon)
    app.setWindowIcon(test_icon)
    try:
        window, _ = _main_window(tmp_path)
        assert not window.windowIcon().isNull()
        assert window.windowIcon().cacheKey() == test_icon.cacheKey()
    finally:
        app.setWindowIcon(original_icon)


def test_main_window_uses_warning_icon_for_broken_launcher(tmp_path: Path) -> None:
    settings_service = SettingsService(config_root=tmp_path / "config")
    settings = settings_service.load()
    launcher = settings.workspace_path / "Broken.desktop"
    launcher.write_text(
        "\n".join(
            [
                "[Desktop Entry]",
                "Type=Application",
                "Name=Broken",
                f"X-DOSMachines-ProfilePath={tmp_path / 'missing' / '.dosmachines' / 'profile.json'}",
                f"Icon={tmp_path / 'missing-icon.png'}",
                "",
            ]
        ),
        encoding="utf-8",
    )

    window, _ = _main_window(tmp_path)
    window._list_model.set_current_dir(settings.workspace_path)
    QApplication.processEvents()
    index = window._list_model.index(0, 0)
    icon = window._list_model.data(index, Qt.ItemDataRole.DecorationRole)
    warning_icon = QApplication.style().standardIcon(window.style().StandardPixmap.SP_MessageBoxWarning)

    assert icon is not None
    assert not icon.isNull()
    assert icon.pixmap(16, 16).toImage() == warning_icon.pixmap(16, 16).toImage()


def _machine_launcher(tmp_path: Path):
    settings_service = SettingsService(config_root=tmp_path / "config")
    settings_service.load()
    engine_registry = EngineRegistry(settings_service.app_paths)
    preset_service = PresetService(settings_service.app_paths)
    profile_service = ProfileService(settings_service.app_paths, engine_registry, ConfigRenderer())
    launcher_service = LauncherService()
    binary = tmp_path / "bin" / "dosbox"
    binary.parent.mkdir(parents=True, exist_ok=True)
    binary.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = \"--list-glshaders\" ]; then\n"
        "  echo crt-auto\n"
        "  echo sharp\n"
        "  exit 0\n"
        "fi\n"
        "echo 'dosbox staging 0.81.0'\n",
        encoding="utf-8",
    )
    binary.chmod(binary.stat().st_mode | 0o111)
    cache = engine_registry.register(binary)
    schema = engine_registry.load_schema(cache.ref.engine_id)
    profile = profile_service.create(
        CreateProfileRequest(
            title="Media Game",
            game_dir=tmp_path / "game",
            executable="GAME.EXE",
            engine_binary=binary,
            workspace_dir=settings_service.load().workspace_path,
            option_states={
                section.name: {
                    option.name: OptionState(value=option.default_value, checked=True, origin="default")
                    for option in section.options
                }
                for section in schema.sections
                if section.name != "autoexec"
            },
        )
    )
    launcher = launcher_service.create_launcher(profile, settings_service.load().workspace_path)
    return launcher, profile, settings_service


def test_open_machine_media_creates_media_dir_and_uses_dolphin(tmp_path: Path, monkeypatch) -> None:
    launcher, profile, _ = _machine_launcher(tmp_path)
    window, _ = _main_window(tmp_path)
    media_dir = profile.game.game_dir / ".dosmachines" / "media"

    monkeypatch.setattr("dos_machines.ui.media.shutil.which", lambda name: "/usr/bin/dolphin" if name == "dolphin" else None)
    with patch("dos_machines.ui.media.subprocess.Popen") as popen:
        window._open_machine_media(launcher)

    assert media_dir.exists()
    args, kwargs = popen.call_args
    assert args[0] == [
        "/usr/bin/dolphin",
        "--new-window",
        "--split",
        str(media_dir),
        str(profile.game.game_dir),
    ]
    assert kwargs["start_new_session"] is True


def test_open_machine_media_falls_back_to_xdg_open(tmp_path: Path, monkeypatch) -> None:
    launcher, profile, _ = _machine_launcher(tmp_path)
    window, _ = _main_window(tmp_path)
    media_dir = profile.game.game_dir / ".dosmachines" / "media"

    monkeypatch.setattr(
        "dos_machines.ui.media.shutil.which",
        lambda name: "/usr/bin/xdg-open" if name == "xdg-open" else None,
    )
    with patch("dos_machines.ui.media.subprocess.Popen") as popen:
        window._open_machine_media(launcher)

    args, kwargs = popen.call_args
    assert args[0] == ["/usr/bin/xdg-open", str(media_dir)]
    assert kwargs["start_new_session"] is True


def test_open_machine_media_warns_for_broken_launcher(tmp_path: Path) -> None:
    settings_service = SettingsService(config_root=tmp_path / "config")
    settings = settings_service.load()
    launcher = settings.workspace_path / "Broken.desktop"
    launcher.write_text(
        "\n".join(
            [
                "[Desktop Entry]",
                "Type=Application",
                "Name=Broken",
                f"X-DOSMachines-ProfilePath={tmp_path / 'missing' / '.dosmachines' / 'profile.json'}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    window, _ = _main_window(tmp_path)

    with patch("dos_machines.ui.main_window.QMessageBox.warning") as warning, patch("dos_machines.ui.media.subprocess.Popen") as popen:
        window._open_machine_media(launcher)

    warning.assert_called_once()
    popen.assert_not_called()


def test_file_menu_includes_configure_host_action(tmp_path: Path) -> None:
    window, _ = _main_window(tmp_path)

    action_texts = [action.text() for action in window.findChildren(QAction)]

    assert "Configure Host…" in action_texts


def test_configure_host_action_opens_dialog(tmp_path: Path) -> None:
    window, _ = _main_window(tmp_path)

    with patch("dos_machines.ui.main_window.HostConfigDialog") as dialog_cls:
        window._configure_host()

    dialog_cls.assert_called_once()
    dialog_cls.return_value.exec.assert_called_once()
