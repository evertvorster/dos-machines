from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from dos_machines.application.profile_service import CreateProfileRequest


class CreateMachineDialog(QDialog):
    def __init__(self, workspace_dir: Path, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add New Machine")
        self._workspace_dir = workspace_dir

        self.title_edit = QLineEdit()
        self.game_dir_edit = QLineEdit()
        self.executable_edit = QLineEdit()
        self.engine_binary_edit = QLineEdit("/usr/bin/dosbox")

        form = QFormLayout()
        form.addRow("Title", self.title_edit)
        form.addRow("Game Directory", self._with_browse(self.game_dir_edit, self._browse_game_dir))
        form.addRow("Executable", self.executable_edit)
        form.addRow("Engine Binary", self._with_browse(self.engine_binary_edit, self._browse_engine_binary))

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def build_request(self) -> CreateProfileRequest:
        return CreateProfileRequest(
            title=self.title_edit.text().strip(),
            game_dir=Path(self.game_dir_edit.text().strip()).expanduser(),
            executable=self.executable_edit.text().strip(),
            engine_binary=Path(self.engine_binary_edit.text().strip()).expanduser(),
            workspace_dir=self._workspace_dir,
        )

    def _with_browse(self, line_edit: QLineEdit, callback) -> QHBoxLayout:
        button = QPushButton("Browse…")
        button.clicked.connect(callback)
        layout = QHBoxLayout()
        layout.addWidget(line_edit)
        layout.addWidget(button)
        return layout

    def _browse_game_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select Game Directory")
        if path:
            self.game_dir_edit.setText(path)

    def _browse_engine_binary(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select DOSBox Binary")
        if path:
            self.engine_binary_edit.setText(path)
