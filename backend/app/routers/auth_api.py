"""
认证相关 API
"""
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..auth import authenticate_user, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from ..database import get_db
from ..deps import get_current_user
from ..models import LoginRequest, Token, User, UserResponse, ChangePasswordRequest, UserSettingsRequest


router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.post("/login", response_model=Token)
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

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires,
    )

    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(user: User = Depends(get_current_user)):
    """
    获取当前登录用户信息

    需要在请求头中提供有效的 JWT Token
    """
    return UserResponse.from_user(user)


@router.post("/change-password", tags=["用户设置"])
async def change_password(
    password_data: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    修改密码

    - **old_password**: 旧密码
    - **new_password**: 新密码
    """
    from ..auth import verify_password, get_password_hash

    if not verify_password(password_data.old_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="旧密码错误")

    user.hashed_password = get_password_hash(password_data.new_password)
    db.commit()

    return {"message": "密码修改成功"}


@router.put("/username", tags=["用户设置"])
async def change_username(
    username_data: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    修改用户名

    - **new_username**: 新用户名
    """
    current_username = user.username
    new_username = username_data.get("new_username")

    if not new_username:
        raise HTTPException(status_code=400, detail="请提供新用户名")

    existing_user = db.query(User).filter(User.username == new_username).first()
    if existing_user and existing_user.id != user.id:
        raise HTTPException(status_code=400, detail="用户名已存在")

    user.username = new_username
    db.commit()

    access_token = create_access_token(
        data={"sub": new_username},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    return {
        "message": "用户名修改成功",
        "access_token": access_token,
        "token_type": "bearer",
    }


@router.put("/settings", tags=["用户设置"])
async def update_settings(
    settings: UserSettingsRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    更新用户 AI 配置

    - **ai_api_key**: AI API Key (可选)
    - **ai_base_url**: AI Base URL (可选)
    - **ai_model_name**: 模型名称 (可选)
    """
    if settings.ai_base_url is not None and settings.ai_base_url:
        base_url = settings.ai_base_url.strip()

        if not base_url.startswith("http://") and not base_url.startswith("https://"):
            raise HTTPException(
                status_code=400,
                detail="Base URL 必须以 http:// 或 https:// 开头",
            )

        if "://http://" in base_url or "://https://" in base_url:
            raise HTTPException(
                status_code=400,
                detail="Base URL 格式错误，请移除重复的协议",
            )

        if not base_url.endswith("/v1"):
            raise HTTPException(
                status_code=400,
                detail="Base URL 必须以 /v1 结尾，例如: https://api.openai.com/v1",
            )

        from urllib.parse import urlparse

        try:
            result = urlparse(base_url)
            if not all([result.scheme, result.netloc]):
                raise ValueError("Invalid URL")
        except Exception:
            raise HTTPException(status_code=400, detail="Base URL 格式无效")

    if settings.ai_api_key is not None:
        user.ai_api_key = settings.ai_api_key
    if settings.ai_base_url is not None:
        user.ai_base_url = settings.ai_base_url.strip() if settings.ai_base_url else None
    if settings.ai_model_name is not None:
        user.ai_model_name = settings.ai_model_name

    db.commit()
    db.refresh(user)

    return {"message": "设置保存成功"}


@router.post("/models", tags=["用户设置"])
async def get_available_models(
    config: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取可用的 AI 模型列表

    - **ai_api_key**: AI API Key (可选，如果不提供则使用已保存的)
    - **ai_base_url**: AI Base URL (必填)
    """
    import openai

    api_key = config.get("ai_api_key")
    base_url = config.get("ai_base_url")

    if not api_key:
        if not user.ai_api_key:
            raise HTTPException(status_code=400, detail="请先配置 API Key")
        api_key = user.ai_api_key

    if not base_url:
        raise HTTPException(status_code=400, detail="请提供 Base URL")

    try:
        client = openai.OpenAI(api_key=api_key, base_url=base_url)
        models = client.models.list()

        model_list = [
            {"id": model.id, "name": model.id, "created": model.created}
            for model in models.data
        ]

        model_list.sort(key=lambda x: x.get("created", 0), reverse=True)

        return {"models": model_list}
    except Exception as e:
        return {
            "models": [
                {"id": "gpt-4", "name": "gpt-4"},
                {"id": "gpt-4-turbo", "name": "gpt-4-turbo"},
                {"id": "gpt-3.5-turbo", "name": "gpt-3.5-turbo"},
                {"id": "gpt-4o", "name": "gpt-4o"},
                {"id": "gpt-4o-mini", "name": "gpt-4o-mini"},
            ],
            "error": str(e),
        }
