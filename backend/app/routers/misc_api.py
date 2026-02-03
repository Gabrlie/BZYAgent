"""
杂项 API
"""
from fastapi import APIRouter, Request


router = APIRouter(tags=["根路径", "测试"])


@router.get("/api/test", tags=["测试"])
async def test_endpoint(request: Request):
    """
    测试接口 - 需要认证

    用于测试中间件鉴权功能
    """
    return {"message": "认证成功", "username": request.state.username}


@router.get("/", tags=["根路径"])
async def root():
    """根路径"""
    return {"message": "BZYAgent API", "docs": "/docs"}
