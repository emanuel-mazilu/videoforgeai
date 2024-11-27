import json
import time
import shutil
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
from pathlib import Path


@dataclass
class Project:
    id: str
    title: str
    subject: str
    duration: int
    images: List[str]
    audio_files: List[str]
    scripts: List[str]
    output_path: str
    created_at: float
    updated_at: float
    metadata: Dict[str, any]

    @classmethod
    def create(cls, subject: str, duration: int) -> 'Project':
        """Create a new project instance"""
        project_id = str(int(time.time()))
        timestamp = time.time()
        project_dir = Path(f"projects/{project_id}")
        project_dir.mkdir(parents=True, exist_ok=True)

        output_path = project_dir / "output.mp4"

        return cls(
            id=project_id,
            title="",  # Will be set after script generation
            subject=subject,
            duration=duration,
            images=[],
            audio_files=[],
            scripts=[],
            output_path=str(output_path.resolve()),
            created_at=timestamp,
            updated_at=timestamp,
            metadata={}
        )

    def to_dict(self) -> dict:
        """Convert project to dictionary format"""
        return asdict(self)

    def save(self) -> None:
        """Save project state to disk"""
        # Create project directory structure
        project_dir = Path(f"projects/{self.id}")
        project_dir.mkdir(parents=True, exist_ok=True)

        for subdir in ['images', 'audio', 'temp']:
            (project_dir / subdir).mkdir(exist_ok=True)

        # Save project metadata
        metadata_path = project_dir / "project.json"
        with open(metadata_path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, project_id: str) -> Optional['Project']:
        """Load project from disk"""
        try:
            project_path = Path(f"projects/{project_id}/project.json")
            if not project_path.exists():
                return None

            with open(project_path) as f:
                data = json.load(f)
                return cls(**data)
        except Exception as e:
            print(f"Error loading project {project_id}: {e}")
            return None

    def update(self) -> None:
        """Update project timestamp and save"""
        self.updated_at = time.time()
        self.save()

    def add_image(self, image_path: str) -> None:
        """Add an image to the project"""
        self.images.append(image_path)
        self.update()

    def add_audio(self, audio_path: str) -> None:
        """Add an audio file to the project"""
        self.audio_files.append(audio_path)
        self.update()

    def add_script(self, script: str) -> None:
        """Add a script to the project"""
        self.scripts.append(script)
        self.update()

    def set_title(self, title: str) -> None:
        """Set project title"""
        self.title = title
        self.update()

    def add_metadata(self, key: str, value: any) -> None:
        """Add metadata to the project"""
        self.metadata[key] = value
        self.update()


class ProjectManager:
    def __init__(self):
        self.projects_dir = Path("projects")
        self.projects_dir.mkdir(exist_ok=True)

    def list_projects(self) -> List[Project]:
        """List all available projects"""
        projects = []
        for project_dir in self.projects_dir.iterdir():
            if project_dir.is_dir():
                project = Project.load(project_dir.name)
                if project:
                    projects.append(project)
        return sorted(projects, key=lambda p: p.created_at, reverse=True)

    def get_project(self, project_id: str) -> Optional[Project]:
        """Get a specific project by ID"""
        return Project.load(project_id)

    def create_project(self, subject: str, duration: int) -> Project:
        """Create a new project"""
        project = Project.create(subject, duration)
        project.save()
        return project

    def delete_project(self, project_id: str) -> bool:
        """Delete a project and its files"""
        try:
            project_dir = self.projects_dir / project_id
            if project_dir.exists():
                # Use shutil.rmtree to recursively delete directory and contents
                shutil.rmtree(project_dir)
                return True
            return False
        except Exception as e:
            print(f"Error deleting project {project_id}: {e}")
            return False
