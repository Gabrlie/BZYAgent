"""
JWT 认证中间件
"""
from urllib.parse import parse_qs

from fastapi import status
from fastapi.responses import JSONResponse
from starlette.datastructures import Headers
from starlette.types import ASGIApp, Receive, Scope, Send

from .auth import verify_token


class JWTAuthMiddleware:
    """JWT 认证中间件 - 拦截所有请求进行鉴权（兼容 SSE 流式响应）"""

    # 不需要鉴权的路径
    EXCLUDE_PATHS = {
        "/api/auth/login",
        "/docs",
        "/redoc",
        "/openapi.json",
    }

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        # 非 API 路径（前端静态资源等）不做鉴权
        if not path.startswith("/api/"):
            await self.app(scope, receive, send)
            return

        if path in self.EXCLUDE_PATHS or path.startswith("/uploads/"):
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        auth_header = headers.get("authorization")
        token = None

        if auth_header and auth_header.lower().startswith("bearer "):
            token = auth_header.split(" ", 1)[1]
        else:
            query_string = scope.get("query_string", b"").decode("utf-8")
            if query_string:
                params = parse_qs(query_string)
                token_values = params.get("token")
                if token_values:
                    token = token_values[0]

        if not token:
            response = JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "未提供认证令牌"},
                headers={"WWW-Authenticate": "Bearer"},
            )
            await response(scope, receive, send)
            return

        username = verify_token(token)
        if username is None:
            response = JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "无效的认证令牌"},
                headers={"WWW-Authenticate": "Bearer"},
            )
            await response(scope, receive, send)
            return

        scope.setdefault("state", {})
        scope["state"]["username"] = username

        await self.app(scope, receive, send)
