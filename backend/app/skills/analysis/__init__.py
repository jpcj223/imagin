"""分析类 Skill。

这些 Skill 用于增强 Analyzer Agent 的分析提取能力。
"""
from .core_analysis import CoreAnalysisSkill
from .character_change import CharacterChangeSkill
from .foreshadow_detect import ForeshadowDetectSkill

__all__ = [
    "CoreAnalysisSkill",
    "CharacterChangeSkill",
    "ForeshadowDetectSkill",
]
