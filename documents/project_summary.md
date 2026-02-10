# BZYAgent 项目梳理（自动生成）

## 总览
- 类型：课程管理 + AI 教学文档生成的全栈应用
- 后端：FastAPI + PostgreSQL + SQLAlchemy + Alembic
- 前端：Umi Max（Ant Design Pro）+ React 19
- 认证：JWT（全局中间件）
- 文档生成：SSE 流式进度 + Word 模板（docxtpl）

## 目录结构
- backend/：后端服务
- frontend/：前端应用
- docker-compose.yml：PostgreSQL 容器配置
- .env / .env.example：运行配置
- documents/：本项目说明文档（本文件所在目录）

## 后端要点
- 入口与路由：`backend/app/main.py`
- 认证逻辑：`backend/app/auth.py`
- JWT 中间件：`backend/app/middleware.py`
- 数据模型：`backend/app/models.py`
- AI 服务：`backend/app/ai_service.py`
- 教案生成 API：`backend/app/lesson_plan_api.py`
- 授课计划 API：`backend/app/teaching_plan_api.py`
- RAG/知识上下文：`backend/app/knowledge_service.py`
- Word 模板渲染：`backend/app/docx_service.py`
- 模板文件：`backend/templates/教案模板.docx`、`授课计划模板.docx`

## 核心功能
- 用户：JWT 登录、获取当前用户、修改密码/用户名、配置 AI 参数
- AI 对话：消息发送、历史记录、清空记录（流式响应）
- 课程管理：创建/列表/详情/更新/删除
- 文档管理：创建/上传/下载/更新/删除
- 教案生成：仅支持系统生成授课计划作为输入，SSE 推送进度并生成 Word 文档入库
- 授课计划生成：SSE 推送进度，生成 Word 文档并入库
- 上传文档仅用于下载与查看，不支持 AI 生成与编辑
- 上传文件类型仅支持 `.doc` `.docx`

## 关键接口（后端）
- 登录：`POST /api/auth/login`
- 当前用户：`GET /api/auth/me`
- AI 对话：`POST /api/chat/send`
- 课程：`/api/courses`（CRUD）
- 文档：`/api/courses/{course_id}/documents` 等
- 教案生成：`POST /api/courses/{course_id}/generate-lesson-plan/stream`
- 授课计划：`GET /api/courses/{course_id}/generate-teaching-plan/stream`

## 前端要点
- 框架：Umi Max + Ant Design Pro
- 请求与鉴权：`frontend/src/requestErrorConfig.ts` 自动注入 JWT
- 服务层：`frontend/src/services/*`
- 课程相关页面：`frontend/src/pages/Course/*`

## 运行方式（参考 README）
- 启动数据库：`docker-compose up -d`
- 启动后端：
  - `cd backend`
  - `uv sync`
  - `uv run python -m app.init_db`
  - `uv run uvicorn app.main:app --reload --port 8000`
- 启动前端：
  - `cd frontend`
  - `npm install`
  - `npm run dev`

## 备注
- README 中写的是 Vite + React，但当前前端为 Umi Max（Ant Design Pro）。
- SSE 鉴权：授课计划生成接口通过 URL 参数 token 认证；教案生成接口前端暂未附加 token（可能导致 401）。

## 数据模型简表
- users：id, username, hashed_password, ai_api_key, ai_base_url, ai_model_name, created_at
- messages：id, user_id, role, content, created_at
- courses：id, user_id, name, semester, class_name, total_hours, practice_hours, course_type, textbook_*, course_catalog, parent_course_id, is_template, share_*
- course_documents：id, course_id, doc_type, title, content, file_url, lesson_number, created_at

关系：User 1..n Course，User 1..n Message，Course 1..n CourseDocument。

## API 细表
- 认证：`POST /api/auth/login`
- 认证：`GET /api/auth/me`
- 认证：`POST /api/auth/change-password`
- 认证：`PUT /api/auth/username`
- 认证：`PUT /api/auth/settings`
- 认证：`POST /api/auth/models`
- 对话：`POST /api/chat/send`
- 对话：`GET /api/chat/history`
- 对话：`DELETE /api/chat/clear`
- 课程：`POST /api/courses`
- 课程：`GET /api/courses`
- 课程：`GET /api/courses/{course_id}`
- 课程：`PUT /api/courses/{course_id}`
- 课程：`DELETE /api/courses/{course_id}`
- 文档：`POST /api/courses/{course_id}/documents`
- 文档：`POST /api/courses/{course_id}/documents/upload`
- 文档：`GET /api/courses/{course_id}/documents`
- 文档：`GET /api/courses/{course_id}/documents/type/{doc_type}`
- 文档：`GET /api/documents/{document_id}`
- 文档：`PUT /api/documents/{document_id}`
- 文档：`DELETE /api/documents/{document_id}`
- 文档：`GET /api/documents/files/{course_id}/{filename}`
- 教案：`POST /api/courses/{course_id}/generate-lesson-plan/stream`
- 教案：`GET /api/courses/{course_id}/lesson-plans`
- 授课计划：`GET /api/courses/{course_id}/generate-teaching-plan/stream`
- 授课计划：`GET /api/courses/{course_id}/teaching-plans`

## SSE 进度阶段
- 教案生成：analyzing(10%) → retrieving(30%) → generating(50/70%) → rendering(85%) → completed(100%)
- 授课计划：validating(10%) → generating(30/70%) → rendering(85%) → saving(95%) → completed(100%)

## 文件与静态资源
- 生成文档：`backend/uploads/generated/*`，通过 `/uploads/*` 静态访问
- 课程文档上传：`backend/uploads/courses/{course_id}/documents/*`
- 文档下载：`GET /api/documents/files/{course_id}/{filename}`

## 前端页面与菜单
- 登录页：`frontend/src/pages/user/login`
- 课程模块：`frontend/src/pages/Course/*`（List/Create/Edit/Detail/生成页）
- 动态菜单：`frontend/src/app.tsx` 按课程列表动态生成子菜单

## 环境变量（示例）
- 数据库：`DATABASE_URL`、`POSTGRES_USER`、`POSTGRES_PASSWORD`、`POSTGRES_DB`
- JWT：`SECRET_KEY`、`ALGORITHM`、`ACCESS_TOKEN_EXPIRE_MINUTES`
- 服务：`HOST`、`PORT`、`CORS_ORIGINS`
- 日志：`LOG_LEVEL`

## 默认账号
- 用户名：`admin`
- 密码：`admin123`

## 备注补充
- README 中写的是 Vite + React，但当前前端为 Umi Max（Ant Design Pro）。
- 教案生成前端使用 EventSource（GET），后端接口为 POST，方法可能不匹配。
- 教案生成前端未显式附带 token；授课计划接口通过 URL 参数 token 进行鉴权。

## 结构优化（最新）
- 路由拆分到 `backend/app/routers/`：认证、对话、课程、文档、教案、授课计划、杂项
- `backend/app/main.py` 仅保留应用初始化与路由挂载
- 公共依赖抽离到 `backend/app/deps.py`（当前用户、课程、文档）

## 结构优化（补充）
- 新增 `backend/app/utils/paths.py`：统一模板/上传目录路径
- 新增 `backend/app/utils/sse.py`：统一 SSE 事件与响应头
- `docx_service.py` 与文档上传/下载逻辑使用统一路径工具
