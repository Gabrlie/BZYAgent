"""
API dependencies
"""
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from .database import get_db
from .models import Course, CourseDocument, User, CopyrightProject


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """获取当前登录用户（依赖 JWT 中间件注入的用户名）"""
    username = request.state.username
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


def get_course_for_user(
    course_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Course:
    """获取当前用户的课程"""
    course = (
        db.query(Course)
        .filter(Course.id == course_id, Course.user_id == user.id)
        .first()
    )
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    return course


def get_document_for_user(
    document_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CourseDocument:
    """获取当前用户的文档（校验归属课程）"""
    document = db.query(CourseDocument).filter(CourseDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")

    course = (
        db.query(Course)
        .filter(Course.id == document.course_id, Course.user_id == user.id)
        .first()
    )
    if not course:
        raise HTTPException(status_code=403, detail="无权访问此文档")

    return document


def get_copyright_project_for_user(
    project_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CopyrightProject:
    """获取当前用户的软著项目"""
    project = (
        db.query(CopyrightProject)
        .filter(CopyrightProject.id == project_id, CopyrightProject.user_id == user.id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="软著项目不存在")
    return project
