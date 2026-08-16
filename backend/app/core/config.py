"""应用配置管理。

通过环境变量或 .env 文件配置数据库连接等运行参数。
支持 SQLite / MySQL / MariaDB 三种后端，切换只需修改环境变量。
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Literal


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR.parent / "data"


def _env(key: str, default: str = "") -> str:
    """读取环境变量，兼容 .env 文件（简单实现）。"""
    value = os.environ.get(key, default)
    return value.strip() if value else default


# ---------------------------------------------------------------------------
# 数据库类型：sqlite / mysql / mariadb
# ---------------------------------------------------------------------------
DB_TYPE: Literal["sqlite", "mysql", "mariadb"] = _env("DB_TYPE", "sqlite")  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# 核心库（系统库）连接配置
# 存放：用户、菜单、字典、枚举、系统配置、模型配置 等全局共享数据
# ---------------------------------------------------------------------------
CORE_DB_PATH = _env("CORE_DB_PATH", str(DATA_DIR / "core.db"))
CORE_DB_HOST = _env("CORE_DB_HOST", "127.0.0.1")
CORE_DB_PORT = int(_env("CORE_DB_PORT", "3306"))
CORE_DB_USER = _env("CORE_DB_USER", "root")
CORE_DB_PASSWORD = _env("CORE_DB_PASSWORD", "")
CORE_DB_NAME = _env("CORE_DB_NAME", "yixiang_core")

# ---------------------------------------------------------------------------
# 业务库（创作库）连接配置
# 存放：项目、章节、角色、组织、伏笔、大纲 等创作数据
# ---------------------------------------------------------------------------
BUSINESS_DB_PATH = _env("BUSINESS_DB_PATH", str(DATA_DIR / "yixiang.db"))
BUSINESS_DB_HOST = _env("BUSINESS_DB_HOST", "127.0.0.1")
BUSINESS_DB_PORT = int(_env("BUSINESS_DB_PORT", "3306"))
BUSINESS_DB_USER = _env("BUSINESS_DB_USER", "root")
BUSINESS_DB_PASSWORD = _env("BUSINESS_DB_PASSWORD", "")
BUSINESS_DB_NAME = _env("BUSINESS_DB_NAME", "yixiang_business")


def get_core_db_url() -> str:
    """构造核心库 SQLAlchemy 连接串。"""
    if DB_TYPE == "sqlite":
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{CORE_DB_PATH}"
    # mysql / mariadb
    return (
        f"mysql+pymysql://{CORE_DB_USER}:{CORE_DB_PASSWORD}"
        f"@{CORE_DB_HOST}:{CORE_DB_PORT}/{CORE_DB_NAME}"
        f"?charset=utf8mb4"
    )


def get_business_db_url() -> str:
    """构造业务库 SQLAlchemy 连接串。"""
    if DB_TYPE == "sqlite":
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{BUSINESS_DB_PATH}"
    # mysql / mariadb
    return (
        f"mysql+pymysql://{BUSINESS_DB_USER}:{BUSINESS_DB_PASSWORD}"
        f"@{BUSINESS_DB_HOST}:{BUSINESS_DB_PORT}/{BUSINESS_DB_NAME}"
        f"?charset=utf8mb4"
    )
