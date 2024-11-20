import os
from PyQt6.QtWidgets import (
    QVBoxLayout,
    QLineEdit,
    QLabel,
    QDialog,
    QDialogButtonBox,
)
from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QComboBox

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.setMinimumWidth(400)

        # Load settings
        self.settings = QSettings("CloudePython", "AIVideoCreator")

        layout = QVBoxLayout(self)

        # API Keys section
        layout.addWidget(QLabel("API Keys:"))

        # OpenRouter API Key
        layout.addWidget(QLabel("OpenRouter API Key:"))
        self.openrouter_key = QLineEdit()
        self.openrouter_key.setText(self.settings.value("openrouter_api_key", ""))
        self.openrouter_key.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.openrouter_key)

        # Stability API Key
        layout.addWidget(QLabel("Stability API Key:"))
        self.stability_key = QLineEdit()
        self.stability_key.setText(self.settings.value("stability_api_key", ""))
        self.stability_key.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.stability_key)

        # ElevenLabs API Key
        layout.addWidget(QLabel("ElevenLabs API Key:"))
        self.elevenlabs_key = QLineEdit()
        self.elevenlabs_key.setText(self.settings.value("elevenlabs_api_key", ""))
        self.elevenlabs_key.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.elevenlabs_key)

        # Voice ID section
        layout.addWidget(QLabel("ElevenLabs Voice ID:"))
        self.voice_id = QLineEdit()
        self.voice_id.setText(
            self.settings.value("elevenlabs_voice_id", "Nhs6IYoAcBwjSVy82OUS")
        )  # Default voice
        layout.addWidget(self.voice_id)

        # Add help text for voice ID
        help_text = QLabel("Default: Nhs6IYoAcBwjSVy82OUS (Rachel Voice)")
        help_text.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(help_text)

        # Script Language section
        layout.addWidget(QLabel("Script Generation:"))

        self.language_combo = QComboBox()
        self.language_combo.addItems(["Romanian", "English"])
        current_lang = self.settings.value("script_language", "Romanian")
        self.language_combo.setCurrentText(current_lang)
        layout.addWidget(self.language_combo)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.save_settings)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def save_settings(self):
        # Save API keys
        self.settings.setValue("openrouter_api_key", self.openrouter_key.text())
        self.settings.setValue("stability_api_key", self.stability_key.text())
        self.settings.setValue("elevenlabs_api_key", self.elevenlabs_key.text())

        # Save voice ID
        self.settings.setValue("elevenlabs_voice_id", self.voice_id.text())

        # Save language
        self.settings.setValue("script_language", self.language_combo.currentText())

        # Update environment variables
        os.environ["OPENROUTER_API_KEY"] = self.openrouter_key.text()
        os.environ["STABILITY_API_KEY"] = self.stability_key.text()
        os.environ["ELEVENLABS_API_KEY"] = self.elevenlabs_key.text()
        os.environ["ELEVENLABS_VOICE_ID"] = self.voice_id.text()

        self.accept()

