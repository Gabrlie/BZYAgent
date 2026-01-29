# BZYAgent

基于 FastAPI + Vite + React 的 Web 应用框架，实现了基础的 JWT 用户名密码登录功能。

## 技术栈

- **后端**：FastAPI + PostgreSQL + SQLAlchemy + Alembic
- **前端**：Vite + React + TypeScript + Axios
- **数据库**：PostgreSQL (Docker Compose)
- **包管理**：uv (Python) + npm (Node.js)

## 功能特性

✅ JWT Token 认证  
✅ 后端全局中间件鉴权  
✅ 前端 401 自动拦截跳转  
✅ PostgreSQL 数据持久化  
✅ 淡蓝色扁平化界面设计  
✅ 完整的错误处理

## 项目结构

```
BZYAgent/
├── backend/                 # FastAPI 后端
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py         # 应用主入口
│   │   ├── models.py       # 数据库模型
│   │   ├── database.py     # 数据库连接
│   │   ├── auth.py         # JWT 认证逻辑
│   │   ├── middleware.py   # 认证中间件
│   │   └── init_db.py      # 数据库初始化
│   └── pyproject.toml      # uv 项目配置
├── frontend/                # Vite + React 前端
│   ├── src/
│   │   ├── components/     # React 组件
│   │   ├── services/       # API 服务
│   │   ├── types/          # TypeScript 类型
│   │   ├── App.tsx         # 主应用
│   │   └── App.css         # 全局样式
│   └── package.json
├── docker-compose.yml       # PostgreSQL 容器配置
└── .env.example            # 环境变量模板
```

## 快速开始

### 1. 环境准备

确保已安装：
- Python 3.12+
- Node.js 18+
- Docker 和 Docker Compose
- uv（Python 包管理器）

安装 uv：
```bash
pip install uv
```

### 2. 配置环境变量

复制环境变量模板：
```bash
cp .env.example .env
```

可根据需要修改 `.env` 文件中的配置。

### 3. 启动数据库

```bash
docker-compose up -d
```

### 4. 启动后端

```bash
cd backend

# 安装依赖
uv sync

# 初始化数据库
uv run python -m app.init_db

# 启动开发服务器
uv run uvicorn app.main:app --reload --port 8000
```

后端将在 `http://localhost:8000` 启动。

访问 API 文档：`http://localhost:8000/docs`

### 5. 启动前端

```bash
cd frontend

# 安装依赖（如果还未安装）
npm install

# 启动开发服务器
npm run dev
```

前端将在 `http://localhost:5173` 启动。

## 默认账号

- **用户名**：admin
- **密码**：admin123

## API 接口

### 登录
```
POST /api/auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "admin123"
}
```

### 获取当前用户信息
```
GET /api/auth/me
Authorization: Bearer <token>
```

## 界面设计

前端采用扁平化设计风格，使用淡蓝色作为主色调：
- 主色：`#4A90E2`
- 辅助色：`#E8F4FF`

## 安全特性

1. **JWT 认证**：使用 JWT Token 进行用户认证
2. **密码加密**：使用 bcrypt 哈希存储密码
3. **中间件鉴权**：后端所有接口（除登录外）都需要认证
4. **自动跳转**：前端拦截 401 错误自动跳转登录页

## 开发说明

### 后端开发

后端使用 `uv` 管理依赖，常用命令：

```bash
# 添加新依赖
uv add <package-name>

# 运行脚本
uv run python -m app.init_db

# 启动服务
uv run uvicorn app.main:app --reload
```

### 前端开发

前端使用标准的 npm 工作流：

```bash
# 安装依赖
npm install

# 开发模式
npm run dev

# 构建生产版本
npm run build
```

## 常见问题

### 1. 数据库连接失败

确保 Docker 容器正在运行：
```bash
docker-compose ps
```

### 2. 前端 CORS 错误

检查后端 `app/main.py` 中的 CORS 配置是否包含前端地址。

### 3. Token 过期

默认 Token 有效期为 30 分钟，可在 `.env` 中修改 `ACCESS_TOKEN_EXPIRE_MINUTES`。

## 许可证

MIT
