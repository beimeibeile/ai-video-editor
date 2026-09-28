"""
cap_effect_library — 特效库模块
转场/滤镜预设，自动匹配风格
"""
from .effect_library import (
    add_transition,
    auto_add_transitions,
    get_style_preset,
    list_transitions,
    list_filters,
    list_style_presets,
    TRANSITIONS,
    FILTERS,
    STYLE_PRESETS,
)

__all__ = [
    "add_transition",
    "auto_add_transitions",
    "get_style_preset",
    "list_transitions",
    "list_filters",
    "list_style_presets",
    "TRANSITIONS",
    "FILTERS",
    "STYLE_PRESETS",
]
