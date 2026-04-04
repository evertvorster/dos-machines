from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QAbstractListModel, QDir, QFile, QModelIndex, QMimeData, QRect, QSize, Qt
from PySide6.QtGui import QAction, QFontMetrics, QIcon, QTextLayout
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QFileSystemModel,
    QInputDialog,
    QListView,
    QMainWindow,
    QMenu,
    QMessageBox,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
)

from dos_machines.application.engine_registry import EngineRegistry
from dos_machines.application.engine_support import MANAGED_CONFIG_FILENAME
from dos_machines.application.import_service import ImportService
from dos_machines.application.launcher_service import LauncherService
from dos_machines.application.preset_service import PresetService
from dos_machines.application.profile_service import CreateProfileRequest, ProfileService
from dos_machines.application.settings_service import SettingsService
from dos_machines.application.workspace_service import WorkspaceService
from dos_machines.domain.models import MachineProfile
from dos_machines.ui.create_machine_dialog import CreateMachineDialog


class WorkspaceListModel(QAbstractListModel):
    def __init__(self, source_model: QFileSystemModel, workspace_root: Path, parent=None) -> None:
        super().__init__(parent)
        self._source_model = source_model
        self._workspace_root = workspace_root
        self._current_dir = workspace_root
        self._source_model.directoryLoaded.connect(self._on_source_directory_loaded)
        self._source_model.rowsInserted.connect(self._on_source_rows_changed)
        self._source_model.rowsRemoved.connect(self._on_source_rows_changed)
        self._source_model.modelReset.connect(self._reset_from_source)

    def set_current_dir(self, current_dir: Path) -> None:
        if self._current_dir == current_dir:
            self._ensure_current_dir_loaded()
            self._reset_from_source()
            return
        self.beginResetModel()
        self._current_dir = current_dir
        self.endResetModel()
        self._ensure_current_dir_loaded()

    def rowCount(self, parent=QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._source_indexes()) + self._up_row_count()

    def sourceModel(self) -> QFileSystemModel:
        return self._source_model

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        if self.is_up_item(index):
            if role == Qt.ItemDataRole.DisplayRole:
                return ".."
            if role == Qt.ItemDataRole.DecorationRole:
                return QIcon.fromTheme("go-up")
            return None
        source_index = self.map_to_source(index)
        return self._source_model.data(source_index, role)

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemFlag.ItemIsDropEnabled
        if self.is_up_item(index):
            return (
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsDropEnabled
            )
        return self._source_model.flags(self.map_to_source(index))

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if not index.isValid() or self.is_up_item(index):
            return False
        changed = self._source_model.setData(self.map_to_source(index), value, role)
        if changed:
            self.dataChanged.emit(index, index, [role])
        return changed

    def supportedDropActions(self):
        return self._source_model.supportedDropActions()

    def supportedDragActions(self):
        return self._source_model.supportedDragActions()

    def mimeTypes(self) -> list[str]:
        return self._source_model.mimeTypes()

    def mimeData(self, indexes) -> QMimeData | None:
        source_indexes = [
            self.map_to_source(index)
            for index in indexes
            if index.isValid() and not self.is_up_item(index)
        ]
        source_indexes = [index for index in source_indexes if index.isValid()]
        if not source_indexes:
            return None
        return self._source_model.mimeData(source_indexes)

    def index(self, row: int, column: int, parent=QModelIndex()):
        if parent.isValid() or column != 0 or row < 0 or row >= self.rowCount():
            return QModelIndex()
        return self.createIndex(row, column)

    def parent(self, index):
        return QModelIndex()

    def is_up_item(self, index) -> bool:
        return index.isValid() and self._up_row_count() == 1 and index.row() == 0

    def file_path(self, index) -> Path | None:
        if not index.isValid() or self.is_up_item(index):
            return None
        return Path(self._source_model.filePath(self.map_to_source(index)))

    def is_dir(self, index) -> bool:
        if not index.isValid():
            return False
        if self.is_up_item(index):
            return True
        return self._source_model.isDir(self.map_to_source(index))

    def drop_target_index(self, index):
        if not index.isValid():
            return QModelIndex()
        if self.is_up_item(index):
            return self._source_model.index(str(self._current_dir.parent))
        return self.map_to_source(index)

    def _up_row_count(self) -> int:
        return 1 if self._current_dir != self._workspace_root else 0

    def _source_indexes(self) -> list[QModelIndex]:
        source_parent = self._source_model.index(str(self._current_dir))
        if source_parent.isValid() and self._source_model.canFetchMore(source_parent):
            self._source_model.fetchMore(source_parent)
        rows = self._source_model.rowCount(source_parent)
        return [self._source_model.index(row, 0, source_parent) for row in range(rows)]

    def map_to_source(self, proxy_index):
        if not proxy_index.isValid() or self.is_up_item(proxy_index):
            return QModelIndex()
        source_row = proxy_index.row() - self._up_row_count()
        source_indexes = self._source_indexes()
        if source_row < 0 or source_row >= len(source_indexes):
            return QModelIndex()
        return source_indexes[source_row]

    def _reset_from_source(self) -> None:
        self.beginResetModel()
        self.endResetModel()

    def _ensure_current_dir_loaded(self) -> None:
        source_parent = self._source_model.index(str(self._current_dir))
        if source_parent.isValid() and self._source_model.canFetchMore(source_parent):
            self._source_model.fetchMore(source_parent)

    def _on_source_directory_loaded(self, path: str) -> None:
        if Path(path) == self._current_dir:
            self._reset_from_source()

    def _on_source_rows_changed(self, parent: QModelIndex, first: int, last: int) -> None:
        source_path = Path(self._source_model.filePath(parent)) if parent.isValid() else None
        if source_path == self._current_dir:
            self._reset_from_source()


class WorkspaceFileView(QListView):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._import_handler = None
        self._icon_resize_handler = None

    def set_import_handler(self, handler) -> None:
        self._import_handler = handler

    def set_icon_resize_handler(self, handler) -> None:
        self._icon_resize_handler = handler

    def wheelEvent(self, event) -> None:
        if (
            self._icon_resize_handler is not None
            and event.modifiers() & Qt.KeyboardModifier.ControlModifier
            and event.angleDelta().y() != 0
        ):
            self._icon_resize_handler(event.angleDelta().y())
            event.accept()
            return
        super().wheelEvent(event)

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
        if event.source() is not self and event.mimeData().hasUrls() and self._import_handler is not None:
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
        if not model.is_dir(target_index):
            super().dropEvent(event)
            return
        mime_data = event.mimeData()
        if mime_data is None:
            super().dropEvent(event)
            return
        source_model = model.sourceModel() if hasattr(model, "sourceModel") else model
        if source_model.dropMimeData(mime_data, Qt.DropAction.MoveAction, -1, -1, model.drop_target_index(target_index)):
            event.setDropAction(Qt.DropAction.MoveAction)
            event.acceptProposedAction()
            return
        event.ignore()

    def _can_accept_drop(self, point) -> bool:
        target_index = self.indexAt(point)
        if not target_index.isValid():
            return False
        return self.model().is_dir(target_index)


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


class WorkspaceItemDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index) -> None:
        view_option = QStyleOptionViewItem(option)
        self.initStyleOption(view_option, index)
        style = view_option.widget.style() if view_option.widget is not None else QApplication.style()
        style.drawPrimitive(QStyle.PrimitiveElement.PE_PanelItemViewItem, view_option, painter, view_option.widget)

        icon_size = view_option.decorationSize
        icon_rect = QRect(
            view_option.rect.x() + (view_option.rect.width() - icon_size.width()) // 2,
            view_option.rect.y() + 4,
            icon_size.width(),
            icon_size.height(),
        )
        if not view_option.icon.isNull():
            mode = QStyle.StateFlag.State_Enabled
            if not view_option.state & QStyle.StateFlag.State_Enabled:
                mode = QStyle.StateFlag.State_None
            view_option.icon.paint(painter, icon_rect, Qt.AlignmentFlag.AlignCenter, mode=view_option.icon.Mode.Normal)

        text_rect = QRect(
            view_option.rect.x() + 4,
            icon_rect.bottom() + 6,
            view_option.rect.width() - 8,
            max(0, view_option.rect.height() - icon_rect.height() - 10),
        )
        if text_rect.height() <= 0:
            return

        color = view_option.palette.highlightedText().color() if view_option.state & QStyle.StateFlag.State_Selected else view_option.palette.text().color()
        painter.save()
        painter.setPen(color)
        self._draw_wrapped_text(painter, text_rect, view_option.text, view_option.fontMetrics)
        painter.restore()

    def _draw_wrapped_text(self, painter, rect: QRect, text: str, metrics: QFontMetrics) -> None:
        layout = QTextLayout(text, painter.font())
        layout.beginLayout()
        lines: list[tuple[str, int]] = []
        max_lines = 3
        while len(lines) < max_lines:
            line = layout.createLine()
            if not line.isValid():
                break
            line.setLineWidth(rect.width())
            start = line.textStart()
            length = line.textLength()
            lines.append((text[start:start + length], start + length))
        layout.endLayout()

        if not lines:
            return

        if lines[-1][1] < len(text):
            lines[-1] = (metrics.elidedText(text[lines[-1][1] - len(lines[-1][0]):], Qt.TextElideMode.ElideRight, rect.width()), len(text))

        line_height = metrics.lineSpacing()
        y = rect.y()
        for line_text, _ in lines:
            painter.drawText(QRect(rect.x(), y, rect.width(), line_height), Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, line_text)
            y += line_height


class MainWindow(QMainWindow):
    _MIN_ICON_SIZE = 32
    _MAX_ICON_SIZE = 128

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
        self._settings = self._settings_service.load()
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
        self._list_model = WorkspaceListModel(self._model, self._workspace_service.workspace_path, self)
        self._view = WorkspaceFileView(self)
        self._view.setViewMode(QListView.ViewMode.IconMode)
        self._view.setMovement(QListView.Movement.Static)
        self._view.setResizeMode(QListView.ResizeMode.Adjust)
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
        self._view.setItemDelegate(WorkspaceItemDelegate(self._view))
        self._view.setModel(self._list_model)
        self._view.set_import_handler(self._import_paths)
        self._view.set_icon_resize_handler(self._resize_icons)
        self._view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._view.customContextMenuRequested.connect(self._open_context_menu)
        self._view.activated.connect(self._activate_index)
        self.setCentralWidget(self._view)
        self._apply_workspace_icon_size(self._settings.workspace_icon_size)

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
        self._list_model.set_current_dir(self._current_dir)
        self.statusBar().showMessage(str(self._current_dir))

    def _choose_workspace(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select Workspace")
        if not path:
            return
        self._workspace_service.set_workspace(Path(path))
        self._current_dir = self._workspace_service.workspace_path
        self._model.setRootPath(str(self._current_dir))
        self._list_model = WorkspaceListModel(self._model, self._workspace_service.workspace_path, self)
        self._view.setModel(self._list_model)
        self._refresh()

    def _apply_workspace_icon_size(self, icon_size: int) -> None:
        clamped = max(self._MIN_ICON_SIZE, min(self._MAX_ICON_SIZE, int(icon_size)))
        self._view.setIconSize(QSize(clamped, clamped))
        self._view.setGridSize(QSize(max(120, clamped + 56), max(100, clamped + 36)))

    def _resize_icons(self, angle_delta_y: int) -> None:
        step = 8 if angle_delta_y > 0 else -8
        new_size = self._view.iconSize().width() + step
        clamped = max(self._MIN_ICON_SIZE, min(self._MAX_ICON_SIZE, new_size))
        if clamped == self._view.iconSize().width():
            return
        self._apply_workspace_icon_size(clamped)
        self._settings.workspace_icon_size = clamped
        self._settings_service.save(self._settings)

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
            self._settings_service,
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
        target_config_path = managed_dir / MANAGED_CONFIG_FILENAME
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
                self._settings_service,
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
                        self._settings_service,
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
        if index.isValid() and self._list_model.is_up_item(index):
            path = None
        else:
            path = self._list_model.file_path(index) if index.isValid() else None
        menu = QMenu(self)
        if index.isValid() and self._list_model.is_up_item(index):
            open_action = menu.addAction("Up")
            open_action.triggered.connect(self._go_up)
            menu.addSeparator()
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
        if self._list_model.is_up_item(index):
            self._go_up()
            return
        path = self._list_model.file_path(index)
        if path is None:
            return
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
            self._settings_service,
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
        if not index.isValid() or self._list_model.is_up_item(index):
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
