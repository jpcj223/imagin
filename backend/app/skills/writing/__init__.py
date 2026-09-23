"""写作类 Skill。

这些 Skill 用于增强 Writer/Planner/Polisher Agent 的写作相关能力。
"""
from .core_writing import CoreWritingSkill
from .core_planning import CorePlanningSkill
from .core_polishing import CorePolishingSkill
from .character_dialogue import CharacterDialogueSkill
from .foreshadow_plant import ForeshadowPlantSkill
from .rhythm_control import RhythmControlSkill
from .environment_desc import EnvironmentDescSkill

__all__ = [
    "CoreWritingSkill",
    "CorePlanningSkill",
    "CorePolishingSkill",
    "CharacterDialogueSkill",
    "ForeshadowPlantSkill",
    "RhythmControlSkill",
    "EnvironmentDescSkill",
]
