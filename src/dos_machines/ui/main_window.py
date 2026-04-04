from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QDir, QFile, QSize, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFileSystemModel,
    QInputDialog,
    QListView,
    QMainWindow,
    QMenu,
    QMessageBox,
    QStyle,
)

from dos_machines.application.engine_registry import EngineRegistry
from dos_machines.application.engine_support import managed_config_filename
from dos_machines.application.import_service import ImportService
from dos_machines.application.launcher_service import LauncherService
from dos_machines.application.preset_service import PresetService
from dos_machines.application.profile_service import CreateProfileRequest, ProfileService
from dos_machines.application.settings_service import SettingsService
from dos_machines.application.workspace_service import WorkspaceService
from dos_machines.domain.models import MachineProfile
from dos_machines.ui.create_machine_dialog import CreateMachineDialog


class WorkspaceFileView(QListView):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._import_handler = None

    def set_import_handler(self, handler) -> None:
        self._import_handler = handler

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls() or event.mimeData().hasFormat("application/x-qabstractitemmodeldatalist"):
            event.setDropAction(Qt.DropAction.MoveAction)
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event) -> None:
        if self._can_accept_drop(event.position().toPoint()):
            event.setDropAction(Qt.DropAction.MoveAction)
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event) -> None:
        if event.mimeData().hasUrls() and self._import_handler is not None:
            import_paths = [
                Path(url.toLocalFile())
                for url in event.mimeData().urls()
                if url.isLocalFile()
            ]
            if import_paths and self._import_handler(import_paths):
                event.acceptProposedAction()
                return
        target_index = self.indexAt(event.position().toPoint())
        if not target_index.isValid():
            super().dropEvent(event)
            return
        model = self.model()
        if not model.isDir(target_index):
            super().dropEvent(event)
            return
        mime_data = event.mimeData()
        if mime_data is None:
            super().dropEvent(event)
            return
        if model.dropMimeData(mime_data, Qt.DropAction.MoveAction, -1, -1, target_index):
            event.setDropAction(Qt.DropAction.MoveAction)
            event.acceptProposedAction()
            return
        event.ignore()

    def _can_accept_drop(self, point) -> bool:
        target_index = self.indexAt(point)
        if not target_index.isValid():
            return False
        return self.model().isDir(target_index)


class WorkspaceFileModel(QFileSystemModel):
    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and index.isValid():
            file_info = self.fileInfo(index)
            if file_info.isFile() and file_info.suffix() == "desktop":
                return file_info.completeBaseName()
        return super().data(index, role)

    def flags(self, index):
        flags = super().flags(index)
        if not index.isValid():
            return flags
        file_info = self.fileInfo(index)
        if file_info.isFile() and file_info.suffix() == "desktop":
            return flags & ~Qt.ItemFlag.ItemIsEditable
        return flags


class MainWindow(QMainWindow):
    def __init__(
        self,
        settings_service: SettingsService,
        workspace_service: WorkspaceService,
        profile_service: ProfileService,
        import_service: ImportService,
        launcher_service: LauncherService,
        engine_registry: EngineRegistry,
        preset_service: PresetService,
    ) -> None:
        super().__init__()
        self._settings_service = settings_service
        self._workspace_service = workspace_service
        self._profile_service = profile_service
        self._import_service = import_service
        self._launcher_service = launcher_service
        self._engine_registry = engine_registry
        self._preset_service = preset_service
        self._current_dir = self._workspace_service.ensure_workspace()
        self.setWindowTitle("DOS Machines")
        self.resize(960, 640)

        self._model = WorkspaceFileModel(self)
        self._model.setReadOnly(False)
        self._model.setRootPath(str(self._workspace_service.workspace_path))
        self._model.setFilter(
            self._model.filter()
            | QDir.Filter.AllDirs
            | QDir.Filter.Files
            | QDir.Filter.Hidden
            | QDir.Filter.NoDotAndDotDot
        )
        self._model.fileRenamed.connect(self._on_file_renamed)
        self._view = WorkspaceFileView(self)
        self._view.setViewMode(QListView.ViewMode.IconMode)
        self._view.setMovement(QListView.Movement.Static)
        self._view.setResizeMode(QListView.ResizeMode.Adjust)
        self._view.setIconSize(QSize(64, 64))
        self._view.setGridSize(QSize(120, 100))
        self._view.setWordWrap(True)
        self._view.setDragEnabled(True)
        self._view.setAcceptDrops(True)
        self._view.viewport().setAcceptDrops(True)
        self._view.setDropIndicatorShown(True)
        self._view.setDragDropMode(QListView.DragDropMode.DragDrop)
        self._view.setDragDropOverwriteMode(False)
        self._view.setDefaultDropAction(Qt.DropAction.MoveAction)
        self._view.setEditTriggers(
            QListView.EditTrigger.EditKeyPressed
        )
        self._view.setModel(self._model)
        self._view.setRootIndex(self._model.index(str(self._current_dir)))
        self._view.set_import_handler(self._import_paths)
        self._view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._view.customContextMenuRequested.connect(self._open_context_menu)
        self._view.activated.connect(self._activate_index)
        self.setCentralWidget(self._view)

        self._build_menus()
        self._build_toolbar()
        self._refresh()

    def _build_menus(self) -> None:
        file_menu = self.menuBar().addMenu("&File")

        choose_workspace = QAction("Choose Workspace…", self)
        choose_workspace.triggered.connect(self._choose_workspace)
        file_menu.addAction(choose_workspace)

        up_action = QAction("Up", self)
        up_action.triggered.connect(self._go_up)
        file_menu.addAction(up_action)

        new_folder = QAction("New Folder", self)
        new_folder.triggered.connect(self._create_folder)
        file_menu.addAction(new_folder)

        add_machine = QAction("Add New Machine", self)
        add_machine.triggered.connect(self._add_machine)
        file_menu.addAction(add_machine)

        refresh = QAction("Refresh", self)
        refresh.triggered.connect(self._refresh)
        file_menu.addAction(refresh)

    def _build_toolbar(self) -> None:
        toolbar = self.addToolBar("Navigation")
        toolbar.setMovable(False)

        up_action = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogToParent), "Up", self)
        up_action.triggered.connect(self._go_up)
        toolbar.addAction(up_action)

    def _refresh(self) -> None:
        workspace = self._workspace_service.ensure_workspace()
        if not self._current_dir.exists():
            self._current_dir = workspace
        self._view.setRootIndex(self._model.index(str(self._current_dir)))
        self.statusBar().showMessage(str(self._current_dir))

    def _choose_workspace(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select Workspace")
        if not path:
            return
        self._workspace_service.set_workspace(Path(path))
        self._current_dir = self._workspace_service.workspace_path
        self._model.setRootPath(str(self._current_dir))
        self._refresh()

    def _go_up(self) -> None:
        workspace = self._workspace_service.workspace_path
        if self._current_dir == workspace:
            return
        self._current_dir = self._current_dir.parent
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
            import_service=self._import_service,
            parent=self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        request = dialog.build_request()
        try:
            request = self._resolve_new_machine_conflicts(request)
            if request is None:
                return
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

    def _resolve_new_machine_conflicts(self, request: CreateProfileRequest) -> CreateProfileRequest | None:
        managed_dir = request.game_dir.expanduser().resolve() / ".dosmachines"
        target_config_path = managed_dir / managed_config_filename(request.engine_binary)
        existing_profile_path = managed_dir / "profile.json"
        if not target_config_path.exists() and not existing_profile_path.exists():
            return request

        message = QMessageBox(self)
        message.setIcon(QMessageBox.Icon.Warning)
        message.setWindowTitle("Existing Managed Files")
        message.setText(f"Managed files already exist in '{managed_dir}'.")
        message.setInformativeText("Overwrite the destination config, or use the destination config as the basis for the new machine?")
        overwrite_button = message.addButton("Overwrite", QMessageBox.ButtonRole.AcceptRole)
        use_existing_button = message.addButton("Use Existing Config", QMessageBox.ButtonRole.ActionRole)
        cancel_button = message.addButton(QMessageBox.StandardButton.Cancel)
        message.setDefaultButton(overwrite_button)
        message.exec()

        clicked = message.clickedButton()
        if clicked == cancel_button:
            return None
        if clicked == overwrite_button:
            request.overwrite_existing = True
            return request
        if clicked == use_existing_button:
            if not target_config_path.exists():
                QMessageBox.warning(
                    self,
                    "Config Missing",
                    f"No existing config file was found at '{target_config_path}'.",
                )
                return None
            analysis = self._import_service.analyse_config(target_config_path)
            dialog = CreateMachineDialog(
                self._current_dir,
                self._engine_registry,
                self._preset_service,
                import_service=self._import_service,
                import_analysis=analysis,
                parent=self,
            )
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return None
            imported_request = dialog.build_request()
            imported_request.overwrite_existing = True
            return imported_request
        return None

    def _import_paths(self, paths: list[Path]) -> bool:
        config_paths = [path for path in paths if self._import_service.can_import(path)]
        if not config_paths:
            return False
        imported_titles: list[str] = []
        for config_path in config_paths:
            try:
                analysis = self._import_service.analyse_config(config_path)
                if analysis.has_issues:
                    dialog = CreateMachineDialog(
                        self._current_dir,
                        self._engine_registry,
                        self._preset_service,
                        import_service=self._import_service,
                        import_analysis=analysis,
                        parent=self,
                    )
                    if dialog.exec() != QDialog.DialogCode.Accepted:
                        return True
                    request = dialog.build_request()
                    profile = self._profile_service.create(request)
                else:
                    profile = self._import_service.import_config(config_path, self._current_dir)
                self._launcher_service.create_launcher(profile, self._current_dir)
                imported_titles.append(profile.identity.title)
            except FileExistsError:
                QMessageBox.warning(
                    self,
                    "Import Failed",
                    f"A machine for '{config_path.parent.name}' already exists.",
                )
                return True
            except Exception as exc:  # pragma: no cover - UI safety net
                QMessageBox.critical(self, "Import Failed", str(exc))
                return True
        self._refresh()
        if imported_titles:
            QMessageBox.information(
                self,
                "Import Complete",
                f"Imported {len(imported_titles)} config file(s) into '{self._current_dir.name or self._current_dir}'.",
            )
        return True

    def _open_context_menu(self, point) -> None:
        index = self._view.indexAt(point)
        path = Path(self._model.filePath(index)) if index.isValid() else None
        menu = QMenu(self)
        if path is not None and path.suffix == ".desktop":
            launch_action = menu.addAction("Launch")
            launch_action.triggered.connect(lambda: self._activate_index(index))
            configure_action = menu.addAction("Configure Machine")
            configure_action.triggered.connect(lambda: self._configure_launcher(path))
            rename_action = menu.addAction("Rename Machine")
            rename_action.triggered.connect(lambda: self._rename_launcher(path))
            delete_action = menu.addAction("Delete Machine")
            delete_action.triggered.connect(lambda: self._delete_machine(path))
            menu.addSeparator()
        elif path is not None:
            if path.is_dir():
                open_action = menu.addAction("Open Folder")
                open_action.triggered.connect(lambda: self._open_directory(path))
            rename_action = menu.addAction("Rename")
            rename_action.triggered.connect(lambda: self._rename_entry(index))
            trash_action = menu.addAction("Move to Trash")
            trash_action.triggered.connect(lambda: self._move_entry_to_trash(path))
            menu.addSeparator()
        add_machine = menu.addAction("Add New Machine")
        add_machine.triggered.connect(self._add_machine)
        new_folder = menu.addAction("New Folder")
        new_folder.triggered.connect(self._create_folder)
        up_action = menu.addAction("Up")
        up_action.triggered.connect(self._go_up)
        refresh = menu.addAction("Refresh")
        refresh.triggered.connect(self._refresh)
        menu.exec(self._view.viewport().mapToGlobal(point))

    def _activate_index(self, index) -> None:
        path = Path(self._model.filePath(index))
        if path.is_dir():
            self._open_directory(path)
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

    def _open_directory(self, path: Path) -> None:
        self._current_dir = path
        self._refresh()

    def _configure_launcher(self, launcher_path: Path) -> None:
        entry = self._workspace_service.read_launcher_entry(launcher_path)
        if entry.profile_path is None or not entry.profile_path.exists():
            QMessageBox.warning(self, "Broken Machine", f"Missing profile: {entry.profile_path}")
            return
        try:
            profile = self._profile_service.load(entry.profile_path)
        except Exception as exc:  # pragma: no cover - UI safety net
            QMessageBox.critical(self, "Load Failed", str(exc))
            return
        dialog = CreateMachineDialog(
            launcher_path.parent,
            self._engine_registry,
            self._preset_service,
            profile=profile,
            import_service=self._import_service,
            parent=self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        request = dialog.build_request()
        try:
            updated_profile = self._profile_service.create(request)
            self._launcher_service.sync_launcher(updated_profile, launcher_path.parent, launcher_path)
        except FileExistsError:
            QMessageBox.warning(
                self,
                "Launcher Exists",
                f"A machine named '{request.title}' already exists in this folder.",
            )
            return
        except Exception as exc:  # pragma: no cover - UI safety net
            QMessageBox.critical(self, "Save Failed", str(exc))
            return
        self._refresh()

    def _rename_launcher(self, launcher_path: Path) -> None:
        entry = self._workspace_service.read_launcher_entry(launcher_path)
        if entry.profile_path is None or not entry.profile_path.exists():
            QMessageBox.warning(self, "Broken Machine", f"Missing profile: {entry.profile_path}")
            return
        title, accepted = QInputDialog.getText(self, "Rename Machine", "Machine name", text=entry.title)
        if not accepted:
            return
        new_title = title.strip()
        if not new_title or new_title == entry.title:
            return
        try:
            profile = self._profile_service.load(entry.profile_path)
            request = self._build_profile_update_request(profile, launcher_path.parent, new_title)
            updated_profile = self._profile_service.create(request)
            self._launcher_service.sync_launcher(updated_profile, launcher_path.parent, launcher_path)
        except FileExistsError:
            QMessageBox.warning(
                self,
                "Launcher Exists",
                f"A machine named '{new_title}' already exists in this folder.",
            )
            return
        except Exception as exc:  # pragma: no cover - UI safety net
            QMessageBox.critical(self, "Rename Failed", str(exc))
            return
        self._refresh()

    def _delete_machine(self, launcher_path: Path) -> None:
        entry = self._workspace_service.read_launcher_entry(launcher_path)
        answer = QMessageBox.question(
            self,
            "Delete Machine",
            f"Delete machine '{entry.title}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            if entry.profile_path is not None and entry.profile_path.exists():
                self._profile_service.delete(entry.profile_path)
            if launcher_path.exists():
                launcher_path.unlink()
        except Exception as exc:  # pragma: no cover - UI safety net
            QMessageBox.critical(self, "Delete Failed", str(exc))
            return
        self._refresh()

    def _rename_entry(self, index) -> None:
        if not index.isValid():
            return
        self._view.edit(index)

    def _move_entry_to_trash(self, path: Path) -> None:
        label = "folder" if path.is_dir() else "file"
        answer = QMessageBox.question(
            self,
            "Move to Trash",
            f"Move {label} '{path.name}' to Trash?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            if not self._move_to_trash(path):
                raise OSError(f"Could not move '{path}' to Trash.")
        except Exception as exc:  # pragma: no cover - UI safety net
            QMessageBox.critical(self, "Trash Failed", str(exc))
            return
        if self._current_dir == path:
            self._current_dir = self._workspace_service.workspace_path
        self._refresh()

    def _move_to_trash(self, path: Path) -> bool:
        return QFile.moveToTrash(str(path))

    def _on_file_renamed(self, directory: str, old_name: str, new_name: str) -> None:
        old_path = Path(directory) / old_name
        if self._current_dir == old_path:
            self._current_dir = Path(directory) / new_name
            self._refresh()

    def _build_profile_update_request(
        self,
        profile: MachineProfile,
        workspace_dir: Path,
        title: str,
    ) -> CreateProfileRequest:
        return CreateProfileRequest(
            title=title,
            game_dir=profile.game.game_dir,
            executable=profile.game.executable,
            engine_binary=profile.engine.binary_path,
            workspace_dir=workspace_dir,
            setup_executable=profile.game.setup_executable,
            notes=profile.identity.notes,
            option_states=profile.option_states,
            autoexec_text=profile.autoexec_text,
            existing_profile_path=profile.game.game_dir / ".dosmachines" / "profile.json",
        )
