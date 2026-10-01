"""
角色性格引擎 v2.0 (cap_character_engine_v2)
角色性格定义+一致性保持+对话风格生成+角色关系图谱

核心功能：
- 性格画像：MBTI/大五人格/自定义标签/优缺点/价值观
- 语言风格：词汇复杂度/句长/正式度/幽默感/口头禅
- 对话生成：根据性格+情绪+关系生成符合角色的对话
- 一致性检测：跨场景行为/语言一致性检测与违规报告
- 角色关系图谱：关系类型/强度/历史/互动模式
- 角色弧光：成长轨迹/关键时刻/变化维度
"""
from .character_engine import (
    CharacterEngineV2,
    CharacterV2,
    PersonalityProfile,
    SpeechStyle,
    CharacterArc,
    Relationship,
    DialogueGenerator,
    ConsistencyChecker,
    MBTIType,
    BigFive,
    RelationshipType,
    EmotionType,
)

__all__ = [
    "CharacterEngineV2",
    "CharacterV2",
    "PersonalityProfile",
    "SpeechStyle",
    "CharacterArc",
    "Relationship",
    "DialogueGenerator",
    "ConsistencyChecker",
    "MBTIType",
    "BigFive",
    "RelationshipType",
    "EmotionType",
]
__version__ = "2.0.0"
