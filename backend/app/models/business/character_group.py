"""角色分组模型。"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from app.db.session import Base


class CharacterGroup(Base):
    """角色分组表。"""

    __tablename__ = "character_groups"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    group_type = Column(String(20), default="custom")  # default / custom
    role_type = Column(String(50), nullable=True)  # 默认分组关联的角色类型
    sort_index = Column(Integer, default=0)
    color = Column(String(20), nullable=True)
    is_builtin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
