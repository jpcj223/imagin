"""轻量版数据库迁移框架。

设计原则：
- 版本化：每个迁移脚本一个版本号，按顺序执行
- 幂等性：迁移脚本必须可重复执行（CREATE TABLE IF NOT EXISTS 等）
- 双库支持：核心库和业务库各有独立的迁移版本表
- 自动执行：应用启动时自动检测并执行未执行的迁移

迁移脚本存放位置：
    app/db/migrations/core/      核心库迁移
    app/db/migrations/business/  业务库迁移

迁移脚本命名：
    v001_xxx.py  v002_xxx.py  ...  按版本号排序

每个迁移脚本必须包含：
    def upgrade(db: Session) -> None:  # 升级函数
"""
from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path
from typing import Callable

from sqlalchemy import text

from app.db.session import Base, get_business_db, get_core_db


# ---------------------------------------------------------------------------
# 迁移版本表（两个库各有一份）
# ---------------------------------------------------------------------------
SCHEMA_VERSION_TABLE = "schema_version"


def _ensure_version_table(engine) -> None:
    """确保迁移版本表存在。"""
    from sqlalchemy import inspect
    inspector = inspect(engine)
    if SCHEMA_VERSION_TABLE not in inspector.get_table_names():
        with engine.connect() as conn:
            conn.execute(text(f"""
                CREATE TABLE {SCHEMA_VERSION_TABLE} (
                    version VARCHAR(32) PRIMARY KEY,
                    name VARCHAR(128) NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()


def _get_applied_versions(session) -> set[str]:
    """读取已应用的版本号集合。"""
    rows = session.execute(text(f"SELECT version FROM {SCHEMA_VERSION_TABLE}")).fetchall()
    return {row[0] for row in rows}


def _record_version(session, version: str, name: str) -> None:
    """记录已应用的迁移版本。"""
    session.execute(
        text(f"INSERT INTO {SCHEMA_VERSION_TABLE} (version, name) VALUES (:v, :n)"),
        {"v": version, "n": name},
    )


# ---------------------------------------------------------------------------
# 迁移发现与执行
# ---------------------------------------------------------------------------
def _discover_migrations(package_path: str) -> list[tuple[str, str, Callable]]:
    """发现指定包下的所有迁移脚本，按版本号排序。

    返回: [(version, name, upgrade_func), ...]
    """
    migrations: list[tuple[str, str, Callable]] = []

    package = importlib.import_module(package_path)
    package_dir = Path(package.__file__).parent

    for module_info in pkgutil.iter_modules([str(package_dir)]):
        if not module_info.name.startswith("v"):
            continue
        # 解析版本号和名称
        parts = module_info.name.split("_", 1)
        if len(parts) != 2:
            continue
        version = parts[0]  # v001
        name = parts[1]     # initial_schema 等

        module = importlib.import_module(f"{package_path}.{module_info.name}")
        upgrade_func = getattr(module, "upgrade", None)
        if callable(upgrade_func):
            migrations.append((version, name, upgrade_func))

    # 按版本号排序
    migrations.sort(key=lambda x: x[0])
    return migrations


def run_migrations(db_type: str = "both") -> None:
    """执行数据库迁移。

    Args:
        db_type: "core" / "business" / "both"
    """
    if db_type in ("core", "both"):
        _run_migrations_for_db(
            "core",
            "app.db.migrations.core",
            get_core_db,
        )

    if db_type in ("business", "both"):
        _run_migrations_for_db(
            "business",
            "app.db.migrations.business",
            get_business_db,
        )


def _run_migrations_for_db(
    db_label: str,
    package_path: str,
    session_factory: Callable,
) -> None:
    """为单个数据库执行迁移。"""
    from app.db.session import _core_engine, _business_engine
    engine = _core_engine if db_label == "core" else _business_engine

    # 确保版本表存在
    _ensure_version_table(engine)

    # 发现迁移脚本
    migrations = _discover_migrations(package_path)

    with session_factory() as db:
        applied = _get_applied_versions(db)

        for version, name, upgrade_func in migrations:
            if version in applied:
                continue

            # 执行迁移
            print(f"[{db_label}] 执行迁移 {version}: {name}")
            upgrade_func(db)
            _record_version(db, version, name)
            db.commit()
            print(f"[{db_label}] 迁移 {version} 完成")
