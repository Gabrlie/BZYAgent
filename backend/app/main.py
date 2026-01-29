"""
FastAPI 应用主入口
"""
from datetime import timedelta
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .models import (
    Token, LoginRequest, UserResponse, User, Message,
    ChangePasswordRequest, UserSettingsRequest, ChatMessageRequest,
    MessageResponse
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
    
    # 获取历史消息（最近 10 条）
    history = db.query(Message).filter(
        Message.user_id == user.id
    ).order_by(Message.created_at.desc()).limit(10).all()
    
    messages = [
        {"role": msg.role, "content": msg.content}
        for msg in reversed(history)
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

