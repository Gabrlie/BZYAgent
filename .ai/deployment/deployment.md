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

## Docker 一体化部署
1. 构建并启动
- `docker-compose up -d --build`
2. 服务说明
- 前端静态资源由后端服务托管，统一通过 `http://localhost:8000` 访问
- 数据目录挂载到 `./data`，包含上传文件与软著材料 ZIP

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
- 生成文档目录：`data/uploads/generated`
- 课程文档目录：`data/uploads/courses/{course_id}/documents`
- 软著材料目录：`data/copyright/projects/{project_id}`
- 软著 ZIP 目录：`data/copyright/zips/{project_id}`
- 模板目录：`backend/templates`
