"""
片头生成器模块 (cap_intro_generator)
一键生成短视频片头，支持5种风格+时长自适应+本地资源库优先

风格：impact(震撼)/cute(可爱)/funny(滑稽)/minimal(简约)/suspense(悬念)
视频类型：short(1-3s)/medium(3-5s)/long(5-10s)

资源策略：本地资源库优先，缺失时ffmpeg降级，AI生成仅在明确要求时调用
"""
from .intro_generator import IntroGenerator, generate_intro, list_styles
from .styles import STYLES, get_style, get_duration, DURATION_PRESETS

__all__ = [
    "IntroGenerator", "generate_intro", "list_styles",
    "STYLES", "get_style", "get_duration", "DURATION_PRESETS",
]
