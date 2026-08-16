"""核心库 API 路由。

包含菜单、字典、认证、系统配置、模型配置等核心功能接口。
"""
from app.api.core.menus import router as menus_router
from app.api.core.dictionaries import router as dictionaries_router
from app.api.core.auth import router as auth_router
from app.api.core.users import router as users_router
from app.api.core.system import router as system_router
from app.api.core.models import router as models_router

__all__ = [
    "menus_router",
    "dictionaries_router",
    "auth_router",
    "users_router",
    "system_router",
    "models_router",
]
