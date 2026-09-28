"""
cap_audio_designer — 音频设计模块
BGM智能匹配、TTS旁白、音效推荐、多音轨管理
"""
from .audio_designer import (
    match_bgm,
    add_bgm,
    add_tts_narration,
    add_sfx,
    auto_audio_design,
    list_bgm_themes,
    list_tts_voices,
    list_sfx_scenes,
    BGM_LIBRARY,
    SFX_LIBRARY,
    TTS_VOICES,
)

__all__ = [
    "match_bgm",
    "add_bgm",
    "add_tts_narration",
    "add_sfx",
    "auto_audio_design",
    "list_bgm_themes",
    "list_tts_voices",
    "list_sfx_scenes",
    "BGM_LIBRARY",
    "SFX_LIBRARY",
    "TTS_VOICES",
]
