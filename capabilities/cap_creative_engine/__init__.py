"""
创意引擎模块 - 创意生成、热点搜索、分镜脚本设计

能力：
- 理解用户诉求，生成创意方向建议
- AnySearch热点搜索（流行元素、BGM推荐、文案参考）
- 专业分镜脚本生成（景别/运镜/转场/字幕/音效/调色）
- 多主题创意模板库
"""

from .creative_engine import CreativeEngine, CreativeDirection
from .storyboard import StoryboardGenerator, Shot, Storyboard
from .hot_trends import HotTrendsSearcher
from .templates import CREATIVE_TEMPLATES, get_template, list_themes

__all__ = [
    "CreativeEngine",
    "CreativeDirection",
    "StoryboardGenerator",
    "Shot",
    "Storyboard",
    "HotTrendsSearcher",
    "CREATIVE_TEMPLATES",
    "get_template",
    "list_themes",
]
