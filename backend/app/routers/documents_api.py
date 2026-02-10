"""
文档管理 API
"""
import hashlib
import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_course_for_user, get_current_user, get_document_for_user
from ..utils.paths import UPLOADS_DIR, course_documents_dir, ensure_dir
from ..utils.documents import attach_file_exists, resolve_document_file_path
from ..utils.plan_params import (
    extract_text_from_docx_bytes,
    extract_text_from_plain_bytes,
    parse_plan_params_json,
)
from ..ai_service import parse_teaching_plan_params
from ..models import (
    Course,
    CourseDocument,
    DocumentCreateRequest,
    DocumentResponse,
    DocumentUpdateRequest,
    User,
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
        plan_params=document_data.plan_params,
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
    user: User = Depends(get_current_user),
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

    if doc_type == "lesson" and lesson_number is None:
        raise HTTPException(status_code=400, detail="教案上传必须指定课次")

    if doc_type == "plan":
        upload_dir = UPLOADS_DIR / "generated"
    else:
        upload_dir = course_documents_dir(course.id)

    ensure_dir(upload_dir)

    content = file.file.read()
    file_md5 = hashlib.md5(content).hexdigest()
    filename = f"{file_md5}{file_ext}"
    file_path = Path(upload_dir) / filename

    existing_doc = None
    if doc_type == "plan":
        existing_doc = (
            db.query(CourseDocument)
            .filter(CourseDocument.course_id == course.id, CourseDocument.doc_type == "plan")
            .first()
        )
    elif doc_type == "lesson":
        existing_doc = (
            db.query(CourseDocument)
            .filter(
                CourseDocument.course_id == course.id,
                CourseDocument.doc_type.in_(["lesson", "lesson_plan"]),
                CourseDocument.lesson_number == lesson_number,
            )
            .first()
        )

    plan_params_json: Optional[str] = None
    if doc_type == "plan":
        if not user.ai_api_key or not user.ai_base_url:
            raise HTTPException(status_code=400, detail="请先配置 AI API")

        if file_ext not in [".docx", ".md"]:
            raise HTTPException(status_code=400, detail="授课计划解析仅支持 .docx 或 .md 文件")

        if file_ext == ".docx":
            extracted_text = extract_text_from_docx_bytes(content)
        else:
            extracted_text = extract_text_from_plain_bytes(content)

        if not extracted_text.strip():
            raise HTTPException(status_code=400, detail="授课计划解析失败：文档内容为空")

        try:
            plan_params = await parse_teaching_plan_params(
                extracted_text=extracted_text,
                course_total_hours=course.total_hours,
                api_key=user.ai_api_key,
                base_url=user.ai_base_url,
                model=user.ai_model_name or "gpt-4",
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"授课计划解析失败：{str(e)}")

        if not plan_params or not plan_params.get("schedule"):
            raise HTTPException(status_code=400, detail="未解析到授课计划课次列表")

        plan_params_json = json.dumps(plan_params, ensure_ascii=False)

    if existing_doc:
        old_file_path = resolve_document_file_path(existing_doc)
        if old_file_path and old_file_path.exists():
            old_file_path.unlink()

    with open(file_path, "wb") as buffer:
        buffer.write(content)

    if doc_type == "plan":
        file_url = f"/uploads/generated/{filename}"
    else:
        file_url = f"/api/documents/files/{course.id}/{filename}"

    if doc_type == "plan":
        title = f"《{course.name}》授课计划"
    elif doc_type == "lesson":
        plan_doc = (
            db.query(CourseDocument)
            .filter(CourseDocument.course_id == course.id, CourseDocument.doc_type == "plan")
            .order_by(CourseDocument.created_at.desc())
            .first()
        )
        week_number = lesson_number
        if plan_doc:
            schedule = None
            if plan_doc.plan_params:
                parsed = parse_plan_params_json(plan_doc.plan_params)
                if isinstance(parsed, dict):
                    schedule = parsed.get("schedule")
            elif plan_doc.content:
                try:
                    plan_data = json.loads(plan_doc.content)
                    schedule = plan_data.get("schedule") if isinstance(plan_data, dict) else None
                except Exception:
                    schedule = None

            if schedule:
                for item in schedule:
                    if isinstance(item, dict) and item.get("order") == lesson_number:
                        try:
                            week_number = int(item.get("week"))
                        except Exception:
                            week_number = lesson_number
                        break
        title = f"{lesson_number + 1}广东碧桂园职业学院教案（主页）-第{week_number}周教案"

    try:
        if existing_doc:
            existing_doc.doc_type = "lesson" if doc_type == "lesson" else doc_type
            existing_doc.title = title
            existing_doc.file_url = file_url
            if plan_params_json:
                existing_doc.plan_params = plan_params_json
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
                plan_params=plan_params_json,
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

    return attach_file_exists(documents)


@router.get("/courses/{course_id}/documents/type/{doc_type}", response_model=list[DocumentResponse])
async def get_documents_by_type(
    doc_type: str,
    course: Course = Depends(get_course_for_user),
    db: Session = Depends(get_db),
):
    """获取指定类型的文档列表"""
    query = db.query(CourseDocument).filter(CourseDocument.course_id == course.id)
    if doc_type == "lesson":
        query = query.filter(CourseDocument.doc_type.in_(["lesson", "lesson_plan"]))
    else:
        query = query.filter(CourseDocument.doc_type == doc_type)

    documents = (
        query.order_by(CourseDocument.lesson_number)
        .all()
    )

    return attach_file_exists(documents)


@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(
    document: CourseDocument = Depends(get_document_for_user),
):
    """获取单个文档详情"""
    attach_file_exists([document])
    return document


@router.get("/documents/{document_id}/download")
async def download_document_by_id(
    document: CourseDocument = Depends(get_document_for_user),
):
    """下载文档文件（带正确文件名）"""
    file_path = resolve_document_file_path(document)
    if not file_path or not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")

    filename = document.title or file_path.name
    filename = filename.replace("/", "_").replace("\\", "_")
    ext = file_path.suffix
    if ext and not filename.endswith(ext):
        filename = f"{filename}{ext}"

    return FileResponse(
        str(file_path),
        media_type="application/octet-stream",
        filename=filename,
    )


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
    file_path = resolve_document_file_path(document)
    if file_path:
        try:
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
