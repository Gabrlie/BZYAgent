"""
FastAPI 应用主入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.staticfiles import StaticFiles as StarletteStaticFiles

from .config import CORS_ORIGINS
from .middleware import JWTAuthMiddleware
from .utils.paths import (
    UPLOADS_DIR,
    COPYRIGHT_PROJECTS_DIR,
    COPYRIGHT_ZIPS_DIR,
    FRONTEND_DIST_DIR,
    ensure_dir,
)
from .routers.auth_api import router as auth_router
from .routers.chat_api import router as chat_router
from .routers.courses_api import router as courses_router
from .routers.documents_api import router as documents_router
from .routers.lesson_plan_api import router as lesson_plan_router
from .routers.teaching_plan_api import router as teaching_plan_router
from .routers.misc_api import router as misc_router
from .routers.dashboard_api import router as dashboard_router
from .routers.copyright_api import router as copyright_router


app = FastAPI(
    title="EduAgent Prime API",
    description="FastAPI + JWT 认证后端",
    version="1.0.0",
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

# 挂载路由
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(courses_router)
app.include_router(documents_router)
app.include_router(lesson_plan_router)
app.include_router(teaching_plan_router)
app.include_router(misc_router)
app.include_router(copyright_router)
app.include_router(dashboard_router)

# 配置静态文件服务（用于下载生成的文档）
ensure_dir(UPLOADS_DIR)
ensure_dir(COPYRIGHT_PROJECTS_DIR)
ensure_dir(COPYRIGHT_ZIPS_DIR)
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")

# 前端静态资源（单容器部署）
if FRONTEND_DIST_DIR.exists():
    class SPAStaticFiles(StarletteStaticFiles):
        async def get_response(self, path: str, scope):  # type: ignore[override]
            response = await super().get_response(path, scope)
            if response.status_code == 404:
                # 避免拦截 API 或上传文件
                if path.startswith(("api", "docs", "redoc", "openapi.json", "uploads")):
                    return response
                return await super().get_response("index.html", scope)
            return response

    app.mount("/", SPAStaticFiles(directory=str(FRONTEND_DIST_DIR), html=True), name="frontend")
