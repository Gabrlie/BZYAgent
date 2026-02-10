"""
数据库模型定义
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel
from datetime import datetime as dt

Base = declarative_base()


# SQLAlchemy ORM 模型
class User(Base):
    """用户表模型"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # AI 配置字段
    ai_api_key = Column(String(255), nullable=True)
    ai_base_url = Column(String(255), nullable=True)
    ai_model_name = Column(String(100), default="gpt-3.5-turbo")
    
    # 关系
    messages = relationship("Message", back_populates="user", cascade="all, delete-orphan")
    courses = relationship("Course", back_populates="user", cascade="all, delete-orphan")


class Message(Base):
    """聊天消息表模型"""
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关系
    user = relationship("User", back_populates="messages")


def calculate_semester() -> str:
    """
    根据当前日期自动计算学期
    1-8月: {上一年}—{当前年}学年度第 2 学期
    9-12月: {当前年}—{下一年}学年度第 1 学期
    """
    now = dt.now()
    year = now.year
    month = now.month
    
    if month >= 9:  # 9-12月
        return f"{year}—{year + 1}学年度第 1 学期"
    else:  # 1-8月
        return f"{year - 1}—{year}学年度第 2 学期"


class Course(Base):
    """课程表模型"""
    __tablename__ = "courses"
    
    # 主键和外键
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # 必填字段
    name = Column(String(200), nullable=False)  # 课程名称
    semester = Column(String(50), nullable=False, default=calculate_semester)  # 课程学期
    class_name = Column(String(100), nullable=False)  # 授课班级
    total_hours = Column(Integer, nullable=False)  # 课程总学时
    practice_hours = Column(Integer, nullable=False)  # 课程实训学时
    course_type = Column(String(10), nullable=False)  # 课程类型 A/B/C
    textbook_isbn = Column(String(50), nullable=False)  # 教材 ISBN
    textbook_name = Column(String(200), nullable=False)  # 教材名称
    textbook_image = Column(String(500), nullable=False)  # 教材图片 URL
    
    # 可选字段
    textbook_publisher = Column(String(100), nullable=True)  # 教材出版社
    textbook_link = Column(String(500), nullable=True)  # 教材展示链接
    course_catalog = Column(Text, nullable=True)  # 课程目录（JSON 或文本）
    
    # 副本功能字段（预留）
    parent_course_id = Column(Integer, ForeignKey("courses.id"), nullable=True, index=True)  # 父课程 ID
    is_template = Column(Boolean, default=False, nullable=False)  # 是否为模板
    
    # 分享功能字段（预留）
    share_key = Column(String(36), unique=True, nullable=True, index=True)  # 分享密钥 UUID
    share_enabled = Column(Boolean, default=False, nullable=False)  # 是否启用分享
    share_expires_at = Column(DateTime, nullable=True)  # 分享过期时间
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # 关系
    user = relationship("User", back_populates="courses")
    documents = relationship("CourseDocument", back_populates="course", cascade="all, delete-orphan")
    # 副本关系（自引用）
    parent_course = relationship("Course", remote_side=[id], backref="child_courses")


class CourseDocument(Base):
    """课程文档表模型"""
    __tablename__ = "course_documents"
    
    # 主键和外键
    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    
    # 文档信息
    doc_type = Column(String(20), nullable=False)  # 文档类型: standard/plan/info/lesson/courseware
    title = Column(String(200), nullable=False)  # 文档标题
    content = Column(Text, nullable=True)  # 文档内容（AI 生成或手动编辑）
    plan_params = Column(Text, nullable=True)  # 授课计划参数（JSON）
    file_url = Column(String(500), nullable=True)  # 文件 URL（上传的文档）
    lesson_number = Column(Integer, nullable=True)  # 课次编号（仅 lesson 和 courseware 使用）
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # 关系
    course = relationship("Course", back_populates="documents")


# Pydantic 模型 - 响应模型
class UserResponse(BaseModel):
    """用户信息响应模型"""
    id: int
    username: str
    created_at: datetime
    ai_base_url: Optional[str] = None
    ai_model_name: Optional[str] = None
    has_api_key: bool = False  # 是否已配置 API Key（不返回实际值）

    class Config:
        from_attributes = True

    @classmethod
    def from_user(cls, user):
        """从 User 对象创建响应"""
        return cls(
            id=user.id,
            username=user.username,
            created_at=user.created_at,
            ai_base_url=user.ai_base_url,
            ai_model_name=user.ai_model_name,
            has_api_key=bool(user.ai_api_key)  # 只返回是否配置的标志
        )


class MessageResponse(BaseModel):
    """消息响应模型"""
    id: int
    role: str
    content: str
    created_at: datetime
    
    class Config:
        from_attributes = True


# Pydantic 模型 - 请求模型
class Token(BaseModel):
    """登录响应 Token 模型"""
    access_token: str
    token_type: str


class LoginRequest(BaseModel):
    """登录请求模型"""
    username: str
    password: str


class ChangePasswordRequest(BaseModel):
    """修改密码请求模型"""
    old_password: str
    new_password: str


class UserSettingsRequest(BaseModel):
    """用户设置请求模型"""
    ai_api_key: Optional[str] = None
    ai_base_url: Optional[str] = None
    ai_model_name: Optional[str] = None


class ChatMessageRequest(BaseModel):
    """聊天消息请求模型"""
    content: str


# ==================== 课程管理模型 ====================

# 课程请求模型
class CourseCreateRequest(BaseModel):
    """创建课程请求模型"""
    name: str
    semester: Optional[str] = None  # 如果不提供，使用自动计算的默认值
    class_name: str
    total_hours: int
    practice_hours: int
    course_type: str  # A/B/C
    textbook_isbn: str
    textbook_name: str
    textbook_image: str
    textbook_publisher: Optional[str] = None
    textbook_link: Optional[str] = None
    course_catalog: Optional[str] = None


class CourseUpdateRequest(BaseModel):
    """更新课程请求模型"""
    name: Optional[str] = None
    semester: Optional[str] = None
    class_name: Optional[str] = None
    total_hours: Optional[int] = None
    practice_hours: Optional[int] = None
    course_type: Optional[str] = None
    textbook_isbn: Optional[str] = None
    textbook_name: Optional[str] = None
    textbook_image: Optional[str] = None
    textbook_publisher: Optional[str] = None
    textbook_link: Optional[str] = None
    course_catalog: Optional[str] = None


# 课程响应模型
class CourseResponse(BaseModel):
    """课程响应模型"""
    id: int
    user_id: int
    name: str
    semester: str
    class_name: str
    total_hours: int
    practice_hours: int
    course_type: str
    textbook_isbn: str
    textbook_name: str
    textbook_image: str
    textbook_publisher: Optional[str] = None
    textbook_link: Optional[str] = None
    course_catalog: Optional[str] = None
    parent_course_id: Optional[int] = None
    is_template: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# 文档请求模型
class DocumentCreateRequest(BaseModel):
    """创建文档请求模型"""
    doc_type: str  # standard/plan/info/lesson/courseware
    title: str
    content: Optional[str] = None
    plan_params: Optional[str] = None
    file_url: Optional[str] = None
    lesson_number: Optional[int] = None


class DocumentUpdateRequest(BaseModel):
    """更新文档请求模型"""
    title: Optional[str] = None
    content: Optional[str] = None
    plan_params: Optional[str] = None
    file_url: Optional[str] = None
    lesson_number: Optional[int] = None


# 文档响应模型
class DocumentResponse(BaseModel):
    """文档响应模型"""
    id: int
    course_id: int
    doc_type: str
    title: str
    content: Optional[str] = None
    plan_params: Optional[str] = None
    file_url: Optional[str] = None
    lesson_number: Optional[int] = None
    file_exists: Optional[bool] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# 课程及其文档响应模型
class CourseWithDocumentsResponse(BaseModel):
    """课程及其文档响应模型"""
    course: CourseResponse
    documents: List[DocumentResponse]

