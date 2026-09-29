"""
分镜叙事引擎模块 (cap_storyboard_engine)
软实力核心：把创意想法转化为可执行的分镜脚本

核心能力：
- 叙事结构：钩子→展开→高潮→收束
- 景别递进：特写→近景→中景→全景→远景
- 运镜连贯：推→推→移→拉（避免方向断裂）
- 转场匹配：快切/叠化/闪白根据情绪选择
- 节奏设计：快慢对比
- 颜色衔接：相邻镜头色调过渡

风格预设：cinematic/vlog/tutorial/thriller/emotional

使用：
    from cap_storyboard_engine import generate_storyboard
    sb = generate_storyboard("城市夜景", style="cinematic", total_duration=15, shot_count=5)
    print(sb.summary())
    print(sb.to_json())
"""
from .storyboard_engine import (
    Storyboard, Shot, StoryboardGenerator,
    generate_storyboard, list_storyboard_styles,
    STYLE_PRESETS, TRANSITION_BY_EMOTION,
)

__all__ = [
    "Storyboard", "Shot", "StoryboardGenerator",
    "generate_storyboard", "list_storyboard_styles",
    "STYLE_PRESETS", "TRANSITION_BY_EMOTION",
]
