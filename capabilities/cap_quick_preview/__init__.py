"""
快速整剧小样生成器 v1.0 (cap_quick_preview)
快速生成全剧预览小样+关键帧预览+节奏预览+批量导出

核心功能：
- 关键帧预览：为每个镜头生成带信息的预览图
- 节奏预览：全剧情绪曲线+场景时长分布可视化
- 剪映工程：快速生成预览用剪映工程（纯色背景+文字占位）
- 批量导出：一键导出全部预览素材
- 小样报告：生成完整制作报告
"""
from .quick_preview import (
    QuickPreviewGenerator,
    KeyframeGenerator,
    RhythmChartGenerator,
    PreviewConfig,
    PreviewResult,
)

__all__ = [
    "QuickPreviewGenerator",
    "KeyframeGenerator",
    "RhythmChartGenerator",
    "PreviewConfig",
    "PreviewResult",
]
__version__ = "1.0.0"
