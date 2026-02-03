"""
教案生成 API 端点（带进度推送）
"""
import asyncio
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import AsyncGenerator

from ..database import get_db
from ..deps import get_course_for_user, get_current_user
from ..docx_service import render_lesson_plan_docx
from ..knowledge_service import retrieve_course_context, build_ai_context_prompt
from ..models import Course, CourseDocument, User
from ..utils.sse import sse_event, sse_response


router = APIRouter(prefix="/api/courses", tags=["教案生成"])


@router.post("/{course_id}/generate-lesson-plan/stream")
async def generate_lesson_plan_stream(
    sequence: int,
    documents: str,
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
                documents=documents,
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
            
            # 保存到数据库
            document = CourseDocument(
                course_id=course.id,
                doc_type="lesson_plan",
                title=f"教案 - 第{sequence}次课",
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
            CourseDocument.doc_type == "lesson_plan",
        )
        .order_by(CourseDocument.lesson_number)
        .all()
    )
    
    return {
        "documents": [
            {
                "id": doc.id,
                "title": doc.title,
                "lesson_number": doc.lesson_number,
                "created_at": doc.created_at,
                "file_url": doc.file_url,
            }
            for doc in documents
        ]
    }
