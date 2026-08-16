from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from app.db.session import Base


class SysDictItem(Base):
    """字典项表。"""

    __tablename__ = "sys_dict_items"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    dict_id = Column(
        Integer,
        ForeignKey("sys_dictionaries.id", ondelete="CASCADE"),
        nullable=False,
        comment="所属字典ID",
    )
    item_label = Column(String(128), nullable=False, comment="显示标签")
    item_value = Column(String(128), nullable=False, comment="存储值")
    sort_order = Column(Integer, default=0, comment="排序")
    status = Column(String(16), default="active", comment="状态: active/disabled")
    remark = Column(String(255), default="", comment="备注")
    created_at = Column(
        DateTime,
        server_default=func.now(),
        default=datetime.utcnow,
        comment="创建时间",
    )

    dictionary = relationship("SysDictionary", backref="items")
