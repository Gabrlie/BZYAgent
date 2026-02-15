# 技术选型与依赖

## 后端
- 语言与运行时：Python 3.12
- Web 框架：FastAPI
- ORM 与迁移：SQLAlchemy 2.x，Alembic
- 认证：python-jose（JWT），bcrypt
- AI 调用：openai SDK（兼容 OpenAI API）
- 文件与模板：docxtpl，python-docx
- 运行与依赖管理：uv，uvicorn

## 前端
- 框架：Umi Max（Ant Design Pro）
- 视图库：React 19
- UI：Ant Design 5
- 请求与路由：@umijs/max
- 构建与脚本：Node.js 20+

## 数据库与存储
- 数据库：PostgreSQL 16（Docker Compose）
- 文件存储：本地文件系统 `data/uploads`
- 软著材料：`data/copyright` 下的项目与 ZIP
- 模板：`backend/templates` 下的 Word 模板

## 环境与配置
- 环境变量：`.env` 与 `.env.example`
- 本地代理：前端 `config/proxy.ts` 指向 `http://localhost:8000`
- 生产容器：单容器部署，后端提供前端静态资源
