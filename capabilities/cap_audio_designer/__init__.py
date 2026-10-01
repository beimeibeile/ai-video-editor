"""
cap_audio_designer — 声音设计引擎 v2.0 (P9)
角色对话TTS + 旁白解说 + BGM + 场景音效 + 环境音，完整音轨设计
"""
from .audio_designer import (
    AudioDesigner,
    AudioDesignPlan,
    AudioClip,
    CharacterVoice,
    AudioTrackType,
    BGMEmotionStyle,
    match_bgm,
    list_bgm_themes,
    list_tts_voices,
    BGM_LIBRARY,
    TTS_VOICES,
)

__all__ = [
    "AudioDesigner",
    "AudioDesignPlan",
    "AudioClip",
    "CharacterVoice",
    "AudioTrackType",
    "BGMEmotionStyle",
    "match_bgm",
    "list_bgm_themes",
    "list_tts_voices",
    "BGM_LIBRARY",
    "TTS_VOICES",
]
