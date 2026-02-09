"""
授课计划 API 端点（带进度推送）
"""
import asyncio
import json
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from ..database import get_db
from ..deps import get_course_for_user, get_current_user
from ..docx_service import render_docx_template
from ..models import Course, CourseDocument, User
from ..teaching_plan_service import generate_teaching_plan_schedule
from ..utils.documents import attach_file_exists, resolve_document_file_path
from ..utils.sse import sse_event, sse_response


router = APIRouter(prefix="/api/courses", tags=["授课计划生成"])


@router.get("/{course_id}/generate-teaching-plan/stream")
async def generate_teaching_plan_stream(
    course: Course = Depends(get_course_for_user),
    user: User = Depends(get_current_user),
    teacher_name: str = Query(..., description="授课教师"),
    total_weeks: int = Query(18, description="总周数"),
    hour_per_class: int = Query(4, description="单次学时"),
    classes_per_week: int = Query(1, description="每周上课次数"),
    final_review: bool = Query(True, description="最后一次课为复习考核"),
    first_week_classes: int = Query(1, description="第一周上课次数"),
    skip_slots: Optional[str] = Query(None, description="不上课的周次与课次 JSON 数组"),
    token: str = Query(None, description="认证 Token（用于 SSE）"),
    db: Session = Depends(get_db)
):
    """
    生成授课计划（带进度推送）
    
    SSE 推送 4 个阶段：
    1. 验证课程信息 (10%)
    2. 生成授课计划内容 (70%)
    3. 组装数据并渲染模板 (90%)
    4. 保存到数据库 (100%)
    """
    # 检查 AI 配置
    if not user.ai_api_key or not user.ai_base_url:
        raise HTTPException(status_code=400, detail="请先配置 AI API")
    
    async def event_generator():
        try:
            # 阶段 1: 验证课程信息
            yield sse_event(
                {
                    "stage": "validating",
                    "progress": 10,
                    "message": "正在检查课程信息...",
                }
            )
            
            # 检查课程目录
            if not course.course_catalog:
                yield sse_event(
                    {
                        "stage": "error",
                        "progress": 0,
                        "message": "课程目录为空，请先在课程详情页编辑课程目录",
                    }
                )
                return
            
            await asyncio.sleep(0.5)
            
            # 阶段 2: 生成授课计划内容
            yield sse_event(
                {
                    "stage": "generating",
                    "progress": 30,
                    "message": "正在生成授课计划内容...",
                }
            )
            
            # 计算学时
            theory_hours = course.total_hours - course.practice_hours
            
            skip_slots_payload = []
            if skip_slots:
                try:
                    parsed = json.loads(skip_slots)
                    if isinstance(parsed, list):
                        skip_slots_payload = parsed
                    else:
                        raise ValueError("排课调整参数格式错误")
                except Exception:
                    yield sse_event(
                        {
                            "stage": "error",
                            "progress": 0,
                            "message": "排课调整参数格式错误，请检查不上课的周次与次数设置。",
                        }
                    )
                    return

            schedule = await generate_teaching_plan_schedule(
                course_catalog=course.course_catalog,
                course_name=course.name,
                total_hours=course.total_hours,
                theory_hours=theory_hours,
                practice_hours=course.practice_hours,
                hour_per_class=hour_per_class,
                total_weeks=total_weeks,
                classes_per_week=classes_per_week,
                final_review=final_review,
                api_key=user.ai_api_key,
                base_url=user.ai_base_url,
                model=user.ai_model_name or "gpt-4",
                first_week_classes=first_week_classes,
                skip_slots=skip_slots_payload
            )
            
            yield sse_event(
                {
                    "stage": "generating",
                    "progress": 70,
                    "message": f"AI 生成完成，共 {len(schedule)} 次课",
                }
            )
            
            # 阶段 3: 组装数据并渲染
            yield sse_event(
                {
                    "stage": "rendering",
                    "progress": 85,
                    "message": "正在渲染 Word 文档...",
                }
            )
            
            # 组装模板数据
            template_data = {
                "academic_year": course.semester,  # 学年
                "course_name": course.name,
                "target_classes": course.class_name,
                "teacher_name": teacher_name,
                "total_hours": course.total_hours,
                "theory_hours": theory_hours,
                "practice_hours": course.practice_hours,
                "schedule": schedule,
            }
            
            # 渲染 Word 文档
            file_path = render_docx_template(
                template_name="授课计划模板.docx",
                data=template_data,
                course_id=course.id
            )
            
            # 阶段 4: 保存到数据库
            yield sse_event(
                {
                    "stage": "saving",
                    "progress": 95,
                    "message": "正在保存到数据库...",
                }
            )
            
            # 检查是否已有授课计划，如有则覆盖
            existing_doc = db.query(CourseDocument).filter(
                CourseDocument.course_id == course.id,
                CourseDocument.doc_type == "plan"
            ).first()
            
            plan_title = f"《{course.name}》授课计划"

            if existing_doc:
                old_file_path = resolve_document_file_path(existing_doc)
                if old_file_path and old_file_path.exists():
                    old_file_path.unlink()
                
                # 更新记录
                existing_doc.title = plan_title
                existing_doc.content = json.dumps(template_data, ensure_ascii=False)
                existing_doc.file_url = f"/uploads/{file_path}"
                db.commit()
                db.refresh(existing_doc)
                document = existing_doc
            else:
                # 创建新记录
                document = CourseDocument(
                    course_id=course.id,
                    doc_type="plan",
                    title=plan_title,
                    content=json.dumps(template_data, ensure_ascii=False),
                    file_url=f"/uploads/{file_path}",
                )
                db.add(document)
                db.commit()
                db.refresh(document)
            
            # 完成
            yield sse_event(
                {
                    "stage": "completed",
                    "progress": 100,
                    "message": "授课计划生成完成！",
                    "document_id": document.id,
                    "file_url": document.file_url,
                    "data": template_data,
                }
            )
            
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            print(f"生成失败：{error_detail}")
            yield sse_event(
                {"stage": "error", "progress": 0, "message": f"生成失败：{str(e)}"}
            )
    
    return sse_response(event_generator())


@router.get("/{course_id}/teaching-plans")
async def get_teaching_plans(
    course: Course = Depends(get_course_for_user),
    db: Session = Depends(get_db),
):
    """获取课程的授课计划列表"""
    documents = (
        db.query(CourseDocument)
        .filter(CourseDocument.course_id == course.id, CourseDocument.doc_type == "plan")
        .order_by(CourseDocument.created_at.desc())
        .all()
    )

    attach_file_exists(documents)
    return {
        "documents": [
            {
                "id": doc.id,
                "title": doc.title,
                "created_at": doc.created_at,
                "file_url": doc.file_url,
                "file_exists": doc.file_exists,
            }
            for doc in documents
        ]
    }
