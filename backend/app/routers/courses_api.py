"""
课程管理 API
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_course_for_user, get_current_user
from ..models import (
    Course,
    CourseCreateRequest,
    CourseResponse,
    CourseUpdateRequest,
    CourseWithDocumentsResponse,
    CourseDocument,
    User,
    calculate_semester,
)


router = APIRouter(prefix="/api/courses", tags=["课程管理"])


@router.post("", response_model=CourseResponse)
async def create_course(
    course_data: CourseCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    创建课程

    - 如果未提供学期，将自动根据当前日期计算
    - 所有教材信息字段必填
    """
    semester = course_data.semester if course_data.semester else calculate_semester()

    course = Course(
        user_id=user.id,
        name=course_data.name,
        semester=semester,
        class_name=course_data.class_name,
        total_hours=course_data.total_hours,
        practice_hours=course_data.practice_hours,
        course_type=course_data.course_type,
        textbook_isbn=course_data.textbook_isbn,
        textbook_name=course_data.textbook_name,
        textbook_image=course_data.textbook_image,
        textbook_publisher=course_data.textbook_publisher,
        textbook_link=course_data.textbook_link,
        course_catalog=course_data.course_catalog,
    )

    db.add(course)
    db.commit()
    db.refresh(course)

    return course


@router.get("", response_model=list[CourseResponse])
async def get_courses(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取当前用户的所有课程列表

    按创建时间倒序排列
    """
    courses = (
        db.query(Course)
        .filter(Course.user_id == user.id)
        .order_by(Course.created_at.desc())
        .all()
    )

    return courses


@router.get("/{course_id}", response_model=CourseWithDocumentsResponse)
async def get_course(
    course: Course = Depends(get_course_for_user),
    db: Session = Depends(get_db),
):
    """
    获取单个课程详情，包含所有文档
    """
    documents = (
        db.query(CourseDocument)
        .filter(CourseDocument.course_id == course.id)
        .order_by(CourseDocument.created_at.desc())
        .all()
    )

    return {"course": course, "documents": documents}


@router.put("/{course_id}", response_model=CourseResponse)
async def update_course(
    course_data: CourseUpdateRequest,
    course: Course = Depends(get_course_for_user),
    db: Session = Depends(get_db),
):
    """
    更新课程信息

    只更新提供的字段，未提供的字段保持不变
    """
    update_data = course_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(course, field, value)

    db.commit()
    db.refresh(course)

    return course


@router.delete("/{course_id}")
async def delete_course(
    course: Course = Depends(get_course_for_user),
    db: Session = Depends(get_db),
):
    """
    删除课程

    会级联删除该课程下的所有文档
    """
    db.delete(course)
    db.commit()

    return {"message": "课程删除成功"}
