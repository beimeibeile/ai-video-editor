"""
剧本质量引擎v2 (cap_script_quality)
人性认知+剧情创造能力

解决"系统缺乏人性认知和剧本创造能力"的核心问题

核心能力：
- 三幕结构深化
- 角色弧光设计
- 情感曲线设计
- 冲突设计（内部+外部+情感）
- 钩子优化（前3秒抓人）
- 节奏控制（快慢交替）
- 多维度质量评估
"""
from .models import (
    EmotionType, ConflictType, HookType, PacingType,
    EmotionPoint, CharacterArc, Conflict, Hook, Beat,
    QualityReport, EnhancedScript,
)
from .script_quality_engine import ScriptQualityEngine

__all__ = [
    "ScriptQualityEngine",
    "EnhancedScript",
    "QualityReport",
    "EmotionType",
    "ConflictType",
    "HookType",
    "PacingType",
    "EmotionPoint",
    "CharacterArc",
    "Conflict",
    "Hook",
    "Beat",
]

__version__ = "2.0.0"
