"""
教案生成 API 端点（带进度推送）
"""
import asyncio
import json
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import AsyncGenerator

from ..database import get_db
from ..deps import get_course_for_user, get_current_user
from ..docx_service import render_lesson_plan_docx
from ..knowledge_service import retrieve_course_context, build_ai_context_prompt
from ..models import Course, CourseDocument, User
from ..utils.documents import attach_file_exists, resolve_document_file_path
from ..utils.sse import sse_event, sse_response


router = APIRouter(prefix="/api/courses", tags=["教案生成"])


@router.api_route("/{course_id}/generate-lesson-plan/stream", methods=["GET", "POST"])
async def generate_lesson_plan_stream(
    sequence: int = Query(..., description="授课顺序"),
    course: Course = Depends(get_course_for_user),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    生成教案（带进度推送）
    
    使用 SSE 推送 4 个阶段的进度：
    1. 解析需求 (10%)
    2. 检索知识 (30%)
    3. AI 生成 (70%)
    4. 填充模板 (90%)
    5. 完成 (100%)
    """
    from ..ai_service import generate_lesson_plan_content
    
    # 检查 AI 配置
    if not user.ai_api_key or not user.ai_base_url:
        raise HTTPException(status_code=400, detail="请先配置 AI API")

    # 获取授课计划文档（教案生成所需的核心输入）
    plan_docs = (
        db.query(CourseDocument)
        .filter(CourseDocument.course_id == course.id, CourseDocument.doc_type == "plan")
        .order_by(CourseDocument.created_at.desc())
        .all()
    )

    if not plan_docs:
        raise HTTPException(status_code=400, detail="请先创建授课计划")

    documents_text = "\n\n".join([doc.content or "" for doc in plan_docs]).strip()

    def resolve_week_number() -> int:
        for doc in plan_docs:
            if not doc.content:
                continue
            try:
                data = json.loads(doc.content)
            except Exception:
                continue
            schedule = data.get("schedule") if isinstance(data, dict) else None
            if not schedule:
                continue
            for item in schedule:
                if isinstance(item, dict) and item.get("order") == sequence:
                    try:
                        return int(item.get("week"))
                    except Exception:
                        return sequence
        return sequence
    
    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            # 阶段 1: 解析需求
            yield sse_event(
                {
                    "stage": "analyzing",
                    "progress": 10,
                    "message": "正在分析教案生成需求...",
                }
            )
            await asyncio.sleep(0.5)
            
            # 阶段 2: 检索知识库
            yield sse_event(
                {
                    "stage": "retrieving",
                    "progress": 30,
                    "message": "正在检索课程信息...",
                }
            )
            
            context = retrieve_course_context(db, course.id)
            context_prompt = build_ai_context_prompt(context)
            await asyncio.sleep(0.5)
            
            # 阶段 3: AI 生成内容
            yield sse_event(
                {
                    "stage": "generating",
                    "progress": 50,
                    "message": "正在调用 AI 生成教案内容...",
                }
            )
            
            lesson_plan_data = await generate_lesson_plan_content(
                sequence=sequence,
                documents=documents_text,
                course_context=context_prompt,
                api_key=user.ai_api_key,
                base_url=user.ai_base_url,
                model=user.ai_model_name or "gpt-4"
            )
            
            yield sse_event(
                {
                    "stage": "generating",
                    "progress": 70,
                    "message": "AI 生成完成，正在处理数据...",
                }
            )
            
            # 阶段 4: 填充模板
            yield sse_event(
                {
                    "stage": "rendering",
                    "progress": 85,
                    "message": "正在填充 Word 模板...",
                }
            )
            
            # 渲染 Word 文档
            file_path = render_lesson_plan_docx(lesson_plan_data, course.id)
            
            week_number = resolve_week_number()
            title = f"{sequence + 1}广东碧桂园职业学院教案（主页）-第{week_number}周教案"

            # 保存到数据库（同课次存在则覆盖）
            existing_doc = (
                db.query(CourseDocument)
                .filter(
                    CourseDocument.course_id == course.id,
                    CourseDocument.doc_type.in_(["lesson", "lesson_plan"]),
                    CourseDocument.lesson_number == sequence,
                )
                .first()
            )

            if existing_doc:
                old_file_path = resolve_document_file_path(existing_doc)
                if old_file_path and old_file_path.exists():
                    old_file_path.unlink()

                existing_doc.doc_type = "lesson"
                existing_doc.title = title
                existing_doc.content = json.dumps(lesson_plan_data, ensure_ascii=False)
                existing_doc.file_url = f"/uploads/{file_path}"
                existing_doc.lesson_number = sequence
                db.commit()
                db.refresh(existing_doc)
                document = existing_doc
            else:
                document = CourseDocument(
                    course_id=course.id,
                    doc_type="lesson",
                    title=title,
                    content=json.dumps(lesson_plan_data, ensure_ascii=False),
                    file_url=f"/uploads/{file_path}",
                    lesson_number=sequence,
                )

                db.add(document)
                db.commit()
                db.refresh(document)
            
            # 完成
            yield sse_event(
                {
                    "stage": "completed",
                    "progress": 100,
                    "message": "教案生成完成！",
                    "document_id": document.id,
                    "data": lesson_plan_data,
                }
            )
            
        except Exception as e:
            yield sse_event(
                {"stage": "error", "progress": 0, "message": f"生成失败：{str(e)}"}
            )

    return sse_response(event_generator())


@router.get("/{course_id}/lesson-plans")
async def get_lesson_plans(
    course: Course = Depends(get_course_for_user),
    db: Session = Depends(get_db),
):
    """获取课程的所有教案列表"""
    documents = (
        db.query(CourseDocument)
        .filter(
            CourseDocument.course_id == course.id,
            CourseDocument.doc_type.in_(["lesson", "lesson_plan"]),
        )
        .order_by(CourseDocument.lesson_number)
        .all()
    )
    attach_file_exists(documents)

    return {
        "documents": [
            {
                "id": doc.id,
                "title": doc.title,
                "lesson_number": doc.lesson_number,
                "created_at": doc.created_at,
                "file_url": doc.file_url,
                "file_exists": doc.file_exists,
            }
            for doc in documents
        ]
    }
