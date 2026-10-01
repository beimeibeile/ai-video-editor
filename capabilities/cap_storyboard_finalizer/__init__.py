"""
全剧分镜头定版系统 v1.0 (cap_storyboard_finalizer)
全剧分镜统一编号+场景调度+镜头语言规范+分镜表导出

核心功能：
- 统一编号：全剧唯一镜头编号 S01E01C01
- 场景调度：场景顺序、时长、转场规划
- 镜头语言：景别/角度/运镜/光线/声音标准化
- 多格式导出：JSON/CSV/Markdown
- 全剧统计：时长分配、镜头分布、景别/运镜统计
- 适配器导入：从剧本解析改编引擎直接导入
"""
from .storyboard_finalizer import (
    StoryboardFinalizer,
    FinalShot,
    FinalScene,
    FinalEpisode,
    ShotSize,
    CameraAngle,
    CameraMove,
    TransitionType,
)

__all__ = [
    "StoryboardFinalizer",
    "FinalShot",
    "FinalScene",
    "FinalEpisode",
    "ShotSize",
    "CameraAngle",
    "CameraMove",
    "TransitionType",
]
__version__ = "1.0.0"
