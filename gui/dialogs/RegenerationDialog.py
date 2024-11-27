from PyQt6.QtWidgets import (
    QVBoxLayout,
    QLabel,
    QCheckBox,
    QDialog,
    QTextEdit,
    QDialogButtonBox,
)


class RegenerationDialog(QDialog):
    def __init__(self, prompt: str, script: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Regenerate Scene")
        self.setModal(True)
        self.setMinimumWidth(500)

        layout = QVBoxLayout(self)

        # Image prompt section
        layout.addWidget(QLabel("Image Prompt:"))
        self.prompt_edit = QTextEdit()
        self.prompt_edit.setPlainText(prompt)
        layout.addWidget(self.prompt_edit)

        # Audio script section
        layout.addWidget(QLabel("Audio Script:"))
        self.script_edit = QTextEdit()
        self.script_edit.setPlainText(script)
        layout.addWidget(self.script_edit)

        # Checkboxes
        self.regen_image_cb = QCheckBox("Regenerate Image")
        self.regen_image_cb.setChecked(True)
        layout.addWidget(self.regen_image_cb)

        self.regen_audio_cb = QCheckBox("Regenerate Audio")
        layout.addWidget(self.regen_audio_cb)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
