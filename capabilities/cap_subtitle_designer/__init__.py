"""
cap_subtitle_designer — 字幕设计模块
动态艺术组合式字幕，多轨道叠加+动画+样式
"""
from .subtitle_designer import (
    add_artistic_subtitle,
    add_simple_subtitle,
    add_hook_title,
    list_styles,
    SUBTITLE_STYLES,
)

__all__ = [
    "add_artistic_subtitle",
    "add_simple_subtitle",
    "add_hook_title",
    "list_styles",
    "SUBTITLE_STYLES",
]
