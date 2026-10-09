"""
剪映运镜预设库
通过Keyframe API实现电影级运镜效果，支持缓动曲线

运镜类型：
- zoom_in / zoom_out: 推镜/拉镜
- pan_left / pan_right: 左摇/右摇
- tilt_up / tilt_down: 上摇/下摇
- rotate_cw / rotate_ccw: 顺时针/逆时针旋转
- pulse: 呼吸效果
- push_pan: 推+摇组合
- handheld: 手持晃动（微颤）
- dolly_zoom: 滑动变焦（希区柯克变焦）
"""

import logging
logger = logging.getLogger(__name__)

import sys
import os

JY_SKILL = r"C:\Users\Administrator\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills\jianying-editor"
sys.path.insert(0, os.path.join(JY_SKILL, "scripts"))

import pyJianYingDraft as draft
from pyJianYingDraft import KeyframeProperty as KP
from pyJianYingDraft import Keyframe


# 缓动曲线预设
EASE = {
    "linear": {"curve_type": "Line"},
    "ease_in": Keyframe.EASE_IN,
    "ease_out": Keyframe.EASE_OUT,
    "ease_in_out": Keyframe.EASE_IN_OUT,
}


def add_camera_move(segment, move_type: str, duration_us: int,
                    intensity: float = 0.12, ease: str = "ease_in_out"):
    """
    给视频片段添加运镜关键帧

    Args:
        segment: pyJianYingDraft VideoSegment 实例
        move_type: 运镜类型（见上方列表）
        duration_us: 片段时长（微秒）
        intensity: 运镜强度（0.05-0.3，默认0.12）
        ease: 缓动曲线 linear/ease_in/ease_out/ease_in_out
    """
    ease_params = EASE.get(ease, EASE["ease_in_out"])
    t_start = 0
    t_end = duration_us

    if move_type == "zoom_in":
        segment.add_keyframe(KP.uniform_scale, t_start, 1.0, **ease_params)
        segment.add_keyframe(KP.uniform_scale, t_end, 1.0 + intensity, **ease_params)

    elif move_type == "zoom_out":
        segment.add_keyframe(KP.uniform_scale, t_start, 1.0 + intensity, **ease_params)
        segment.add_keyframe(KP.uniform_scale, t_end, 1.0, **ease_params)

    elif move_type == "pan_left":
        base_scale = 1.0 + intensity * 1.5
        segment.add_keyframe(KP.uniform_scale, t_start, base_scale, **ease_params)
        segment.add_keyframe(KP.uniform_scale, t_end, base_scale, **ease_params)
        segment.add_keyframe(KP.position_x, t_start, intensity, **ease_params)
        segment.add_keyframe(KP.position_x, t_end, -intensity, **ease_params)

    elif move_type == "pan_right":
        base_scale = 1.0 + intensity * 1.5
        segment.add_keyframe(KP.uniform_scale, t_start, base_scale, **ease_params)
        segment.add_keyframe(KP.uniform_scale, t_end, base_scale, **ease_params)
        segment.add_keyframe(KP.position_x, t_start, -intensity, **ease_params)
        segment.add_keyframe(KP.position_x, t_end, intensity, **ease_params)

    elif move_type == "tilt_up":
        base_scale = 1.0 + intensity * 1.5
        segment.add_keyframe(KP.uniform_scale, t_start, base_scale, **ease_params)
        segment.add_keyframe(KP.uniform_scale, t_end, base_scale, **ease_params)
        segment.add_keyframe(KP.position_y, t_start, -intensity, **ease_params)
        segment.add_keyframe(KP.position_y, t_end, intensity, **ease_params)

    elif move_type == "tilt_down":
        base_scale = 1.0 + intensity * 1.5
        segment.add_keyframe(KP.uniform_scale, t_start, base_scale, **ease_params)
        segment.add_keyframe(KP.uniform_scale, t_end, base_scale, **ease_params)
        segment.add_keyframe(KP.position_y, t_start, intensity, **ease_params)
        segment.add_keyframe(KP.position_y, t_end, -intensity, **ease_params)

    elif move_type == "rotate_cw":
        segment.add_keyframe(KP.rotation, t_start, 0.0, **ease_params)
        segment.add_keyframe(KP.rotation, t_end, intensity * 30, **ease_params)

    elif move_type == "rotate_ccw":
        segment.add_keyframe(KP.rotation, t_start, 0.0, **ease_params)
        segment.add_keyframe(KP.rotation, t_end, -intensity * 30, **ease_params)

    elif move_type == "pulse":
        # 呼吸：缩放1.0→1.0+intensity/2→1.0
        mid = t_end // 2
        segment.add_keyframe(KP.uniform_scale, t_start, 1.0, **ease_params)
        segment.add_keyframe(KP.uniform_scale, mid, 1.0 + intensity * 0.5, **ease_params)
        segment.add_keyframe(KP.uniform_scale, t_end, 1.0, **ease_params)

    elif move_type == "push_pan":
        # 推+右摇组合（起始带缩放补偿防黑边）
        segment.add_keyframe(KP.uniform_scale, t_start, 1.0 + intensity, **ease_params)
        segment.add_keyframe(KP.uniform_scale, t_end, 1.0 + intensity * 1.5, **ease_params)
        segment.add_keyframe(KP.position_x, t_start, -intensity * 0.5, **ease_params)
        segment.add_keyframe(KP.position_x, t_end, intensity * 0.5, **ease_params)

    elif move_type == "handheld":
        # 手持晃动：多段微颤（基础缩放防黑边）
        base_scale = 1.0 + intensity
        segment.add_keyframe(KP.uniform_scale, t_start, base_scale, curve_type="Line")
        segment.add_keyframe(KP.uniform_scale, t_end, base_scale, curve_type="Line")
        num_shakes = 6
        for i in range(num_shakes):
            t1 = int(t_end * i / num_shakes)
            t2 = int(t_end * (i + 0.5) / num_shakes)
            t3 = int(t_end * (i + 1) / num_shakes)
            dx = intensity * 0.3 * (1 if i % 2 == 0 else -1)
            dy = intensity * 0.2 * (1 if i % 3 == 0 else -1)
            segment.add_keyframe(KP.position_x, t1, 0.0, curve_type="Line")
            segment.add_keyframe(KP.position_x, t2, dx, curve_type="Line")
            segment.add_keyframe(KP.position_x, t3, 0.0, curve_type="Line")
            segment.add_keyframe(KP.position_y, t1, 0.0, curve_type="Line")
            segment.add_keyframe(KP.position_y, t2, dy, curve_type="Line")
            segment.add_keyframe(KP.position_y, t3, 0.0, curve_type="Line")

    elif move_type == "dolly_zoom":
        # 希区柯克变焦：缩放+反向位移（起始带缩放补偿防黑边）
        segment.add_keyframe(KP.uniform_scale, t_start, 1.0 + intensity * 0.5, **ease_params)
        segment.add_keyframe(KP.uniform_scale, t_end, 1.0 + intensity, **ease_params)
        segment.add_keyframe(KP.position_x, t_start, 0.0, **ease_params)
        segment.add_keyframe(KP.position_x, t_end, -intensity * 0.3, **ease_params)

    elif move_type == "fade_in":
        segment.add_keyframe(KP.alpha, t_start, 0.0, **ease_params)
        segment.add_keyframe(KP.alpha, min(t_end, int(duration_us * 0.3)), 1.0, **ease_params)

    elif move_type == "fade_out":
        segment.add_keyframe(KP.alpha, max(0, t_end - int(duration_us * 0.3)), 1.0, **ease_params)
        segment.add_keyframe(KP.alpha, t_end, 0.0, **ease_params)

    else:
        # 默认推镜
        segment.add_keyframe(KP.uniform_scale, t_start, 1.0, **ease_params)
        segment.add_keyframe(KP.uniform_scale, t_end, 1.0 + intensity, **ease_params)


def add_cinematic_color_grade(segment, duration_us: int,
                                style: str = "cinematic"):
    """
    给片段添加调色关键帧（亮度/对比度/饱和度渐变）

    Args:
        segment: VideoSegment实例
        duration_us: 片段时长
        style: 调色风格 cinematic/warm/cool/vintage/noir
    """
    styles = {
        "cinematic": {"brightness": 0.02, "contrast": 0.08, "saturation": -0.05},
        "warm": {"brightness": 0.03, "contrast": 0.05, "saturation": 0.1},
        "cool": {"brightness": -0.02, "contrast": 0.06, "saturation": -0.08},
        "vintage": {"brightness": -0.03, "contrast": 0.1, "saturation": -0.15},
        "noir": {"brightness": -0.05, "contrast": 0.15, "saturation": -0.8},
    }
    cfg = styles.get(style, styles["cinematic"])
    ease = EASE["ease_in_out"]

    # 起始为0，结束为目标值（渐变调色）
    for prop, target in [
        (KP.brightness, cfg["brightness"]),
        (KP.contrast, cfg["contrast"]),
        (KP.saturation, cfg["saturation"]),
    ]:
        segment.add_keyframe(prop, 0, 0.0, **ease)
        segment.add_keyframe(prop, duration_us, target, **ease)


# 运镜映射表（分镜引擎的camera_move → 运镜类型）
CAMERA_MOVE_MAP = {
    "推": "zoom_in",
    "拉": "zoom_out",
    "快推": "zoom_in",
    "缓推": "zoom_in",
    "缓拉": "zoom_out",
    "移右": "pan_right",
    "移左": "pan_left",
    "摇上": "tilt_up",
    "摇下": "tilt_down",
    "固定": "pulse",
    "快切": "fade_in",
    "跟拍": "push_pan",
    "手持": "handheld",
    "旋转": "rotate_cw",
}


def apply_storyboard_camera_move(segment, camera_move: str, duration_us: int,
                                   intensity: float = 0.12):
    """根据分镜引擎的camera_move字段自动应用运镜"""
    move_type = CAMERA_MOVE_MAP.get(camera_move, "zoom_in")
    add_camera_move(segment, move_type, duration_us, intensity)


if __name__ == "__main__":
    logger.info("剪映运镜预设库已加载")
    logger.info("可用运镜类型:")
    moves = ["zoom_in", "zoom_out", "pan_left", "pan_right", "tilt_up", "tilt_down",
             "rotate_cw", "rotate_ccw", "pulse", "push_pan", "handheld", "dolly_zoom",
             "fade_in", "fade_out"]
    for m in moves:
        logger.info(f"  - {m}")
    logger.info("\n可用调色风格: cinematic/warm/cool/vintage/noir")
