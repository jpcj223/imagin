from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import agents, models, projects, resources
from app.api.core import (
    auth_router,
    dictionaries_router,
    menus_router,
    models_router as core_models_router,
    system_router,
    users_router,
)
from app.db.migrator import run_migrations


app = FastAPI(title="臆想创作 API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    """应用启动时执行数据库迁移。

    双库架构：核心库（用户/菜单/字典/配置）+ 业务库（创作数据）
    各自有独立的版本化迁移，启动时自动检测并执行未应用的迁移。
    """
    run_migrations("both")


@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "name": "臆想创作"}


# ---------------------------------------------------------------------------
# 业务库 API（创作相关）
# ---------------------------------------------------------------------------
app.include_router(projects.router, prefix="/api/projects", tags=["projects"])
app.include_router(models.router, prefix="/api/models", tags=["models"])  # 兼容旧路径
app.include_router(resources.router, prefix="/api/resources", tags=["resources"])
app.include_router(agents.router, prefix="/api/agents", tags=["agents"])

# ---------------------------------------------------------------------------
# 核心库 API（系统管理相关）
# ---------------------------------------------------------------------------
app.include_router(auth_router, prefix="/api/core/auth", tags=["core-auth"])
app.include_router(users_router, prefix="/api/core/users", tags=["core-users"])
app.include_router(menus_router, prefix="/api/core/menus", tags=["core-menus"])
app.include_router(
    dictionaries_router, prefix="/api/core/dictionaries", tags=["core-dictionaries"]
)
app.include_router(system_router, prefix="/api/core/configs", tags=["core-configs"])
app.include_router(core_models_router, prefix="/api/core/models", tags=["core-models"])
