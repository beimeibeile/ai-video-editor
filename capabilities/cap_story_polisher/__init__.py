"""
剧情多轮打造系统 v1.0 (cap_story_polisher)
剧情迭代优化+多版本对比+冲突检测+节奏分析

核心功能：
- 版本管理：多版本存储、对比、切换
- 节奏分析：场景时长分布、情绪曲线、高潮点识别、节奏评分
- 结构分析：三幕结构验证、关键结构点识别（激励事件/转折点/高潮/结局）
- 冲突检测：逻辑矛盾、角色不一致、时间线冲突、情绪跳跃
- 优化建议：基于分析结果自动生成优化建议
- 完整报告：节奏+结构+问题+建议的综合分析报告
"""
from .story_polisher import (
    StoryPolisher,
    StoryVersion,
    StoryIssue,
    PacingAnalysis,
    StructureAnalysis,
    PacingAnalyzer,
    StructureAnalyzer,
    ConflictDetector,
    StoryIssueSeverity,
    StoryIssueType,
    ActType,
)

__all__ = [
    "StoryPolisher",
    "StoryVersion",
    "StoryIssue",
    "PacingAnalysis",
    "StructureAnalysis",
    "PacingAnalyzer",
    "StructureAnalyzer",
    "ConflictDetector",
    "StoryIssueSeverity",
    "StoryIssueType",
    "ActType",
]
__version__ = "1.0.0"
