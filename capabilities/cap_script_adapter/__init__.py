"""
剧本解析改编引擎 (cap_script_adapter)
将小说/剧本/故事大纲解析并改编成分镜脚本

核心功能：
- 文本解析：场景/角色/对话/动作提取
- 结构分析：三幕结构、节拍识别、节奏分析
- 分镜改编：场景→镜头拆解、镜头语言推荐、时长估算
- 多集拆分：长文本自动拆分为多集
- 输出兼容：生成Script对象，可直接接入现有pipeline
"""
from .script_adapter import (
    ScriptAdapterEngine,
    ScriptParser,
    ScriptAdapter,
    EpisodeSplitter,
    Character,
    Dialogue,
    ParsedScene,
    AdaptedShot,
    AdaptedEpisode,
    SceneType,
    ShotSize,
    CameraMove,
)

__all__ = [
    "ScriptAdapterEngine",
    "ScriptParser",
    "ScriptAdapter",
    "EpisodeSplitter",
    "Character",
    "Dialogue",
    "ParsedScene",
    "AdaptedShot",
    "AdaptedEpisode",
    "SceneType",
    "ShotSize",
    "CameraMove",
]
__version__ = "1.0.0"
