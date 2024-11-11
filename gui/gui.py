import sys
import os
import asyncio
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLineEdit,
    QLabel,
    QProgressBar,
    QListWidget,
    QListWidgetItem,
    QSpinBox,
    QCheckBox,
    QScrollArea,
    QFrame,
    QFileDialog,
    QMessageBox,
    QGridLayout,
    QDialog,
    QTextEdit,
    QDialogButtonBox,
    QSlider,
    QTabWidget,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QUrl, QTimer, QSettings
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
from typing import Optional, Callable
from functools import partial

from project.project import ProjectManager, Project
from video.creator import VideoCreator

from upload.youtube import UploadWorker

from script.generator import ScriptGenerator

from PyQt6.QtWidgets import QMenuBar, QMenu, QComboBox


class VideoWorker(QThread):
    progress = pyqtSignal(str, int)
    finished = pyqtSignal(bool)

    def __init__(self, creator: VideoCreator, project: Project, method: Callable):
        super().__init__()
        self.creator = creator
        self.project = project
        self.method = method

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        success = loop.run_until_complete(self.method(self.project, self.progress.emit))

        loop.close()
        self.finished.emit(success)


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


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VideoForge AI")
        self.setMinimumSize(1200, 800)

        self.project_manager = ProjectManager()
        self.video_creator = VideoCreator()
        self.current_project: Optional[Project] = None
        self.worker: Optional[VideoWorker] = None
        self.current_image_index: int = 0
        self.selected_image_index = None
        self.selected_image_label = None
        self.modified_scenes = set()
        self.slider_being_dragged = False
        self.playing = False

        self.init_ui()
        self.load_projects()

        # Add resize timer
        self.resize_timer = QTimer()
        self.resize_timer.setSingleShot(True)
        self.resize_timer.timeout.connect(self.delayed_resize)

        self.upload_worker = None

        # Create menu bar
        self.create_menu_bar()

        # Load settings
        self.settings = QSettings("CloudePython", "AIVideoCreator")

    def create_menu_bar(self):
        """Create the application menu bar"""
        menubar = self.menuBar()

        # File menu with updated title
        file_menu = menubar.addMenu("File")

        # Settings action
        settings_action = file_menu.addAction("Settings")
        settings_action.triggered.connect(self.show_settings)

        # Exit action
        exit_action = file_menu.addAction("Exit")
        exit_action.triggered.connect(self.close)

    def show_settings(self):
        """Show the settings dialog"""
        dialog = SettingsDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Reload API keys in generators
            self.video_creator.script_generator.api_key = os.getenv(
                "OPENROUTER_API_KEY"
            )
            self.video_creator.image_generator.api_key = os.getenv("STABILITY_API_KEY")
            self.video_creator.audio_generator.api_key = os.getenv("ELEVENLABS_API_KEY")

            QMessageBox.information(self, "Settings", "Settings saved successfully!")

    def init_ui(self):
        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)

        # Left panel
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_panel.setMaximumWidth(400)

        # Project controls - remove new project button, keep only delete
        project_controls = QHBoxLayout()
        self.delete_project_btn = QPushButton("Delete Project")
        self.delete_project_btn.clicked.connect(self.delete_current_project)
        project_controls.addWidget(self.delete_project_btn)
        left_layout.addLayout(project_controls)

        # Project list
        self.project_lists = {}

        projects_widget = QWidget()
        projects_layout = QVBoxLayout(projects_widget)

        projects_layout.addWidget(QLabel("Projects:"))

        tabs = QTabWidget()

        # Shorts List (<= 60s)
        self.project_lists["shorts"] = QListWidget()
        self.project_lists["shorts"].currentItemChanged.connect(
            self.on_project_selected
        )
        tabs.addTab(self.project_lists["shorts"], "Shorts")

        # Long List (> 60s)
        self.project_lists["long"] = QListWidget()
        self.project_lists["long"].currentItemChanged.connect(self.on_project_selected)
        tabs.addTab(self.project_lists["long"], "Long")

        projects_layout.addWidget(tabs)

        # Change chategory button
        self.change_category_btn = QPushButton("Move to Other Category")
        self.change_category_btn.clicked.connect(self.change_project_category)
        self.change_category_btn.setEnabled(False)
        projects_layout.addWidget(self.change_category_btn)

        left_layout.addWidget(projects_widget)

        # Input fields
        input_form = QFrame()
        form_layout = QVBoxLayout(input_form)

        # Subject input
        form_layout.addWidget(QLabel("Subject:"))
        self.subject_input = QLineEdit()
        form_layout.addWidget(self.subject_input)

        # Add suggestion button
        self.suggest_topic_btn = QPushButton("Suggest Topics")
        self.suggest_topic_btn.clicked.connect(self.show_topic_suggestions)
        # Add it near the subject input
        form_layout.insertWidget(1, self.suggest_topic_btn)  # Add after Subject label

        # Duration input
        duration_layout = QHBoxLayout()
        duration_layout.addWidget(QLabel("Duration (seconds):"))
        self.duration_input = QSpinBox()
        self.duration_input.setRange(5, 300)
        self.duration_input.setValue(60)
        duration_layout.addWidget(self.duration_input)
        form_layout.addLayout(duration_layout)

        left_layout.addWidget(input_form)

        # Action buttons
        self.create_video_btn = QPushButton("Create Video")
        self.create_video_btn.clicked.connect(self.start_video_creation)
        left_layout.addWidget(self.create_video_btn)

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self.clear_form)
        left_layout.addWidget(self.clear_btn)

        # Progress section
        self.progress_bar = QProgressBar()
        left_layout.addWidget(self.progress_bar)

        self.status_label = QLabel()
        left_layout.addWidget(self.status_label)

        # Metadata display
        self.metadata_label = QLabel()
        self.metadata_label.setWordWrap(True)
        left_layout.addWidget(self.metadata_label)

        main_layout.addWidget(left_panel)

        # Right panel
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        # Video preview section
        video_preview_container = QWidget()
        video_layout = QVBoxLayout(video_preview_container)
        video_layout.addWidget(QLabel("Video Preview:"))

        # Video widget setup
        self.video_widget = QVideoWidget()
        self.video_widget.setMinimumSize(640, 360)
        self.video_widget.setStyleSheet("border: 1px solid #ccc;")
        self.video_widget.setCursor(Qt.CursorShape.PointingHandCursor)
        video_layout.addWidget(self.video_widget)

        # Slider setup
        self.video_slider = QSlider(Qt.Orientation.Horizontal)
        self.video_slider.setTracking(False)
        self.video_slider.sliderPressed.connect(self.on_slider_pressed)
        self.video_slider.sliderReleased.connect(self.on_slider_released)
        video_layout.addWidget(self.video_slider)

        # Time labels
        time_layout = QHBoxLayout()
        self.current_time_label = QLabel("0:00")
        self.total_time_label = QLabel("0:00")
        time_layout.addWidget(self.current_time_label)
        time_layout.addStretch()
        time_layout.addWidget(self.total_time_label)
        video_layout.addLayout(time_layout)

        # Media player setup
        self.audio_output = QAudioOutput()
        self.media_player = QMediaPlayer()
        self.media_player.setAudioOutput(self.audio_output)
        self.media_player.setVideoOutput(self.video_widget)
        self.media_player.errorOccurred.connect(self.handle_media_error)
        self.media_player.positionChanged.connect(self.on_position_changed)
        self.media_player.durationChanged.connect(self.on_duration_changed)

        # Add video preview container to right layout
        right_layout.addWidget(video_preview_container)

        # Add Video click handler
        self.video_widget.mouseReleaseEvent = self.toggle_video_playback

        # Add buttons container
        button_container = QHBoxLayout()

        # Add regenerate and upload buttons
        self.regenerate_video_btn = QPushButton("Regenerate Video")
        self.regenerate_video_btn.clicked.connect(self.regenerate_video)
        self.upload_video_btn = QPushButton("Upload to YouTube")
        self.upload_video_btn.setEnabled(False)
        self.upload_video_btn.clicked.connect(self.upload_video)

        button_container.addWidget(self.regenerate_video_btn)
        button_container.addWidget(self.upload_video_btn)
        right_layout.addLayout(button_container)

        # Image preview section
        image_preview_widget = QWidget()
        image_layout = QVBoxLayout(image_preview_widget)

        # Create a scroll area for the image gallery
        self.image_scroll_area = QScrollArea()
        self.image_scroll_area_widget = QWidget()
        self.image_scroll_layout = QGridLayout(self.image_scroll_area_widget)
        self.image_scroll_area_widget.setLayout(self.image_scroll_layout)
        self.image_scroll_area.setWidgetResizable(True)
        self.image_scroll_area.setWidget(self.image_scroll_area_widget)
        image_layout.addWidget(QLabel("Image Gallery:"))
        image_layout.addWidget(self.image_scroll_area)

        # Add image action buttons below the gallery
        image_actions = QHBoxLayout()
        self.replace_image_btn = QPushButton("Replace Image")
        self.replace_image_btn.clicked.connect(self.replace_selected_image)
        self.regenerate_image_btn = QPushButton("Regenerate Image/Audio")
        self.regenerate_image_btn.clicked.connect(self.regenerate_selected_image)
        image_actions.addWidget(self.replace_image_btn)
        image_actions.addWidget(self.regenerate_image_btn)
        image_layout.addLayout(image_actions)

        right_layout.addWidget(image_preview_widget)

        main_layout.addWidget(right_panel)

        # Initialize UI state
        self.update_ui_state()

    def handle_media_error(self, error):
        """Handle media player errors"""
        print(f"Media Player Error: {error}")
        self.status_label.setText(
            f"Media Player Error: {self.media_player.errorString()}"
        )

    def on_slider_pressed(self):
        """Called when user starts dragging the slider"""
        self.slider_being_dragged = True
        self.media_player.pause()

    def on_slider_released(self):
        """Called when user releases the slider"""
        self.slider_being_dragged = False
        # Set video position to slider value
        position = self.video_slider.value()
        self.media_player.setPosition(position)
        self.media_player.play()

    def on_position_changed(self, position):
        """Update slider and current time label when video position changes"""
        try:
            if not self.slider_being_dragged and hasattr(self, "video_slider"):
                self.video_slider.setValue(position)
            if hasattr(self, "current_time_label"):
                self.current_time_label.setText(self.format_time(position))
        except RuntimeError:
            # Handle case where widget has been deleted
            pass

    def on_duration_changed(self, duration):
        """Update slider range and total time label when video duration is known"""
        try:
            if hasattr(self, "video_slider"):
                self.video_slider.setRange(0, duration)
            if hasattr(self, "total_time_label"):
                self.total_time_label.setText(self.format_time(duration))
        except RuntimeError:
            # Handle case where widget has been deleted
            pass

    def format_time(self, ms: int) -> str:
        """Convert milliseconds to MM:SS format"""
        s = ms // 1000
        m, s = divmod(s, 60)
        return f"{m:02d}:{s:02d}"

    def toggle_video_playback(self, event):
        """Toggle video play/pause on video widget click"""
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.pause()
            self.playing = False
        else:
            self.media_player.play()
            self.playing = True

    def play_video(self):
        """Play the current video"""
        if self.current_project and self.current_project.output_path:
            video_file = Path(self.current_project.output_path)
            if video_file.exists():
                # Stop and clear current playback first
                self.media_player.stop()
                self.media_player.setSource(QUrl())  # Clear current source

                # Set new source and play
                video_url = QUrl.fromLocalFile(str(video_file))
                self.media_player.setSource(video_url)
                # Reset slider and time labels
                self.video_slider.setValue(0)
                self.current_time_label.setText("0:00")
                # Add a small delay before playing
                QThread.msleep(100)
                self.media_player.play()
                self.playing = True
            else:
                self.status_label.setText("Video file does not exist")
        else:
            self.status_label.setText("No video available to play")

    def pause_video(self):
        """Pause the video playback"""
        self.media_player.pause()

    def stop_video(self):
        """Stop the video playback"""
        self.media_player.stop()
        self.video_slider.setValue(0)

    def load_projects(self):
        """Load existing projects into category lists"""
        for category in self.project_lists.values():
            category.clear()

        for project in self.project_manager.list_projects():
            # Determin category based on duration
            is_short = project.duration <= 60
            category = "shorts" if is_short else "long"
            self.project_lists[category].addItem(project.subject)

        self.update_ui_state()

    def delete_current_project(self):
        """Delete the currently selected project"""
        if not self.current_project:
            return

        reply = QMessageBox.question(
            self,
            "Delete Project",
            f'Are you sure you want to delete project "{self.current_project.subject}"?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.project_manager.delete_project(self.current_project.id)
            self.current_project = None
            self.load_projects()
            self.clear_form()
            self.update_ui_state()

    def start_video_creation(self):
        """Start the video creation process"""
        subject = self.subject_input.text().strip()
        if not subject:
            self.status_label.setText("Please enter a subject")
            return

        # Check if project already exists
        existing_projects = self.project_manager.list_projects()
        for project in existing_projects:
            if project.subject.lower() == subject.lower():
                reply = QMessageBox.question(
                    self,
                    "Project Exists",
                    f'A project with subject "{subject}" already exists. Do you want to create a new one anyway?',
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if reply == QMessageBox.StandardButton.No:
                    return

        # Create new project
        duration = self.duration_input.value()
        project = self.project_manager.create_project(subject, duration)
        project.title = subject
        project.save()

        self.current_project = project
        self.load_projects()

        # Pass language setting to script generator
        self.video_creator.script_generator.language = self.settings.value(
            "script_language", "Romanian"
        )

        # Start video creation with audio
        self.worker = VideoWorker(
            self.video_creator,
            self.current_project,
            lambda p, cb: self.video_creator.create_video(p, cb, skip_audio=False),
        )
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.on_video_creation_finished)
        self.worker.start()

        self.update_ui_state(is_processing=True)

    def create_new_project(self):
        """Remove this method as it's no longer needed"""
        pass

    def update_progress(self, status: str, value: int):
        """Update progress bar and status"""
        self.progress_bar.setValue(value)
        self.status_label.setText(status)

    def on_video_creation_finished(self, success: bool):
        """Handle video creation completion"""
        self.update_ui_state(is_processing=False)
        if success:
            self.status_label.setText("Video created successfully!")

            # Add delay before loading preview
            QThread.msleep(1000)

            # Ensure project is selected in correct category list
            if self.current_project:
                category = "shorts" if self.current_project.duration <= 60 else "long"
                list_widget = self.project_lists[category]
                for i in range(list_widget.count()):
                    item = list_widget.item(i)
                    if item.text() == self.current_project.subject:
                        list_widget.setCurrentItem(item)
                        break

            # Force UI update
            QApplication.processEvents()

            # Load preview
            self.load_preview()
            self.update_metadata_display()
        else:
            self.status_label.setText("Error creating video")

    def on_project_selected(self, current, previous):
        """Handle project selection"""
        if current:
            project_list = current.listWidget()

            # Deselect item from other list if it exists
            for category, list_widget in self.project_lists.items():
                if list_widget != project_list and list_widget.currentItem():
                    list_widget.clearSelection()

            projects = self.project_manager.list_projects()
            for project in projects:
                if project.subject == current.text():
                    self.current_project = project
                    self.current_image_index = 0
                    self.load_preview()
                    self.update_metadata_display()
                    self.update_ui_state()
                    break

    def load_preview(self):
        """Load video and image previews"""
        if not self.current_project:
            print("No current project")
            return

        try:
            # Stop current playback first
            self.media_player.stop()

            # Load video first
            if (
                self.current_project.output_path
                and Path(self.current_project.output_path).exists()
            ):
                video_path = QUrl.fromLocalFile(self.current_project.output_path)
                self.media_player.setSource(video_path)
                print(f"Loaded video: {self.current_project.output_path}")
            else:
                print("No video available")
                self.status_label.setText("No video available")

            # Reduce delays and forced updates
            QThread.msleep(100)

            # Load images only if they exist and haven't been loaded already
            if self.current_project.images:
                print(f"Starting to load {len(self.current_project.images)} images...")
                # Use a timer to load images after a short delay
                QTimer.singleShot(200, self.load_image_gallery)
            else:
                print("No images available")

        except Exception as e:
            print(f"Error in load_preview: {str(e)}")

    def load_image_gallery(self):
        """Load images into the gallery with optimizations"""
        try:
            # Clear existing items before loading new ones
            self.clear_image_gallery()

            if not self.current_project or not self.current_project.images:
                return

            # Calculate dimensions once
            gallery_width = self.image_scroll_area.width()
            image_width = 180
            is_short = self.current_project.duration <= 60
            image_height = (
                int(image_width * 16 / 9) if is_short else int(image_width * 9 / 16)
            )
            num_columns = max(1, gallery_width // (image_width + 10))

            # Pre-calculate layout
            total_images = len(self.current_project.images)
            total_rows = (total_images + num_columns - 1) // num_columns

            # Set fixed size for scroll area content
            content_height = total_rows * (image_height + 10)
            self.image_scroll_area_widget.setFixedHeight(content_height)

            # Create and populate layout
            row = 0
            column = 0

            # Image cache for faster loading
            self.image_cache = {}

            for idx, image_path in enumerate(self.current_project.images):
                if idx > 0 and idx % 5 == 0:
                    QApplication.processEvents()

                path = Path(image_path)
                if not path.exists():
                    continue

                try:
                    # Create label with minimal initial setup
                    label = QLabel()
                    label.setFixedSize(image_width, image_height)
                    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    label.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
                    label.mousePressEvent = partial(self.select_image, idx, label)

                    # Load image using cache
                    if image_path not in self.image_cache:
                        image = QImage(str(path.absolute()))
                        if not image.isNull():
                            pixmap = QPixmap.fromImage(image)
                            scaled_pixmap = pixmap.scaled(
                                image_width,
                                image_height,
                                Qt.AspectRatioMode.KeepAspectRatio,
                                Qt.TransformationMode.SmoothTransformation,
                            )
                            self.image_cache[image_path] = scaled_pixmap

                    if image_path in self.image_cache:
                        label.setPixmap(self.image_cache[image_path])

                    # Add to layout
                    self.image_scroll_layout.addWidget(label, row, column)

                    column += 1
                    if column >= num_columns:
                        column = 0
                        row += 1

                except Exception as e:
                    print(f"Error loading image {image_path}: {str(e)}")
                    continue

            self.image_scroll_layout.update()
            self.highlight_modified_scenes()

        except Exception as e:
            print(f"Error in load_image_gallery: {str(e)}")

    def clear_image_gallery(self):
        """Clear all images from the gallery"""
        try:
            for i in reversed(range(self.image_scroll_layout.count())):
                item = self.image_scroll_layout.itemAt(i)
                if item and item.widget():
                    item.widget().setParent(None)
        except Exception as e:
            print(f"Error clearing image gallery: {str(e)}")

    def resizeEvent(self, event):
        """Handle window resize events with debouncing"""
        super().resizeEvent(event)
        self.resize_timer.start(150)

    def delayed_resize(self):
        """Called after resize events have stopped"""
        if self.current_project and self.current_project.images:
            self.load_image_gallery()

    def regenerate_video(self):
        """Regenerate the video using existing assets"""
        if not self.current_project:
            return

        if not self.modified_scenes:
            reply = QMessageBox.information(
                self,
                "No Changes",
                "No scenes have been modified. Do you still want to regenerate the video?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.No:
                return

        self.worker = VideoWorker(
            self.video_creator, self.current_project, self.video_creator.recreate_video
        )
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.on_video_regeneration_finished)
        self.worker.start()

        self.update_ui_state(is_processing=True)

    def on_video_regeneration_finished(self, success: bool):
        """Handle video regeneration completion"""
        self.update_ui_state(is_processing=False)
        if success:
            self.status_label.setText("Video regenerated successfully!")
            self.modified_scenes.clear()

            # Stop current playback and clear media player
            self.media_player.stop()
            self.media_player.setSource(QUrl())

            # Reset video controls
            self.video_slider.setValue(0)
            self.current_time_label.setText("0:00")
            self.total_time_label.setText("0:00")

            # Force cleanup
            QApplication.processEvents()

            # Add delay before reloading
            QTimer.singleShot(500, lambda: self.reload_video_after_regeneration())
        else:
            self.status_label.setText("Error regenerating video")

    def reload_video_after_regeneration(self):
        """Helper method to reload video after regeneration"""
        try:
            if self.current_project and self.current_project.output_path:
                # Load preview and gallery
                self.load_preview()
                self.load_image_gallery()

                # Force UI update
                QApplication.processEvents()
        except Exception as e:
            print(f"Error reloading video: {e}")
            self.status_label.setText("Error reloading video")

    def select_image(self, index, label, event):
        """Select an image in the gallery."""
        # Deselect previous selection
        if self.selected_image_label is not None:
            self.selected_image_label.setStyleSheet("")
        # Highlight the selected image
        label.setStyleSheet("border: 2px solid blue;")
        self.selected_image_index = index
        self.selected_image_label = label

    def replace_selected_image(self):
        """Replace the selected image with a new one."""
        if not self.current_project or self.selected_image_index is None:
            return
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Select Image", "", "Images (*.png *.jpg *.jpeg *.webp)"
        )
        if file_name:
            self.current_project.images[self.selected_image_index] = file_name
            self.current_project.update()
            self.load_image_gallery()
            self.selected_image_index = None
            self.selected_image_label = None

    def regenerate_selected_image(self):
        """Regenerate the selected image and/or audio using AI."""
        if not self.current_project or self.selected_image_index is None:
            return

        # Get current prompt and script
        prompt = self.current_project.metadata["image_descriptions"][
            self.selected_image_index
        ]
        script = self.current_project.scripts[self.selected_image_index]

        # Show dialog
        dialog = RegenerationDialog(prompt, script, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        # Update prompt and script if changed
        new_prompt = dialog.prompt_edit.toPlainText().strip()
        new_script = dialog.script_edit.toPlainText().strip()

        changes_made = False

        if dialog.regen_image_cb.isChecked():
            self.current_project.metadata["image_descriptions"][
                self.selected_image_index
            ] = new_prompt
            changes_made = True

        if dialog.regen_audio_cb.isChecked():
            self.current_project.scripts[self.selected_image_index] = new_script
            changes_made = True

        # Create worker for regeneration without video recreation
        async def regenerate_scene(project, progress_callback):
            try:
                progress_callback("Regenerating scene...", 0)

                if dialog.regen_image_cb.isChecked():
                    progress_callback("Regenerating image...", 25)
                    new_image, error = (
                        await self.video_creator.image_generator.regenerate_image(
                            project.id,
                            self.selected_image_index,
                            new_prompt,
                            is_short=(project.duration <= 60),
                        )
                    )

                    if error:
                        progress_callback(f"Error: {error}", 0)
                        return False

                    if new_image:
                        project.images[self.selected_image_index] = new_image

                if dialog.regen_audio_cb.isChecked():
                    progress_callback("Regenerating audio...", 50)
                    new_audio = (
                        await self.video_creator.audio_generator.regenerate_audio(
                            project.id,
                            self.selected_image_index,
                            new_script,
                            project.duration,
                        )
                    )

                    if new_audio:
                        project.audio_files[self.selected_image_index] = new_audio

                project.update()
                progress_callback(
                    f"Scene {self.selected_image_index + 1} updated successfully!", 100
                )
                return True

            except Exception as e:
                progress_callback(f"Error regenerating scene: {str(e)}", 0)
                return False

        if changes_made:
            # Add scene to modified set
            self.modified_scenes.add(self.selected_image_index)

            # Create and start the worker
            self.worker = VideoWorker(
                self.video_creator, self.current_project, regenerate_scene
            )
            self.worker.progress.connect(self.update_progress)
            self.worker.finished.connect(self.on_scene_update_finished)
            self.worker.start()

            self.update_ui_state(is_processing=True)

    def on_scene_update_finished(self, success: bool):
        """Handle scene update completion"""
        self.update_ui_state(is_processing=False)
        if success:
            self.status_label.setText(
                f"Scene {self.selected_image_index + 1} updated successfully!"
            )
            self.load_image_gallery()
            # Mark the modified scene in the gallery
            self.highlight_modified_scenes()
        else:
            self.status_label.setText("Error updating scene")

    def highlight_modified_scenes(self):
        """Highlight scenes that have been modified"""
        for i in range(self.image_scroll_layout.count()):
            widget = self.image_scroll_layout.itemAt(i).widget()
            if widget and isinstance(widget, QLabel):
                scene_index = i
                if scene_index in self.modified_scenes:
                    widget.setStyleSheet("border: 2px solid orange;")  # Modified scenes
                elif widget == self.selected_image_label:
                    widget.setStyleSheet("border: 2px solid blue;")  # Selected scene
                else:
                    widget.setStyleSheet("border: 1px solid gray;")  # Normal scenes

    def clear_form(self):
        """Clear input fields"""
        self.subject_input.clear()
        self.duration_input.setValue(60)
        self.metadata_label.clear()
        self.status_label.setText("No video available")

        # Clear image gallery
        for i in reversed(range(self.image_scroll_layout.count())):
            widget = self.image_scroll_layout.itemAt(i).widget()
            if widget is not None:
                widget.setParent(None)

        self.status_label.clear()
        self.progress_bar.setValue(0)
        self.current_image_index = 0
        self.selected_image_index = None
        self.selected_image_label = None
        self.video_slider.setValue(0)
        self.current_time_label.setText("0:00")
        self.total_time_label.setText("0:00")

    def update_ui_state(self, is_processing: bool = False):
        """Update UI elements based on current state"""
        has_project = self.current_project is not None
        has_video = (
            has_project
            and self.current_project.output_path
            and Path(self.current_project.output_path).exists()
        )

        # Update existing buttons
        self.delete_project_btn.setEnabled(has_project and not is_processing)
        self.create_video_btn.setEnabled(not is_processing)
        self.regenerate_video_btn.setEnabled(has_project and not is_processing)
        self.change_category_btn.setEnabled(has_project and not is_processing)

        # Update upload button
        self.upload_video_btn.setEnabled(has_video and not is_processing)

        # Update image buttons
        has_images = (
            has_project
            and hasattr(self.current_project, "images")
            and len(self.current_project.images or []) > 0
        )
        self.replace_image_btn.setEnabled(bool(has_images) and not is_processing)
        self.regenerate_image_btn.setEnabled(bool(has_images) and not is_processing)

    def update_metadata_display(self):
        """Update metadata display"""
        if not self.current_project:
            self.metadata_label.clear()
            return

        metadata = [
            f"Title: {self.current_project.title}",
            f"Subject: {self.current_project.subject}",
            f"Duration: {self.current_project.duration}s",
            f"Created: {self.current_project.created_at}",
            f"Updated: {self.current_project.updated_at}",
        ]

        self.metadata_label.setText("\n".join(metadata))

    def change_project_category(self):
        """Move project between categories"""
        if not self.current_project:
            return

        current_category = "shorts" if self.current_project.duration <= 60 else "long"
        new_category = "long" if current_category == "shorts" else "shorts"

        if new_category == "shorts":
            self.current_project.duration = 60
        else:
            self.current_project.duration = 120

        self.current_project.update()

        self.load_projects()

        list_widget = self.project_lists[new_category]
        for i in range(list_widget.count()):
            if list_widget.item(i).text() == self.current_project.subject:
                list_widget.setCurrentItem(list_widget.item(i))
                break

    def closeEvent(self, event):
        """Handle application closing"""
        # Clear image cache
        if hasattr(self, "image_cache"):
            self.image_cache.clear()
        # Cleanup media player resources
        self.media_player.stop()
        self.media_player.setSource(QUrl())
        event.accept()

    def upload_video(self):
        """Handle video upload to YouTube"""
        if not self.current_project or not self.current_project.output_path:
            return

        video_path = Path(self.current_project.output_path)
        if not video_path.exists():
            QMessageBox.warning(self, "Upload Error", "Video file not found!")
            return

        reply = QMessageBox.question(
            self,
            "Upload to YouTube",
            "Are you sure you want to upload this video to YouTube?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Create worker thread for upload
            self.upload_worker = UploadWorker(self.current_project)
            self.upload_worker.progress.connect(self.update_progress)
            self.upload_worker.finished.connect(self.on_upload_finished)

            # Disable UI during upload
            self.update_ui_state(is_processing=True)
            self.status_label.setText("Uploading to YouTube...")
            self.progress_bar.setMaximum(0)  # Show indefinite progress

            self.upload_worker.start()

    def on_upload_finished(self, success: bool):
        """Handle upload completion"""
        self.progress_bar.setMaximum(100)  # Restore normal progress bar
        self.update_ui_state(is_processing=False)

        if success:
            QMessageBox.information(
                self, "Upload Complete", "Video successfully uploaded to YouTube!"
            )
            self.status_label.setText("Upload complete")
        else:
            QMessageBox.warning(
                self,
                "Upload Failed",
                "Failed to upload video to YouTube. Check the logs for details.",
            )
            self.status_label.setText("Upload failed")

    def show_topic_suggestions(self):
        """Show topic suggestion dialog"""
        # Get list of existing topics
        existing_topics = [
            project.subject for project in self.project_manager.list_projects()
        ]

        dialog = TopicSuggestionDialog(existing_topics, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_topic = dialog.get_selected_topic()
            if selected_topic:
                self.subject_input.setText(selected_topic)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
