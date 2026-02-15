"""
Dashboard summary API
"""
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Course, CourseDocument, CopyrightProject, User


router = APIRouter(prefix="/api/dashboard", tags=["仪表盘"])


@router.get("/summary")
def get_dashboard_summary(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    course_count = (
        db.query(func.count(Course.id)).filter(Course.user_id == user.id).scalar() or 0
    )

    base_query = (
        db.query(CourseDocument)
        .join(Course, CourseDocument.course_id == Course.id)
        .filter(Course.user_id == user.id)
    )

    document_count = base_query.count()
    teaching_plan_count = base_query.filter(CourseDocument.doc_type == "plan").count()
    lesson_plan_count = base_query.filter(
        CourseDocument.doc_type.in_(["lesson", "lesson_plan"])
    ).count()
    courseware_count = base_query.filter(CourseDocument.doc_type == "courseware").count()

    copyright_project_count = (
        db.query(func.count(CopyrightProject.id))
        .filter(CopyrightProject.user_id == user.id)
        .scalar()
        or 0
    )

    ai_configured = bool(user.ai_api_key and user.ai_base_url)

    return {
        "course_count": course_count,
        "document_count": document_count,
        "teaching_plan_count": teaching_plan_count,
        "lesson_plan_count": lesson_plan_count,
        "courseware_count": courseware_count,
        "copyright_project_count": copyright_project_count,
        "ai_configured": ai_configured,
    }
