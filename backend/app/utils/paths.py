"""
Path helpers
"""
from pathlib import Path
from typing import Union


BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_DIR = BACKEND_DIR.parent
DATA_DIR = PROJECT_DIR / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
GENERATED_DIR = UPLOADS_DIR / "generated"
TEMPLATES_DIR = BACKEND_DIR / "templates"
COPYRIGHT_DIR = DATA_DIR / "copyright"
COPYRIGHT_PROJECTS_DIR = COPYRIGHT_DIR / "projects"
COPYRIGHT_ZIPS_DIR = COPYRIGHT_DIR / "zips"
FRONTEND_DIST_DIR = PROJECT_DIR / "frontend" / "dist"


def ensure_dir(path: Path) -> Path:
    """Ensure a directory exists and return it."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def course_documents_dir(course_id: Union[int, str]) -> Path:
    """Get course documents directory."""
    return UPLOADS_DIR / "courses" / str(course_id) / "documents"
