"""
角色性格引擎
角色性格建模 + 关系图谱 + 分剧情重塑 + 一致性检查
"""
from .character_engine import CharacterEngine, PersonalityProfile, Relationship, CharacterArc, ConsistencyIssue

__all__ = ["CharacterEngine", "PersonalityProfile", "Relationship", "CharacterArc", "ConsistencyIssue"]
__version__ = "1.0.0"
