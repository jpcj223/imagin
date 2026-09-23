"""记忆管理器。

提供统一的记忆读写接口，封装四层记忆体系。
"""
from __future__ import annotations

import json
import uuid
from typing import Any

from app.db.session import get_business_db
from app.models.business import (
    Chapter,
    ChapterSummary,
    Character,
    Foreshadowing,
    MemoryItem,
    Organization,
    UserPreference,
    WorldSetting,
)
from app.db.repository import row_to_dict, rows_to_dicts


class MemoryManager:
    """记忆管理器。

    提供对四层记忆的统一读写接口。
    Agent 不需要关心数据存在哪里，只需要调用 retrieve() 和 store()。
    """

    def __init__(self, project_id: int, user_id: int = 1):
        """初始化记忆管理器。

        Args:
            project_id: 项目 ID
            user_id: 用户 ID
        """
        self.project_id = project_id
        self.user_id = user_id
        self._session_memory: dict[str, Any] = {}  # L2 会话记忆

    # ----------------------------------------------------------
    # L2 会话记忆（工作流内共享）
    # ----------------------------------------------------------

    def set_session(self, key: str, value: Any) -> None:
        """设置会话记忆。"""
        self._session_memory[key] = value

    def get_session(self, key: str, default: Any = None) -> Any:
        """获取会话记忆。"""
        return self._session_memory.get(key, default)

    def clear_session(self) -> None:
        """清空调话记忆。"""
        self._session_memory.clear()

    # ----------------------------------------------------------
    # L3 项目记忆（结构化数据）
    # ----------------------------------------------------------

    def get_characters(self, limit: int = 12) -> list[dict]:
        """获取项目人物列表。"""
        with get_business_db() as db:
            rows = (
                db.query(Character)
                .filter(Character.project_id == self.project_id)
                .order_by(Character.id.desc())
                .limit(limit)
                .all()
            )
            return rows_to_dicts(rows)

    def get_organizations(self, limit: int = 8) -> list[dict]:
        """获取项目组织列表。"""
        with get_business_db() as db:
            rows = (
                db.query(Organization)
                .filter(Organization.project_id == self.project_id)
                .order_by(Organization.id.desc())
                .limit(limit)
                .all()
            )
            return rows_to_dicts(rows)

    def get_foreshadowings(self, statuses: list[str] | None = None, limit: int = 12) -> list[dict]:
        """获取项目伏笔列表。"""
        with get_business_db() as db:
            query = db.query(Foreshadowing).filter(
                Foreshadowing.project_id == self.project_id
            )
            if statuses:
                query = query.filter(Foreshadowing.status.in_(statuses))
            rows = query.order_by(Foreshadowing.id.desc()).limit(limit).all()
            return rows_to_dicts(rows)

    def get_world_setting(self) -> dict | None:
        """获取世界观设定。"""
        with get_business_db() as db:
            row = (
                db.query(WorldSetting)
                .filter(WorldSetting.project_id == self.project_id)
                .order_by(WorldSetting.id.desc())
                .first()
            )
            return row_to_dict(row) if row else None

    def get_recent_summaries(self, chapter_no: int, limit: int = 5) -> list[dict]:
        """获取最近几章的摘要。"""
        with get_business_db() as db:
            rows = (
                db.query(ChapterSummary)
                .join(Chapter, Chapter.id == ChapterSummary.chapter_id)
                .filter(
                    Chapter.project_id == self.project_id,
                    Chapter.chapter_no < chapter_no,
                )
                .order_by(Chapter.chapter_no.desc())
                .limit(limit)
                .all()
            )
            return rows_to_dicts(rows)

    # ----------------------------------------------------------
    # L4 长期记忆（用户偏好）
    # ----------------------------------------------------------

    def get_preferences(self, project_level: bool = True) -> dict:
        """获取用户偏好。

        Args:
            project_level: True 表示项目级偏好，False 表示全局偏好
        """
        with get_business_db() as db:
            query = db.query(UserPreference).filter(
                UserPreference.user_id == self.user_id
            )
            if project_level:
                query = query.filter(UserPreference.project_id == self.project_id)
            else:
                query = query.filter(UserPreference.project_id.is_(None))

            row = query.first()
            if row:
                return row_to_dict(row)

            # 没有记录则返回默认值
            return self._default_preferences()

    def set_preferences(self, preferences: dict, project_level: bool = True) -> None:
        """设置用户偏好。"""
        with get_business_db() as db:
            query = db.query(UserPreference).filter(
                UserPreference.user_id == self.user_id
            )
            if project_level:
                query = query.filter(UserPreference.project_id == self.project_id)
            else:
                query = query.filter(UserPreference.project_id.is_(None))

            row = query.first()
            if row:
                # 更新
                for key, value in preferences.items():
                    if hasattr(row, key):
                        setattr(row, key, value)
                db.commit()
            else:
                # 创建
                data = {"user_id": self.user_id}
                if project_level:
                    data["project_id"] = self.project_id
                data.update(preferences)
                pref = UserPreference(**data)
                db.add(pref)
                db.commit()

    def record_generation(self, word_count: int) -> None:
        """记录一次生成，更新统计数据。"""
        prefs = self.get_preferences()
        total_gen = prefs.get("total_generations", 0) + 1
        total_words = prefs.get("total_words_generated", 0) + word_count
        self.set_preferences({
            "total_generations": total_gen,
            "total_words_generated": total_words,
        })

    # ----------------------------------------------------------
    # 通用记忆条目（扩展用）
    # ----------------------------------------------------------

    def store_memory(
        self,
        memory_type: str,
        title: str,
        content: str,
        importance: int = 50,
        source_type: str = "auto_generated",
        source_ref: str | None = None,
        metadata: dict | None = None,
    ) -> str:
        """存储一条记忆。

        Returns:
            memory_id
        """
        memory_id = str(uuid.uuid4())
        with get_business_db() as db:
            item = MemoryItem(
                memory_id=memory_id,
                project_id=self.project_id,
                user_id=self.user_id,
                memory_type=memory_type,
                title=title,
                content=content,
                importance=importance,
                source_type=source_type,
                source_ref=source_ref,
                metadata_json=json.dumps(metadata or {}, ensure_ascii=False),
            )
            db.add(item)
            db.commit()
        return memory_id

    def get_memory(self, memory_id: str) -> dict | None:
        """获取一条记忆。"""
        with get_business_db() as db:
            row = db.query(MemoryItem).filter(MemoryItem.memory_id == memory_id).first()
            if row:
                # 更新访问计数
                row.access_count += 1
                from datetime import datetime
                row.last_accessed_at = datetime.utcnow()
                db.commit()
                return row_to_dict(row)
            return None

    # ----------------------------------------------------------
    # 辅助方法
    # ----------------------------------------------------------

    def _default_preferences(self) -> dict:
        """默认偏好值。"""
        return {
            "default_template": "smart_mode",
            "default_writer_variant": "default",
            "default_temperature": 80,
            "default_target_word_count": 3000,
            "auto_sync_level": "low_risk_only",
            "ui_theme": "dark",
            "editor_font_size": 16,
            "total_generations": 0,
            "total_words_generated": 0,
            "avg_retry_rate": 0,
        }
