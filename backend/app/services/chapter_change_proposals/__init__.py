"""章节变化提案服务兼容入口。

外部调用保持原有导入路径，具体职责拆分到目录索引、草稿和审核模块。
"""

from .catalog import load_entity_catalog
from .drafts import build_proposal_drafts, create_proposals, list_proposals
from .review import review_proposal

__all__ = [
    "build_proposal_drafts",
    "create_proposals",
    "list_proposals",
    "load_entity_catalog",
    "review_proposal",
]
