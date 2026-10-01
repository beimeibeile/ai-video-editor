"""
影视剧剧本引擎
剧本解析改编 → 角色性格和分剧情重塑 → 全剧分镜头定版
"""
from .drama_engine import DramaEngine, DramaScript, Scene, Beat, Character, Shot

__all__ = ["DramaEngine", "DramaScript", "Scene", "Beat", "Character", "Shot"]
__version__ = "1.0.0"
