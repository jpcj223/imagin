"""创作资料 API 包。

将资源路由按领域拆分；保留 ``app.api.resources.router`` 公共导入，
避免应用入口与已有集成代码因目录调整而改动。
"""

from .router import router

__all__ = ["router"]
