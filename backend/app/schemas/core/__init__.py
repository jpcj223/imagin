"""核心库 Pydantic 模型。

包含菜单、字典、用户认证、系统配置、模型配置等请求/响应模型。
"""
from app.schemas.core.menus import (
    MenuCreate,
    MenuUpdate,
    MenuResponse,
    MenuTreeNode,
)
from app.schemas.core.dictionaries import (
    DictionaryCreate,
    DictionaryUpdate,
    DictionaryResponse,
    DictItemCreate,
    DictItemUpdate,
    DictItemResponse,
)
from app.schemas.core.auth import (
    LoginRequest,
    LoginResponse,
    UserProfileResponse,
    UserProfileUpdate,
)
from app.schemas.core.system import (
    SysConfigResponse,
    SysConfigUpdate,
)
from app.schemas.core.models import (
    ModelConfigCreate,
    ModelConfigUpdate,
    ModelConfigResponse,
)

__all__ = [
    # Menus
    "MenuCreate",
    "MenuUpdate",
    "MenuResponse",
    "MenuTreeNode",
    # Dictionaries
    "DictionaryCreate",
    "DictionaryUpdate",
    "DictionaryResponse",
    "DictItemCreate",
    "DictItemUpdate",
    "DictItemResponse",
    # Auth
    "LoginRequest",
    "LoginResponse",
    "UserProfileResponse",
    "UserProfileUpdate",
    # System
    "SysConfigResponse",
    "SysConfigUpdate",
    # Models
    "ModelConfigCreate",
    "ModelConfigUpdate",
    "ModelConfigResponse",
]
