"""
cap_keyframe_engine — 关键帧引擎
为静态图片/视频片段自动添加运镜效果，解决"全是静止图片观感单调"问题

支持：
- Ken Burns效果（缓慢缩放+位移）
- 淡入淡出
- 运镜预设（推近/拉远/左移/右移/上移/下移）
- 随机运镜（避免重复）
"""
import os
import sys
import random
from typing import Optional, Tuple, List

# 确保jianying-editor可导入
def _ensure_jy_path():
    candidates = [
        os.getenv("JY_SKILL_ROOT", ""),
        r"C:\Users\Administrator\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills\jianying-editor",
    ]
    for p in candidates:
        if p and os.path.exists(os.path.join(p, "scripts", "jy_wrapper.py")):
            if p not in sys.path:
                sys.path.insert(0, os.path.join(p, "scripts"))
            return True
    return False

_ensure_jy_path()

try:
    import pyJianYingDraft as draft
    from pyJianYingDraft import KeyframeProperty as KP
    from pyJianYingDraft import Keyframe
    HAS_JY = True
except ImportError:
    HAS_JY = False
    draft = None
    KP = None
    Keyframe = None


# 运镜预设
CAMERA_MOVES = {
    "zoom_in": {
        "desc": "推近（缓慢放大）",
        "scale_start": 1.0, "scale_end": 1.15,
        "x_start": 0.0, "x_end": 0.0,
        "y_start": 0.0, "y_end": 0.0,
    },
    "zoom_out": {
        "desc": "拉远（缓慢缩小）",
        "scale_start": 1.15, "scale_end": 1.0,
        "x_start": 0.0, "x_end": 0.0,
        "y_start": 0.0, "y_end": 0.0,
    },
    "pan_left": {
        "desc": "左移",
        "scale_start": 1.1, "scale_end": 1.1,
        "x_start": 0.1, "x_end": -0.1,
        "y_start": 0.0, "y_end": 0.0,
    },
    "pan_right": {
        "desc": "右移",
        "scale_start": 1.1, "scale_end": 1.1,
        "x_start": -0.1, "x_end": 0.1,
        "y_start": 0.0, "y_end": 0.0,
    },
    "pan_up": {
        "desc": "上移",
        "scale_start": 1.1, "scale_end": 1.1,
        "x_start": 0.0, "x_end": 0.0,
        "y_start": -0.1, "y_end": 0.1,
    },
    "pan_down": {
        "desc": "下移",
        "scale_start": 1.1, "scale_end": 1.1,
        "x_start": 0.0, "x_end": 0.0,
        "y_start": 0.1, "y_end": -0.1,
    },
    "zoom_in_left": {
        "desc": "推近+左移",
        "scale_start": 1.0, "scale_end": 1.15,
        "x_start": 0.05, "x_end": -0.05,
        "y_start": 0.0, "y_end": 0.0,
    },
    "zoom_in_right": {
        "desc": "推近+右移",
        "scale_start": 1.0, "scale_end": 1.15,
        "x_start": -0.05, "x_end": 0.05,
        "y_start": 0.0, "y_end": 0.0,
    },
}


def add_ken_burns(segment, start_us: int, duration_us: int,
                  move_type: str = "zoom_in", intensity: float = 1.0):
    """
    给片段添加Ken Burns运镜效果

    Args:
        segment: 剪映片段对象
        start_us: 片段起始时间（微秒）
        duration_us: 片段持续时间（微秒）
        move_type: 运镜类型，见CAMERA_MOVES
        intensity: 强度系数，1.0为默认，0.5为减半
    """
    if not HAS_JY:
        return

    move = CAMERA_MOVES.get(move_type, CAMERA_MOVES["zoom_in"])
    end_us = start_us + duration_us

    # 缩放关键帧
    scale_start = 1.0 + (move["scale_start"] - 1.0) * intensity
    scale_end = 1.0 + (move["scale_end"] - 1.0) * intensity
    segment.add_keyframe(KP.uniform_scale, start_us, scale_start, **Keyframe.EASE_IN_OUT)
    segment.add_keyframe(KP.uniform_scale, end_us, scale_end, **Keyframe.EASE_IN_OUT)

    # X位移关键帧
    if move["x_start"] != 0 or move["x_end"] != 0:
        segment.add_keyframe(KP.position_x, start_us, move["x_start"] * intensity, **Keyframe.EASE_IN_OUT)
        segment.add_keyframe(KP.position_x, end_us, move["x_end"] * intensity, **Keyframe.EASE_IN_OUT)

    # Y位移关键帧
    if move["y_start"] != 0 or move["y_end"] != 0:
        segment.add_keyframe(KP.position_y, start_us, move["y_start"] * intensity, **Keyframe.EASE_IN_OUT)
        segment.add_keyframe(KP.position_y, end_us, move["y_end"] * intensity, **Keyframe.EASE_IN_OUT)


def add_fade_in_out(segment, start_us: int, duration_us: int,
                    fade_in_us: int = 300000, fade_out_us: int = 300000):
    """
    给片段添加淡入淡出效果

    Args:
        segment: 剪映片段对象
        start_us: 片段起始时间
        duration_us: 片段持续时间
        fade_in_us: 淡入时长（微秒，默认0.3秒）
        fade_out_us: 淡出时长（微秒，默认0.3秒）
    """
    if not HAS_JY:
        return

    end_us = start_us + duration_us

    # 淡入（fade_in_us=0时跳过）
    if fade_in_us > 0:
        segment.add_keyframe(KP.alpha, start_us, 0.0, **Keyframe.EASE_IN)
        segment.add_keyframe(KP.alpha, start_us + fade_in_us, 1.0, **Keyframe.EASE_IN)

    # 淡出（fade_out_us=0时跳过）
    if fade_out_us > 0:
        segment.add_keyframe(KP.alpha, end_us - fade_out_us, 1.0, **Keyframe.EASE_OUT)
        segment.add_keyframe(KP.alpha, end_us, 0.0, **Keyframe.EASE_OUT)


def auto_keyframe_for_still_image(segment, start_us: int, duration_us: int,
                                   index: int = 0, avoid_repeat: bool = True):
    """
    为静态图片自动添加关键帧（一键成片用）

    Args:
        segment: 剪映片段对象
        start_us: 起始时间
        duration_us: 持续时间
        index: 片段序号（用于避免重复运镜）
        avoid_repeat: 是否避免相邻片段使用相同运镜
    """
    if not HAS_JY:
        return

    # 选择运镜类型
    move_types = list(CAMERA_MOVES.keys())
    if avoid_repeat:
        move_type = move_types[index % len(move_types)]
    else:
        move_type = random.choice(move_types)

    # 短片段用弱效果，长片段用强效果
    intensity = 0.8 if duration_us < 2000000 else 1.0

    # 添加运镜
    add_ken_burns(segment, start_us, duration_us, move_type, intensity)

    # 淡入淡出：仅首片段淡入、尾片段淡出，中间保持不透明（避免黑屏）
    # 注意：调用方需传入total_count参数，或由调用方控制首尾
    # 这里默认：index==0淡入，其他不做淡入淡出（由转场负责过渡）
    if index == 0:
        add_fade_in_out(segment, start_us, duration_us, fade_in_us=500000, fade_out_us=0)
    # 中间和尾部片段不做alpha淡入淡出，避免与转场冲突导致黑屏


def list_camera_moves() -> List[str]:
    """列出所有可用运镜类型"""
    return list(CAMERA_MOVES.keys())


def get_move_description(move_type: str) -> str:
    """获取运镜类型描述"""
    return CAMERA_MOVES.get(move_type, {}).get("desc", "未知")
