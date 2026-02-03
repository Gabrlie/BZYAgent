"""
AI 对话相关 API
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..ai_service import chat_completion_stream
from ..database import get_db
from ..deps import get_current_user
from ..models import ChatMessageRequest, Message, MessageResponse, User


router = APIRouter(prefix="/api/chat", tags=["AI 对话"])


@router.post("/send")
async def send_message(
    message_data: ChatMessageRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    发送消息到 AI 并流式返回响应

    - **content**: 消息内容
    """
    if not user.ai_api_key or not user.ai_base_url:
        raise HTTPException(
            status_code=400,
            detail="请先在用户设置中配置 AI API Key 和 Base URL",
        )

    user_msg = Message(user_id=user.id, role="user", content=message_data.content)
    db.add(user_msg)
    db.commit()

    messages = [
        {"role": "system", "content": "你是一个有帮助的AI助手。"},
        {"role": "user", "content": "你好，你是谁"},
        {"role": "assistant", "content": "你好！我是AI助手，很高兴为您服务。"},
        {"role": "user", "content": message_data.content},
    ]

    async def generate():
        assistant_content = ""
        try:
            async for chunk in chat_completion_stream(
                messages=messages,
                api_key=user.ai_api_key,
                base_url=user.ai_base_url,
                model=user.ai_model_name,
            ):
                assistant_content += chunk
                yield chunk
        except Exception as e:
            yield f"\n\nError: {str(e)}"

        ai_msg = Message(user_id=user.id, role="assistant", content=assistant_content)
        db.add(ai_msg)
        db.commit()

    return StreamingResponse(generate(), media_type="text/plain; charset=utf-8")


@router.get("/history")
async def get_chat_history(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取聊天历史
    """
    messages = (
        db.query(Message)
        .filter(Message.user_id == user.id)
        .order_by(Message.created_at.asc())
        .all()
    )

    return {
        "messages": [MessageResponse.from_orm(msg).dict() for msg in messages]
    }


@router.delete("/clear")
async def clear_chat_history(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    清除聊天历史
    """
    db.query(Message).filter(Message.user_id == user.id).delete()
    db.commit()

    return {"message": "历史记录已清除"}
