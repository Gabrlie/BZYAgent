"""
文档管理 API
"""
import shutil
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_course_for_user, get_document_for_user
from ..utils.paths import UPLOADS_DIR, course_documents_dir, ensure_dir
from ..models import (
    Course,
    CourseDocument,
    DocumentCreateRequest,
    DocumentResponse,
    DocumentUpdateRequest,
)


router = APIRouter(prefix="/api", tags=["文档管理"])


@router.post("/courses/{course_id}/documents", response_model=DocumentResponse)
async def create_document(
    document_data: DocumentCreateRequest,
    course: Course = Depends(get_course_for_user),
    db: Session = Depends(get_db),
):
    """创建文档 - 支持 AI 生成或上传文件"""
    document = CourseDocument(
        course_id=course.id,
        doc_type=document_data.doc_type,
        title=document_data.title,
        content=document_data.content,
        file_url=document_data.file_url,
        lesson_number=document_data.lesson_number,
    )

    try:
        db.add(document)
        db.commit()
        db.refresh(document)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"文档创建失败：{str(e)}")

    return document


@router.post("/courses/{course_id}/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    doc_type: str = File(...),
    title: str = File(...),
    lesson_number: Optional[int] = File(None),
    course: Course = Depends(get_course_for_user),
    db: Session = Depends(get_db),
):
    """上传文档文件 - 支持 .docx, .pdf, .pptx, .md，最大 10MB"""
    allowed_extensions = [".docx", ".pdf", ".pptx", ".md"]
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型，仅支持：{', '.join(allowed_extensions)}",
        )

    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)

    if file_size > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件大小不能超过 10MB")

    if doc_type == "plan":
        upload_dir = UPLOADS_DIR / "generated"
        filename = f"授课计划模板_{course.id}_uploaded{file_ext}"
    else:
        upload_dir = course_documents_dir(course.id)
        filename = f"{uuid.uuid4()}{file_ext}"

    ensure_dir(upload_dir)
    file_path = Path(upload_dir) / filename

    existing_doc = None
    if doc_type == "plan":
        existing_doc = (
            db.query(CourseDocument)
            .filter(CourseDocument.course_id == course.id, CourseDocument.doc_type == "plan")
            .first()
        )

        if existing_doc and existing_doc.file_url:
            old_file_path = UPLOADS_DIR / existing_doc.file_url.lstrip("/uploads/")
            if old_file_path.exists():
                old_file_path.unlink()

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    if doc_type == "plan":
        file_url = f"/uploads/generated/{filename}"
    else:
        file_url = f"/api/documents/files/{course.id}/{filename}"

    try:
        if existing_doc:
            existing_doc.title = title
            existing_doc.file_url = file_url
            if lesson_number is not None:
                existing_doc.lesson_number = lesson_number
            db.commit()
            db.refresh(existing_doc)
            document = existing_doc
        else:
            document = CourseDocument(
                course_id=course.id,
                doc_type=doc_type,
                title=title,
                file_url=file_url,
                lesson_number=lesson_number,
            )
            db.add(document)
            db.commit()
            db.refresh(document)
    except Exception as e:
        db.rollback()
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=400, detail=f"文档创建失败：{str(e)}")

    return {"message": "文件上传成功", "document": document}


@router.get("/courses/{course_id}/documents", response_model=list[DocumentResponse])
async def get_documents(
    course: Course = Depends(get_course_for_user),
    db: Session = Depends(get_db),
):
    """获取课程的所有文档列表"""
    documents = (
        db.query(CourseDocument)
        .filter(CourseDocument.course_id == course.id)
        .order_by(CourseDocument.doc_type, CourseDocument.lesson_number)
        .all()
    )

    return documents


@router.get("/courses/{course_id}/documents/type/{doc_type}", response_model=list[DocumentResponse])
async def get_documents_by_type(
    doc_type: str,
    course: Course = Depends(get_course_for_user),
    db: Session = Depends(get_db),
):
    """获取指定类型的文档列表"""
    documents = (
        db.query(CourseDocument)
        .filter(CourseDocument.course_id == course.id, CourseDocument.doc_type == doc_type)
        .order_by(CourseDocument.lesson_number)
        .all()
    )

    return documents


@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(
    document: CourseDocument = Depends(get_document_for_user),
):
    """获取单个文档详情"""
    return document


@router.put("/documents/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_data: DocumentUpdateRequest,
    document: CourseDocument = Depends(get_document_for_user),
    db: Session = Depends(get_db),
):
    """更新文档信息"""
    update_data = document_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(document, field, value)

    db.commit()
    db.refresh(document)

    return document


@router.delete("/documents/{document_id}")
async def delete_document(
    document: CourseDocument = Depends(get_document_for_user),
    db: Session = Depends(get_db),
):
    """删除文档 - 同时删除上传的文件"""
    if document.file_url:
        try:
            parts = document.file_url.split("/")
            if len(parts) >= 3:
                course_id = parts[-2]
                filename = parts[-1]
                file_path = course_documents_dir(course_id) / filename
                if file_path.exists():
                    file_path.unlink()
        except Exception as e:
            print(f"删除文件失败：{e}")

    db.delete(document)
    db.commit()

    return {"message": "文档删除成功"}


@router.get("/documents/files/{course_id}/{filename}")
async def download_document(
    filename: str,
    course: Course = Depends(get_course_for_user),
):
    """下载文档文件"""
    file_path = course_documents_dir(course.id) / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")

    return FileResponse(
        str(file_path),
        media_type="application/octet-stream",
        filename=filename,
    )
