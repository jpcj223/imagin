"""SQLAlchemy 数据库会话管理。

双数据库架构：
- core_db     核心库：用户、菜单、字典、枚举、系统配置
- business_db 业务库：项目、章节、角色、组织、伏笔等创作数据

使用方式：
    from app.db.session import get_core_db, get_business_db

    with get_core_db() as db:
        db.query(...)

    # FastAPI Depends
    def my_endpoint(db = Depends(get_core_db)):
        ...
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_business_db_url, get_core_db_url


# ---------------------------------------------------------------------------
# 声明基类（两个库共用，因为模型类继承同一个 Base 即可）
# ---------------------------------------------------------------------------
class Base(DeclarativeBase):
    """所有 ORM 模型的基类。"""
    pass


# ---------------------------------------------------------------------------
# 核心库引擎与会话工厂
# ---------------------------------------------------------------------------
_core_engine = create_engine(
    get_core_db_url(),
    echo=False,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False} if get_core_db_url().startswith("sqlite") else {},
)

CoreSessionLocal = sessionmaker(
    bind=_core_engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


@contextmanager
def get_core_db() -> Iterator[Session]:
    """核心库会话上下文管理器。"""
    db = CoreSessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_core_db_depends() -> Iterator[Session]:
    """FastAPI Depends 版本的核心库会话。"""
    db = CoreSessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 业务库引擎与会话工厂
# ---------------------------------------------------------------------------
_business_engine = create_engine(
    get_business_db_url(),
    echo=False,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False} if get_business_db_url().startswith("sqlite") else {},
)

BusinessSessionLocal = sessionmaker(
    bind=_business_engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


@contextmanager
def get_business_db() -> Iterator[Session]:
    """业务库会话上下文管理器。"""
    db = BusinessSessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_business_db_depends() -> Iterator[Session]:
    """FastAPI Depends 版本的业务库会话。"""
    db = BusinessSessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# SQLite 外键支持
# ---------------------------------------------------------------------------
def _enable_sqlite_foreign_keys(dbapi_connection, connection_record):
    """SQLite 启用外键约束。"""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


if get_core_db_url().startswith("sqlite"):
    event.listen(_core_engine, "connect", _enable_sqlite_foreign_keys)

if get_business_db_url().startswith("sqlite"):
    event.listen(_business_engine, "connect", _enable_sqlite_foreign_keys)
