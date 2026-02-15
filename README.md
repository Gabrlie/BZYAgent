# EduAgent Prime

EduAgent Prime 是面向高职院校教学场景的课程资产管理与教学文档生成平台，提供课程管理、授课计划与教案生成、软著材料生成与 AI 对话能力。

## 功能概览
- 账号登录与 JWT 认证
- 用户 AI 配置管理（Base URL / API Key / 模型）
- 课程管理与课程目录维护
- 文档管理与文件上传下载
- 授课计划生成（SSE 进度）
- 教案生成（SSE 进度）
- 软著材料生成（后台任务 + 长轮询 + ZIP 下载）
- AI 对话与历史记录

## 技术栈
- 后端：FastAPI + SQLAlchemy + Alembic + Python 3.12
- 前端：Umi Max + React 19 + TypeScript + Ant Design
- 数据库：PostgreSQL 16（Docker Compose）
- AI：OpenAI 兼容接口（可配置 Base URL 与模型）
- 文档：docxtpl + Word 模板
- 存储：本地 `data/` 目录

## 快速开始（本地开发）
1. 启动数据库
```bash
docker-compose up -d
```
2. 启动后端
```bash
cd backend
uv sync
uv run python -m app.init_db
uv run uvicorn app.main:app --reload --port 8000
```
3. 启动前端
```bash
cd frontend
npm install
npm run dev
```
- 后端：`http://localhost:8000`
- 前端：`http://localhost:5173`

## Docker 一体化部署
```bash
docker-compose up -d --build
```
- 访问地址：`http://localhost:8000`
- 数据持久化：`./data`

## 默认账号
- 用户名：`admin`
- 密码：`admin123`

## 核心接口（示例）
- 登录：`POST /api/auth/login`
- 当前用户：`GET /api/auth/me`
- 课程：`/api/courses`（CRUD）
- 文档：`/api/courses/{course_id}/documents` 等
- 授课计划生成：`GET /api/courses/{course_id}/generate-teaching-plan/stream`
- 教案生成：`POST /api/courses/{course_id}/generate-lesson-plan/stream`
- 软著生成：`POST /api/copyright/projects/{id}/generate`
- 软著进度：`GET /api/copyright/projects/{id}/jobs/latest`
- 软著下载：`GET /api/copyright/projects/{id}/download`
- 仪表盘统计：`GET /api/dashboard/summary`

## 文件存储路径
- 生成文档：`data/uploads/generated`
- 课程文档：`data/uploads/courses/{course_id}/documents`
- 软著项目：`data/copyright/projects/{project_id}`
- 软著 ZIP：`data/copyright/zips/{project_id}`

## 备注
- 软著材料生成耗时较长，支持后台生成与长轮询查看进度。
- 未配置 AI 时会提示前往个人中心完成配置。
