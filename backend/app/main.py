"""
FastAPI 应用主入口
"""
from datetime import timedelta
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, status, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.orm import Session
import os
import uuid
import shutil

from .models import (
    Token, LoginRequest, UserResponse, User, Message,
    ChangePasswordRequest, UserSettingsRequest, ChatMessageRequest,
    MessageResponse,
    Course, CourseDocument, calculate_semester,
    CourseCreateRequest, CourseUpdateRequest, CourseResponse,
    DocumentCreateRequest, DocumentUpdateRequest, DocumentResponse,
    CourseWithDocumentsResponse
)
from .database import get_db
from .auth import authenticate_user, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from .middleware import JWTAuthMiddleware
from .config import CORS_ORIGINS

# 创建 FastAPI 应用
app = FastAPI(
    title="BZYAgent API",
    description="FastAPI + JWT 认证后端",
    version="1.0.0"
)

# 添加 JWT 认证中间件（必须在 CORS 之前）
app.add_middleware(JWTAuthMiddleware)

# 配置 CORS 中间件（必须在最后）
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/auth/login", response_model=Token, tags=["认证"])
async def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    """
    用户登录接口
    
    - **username**: 用户名
    - **password**: 密码
    """
    user = authenticate_user(db, login_data.username, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 创建 access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/api/auth/me", response_model=UserResponse, tags=["认证"])
async def get_current_user(request: Request, db: Session = Depends(get_db)):
    """
    获取当前登录用户信息
    
    需要在请求头中提供有效的 JWT Token
    """
    # 从中间件设置的请求状态中获取用户名
    username = request.state.username
    
    # 从数据库查询用户信息
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    return UserResponse.from_user(user)


@app.post("/api/auth/change-password", tags=["用户设置"])
async def change_password(
    request: Request,
    password_data: ChangePasswordRequest,
    db: Session = Depends(get_db)
):
    """
    修改密码
    
    - **old_password**: 旧密码
    - **new_password**: 新密码
    """
    from .auth import verify_password, get_password_hash
    
    username = request.state.username
    user = db.query(User).filter(User.username == username).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 验证旧密码
    if not verify_password(password_data.old_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="旧密码错误")
    
    # 更新密码
    user.hashed_password = get_password_hash(password_data.new_password)
    db.commit()
    
    return {"message": "密码修改成功"}


@app.put("/api/auth/username", tags=["用户设置"])
async def change_username(
    request: Request,
    username_data: dict,
    db: Session = Depends(get_db)
):
    """
    修改用户名
    
    - **new_username**: 新用户名
    """
    current_username = request.state.username
    new_username = username_data.get("new_username")
    
    if not new_username:
        raise HTTPException(status_code=400, detail="请提供新用户名")
    
    user = db.query(User).filter(User.username == current_username).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 检查新用户名是否已存在
    existing_user = db.query(User).filter(User.username == new_username).first()
    if existing_user and existing_user.id != user.id:
        raise HTTPException(status_code=400, detail="用户名已存在")
    
    # 更新用户名
    user.username = new_username
    db.commit()
    
    # 生成新 token
    from .auth import create_access_token
    from datetime import timedelta
    access_token = create_access_token(
        data={"sub": new_username},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    return {
        "message": "用户名修改成功",
        "access_token": access_token,
        "token_type": "bearer"
    }


@app.put("/api/auth/settings", tags=["用户设置"])
async def update_settings(
    request: Request,
    settings: UserSettingsRequest,
    db: Session = Depends(get_db)
):
    """
    更新用户 AI 配置
    
    - **ai_api_key**: AI API Key (可选)
    - **ai_base_url**: AI Base URL (可选)
    - **ai_model_name**: 模型名称 (可选)
    """
    username = request.state.username
    user = db.query(User).filter(User.username == username).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 验证 Base URL 格式
    if settings.ai_base_url is not None and settings.ai_base_url:
        base_url = settings.ai_base_url.strip()
        
        # 检查是否以 http:// 或 https:// 开头
        if not base_url.startswith('http://') and not base_url.startswith('https://'):
            raise HTTPException(
                status_code=400, 
                detail="Base URL 必须以 http:// 或 https:// 开头"
            )
        
        # 检查是否有双重协议
        if '://http://' in base_url or '://https://' in base_url:
            raise HTTPException(
                status_code=400, 
                detail="Base URL 格式错误，请移除重复的协议"
            )
        
        # 检查是否以 /v1 结尾
        if not base_url.endswith('/v1'):
            raise HTTPException(
                status_code=400, 
                detail="Base URL 必须以 /v1 结尾，例如: https://api.openai.com/v1"
            )
        
        # 验证 URL 格式
        from urllib.parse import urlparse
        try:
            result = urlparse(base_url)
            if not all([result.scheme, result.netloc]):
                raise ValueError("Invalid URL")
        except Exception:
            raise HTTPException(status_code=400, detail="Base URL 格式无效")
    
    # 更新 AI 配置
    if settings.ai_api_key is not None:
        user.ai_api_key = settings.ai_api_key
    if settings.ai_base_url is not None:
        user.ai_base_url = settings.ai_base_url.strip() if settings.ai_base_url else None
    if settings.ai_model_name is not None:
        user.ai_model_name = settings.ai_model_name
    
    db.commit()
    db.refresh(user)
    
    return {"message": "设置保存成功"}


@app.post("/api/auth/models", tags=["用户设置"])
async def get_available_models(
    request: Request,
    config: dict,
    db: Session = Depends(get_db)
):
    """
    获取可用的 AI 模型列表
    
    - **ai_api_key**: AI API Key (可选，如果不提供则使用已保存的)
    - **ai_base_url**: AI Base URL (必填)
    """
    import openai
    
    username = request.state.username
    user = db.query(User).filter(User.username == username).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    api_key = config.get("ai_api_key")
    base_url = config.get("ai_base_url")
    
    # 如果没有提供 API Key，使用用户已保存的
    if not api_key:
        if not user.ai_api_key:
            raise HTTPException(status_code=400, detail="请先配置 API Key")
        api_key = user.ai_api_key
    
    if not base_url:
        raise HTTPException(status_code=400, detail="请提供 Base URL")
    
    try:
        client = openai.OpenAI(api_key=api_key, base_url=base_url)
        models = client.models.list()
        
        # 提取模型 ID 列表
        model_list = [
            {
                "id": model.id,
                "name": model.id,
                "created": model.created
            }
            for model in models.data
        ]
        
        # 按创建时间倒序排序
        model_list.sort(key=lambda x: x.get("created", 0), reverse=True)
        
        return {"models": model_list}
    except Exception as e:
        # 如果获取失败，返回常用模型列表
        return {
            "models": [
                {"id": "gpt-4", "name": "gpt-4"},
                {"id": "gpt-4-turbo", "name": "gpt-4-turbo"},
                {"id": "gpt-3.5-turbo", "name": "gpt-3.5-turbo"},
                {"id": "gpt-4o", "name": "gpt-4o"},
                {"id": "gpt-4o-mini", "name": "gpt-4o-mini"},
            ],
            "error": str(e)
        }


@app.post("/api/chat/send", tags=["AI 对话"])
async def send_message(
    request: Request,
    message_data: ChatMessageRequest,
    db: Session = Depends(get_db)
):
    """
    发送消息到 AI 并流式返回响应
    
    - **content**: 消息内容
    """
    from fastapi.responses import StreamingResponse
    from .ai_service import chat_completion_stream
    
    username = request.state.username
    user = db.query(User).filter(User.username == username).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 检查 AI 配置
    if not user.ai_api_key or not user.ai_base_url:
        raise HTTPException(
            status_code=400,
            detail="请先在用户设置中配置 AI API Key 和 Base URL"
        )
    
    # 保存用户消息
    user_msg = Message(
        user_id=user.id,
        role="user",
        content=message_data.content
    )
    db.add(user_msg)
    db.commit()
    
    # 只发送简单的初始对话，不加载历史记录
    messages = [
        {"role": "system", "content": "你是一个有帮助的AI助手。"},
        {"role": "user", "content": "你好，你是谁"},
        {"role": "assistant", "content": "你好！我是AI助手，很高兴为您服务。"},
        {"role": "user", "content": message_data.content}
    ]
    
    # 流式生成响应
    async def generate():
        assistant_content = ""
        try:
            async for chunk in chat_completion_stream(
                messages=messages,
                api_key=user.ai_api_key,
                base_url=user.ai_base_url,
                model=user.ai_model_name
            ):
                assistant_content += chunk
                yield chunk
        except Exception as e:
            yield f"\n\nError: {str(e)}"
        
        # 保存 AI 响应
        ai_msg = Message(
            user_id=user.id,
            role="assistant",
            content=assistant_content
        )
        db.add(ai_msg)
        db.commit()
    
    return StreamingResponse(
        generate(),
        media_type="text/plain; charset=utf-8"
    )


@app.get("/api/chat/history", tags=["AI 对话"])
async def get_chat_history(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    获取聊天历史
    """
    username = request.state.username
    user = db.query(User).filter(User.username == username).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    messages = db.query(Message).filter(
        Message.user_id == user.id
    ).order_by(Message.created_at.asc()).all()
    
    return {
        "messages": [
            MessageResponse.from_orm(msg).dict()
            for msg in messages
        ]
    }


@app.delete("/api/chat/clear", tags=["AI 对话"])
async def clear_chat_history(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    清除聊天历史
    """
    username = request.state.username
    user = db.query(User).filter(User.username == username).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    db.query(Message).filter(Message.user_id == user.id).delete()
    db.commit()
    
    return {"message": "历史记录已清除"}


@app.get("/api/test", tags=["测试"])
async def test_endpoint(request: Request):
    """
    测试接口 - 需要认证
    
    用于测试中间件鉴权功能
    """
    return {
        "message": "认证成功",
        "username": request.state.username
    }


@app.get("/", tags=["根路径"])
async def root():
    """根路径"""
    return {
        "message": "BZYAgent API",
        "docs": "/docs"
    }


# ==================== 课程管理 API ====================

@app.post("/api/courses", response_model=CourseResponse, tags=["课程管理"])
async def create_course(
    request: Request,
    course_data: CourseCreateRequest,
    db: Session = Depends(get_db)
):
    """
    创建课程
    
    - 如果未提供学期，将自动根据当前日期计算
    - 所有教材信息字段必填
    """
    username = request.state.username
    user = db.query(User).filter(User.username == username).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 如果没有提供学期，使用自动计算的值
    semester = course_data.semester if course_data.semester else calculate_semester()
    
    # 创建课程
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
        course_catalog=course_data.course_catalog
    )
    
    db.add(course)
    db.commit()
    db.refresh(course)
    
    return course


@app.get("/api/courses", response_model=list[CourseResponse], tags=["课程管理"])
async def get_courses(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    获取当前用户的所有课程列表
    
    按创建时间倒序排列
    """
    username = request.state.username
    user = db.query(User).filter(User.username == username).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    courses = db.query(Course).filter(
        Course.user_id == user.id
    ).order_by(Course.created_at.desc()).all()
    
    return courses


@app.get("/api/courses/{course_id}", response_model=CourseWithDocumentsResponse, tags=["课程管理"])
async def get_course(
    course_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    获取单个课程详情，包含所有文档
    """
    username = request.state.username
    user = db.query(User).filter(User.username == username).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    course = db.query(Course).filter(
        Course.id == course_id,
        Course.user_id == user.id
    ).first()
    
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    
    # 获取课程的所有文档
    documents = db.query(CourseDocument).filter(
        CourseDocument.course_id == course_id
    ).order_by(CourseDocument.created_at.desc()).all()
    
    return {
        "course": course,
        "documents": documents
    }


@app.put("/api/courses/{course_id}", response_model=CourseResponse, tags=["课程管理"])
async def update_course(
    course_id: int,
    request: Request,
    course_data: CourseUpdateRequest,
    db: Session = Depends(get_db)
):
    """
    更新课程信息
    
    只更新提供的字段，未提供的字段保持不变
    """
    username = request.state.username
    user = db.query(User).filter(User.username == username).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    course = db.query(Course).filter(
        Course.id == course_id,
        Course.user_id == user.id
    ).first()
    
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    
    # 更新字段
    update_data = course_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(course, field, value)
    
    db.commit()
    db.refresh(course)
    
    return course


@app.delete("/api/courses/{course_id}", tags=["课程管理"])
async def delete_course(
    course_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    删除课程
    
    会级联删除该课程下的所有文档
    """
    username = request.state.username
    user = db.query(User).filter(User.username == username).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    course = db.query(Course).filter(
        Course.id == course_id,
        Course.user_id == user.id
    ).first()
    
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    
    db.delete(course)
    db.commit()
    
    return {"message": "课程删除成功"}


# ==================== 文档管理 API ====================

@app.post("/api/courses/{course_id}/documents", response_model=DocumentResponse, tags=["文档管理"])
async def create_document(
    course_id: int,
    request: Request,
    document_data: DocumentCreateRequest,
    db: Session = Depends(get_db)
):
    """创建文档 - 支持 AI 生成或上传文件"""
    username = request.state.username
    user = db.query(User).filter(User.username == username).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    course = db.query(Course).filter(
        Course.id == course_id,
        Course.user_id == user.id
    ).first()
    
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    
    document = CourseDocument(
        course_id=course_id,
        doc_type=document_data.doc_type,
        title=document_data.title,
        content=document_data.content,
        file_url=document_data.file_url,
        lesson_number=document_data.lesson_number
    )
    
    try:
        db.add(document)
        db.commit()
        db.refresh(document)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"文档创建失败：{str(e)}")
    
    return document


@app.post("/api/courses/{course_id}/documents/upload", tags=["文档管理"])
async def upload_document(
    course_id: int,
    request: Request,
    file: UploadFile = File(...),
    doc_type: str = File(...),
    title: str = File(...),
    lesson_number: Optional[int] = File(None),
    db: Session = Depends(get_db)
):
    """上传文档文件 - 支持 .docx, .pdf, .pptx, .md，最大 10MB"""
    username = request.state.username
    user = db.query(User).filter(User.username == username).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    course = db.query(Course).filter(
        Course.id == course_id,
        Course.user_id == user.id
    ).first()
    
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    
    # 验证文件类型
    allowed_extensions = [".docx", ".pdf", ".pptx", ".md"]
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型，仅支持：{', '.join(allowed_extensions)}"
        )
    
    # 验证文件大小（10MB）
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    
    if file_size > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件大小不能超过 10MB")
    
    # 创建上传目录
    upload_dir = f"backend/uploads/courses/{course_id}/documents"
    os.makedirs(upload_dir, exist_ok=True)
    
    # 生成唯一文件名
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(upload_dir, unique_filename)
    
    # 保存文件
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # 创建文档记录
    document = CourseDocument(
        course_id=course_id,
        doc_type=doc_type,
        title=title,
        file_url=f"/api/documents/files/{course_id}/{unique_filename}",
        lesson_number=lesson_number
    )
    
    try:
        db.add(document)
        db.commit()
        db.refresh(document)
    except Exception as e:
        db.rollback()
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=400, detail=f"文档创建失败：{str(e)}")
    
    return {"message": "文件上传成功", "document": document}


@app.get("/api/courses/{course_id}/documents", response_model=list[DocumentResponse], tags=["文档管理"])
async def get_documents(
    course_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """获取课程的所有文档列表"""
    username = request.state.username
    user = db.query(User).filter(User.username == username).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    course = db.query(Course).filter(
        Course.id == course_id,
        Course.user_id == user.id
    ).first()
    
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    
    documents = db.query(CourseDocument).filter(
        CourseDocument.course_id == course_id
    ).order_by(CourseDocument.doc_type, CourseDocument.lesson_number).all()
    
    return documents


@app.get("/api/courses/{course_id}/documents/type/{doc_type}", response_model=list[DocumentResponse], tags=["文档管理"])
async def get_documents_by_type(
    course_id: int,
    doc_type: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """获取指定类型的文档列表"""
    username = request.state.username
    user = db.query(User).filter(User.username == username).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    course = db.query(Course).filter(
        Course.id == course_id,
        Course.user_id == user.id
    ).first()
    
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    
    documents = db.query(CourseDocument).filter(
        CourseDocument.course_id == course_id,
        CourseDocument.doc_type == doc_type
    ).order_by(CourseDocument.lesson_number).all()
    
    return documents


@app.get("/api/documents/{document_id}", response_model=DocumentResponse, tags=["文档管理"])
async def get_document(
    document_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """获取单个文档详情"""
    username = request.state.username
    user = db.query(User).filter(User.username == username).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    document = db.query(CourseDocument).filter(
        CourseDocument.id == document_id
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    course = db.query(Course).filter(
        Course.id == document.course_id,
        Course.user_id == user.id
    ).first()
    
    if not course:
        raise HTTPException(status_code=403, detail="无权访问此文档")
    
    return document


@app.put("/api/documents/{document_id}", response_model=DocumentResponse, tags=["文档管理"])
async def update_document(
    document_id: int,
    request: Request,
    document_data: DocumentUpdateRequest,
    db: Session = Depends(get_db)
):
    """更新文档信息"""
    username = request.state.username
    user = db.query(User).filter(User.username == username).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    document = db.query(CourseDocument).filter(
        CourseDocument.id == document_id
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    course = db.query(Course).filter(
        Course.id == document.course_id,
        Course.user_id == user.id
    ).first()
    
    if not course:
        raise HTTPException(status_code=403, detail="无权修改此文档")
    
    update_data = document_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(document, field, value)
    
    db.commit()
    db.refresh(document)
    
    return document


@app.delete("/api/documents/{document_id}", tags=["文档管理"])
async def delete_document(
    document_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """删除文档 - 同时删除上传的文件"""
    username = request.state.username
    user = db.query(User).filter(User.username == username).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    document = db.query(CourseDocument).filter(
        CourseDocument.id == document_id
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    course = db.query(Course).filter(
        Course.id == document.course_id,
        Course.user_id == user.id
    ).first()
    
    if not course:
        raise HTTPException(status_code=403, detail="无权删除此文档")
    
    # 删除上传的文件
    if document.file_url:
        try:
            parts = document.file_url.split('/')
            if len(parts) >= 3:
                course_id = parts[-2]
                filename = parts[-1]
                file_path = f"backend/uploads/courses/{course_id}/documents/{filename}"
                if os.path.exists(file_path):
                    os.remove(file_path)
        except Exception as e:
            print(f"删除文件失败：{e}")
    
    db.delete(document)
    db.commit()
    
    return {"message": "文档删除成功"}


@app.get("/api/documents/files/{course_id}/{filename}", tags=["文档管理"])
async def download_document(
    course_id: int,
    filename: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """下载文档文件"""
    username = request.state.username
    user = db.query(User).filter(User.username == username).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    course = db.query(Course).filter(
        Course.id == course_id,
        Course.user_id == user.id
    ).first()
    
    if not course:
        raise HTTPException(status_code=403, detail="无权访问此文件")
    
    file_path = f"backend/uploads/courses/{course_id}/documents/{filename}"
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在")
    
    return FileResponse(
        file_path,
        media_type="application/octet-stream",
        filename=filename
    )

