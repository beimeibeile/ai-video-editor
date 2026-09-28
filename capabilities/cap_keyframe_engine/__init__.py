"""
cap_keyframe_engine — 关键帧引擎
为静态图片/视频片段自动添加运镜效果
"""
from .keyframe_engine import (
    add_ken_burns,
    add_fade_in_out,
    auto_keyframe_for_still_image,
    list_camera_moves,
    get_move_description,
    CAMERA_MOVES,
)

__all__ = [
    "add_ken_burns",
    "add_fade_in_out",
    "auto_keyframe_for_still_image",
    "list_camera_moves",
    "get_move_description",
    "CAMERA_MOVES",
]
