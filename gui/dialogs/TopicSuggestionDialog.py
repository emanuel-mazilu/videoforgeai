from PyQt6.QtWidgets import (
    QVBoxLayout,
    QListWidget,
    QListWidgetItem,
    QDialog,
    QDialogButtonBox,
)
from script.generator import ScriptGenerator

class TopicSuggestionDialog(QDialog):
    def __init__(self, existing_topics, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Suggested Topics")
        self.setModal(True)
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)

        # Add topic list
        self.topic_list = QListWidget()
        layout.addWidget(self.topic_list)

        # Add buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Reset
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.StandardButton.Reset).clicked.connect(
            self.generate_topics
        )
        layout.addWidget(button_box)

        self.existing_topics = existing_topics
        self.generate_topics()

    def generate_topics(self):
        """Generate new topic suggestions"""
        self.topic_list.clear()

        # Hardcoded list of topic categories
        categories = [
            "Istorie românească",
            "Legende și mituri",
            "Personalități istorice",
            "Tradiții și obiceiuri",
            "Locuri fascinante din România",
            "Evenimente istorice importante",
            "Povești populare",
            "Artă și cultură românească",
        ]

        # Add 2-3 suggestions per category
        for category in categories:
            suggestions = ScriptGenerator.get_topic_suggestions(
                category, exclude_topics=self.existing_topics
            )
            for topic in suggestions[:3]:
                item = QListWidgetItem(f"{category}: {topic}")
                self.topic_list.addItem(item)

    def get_selected_topic(self):
        """Get the selected topic without category prefix"""
        item = self.topic_list.currentItem()
        if item:
            # Remove category prefix
            return item.text().split(": ", 1)[1]
        return None
