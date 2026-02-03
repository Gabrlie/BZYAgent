"""
Path helpers
"""
from pathlib import Path
from typing import Union


BACKEND_DIR = Path(__file__).resolve().parents[2]
UPLOADS_DIR = BACKEND_DIR / "uploads"
GENERATED_DIR = UPLOADS_DIR / "generated"
TEMPLATES_DIR = BACKEND_DIR / "templates"


def ensure_dir(path: Path) -> Path:
    """Ensure a directory exists and return it."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def course_documents_dir(course_id: Union[int, str]) -> Path:
    """Get course documents directory."""
    return UPLOADS_DIR / "courses" / str(course_id) / "documents"
