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
from ..utils.plan_params import (
    parse_plan_params_json,
    build_plan_params_from_content,
    get_plan_item,
    compute_cumulative_hours,
)
from ..utils.sse import sse_event, sse_response
from ..ai_service import (
    generate_lesson_plan_content,
    regenerate_time_allocation,
    validate_time_allocation,
)


router = APIRouter(prefix="/api/courses", tags=["教案生成"])


LIST_TEXT_FIELDS = {
    "knowledge_goals",
    "ability_goals",
    "quality_goals",
    "teaching_focus",
    "teaching_difficulty",
    "review_content",
    "summary_content",
    "homework_content",
}


def _normalize_list_text(value: str) -> str:
    if not isinstance(value, str):
        return value
    lines = [line.rstrip() for line in value.splitlines() if line.strip()]
    if not lines:
        return value
    return "\n".join(lines) + "\n"


def _apply_list_newlines(data: dict) -> None:
    for key in LIST_TEXT_FIELDS:
        if key in data:
            data[key] = _normalize_list_text(data[key])


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
    # 检查 AI 配置
    if not user.ai_api_key or not user.ai_base_url:
        raise HTTPException(status_code=400, detail="请先配置 AI API")
    if course.course_type == "C":
        raise HTTPException(status_code=400, detail="C类课程教案暂未开发，请自行上传教案")

    # 获取授课计划文档（教案生成所需的核心输入）
    plan_docs = (
        db.query(CourseDocument)
        .filter(CourseDocument.course_id == course.id, CourseDocument.doc_type == "plan")
        .order_by(CourseDocument.created_at.desc())
        .all()
    )

    if not plan_docs:
        raise HTTPException(status_code=400, detail="请先创建授课计划")

    plan_doc = plan_docs[0]

    async def resolve_plan_params() -> dict:
        if not plan_doc.content:
            raise ValueError("当前授课计划为上传文档，无法用于教案生成，请使用系统生成授课计划")
        if plan_doc.plan_params:
            parsed = parse_plan_params_json(plan_doc.plan_params)
            if parsed and parsed.get("schedule"):
                return parsed

        if plan_doc.content:
            try:
                content_data = json.loads(plan_doc.content)
            except Exception:
                content_data = None
            if isinstance(content_data, dict):
                params = build_plan_params_from_content(content_data)
                if params and params.get("schedule"):
                    plan_doc.plan_params = json.dumps(params, ensure_ascii=False)
                    db.commit()
                    return params
        raise ValueError("授课计划内容格式不完整，请重新生成授课计划")
    
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
            
            # 阶段 2: 解析授课计划参数
            yield sse_event(
                {
                    "stage": "parsing",
                    "progress": 20,
                    "message": "正在解析授课计划参数...",
                }
            )

            use_generated_plan = True
            plan_item_payload = None
            system_fields = None

            plan_params = await resolve_plan_params()
            schedule = plan_params.get("schedule") if isinstance(plan_params, dict) else None
            if not isinstance(schedule, list) or not schedule:
                raise ValueError("授课计划参数缺失，请重新生成授课计划")

            plan_item = get_plan_item(schedule, sequence)
            if not plan_item:
                raise ValueError("授课顺序不在授课计划范围内")

            hour_per_class = plan_params.get("hour_per_class")
            if not isinstance(hour_per_class, int) or hour_per_class <= 0:
                hour_per_class = plan_item.get("hour") if isinstance(plan_item.get("hour"), int) else None

            if not isinstance(hour_per_class, int) or hour_per_class <= 0:
                raise ValueError("授课计划缺少单次学时信息")

            hours = plan_item.get("hour") if isinstance(plan_item.get("hour"), int) else hour_per_class
            week_number = plan_item.get("week") if isinstance(plan_item.get("week"), int) else sequence
            cumulative_hours = compute_cumulative_hours(schedule, sequence, default_hour=hour_per_class)

            system_fields = {
                "project_name": plan_item.get("title") or plan_item.get("project_name") or f"第{sequence}次课",
                "week": week_number,
                "sequence": sequence,
                "hours": hours,
                "total_hours": cumulative_hours,
            }

            plan_item_payload = {
                "week": week_number,
                "order": sequence,
                "title": plan_item.get("title") or "",
                "tasks": plan_item.get("tasks") or "",
                "hour": hours,
            }

            # 阶段 3: 检索知识库
            yield sse_event(
                {
                    "stage": "retrieving",
                    "progress": 30,
                    "message": "正在检索课程信息...",
                }
            )
            
            context = retrieve_course_context(db, course.id)
            if context.get("documents"):
                context["documents"] = [
                    doc for doc in context["documents"] if doc.get("type") != "plan"
                ]
            context_prompt = build_ai_context_prompt(context)
            await asyncio.sleep(0.5)
            
            # 阶段 4: AI 生成内容
            yield sse_event(
                {
                    "stage": "generating",
                    "progress": 50,
                    "message": "正在调用 AI 生成教案内容...",
                }
            )
            
            lesson_plan_data = await generate_lesson_plan_content(
                sequence=sequence,
                plan_item=plan_item_payload,
                system_fields=system_fields,
                document_full_text=plan_doc.content or "",
                course_context=context_prompt,
                api_key=user.ai_api_key,
                base_url=user.ai_base_url,
                model=user.ai_model_name or "gpt-4",
                strict_mode=use_generated_plan,
            )

            # 覆盖系统字段
            lesson_plan_data["project_name"] = system_fields["project_name"]
            lesson_plan_data["week"] = system_fields["week"]
            lesson_plan_data["sequence"] = system_fields["sequence"]
            lesson_plan_data["hours"] = system_fields["hours"]
            lesson_plan_data["total_hours"] = system_fields["total_hours"]

            # 列表字段统一换行
            _apply_list_newlines(lesson_plan_data)

            # 时间分配校验
            ok, reason = validate_time_allocation(lesson_plan_data, system_fields["hours"])
            if not ok:
                for _ in range(2):
                    allocation = await regenerate_time_allocation(
                        lesson_plan_data=lesson_plan_data,
                        hours=system_fields["hours"],
                        api_key=user.ai_api_key,
                        base_url=user.ai_base_url,
                        model=user.ai_model_name or "gpt-4",
                    )
                    if isinstance(allocation, dict):
                        if isinstance(allocation.get("review_time"), int):
                            lesson_plan_data["review_time"] = allocation.get("review_time")
                        if isinstance(allocation.get("new_lessons"), list) and isinstance(
                            lesson_plan_data.get("new_lessons"), list
                        ):
                            for idx, item in enumerate(lesson_plan_data["new_lessons"]):
                                if idx < len(allocation["new_lessons"]):
                                    time_value = allocation["new_lessons"][idx].get("time")
                                    if isinstance(time_value, int):
                                        item["time"] = time_value
                    ok, reason = validate_time_allocation(lesson_plan_data, system_fields["hours"])
                    if ok:
                        break
            if not ok:
                raise ValueError(f"时间分配校验失败：{reason}")
            
            yield sse_event(
                {
                    "stage": "generating",
                    "progress": 70,
                    "message": "AI 生成完成，正在处理数据...",
                }
            )
            
            # 阶段 5: 填充模板
            yield sse_event(
                {
                    "stage": "rendering",
                    "progress": 85,
                    "message": "正在填充 Word 模板...",
                }
            )
            
            # 渲染 Word 文档
            file_path = render_lesson_plan_docx(lesson_plan_data, course.id)
            
            title = f"{sequence + 1}广东碧桂园职业学院教案（主页）-第{system_fields['week']}周教案"

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
