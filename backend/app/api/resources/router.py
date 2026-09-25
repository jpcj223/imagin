"""兼容入口：按域汇总创作资料子路由，维持既有资源 API 前缀。"""

from fastapi import APIRouter

from . import crud, dashboard, history, organizations, outlines

router = APIRouter()

# 固定静态与更具体的路径优先注册，再挂载通用资源接口。
router.include_router(dashboard.router)
router.include_router(history.router)
router.include_router(organizations.router)
router.include_router(outlines.router)
router.include_router(crud.router)
