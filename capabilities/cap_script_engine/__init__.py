"""
cap_script_engine - 剧本引擎
输入一句话需求 → 输出有故事线的完整剧本
"""
from .models import Script, Scene, Shot, VideoGenre, Emotion, ShotSize
from .script_engine import ScriptEngine

__all__ = ["Script", "Scene", "Shot", "VideoGenre", "Emotion", "ShotSize", "ScriptEngine"]
__version__ = "0.1.0"
