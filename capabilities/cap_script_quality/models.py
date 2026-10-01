"""
剧本质量引擎v2 数据模型
人性认知+剧情创造能力的核心数据结构
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum


class EmotionType(str, Enum):
    """情绪类型"""
    JOY = "joy"           # 喜悦
    SADNESS = "sadness"   # 悲伤
    ANGER = "anger"       # 愤怒
    FEAR = "fear"         # 恐惧
    SURPRISE = "surprise" # 惊讶
    ANTICIPATION = "anticipation"  # 期待
    TRUST = "trust"       # 信任
    DISGUST = "disgust"   # 厌恶
    NEUTRAL = "neutral"   # 平静
    TENSION = "tension"   # 紧张
    RELIEF = "relief"     # 释然
    EXCITEMENT = "excitement"  # 兴奋


class ConflictType(str, Enum):
    """冲突类型"""
    INTERNAL = "internal"     # 内部冲突（心理/道德/选择）
    EXTERNAL = "external"     # 外部冲突（环境/对手/障碍）
    SOCIAL = "social"         # 社会冲突（关系/群体/文化）
    PHYSICAL = "physical"     # 物理冲突（动作/危险/生存）
    EMOTIONAL = "emotional"   # 情感冲突（爱恨/得失/背叛）


class HookType(str, Enum):
    """钩子类型"""
    QUESTION = "question"           # 悬念提问
    CONTRAST = "contrast"           # 反差对比
    ACTION = "action"               # 动作开场
    EMOTION = "emotion"             # 情感冲击
    MYSTERY = "mystery"             # 神秘悬念
    PROMISE = "promise"             # 价值承诺
    SHOCK = "shock"                 # 震撼开场
    QUOTE = "quote"                 # 金句开场


class PacingType(str, Enum):
    """节奏类型"""
    FAST = "fast"       # 快节奏（快切/高能量）
    MEDIUM = "medium"   # 中节奏
    SLOW = "slow"       # 慢节奏（长镜头/沉浸）
    BUILD = "build"     # 渐强（逐步加速）
    RELEASE = "release" # 释放（从快到慢）


@dataclass
class EmotionPoint:
    """情感曲线节点"""
    time_sec: float                    # 时间点（秒）
    emotion: EmotionType               # 情绪类型
    intensity: float                   # 情绪强度（0-1）
    description: str = ""              # 情绪描述

    def to_dict(self) -> Dict:
        return {
            "time_sec": self.time_sec,
            "emotion": self.emotion.value,
            "intensity": self.intensity,
            "description": self.description,
        }


@dataclass
class CharacterArc:
    """角色弧光"""
    character_name: str                # 角色名
    start_state: str                   # 起始状态
    end_state: str                     # 结束状态
    key_turning_points: List[Tuple[float, str]] = field(default_factory=list)  # 关键转折点 (时间, 描述)
    growth_dimension: str = ""         # 成长维度（勇气/认知/情感/能力）

    def to_dict(self) -> Dict:
        return {
            "character_name": self.character_name,
            "start_state": self.start_state,
            "end_state": self.end_state,
            "key_turning_points": [{"time": t, "desc": d} for t, d in self.key_turning_points],
            "growth_dimension": self.growth_dimension,
        }


@dataclass
class Conflict:
    """冲突设计"""
    conflict_type: ConflictType        # 冲突类型
    description: str                    # 冲突描述
    intensity: float = 0.5             # 冲突强度（0-1）
    start_time: float = 0.0            # 开始时间
    peak_time: float = 0.0             # 高峰时间
    resolution: str = ""               # 解决方式
    resolved: bool = False             # 是否已解决

    def to_dict(self) -> Dict:
        return {
            "conflict_type": self.conflict_type.value,
            "description": self.description,
            "intensity": self.intensity,
            "start_time": self.start_time,
            "peak_time": self.peak_time,
            "resolution": self.resolution,
            "resolved": self.resolved,
        }


@dataclass
class Hook:
    """钩子设计"""
    hook_type: HookType                # 钩子类型
    content: str                       # 钩子内容
    appear_time: float = 0.0           # 出现时间（秒）
    duration: float = 3.0              # 持续时间（秒）
    expected_effect: str = ""          # 预期效果
    strength: float = 0.7              # 钩子强度（0-1）

    def to_dict(self) -> Dict:
        return {
            "hook_type": self.hook_type.value,
            "content": self.content,
            "appear_time": self.appear_time,
            "duration": self.duration,
            "expected_effect": self.expected_effect,
            "strength": self.strength,
        }


@dataclass
class Beat:
    """节拍（比镜头更细粒度的叙事单元）"""
    beat_id: int
    start_time: float
    duration: float
    description: str
    emotion: EmotionType = EmotionType.NEUTRAL
    pacing: PacingType = PacingType.MEDIUM
    conflict_intensity: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "beat_id": self.beat_id,
            "start_time": self.start_time,
            "duration": self.duration,
            "description": self.description,
            "emotion": self.emotion.value,
            "pacing": self.pacing.value,
            "conflict_intensity": self.conflict_intensity,
        }


@dataclass
class QualityReport:
    """剧本质量评估报告"""
    overall_score: float = 0.0         # 综合评分（0-100）
    hook_score: float = 0.0            # 钩子评分
    emotion_score: float = 0.0         # 情感曲线评分
    conflict_score: float = 0.0        # 冲突设计评分
    character_score: float = 0.0       # 角色弧光评分
    pacing_score: float = 0.0          # 节奏控制评分
    structure_score: float = 0.0       # 结构完整性评分
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "overall_score": round(self.overall_score, 1),
            "hook_score": round(self.hook_score, 1),
            "emotion_score": round(self.emotion_score, 1),
            "conflict_score": round(self.conflict_score, 1),
            "character_score": round(self.character_score, 1),
            "pacing_score": round(self.pacing_score, 1),
            "structure_score": round(self.structure_score, 1),
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "suggestions": self.suggestions,
        }


@dataclass
class EnhancedScript:
    """增强后的高质量剧本"""
    title: str
    idea: str
    genre: str
    duration: float
    hook: Optional[Hook] = None
    emotion_curve: List[EmotionPoint] = field(default_factory=list)
    character_arcs: List[CharacterArc] = field(default_factory=list)
    conflicts: List[Conflict] = field(default_factory=list)
    beats: List[Beat] = field(default_factory=list)
    pacing_map: List[Tuple[float, PacingType]] = field(default_factory=list)
    quality_report: Optional[QualityReport] = None
    original_script_ref: str = ""      # 原始剧本引用

    def to_dict(self) -> Dict:
        return {
            "title": self.title,
            "idea": self.idea,
            "genre": self.genre,
            "duration": self.duration,
            "hook": self.hook.to_dict() if self.hook else None,
            "emotion_curve": [e.to_dict() for e in self.emotion_curve],
            "character_arcs": [c.to_dict() for c in self.character_arcs],
            "conflicts": [c.to_dict() for c in self.conflicts],
            "beats": [b.to_dict() for b in self.beats],
            "pacing_map": [{"time": t, "pacing": p.value} for t, p in self.pacing_map],
            "quality_report": self.quality_report.to_dict() if self.quality_report else None,
        }
