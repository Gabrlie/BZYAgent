# 部署配置与运维说明

## 本地开发启动
1. 启动数据库
- `docker-compose up -d`
2. 启动后端
- `cd backend`
- `uv sync`
- `uv run python -m app.init_db`
- `uv run uvicorn app.main:app --reload --port 8000`
3. 启动前端
- `cd frontend`
- `npm install`
- `npm run dev`

## 环境变量
- `DATABASE_URL`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_DB`
- `SECRET_KEY`
- `ALGORITHM`
- `ACCESS_TOKEN_EXPIRE_MINUTES`
- `HOST`
- `PORT`
- `CORS_ORIGINS`
- `LOG_LEVEL`

## 生产部署建议
- 数据库与文件系统应使用持久化卷。
- `SECRET_KEY` 必须替换为随机强密钥。
- 建议开启反向代理与 HTTPS。
- 后端可使用进程管理工具托管。

## 文件存储路径
- 生成文档目录：`backend/uploads/generated`
- 课程文档目录：`backend/uploads/courses/{course_id}/documents`
- 模板目录：`backend/templates`
