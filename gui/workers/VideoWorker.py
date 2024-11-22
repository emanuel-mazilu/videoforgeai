from PyQt6.QtCore import Qt, QThread, pyqtSignal, QUrl, QTimer, QSettings
from video.creator import VideoCreator
from project.project import ProjectManager, Project
import asyncio
from typing import Optional, Callable

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