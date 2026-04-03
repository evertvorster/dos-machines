from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QFileInfo, QSize, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFileIconProvider,
    QInputDialog,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
)

from dos_machines.application.engine_registry import EngineRegistry
from dos_machines.application.launcher_service import LauncherService
from dos_machines.application.preset_service import PresetService
from dos_machines.application.profile_service import ProfileService
from dos_machines.application.settings_service import SettingsService
from dos_machines.application.workspace_service import WorkspaceService
from dos_machines.ui.create_machine_dialog import CreateMachineDialog


UP_MARKER = ".."


class MainWindow(QMainWindow):
    def __init__(
        self,
        settings_service: SettingsService,
        workspace_service: WorkspaceService,
        profile_service: ProfileService,
        launcher_service: LauncherService,
        engine_registry: EngineRegistry,
        preset_service: PresetService,
    ) -> None:
        super().__init__()
        self._settings_service = settings_service
        self._workspace_service = workspace_service
        self._profile_service = profile_service
        self._launcher_service = launcher_service
        self._engine_registry = engine_registry
        self._preset_service = preset_service
        self._icon_provider = QFileIconProvider()
        self._current_dir = self._workspace_service.ensure_workspace()
        self.setWindowTitle("DOS Machines")
        self.resize(960, 640)

        self._view = QListWidget(self)
        self._view.setViewMode(QListWidget.IconMode)
        self._view.setMovement(QListWidget.Static)
        self._view.setResizeMode(QListWidget.Adjust)
        self._view.setIconSize(QSize(64, 64))
        self._view.setGridSize(QSize(120, 100))
        self._view.setWordWrap(True)
        self._view.setContextMenuPolicy(Qt.CustomContextMenu)
        self._view.customContextMenuRequested.connect(self._open_context_menu)
        self._view.itemActivated.connect(self._activate_item)
        self.setCentralWidget(self._view)

        self._build_menus()
        self._refresh()

    def _build_menus(self) -> None:
        file_menu = self.menuBar().addMenu("&File")

        choose_workspace = QAction("Choose Workspace…", self)
        choose_workspace.triggered.connect(self._choose_workspace)
        file_menu.addAction(choose_workspace)

        new_folder = QAction("New Folder", self)
        new_folder.triggered.connect(self._create_folder)
        file_menu.addAction(new_folder)

        add_machine = QAction("Add New Machine", self)
        add_machine.triggered.connect(self._add_machine)
        file_menu.addAction(add_machine)

        refresh = QAction("Refresh", self)
        refresh.triggered.connect(self._refresh)
        file_menu.addAction(refresh)

    def _refresh(self) -> None:
        workspace = self._workspace_service.ensure_workspace()
        if not self._current_dir.exists():
            self._current_dir = workspace
        self._view.clear()
        if self._current_dir != workspace:
            self._add_item(UP_MARKER, self._current_dir.parent, is_dir=True)
        for child in sorted(self._current_dir.iterdir(), key=lambda path: (not path.is_dir(), path.name.lower())):
            self._add_item(child.name, child, is_dir=child.is_dir())
        self.statusBar().showMessage(str(self._current_dir))

    def _add_item(self, label: str, path: Path, is_dir: bool) -> None:
        item = QListWidgetItem(label)
        item.setData(Qt.ItemDataRole.UserRole, str(path))
        icon_source = self._icon_provider.icon(
            QFileIconProvider.IconType.Folder if is_dir else QFileInfo(str(path))
        )
        item.setIcon(icon_source)
        self._view.addItem(item)

    def _choose_workspace(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select Workspace")
        if not path:
            return
        self._workspace_service.set_workspace(Path(path))
        self._current_dir = self._workspace_service.workspace_path
        self._refresh()

    def _create_folder(self) -> None:
        name, accepted = QInputDialog.getText(self, "New Folder", "Folder name")
        if not accepted or not name.strip():
            return
        try:
            self._workspace_service.create_folder(self._current_dir, name.strip())
        except FileExistsError:
            QMessageBox.warning(self, "Folder Exists", "A folder with that name already exists.")
        self._refresh()

    def _add_machine(self) -> None:
        dialog = CreateMachineDialog(
            self._current_dir,
            self._engine_registry,
            self._preset_service,
            self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        request = dialog.build_request()
        try:
            profile = self._profile_service.create(request)
            self._launcher_service.create_launcher(profile, request.workspace_dir)
        except FileExistsError:
            QMessageBox.information(
                self,
                "Already Registered",
                "That game directory already contains a DOS Machines profile.",
            )
        except Exception as exc:  # pragma: no cover - UI safety net
            QMessageBox.critical(self, "Create Machine Failed", str(exc))
        self._refresh()

    def _open_context_menu(self, point) -> None:
        menu = QMenu(self)
        add_machine = menu.addAction("Add New Machine")
        add_machine.triggered.connect(self._add_machine)
        new_folder = menu.addAction("New Folder")
        new_folder.triggered.connect(self._create_folder)
        refresh = menu.addAction("Refresh")
        refresh.triggered.connect(self._refresh)
        menu.exec(self._view.viewport().mapToGlobal(point))

    def _activate_item(self, item: QListWidgetItem) -> None:
        path = Path(item.data(Qt.ItemDataRole.UserRole))
        if path.is_dir():
            self._current_dir = path
            self._refresh()
            return
        if path.suffix != ".desktop":
            return
        entry = self._workspace_service.read_launcher_entry(path)
        if entry.broken:
            QMessageBox.warning(
                self,
                "Broken Machine",
                f"Missing profile: {entry.profile_path}",
            )
            return
        try:
            self._launcher_service.launch_launcher(path)
        except Exception as exc:  # pragma: no cover - UI safety net
            QMessageBox.critical(self, "Launch Failed", str(exc))
