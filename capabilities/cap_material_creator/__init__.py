"""
cap_material_creator — 制作素材能力模块
可用户触发，也可由主流程在素材准备阶段自主触发。
"""
from .outline_generator import generate_outline, generate_outline_from_text
from .texture_generator import generate_texture, TEXTURE_PRESETS
from .blend_compositor import multiply_blend, screen_blend, composite
from .placeholder_generator import generate_placeholder, generate_placeholder_batch
from .background_generator import generate_background
from .subtitle_bar_generator import (
    generate_subtitle_bar, generate_subtitle_bar_preset,
    generate_subtitle_bar_animated, SUBTITLE_BAR_PRESETS, ANIMATION_PRESETS
)

__all__ = [
    "generate_outline", "generate_outline_from_text",
    "generate_texture", "TEXTURE_PRESETS",
    "multiply_blend", "screen_blend", "composite",
    "generate_placeholder", "generate_placeholder_batch",
    "generate_background",
    "generate_subtitle_bar", "generate_subtitle_bar_preset",
    "generate_subtitle_bar_animated", "SUBTITLE_BAR_PRESETS", "ANIMATION_PRESETS",
]
