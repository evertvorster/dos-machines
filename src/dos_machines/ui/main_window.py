from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFileSystemModel,
    QInputDialog,
    QMainWindow,
    QMenu,
    QMessageBox,
    QTreeView,
)

from dos_machines.application.launcher_service import LauncherService
from dos_machines.application.profile_service import ProfileService
from dos_machines.application.settings_service import SettingsService
from dos_machines.application.workspace_service import WorkspaceService
from dos_machines.ui.create_machine_dialog import CreateMachineDialog


class MainWindow(QMainWindow):
    def __init__(
        self,
        settings_service: SettingsService,
        workspace_service: WorkspaceService,
        profile_service: ProfileService,
        launcher_service: LauncherService,
    ) -> None:
        super().__init__()
        self._settings_service = settings_service
        self._workspace_service = workspace_service
        self._profile_service = profile_service
        self._launcher_service = launcher_service
        self.setWindowTitle("DOS Machines")
        self.resize(960, 640)

        self._model = QFileSystemModel(self)
        self._model.setRootPath(str(self._workspace_service.ensure_workspace()))

        self._view = QTreeView(self)
        self._view.setModel(self._model)
        self._view.setRootIndex(self._model.index(str(self._workspace_service.workspace_path)))
        self._view.setContextMenuPolicy(Qt.CustomContextMenu)
        self._view.customContextMenuRequested.connect(self._open_context_menu)
        # Follow the desktop environment's activation preference.
        self._view.activated.connect(self._activate_index)
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
        self._model.setRootPath(str(workspace))
        self._view.setRootIndex(self._model.index(str(workspace)))
        self.statusBar().showMessage(str(workspace))

    def _choose_workspace(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select Workspace")
        if not path:
            return
        self._workspace_service.set_workspace(Path(path))
        self._refresh()

    def _create_folder(self) -> None:
        name, accepted = QInputDialog.getText(self, "New Folder", "Folder name")
        if not accepted or not name.strip():
            return
        index = self._view.currentIndex()
        parent_path = Path(self._model.filePath(index)) if index.isValid() else self._workspace_service.workspace_path
        if parent_path.is_file():
            parent_path = parent_path.parent
        try:
            self._workspace_service.create_folder(parent_path, name.strip())
        except FileExistsError:
            QMessageBox.warning(self, "Folder Exists", "A folder with that name already exists.")
        self._refresh()

    def _add_machine(self) -> None:
        dialog = CreateMachineDialog(self._workspace_service.workspace_path, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        request = dialog.build_request()
        if not request.title or not request.executable or not str(request.game_dir):
            QMessageBox.warning(self, "Missing Fields", "Title, game directory, and executable are required.")
            return
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

    def _activate_index(self, index) -> None:
        path = Path(self._model.filePath(index))
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
        QMessageBox.information(
            self,
            "Launcher",
            f"Launcher ready:\n{path}",
        )
