"""核心库初始迁移脚本 v002 — 系统表与种子数据。

创建系统用户、菜单、字典、配置等核心表（model_configs 已在 v001 创建），
并插入初始种子数据。
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


def upgrade(db: Session) -> None:
    """执行初始迁移。"""
    dialect = db.bind.dialect.name

    if dialect == "sqlite":
        _create_tables_sqlite(db)
    else:
        _create_tables_mysql(db)

    _insert_seed_data(db, dialect)
    db.commit()


# ---------------------------------------------------------------------------
# SQLite DDL
# ---------------------------------------------------------------------------
def _create_tables_sqlite(db: Session) -> None:
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS sys_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(64) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            nickname VARCHAR(64) DEFAULT '',
            email VARCHAR(128) DEFAULT '',
            avatar VARCHAR(255) DEFAULT '',
            role VARCHAR(32) DEFAULT 'user',
            status VARCHAR(16) DEFAULT 'active',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """))

    db.execute(text("""
        CREATE TABLE IF NOT EXISTS sys_menus (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            parent_id INTEGER DEFAULT 0,
            name VARCHAR(64) NOT NULL,
            path VARCHAR(255) DEFAULT '',
            icon VARCHAR(64) DEFAULT '',
            component VARCHAR(255) DEFAULT '',
            sort_order INTEGER DEFAULT 0,
            menu_type VARCHAR(16) DEFAULT 'menu',
            permission VARCHAR(128) DEFAULT '',
            is_visible INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """))

    db.execute(text("""
        CREATE TABLE IF NOT EXISTS sys_dictionaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dict_code VARCHAR(64) NOT NULL UNIQUE,
            dict_name VARCHAR(128) NOT NULL,
            description VARCHAR(255) DEFAULT '',
            sort_order INTEGER DEFAULT 0,
            status VARCHAR(16) DEFAULT 'active',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """))

    db.execute(text("""
        CREATE TABLE IF NOT EXISTS sys_dict_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dict_id INTEGER NOT NULL,
            item_label VARCHAR(128) NOT NULL,
            item_value VARCHAR(128) NOT NULL,
            sort_order INTEGER DEFAULT 0,
            status VARCHAR(16) DEFAULT 'active',
            remark VARCHAR(255) DEFAULT '',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (dict_id) REFERENCES sys_dictionaries(id) ON DELETE CASCADE
        )
    """))

    db.execute(text("""
        CREATE TABLE IF NOT EXISTS sys_configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            config_key VARCHAR(128) NOT NULL UNIQUE,
            config_value TEXT DEFAULT '',
            config_name VARCHAR(128) DEFAULT '',
            description VARCHAR(255) DEFAULT '',
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """))


# ---------------------------------------------------------------------------
# MySQL DDL
# ---------------------------------------------------------------------------
def _create_tables_mysql(db: Session) -> None:
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS sys_users (
            id INTEGER PRIMARY KEY AUTO_INCREMENT,
            username VARCHAR(64) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            nickname VARCHAR(64) DEFAULT '',
            email VARCHAR(128) DEFAULT '',
            avatar VARCHAR(255) DEFAULT '',
            role VARCHAR(32) DEFAULT 'user',
            status VARCHAR(16) DEFAULT 'active',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """))

    db.execute(text("""
        CREATE TABLE IF NOT EXISTS sys_menus (
            id INTEGER PRIMARY KEY AUTO_INCREMENT,
            parent_id INTEGER DEFAULT 0,
            name VARCHAR(64) NOT NULL,
            path VARCHAR(255) DEFAULT '',
            icon VARCHAR(64) DEFAULT '',
            component VARCHAR(255) DEFAULT '',
            sort_order INTEGER DEFAULT 0,
            menu_type VARCHAR(16) DEFAULT 'menu',
            permission VARCHAR(128) DEFAULT '',
            is_visible INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """))

    db.execute(text("""
        CREATE TABLE IF NOT EXISTS sys_dictionaries (
            id INTEGER PRIMARY KEY AUTO_INCREMENT,
            dict_code VARCHAR(64) NOT NULL UNIQUE,
            dict_name VARCHAR(128) NOT NULL,
            description VARCHAR(255) DEFAULT '',
            sort_order INTEGER DEFAULT 0,
            status VARCHAR(16) DEFAULT 'active',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """))

    db.execute(text("""
        CREATE TABLE IF NOT EXISTS sys_dict_items (
            id INTEGER PRIMARY KEY AUTO_INCREMENT,
            dict_id INTEGER NOT NULL,
            item_label VARCHAR(128) NOT NULL,
            item_value VARCHAR(128) NOT NULL,
            sort_order INTEGER DEFAULT 0,
            status VARCHAR(16) DEFAULT 'active',
            remark VARCHAR(255) DEFAULT '',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (dict_id) REFERENCES sys_dictionaries(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """))

    db.execute(text("""
        CREATE TABLE IF NOT EXISTS sys_configs (
            id INTEGER PRIMARY KEY AUTO_INCREMENT,
            config_key VARCHAR(128) NOT NULL UNIQUE,
            config_value TEXT,
            config_name VARCHAR(128) DEFAULT '',
            description VARCHAR(255) DEFAULT '',
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """))


# ---------------------------------------------------------------------------
# 种子数据
# ---------------------------------------------------------------------------
def _insert_seed_data(db: Session, dialect: str) -> None:
    """插入初始种子数据（幂等）。"""
    _insert_default_user(db)
    _insert_menus(db)
    _insert_dictionaries(db)
    _insert_system_configs(db)


def _insert_default_user(db: Session) -> None:
    """插入默认管理员 admin/admin123。"""
    result = db.execute(text("SELECT id FROM sys_users WHERE username = 'admin'")).fetchone()
    if result:
        return
    db.execute(text("""
        INSERT INTO sys_users (username, password_hash, nickname, role, status)
        VALUES ('admin', 'admin123', '超级管理员', 'admin', 'active')
    """))


def _insert_menus(db: Session) -> None:
    """插入完整菜单树。"""
    # 检查是否已有菜单数据
    result = db.execute(text("SELECT COUNT(*) FROM sys_menus")).fetchone()
    if result and result[0] > 0:
        return

    menus = [
        # 分组1：导航控制台
        (0, "导航控制台", "", "🚀", "", 1, "dir", "", 1),
        (1, "创作中心", "/dashboard", "🚀", "Dashboard", 1, "menu", "", 1),
        (1, "章节生成", "/chapter-generate", "✨", "ChapterGenerate", 2, "menu", "", 1),
        # 分组2：核心管理
        (0, "核心管理", "", "📋", "", 2, "dir", "", 1),
        (4, "大纲规划", "/outline", "📋", "Outline", 1, "menu", "", 1),
        (4, "世界观设定", "/world", "🌍", "WorldSettings", 2, "menu", "", 1),
        # 分组3：项目数据
        (0, "项目数据", "", "👥", "", 3, "dir", "", 1),
        (7, "人物卡片", "/characters", "👥", "Characters", 1, "menu", "", 1),
        (7, "人物关系", "/character-relations", "🕸️", "CharacterRelations", 2, "menu", "", 1),
        (7, "组织势力", "/organizations", "🏛️", "Organizations", 3, "menu", "", 1),
        (7, "伏笔看板", "/foreshadowings", "🎭", "Foreshadowings", 4, "menu", "", 1),
        (7, "长期记忆", "/memory", "🧠", "LongTermMemory", 5, "menu", "", 1),
        (7, "项目配置", "/project-config", "⚙️", "ProjectConfig", 6, "menu", "", 1),
        # 分组4：配置
        (0, "配置", "", "🔌", "", 4, "dir", "", 1),
        (14, "API 配置", "/api-config", "🔌", "ApiConfig", 1, "menu", "", 1),
        # 系统管理（隐藏，预留管理后台页面）
        (0, "系统管理", "/system", "🛠️", "SystemManagement", 99, "dir", "", 0),
        (99, "用户管理", "/system/users", "👥", "UserManagement", 1, "menu", "system:user", 0),
        (99, "菜单管理", "/system/menus", "📋", "MenuManagement", 2, "menu", "system:menu", 0),
        (99, "字典管理", "/system/dictionaries", "📚", "DictionaryManagement", 3, "menu", "system:dict", 0),
        (99, "系统配置", "/system/configs", "🔧", "SystemConfig", 4, "menu", "system:config", 0),
    ]

    for parent_id, name, path, icon, component, sort_order, menu_type, permission, is_visible in menus:
        db.execute(text("""
            INSERT INTO sys_menus (parent_id, name, path, icon, component, sort_order, menu_type, permission, is_visible)
            VALUES (:parent_id, :name, :path, :icon, :component, :sort_order, :menu_type, :permission, :is_visible)
        """), {
            "parent_id": parent_id,
            "name": name,
            "path": path,
            "icon": icon,
            "component": component,
            "sort_order": sort_order,
            "menu_type": menu_type,
            "permission": permission,
            "is_visible": is_visible,
        })


def _insert_dictionaries(db: Session) -> None:
    """插入常用字典及字典项。"""
    # 字典数据
    dictionaries = [
        ("novel_type", "小说类型", "小说分类类型", 1),
        ("importance", "重要程度", "通用重要性等级", 2),
        ("character_role", "角色类型", "人物角色分类", 3),
        ("foreshadowing_status", "伏笔状态", "伏笔进度状态", 4),
        ("writing_style", "文风基调", "写作风格类型", 5),
        ("view_point", "叙事视角", "叙述角度类型", 6),
    ]

    dict_items = {
        "novel_type": [
            ("玄幻", "xuanhuan", 1),
            ("都市", "dushi", 2),
            ("科幻", "kehuan", 3),
            ("仙侠", "xianxia", 4),
            ("言情", "yanqing", 5),
            ("悬疑", "xuanyi", 6),
            ("历史", "lishi", 7),
            ("游戏", "youxi", 8),
            ("其他", "other", 99),
        ],
        "importance": [
            ("低", "low", 1),
            ("中", "medium", 2),
            ("高", "high", 3),
        ],
        "character_role": [
            ("主角", "protagonist", 1),
            ("配角", "supporting", 2),
            ("反派", "antagonist", 3),
            ("导师", "mentor", 4),
            ("恋人", "love_interest", 5),
        ],
        "foreshadowing_status": [
            ("待埋", "pending", 1),
            ("已埋", "planted", 2),
            ("发展中", "developing", 3),
            ("已回收", "resolved", 4),
            ("已废弃", "abandoned", 5),
        ],
        "writing_style": [
            ("严肃", "serious", 1),
            ("轻松", "light", 2),
            ("热血", "passionate", 3),
            ("治愈", "healing", 4),
            ("暗黑", "dark", 5),
            ("史诗", "epic", 6),
            ("其他", "other", 99),
        ],
        "view_point": [
            ("第一人称", "first_person", 1),
            ("第三人称有限", "third_person_limited", 2),
            ("第三人称全知", "third_person_omniscient", 3),
            ("第二人称", "second_person", 4),
        ],
    }

    for dict_code, dict_name, description, sort_order in dictionaries:
        # 检查字典是否已存在
        result = db.execute(
            text("SELECT id FROM sys_dictionaries WHERE dict_code = :code"),
            {"code": dict_code},
        ).fetchone()
        if result:
            continue

        db.execute(text("""
            INSERT INTO sys_dictionaries (dict_code, dict_name, description, sort_order, status)
            VALUES (:dict_code, :dict_name, :description, :sort_order, 'active')
        """), {
            "dict_code": dict_code,
            "dict_name": dict_name,
            "description": description,
            "sort_order": sort_order,
        })

        # 获取刚插入的字典 ID
        dict_row = db.execute(
            text("SELECT id FROM sys_dictionaries WHERE dict_code = :code"),
            {"code": dict_code},
        ).fetchone()
        dict_id = dict_row[0]

        # 插入字典项
        for item_label, item_value, item_sort in dict_items[dict_code]:
            db.execute(text("""
                INSERT INTO sys_dict_items (dict_id, item_label, item_value, sort_order, status)
                VALUES (:dict_id, :item_label, :item_value, :sort_order, 'active')
            """), {
                "dict_id": dict_id,
                "item_label": item_label,
                "item_value": item_value,
                "sort_order": item_sort,
            })


def _insert_system_configs(db: Session) -> None:
    """插入默认系统配置。"""
    configs = [
        ("site_name", "臆想创作", "站点名称", "网站显示名称"),
        ("default_novel_type", "xuanhuan", "默认小说类型", "新建项目时的默认类型"),
        ("default_target_words", "2500", "默认目标字数", "单章默认目标字数"),
        ("default_pace_level", "3", "默认节奏等级", "1-5级节奏强度"),
        ("auto_save_interval", "30", "自动保存间隔(秒)", "编辑器自动保存间隔"),
    ]

    for config_key, config_value, config_name, description in configs:
        result = db.execute(
            text("SELECT id FROM sys_configs WHERE config_key = :key"),
            {"key": config_key},
        ).fetchone()
        if result:
            continue
        db.execute(text("""
            INSERT INTO sys_configs (config_key, config_value, config_name, description)
            VALUES (:config_key, :config_value, :config_name, :description)
        """), {
            "config_key": config_key,
            "config_value": config_value,
            "config_name": config_name,
            "description": description,
        })
