"""
应用配置模块 - 从根目录 .env 文件加载环境变量
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 获取项目根目录（backend 的上一级）
ROOT_DIR = Path(__file__).parent.parent.parent
ENV_FILE = ROOT_DIR / ".env"

# 从根目录加载 .env 文件
load_dotenv(ENV_FILE)

# 数据库配置
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://admin:admin123@localhost:5432/bzyagent"
)

# JWT 配置
SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "your-secret-key-change-this-in-production-min-32-chars"
)
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# 服务器配置
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

# CORS 配置
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:8001").split(",")

# 日志配置
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
