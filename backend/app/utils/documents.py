"""
Document helper utilities.
"""
from pathlib import Path
from typing import Optional

from ..models import CourseDocument
from ..utils.paths import UPLOADS_DIR, course_documents_dir


def resolve_document_file_path(document: CourseDocument) -> Optional[Path]:
    if not document.file_url:
        return None

    file_url = document.file_url
    if file_url.startswith("/uploads/"):
        return UPLOADS_DIR / file_url.lstrip("/uploads/")

    if file_url.startswith("/api/documents/files/"):
        parts = file_url.split("/")
        if len(parts) >= 6:
            course_id = parts[-2]
            filename = parts[-1]
            return course_documents_dir(course_id) / filename

    if file_url.startswith("uploads/") or file_url.startswith("generated/"):
        return UPLOADS_DIR / file_url.lstrip("/")

    return None


def attach_file_exists(documents: list[CourseDocument]) -> list[CourseDocument]:
    for doc in documents:
        file_path = resolve_document_file_path(doc)
        if not doc.file_url:
            doc.file_exists = False
        else:
            doc.file_exists = bool(file_path and file_path.exists())
    return documents
