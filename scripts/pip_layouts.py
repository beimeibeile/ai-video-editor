"""
多轨道画中画布局模板
通过ClipSettings的transform/scale实现多画面布局

布局类型：
- split_h: 左右分屏
- split_v: 上下分屏
- pip: 画中画（小窗口）
- triple_v: 三屏竖排
- quad: 四宫格
- pip_corner: 角落画中画（可指定角落）
"""

import logging
logger = logging.getLogger(__name__)

import os
import sys

JY_SKILL = r"C:\Users\Administrator\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills\jianying-editor"
sys.path.insert(0, os.path.join(JY_SKILL, "scripts"))

import pyJianYingDraft as draft
from pyJianYingDraft import ClipSettings


def _add_clip_to_track(project, media_path: str, start_time: str, duration: str,
                         track_name: str, clip_settings: ClipSettings):
    """添加片段到指定轨道并应用ClipSettings"""
    seg = project.add_media_safe(
        media_path, start_time=start_time, duration=duration,
        track_name=track_name,
    )
    if seg:
        seg.clip_settings = clip_settings
    return seg


def layout_split_h(project, left_media: str, right_media: str,
                    start_time: str, duration: str,
                    gap: float = 0.02) -> list:
    """
    左右分屏布局

    Args:
        project: JyProject实例
        left_media: 左侧素材路径
        right_media: 右侧素材路径
        start_time: 起始时间
        duration: 持续时长
        gap: 中间间隙（0-0.1）

    Returns:
        [left_segment, right_segment]
    """
    scale = 0.5 - gap / 2
    left_settings = ClipSettings(
        transform_x=-(0.5 + gap / 2),
        scale_x=scale * 2, scale_y=1.0,
    )
    right_settings = ClipSettings(
        transform_x=(0.5 + gap / 2),
        scale_x=scale * 2, scale_y=1.0,
    )

    segs = []
    segs.append(_add_clip_to_track(project, left_media, start_time, duration, "PIP_Left", left_settings))
    segs.append(_add_clip_to_track(project, right_media, start_time, duration, "PIP_Right", right_settings))
    return segs


def layout_split_v(project, top_media: str, bottom_media: str,
                    start_time: str, duration: str,
                    gap: float = 0.02) -> list:
    """上下分屏布局"""
    scale = 0.5 - gap / 2
    top_settings = ClipSettings(
        transform_y=(0.5 + gap / 2),
        scale_x=1.0, scale_y=scale * 2,
    )
    bottom_settings = ClipSettings(
        transform_y=-(0.5 + gap / 2),
        scale_x=1.0, scale_y=scale * 2,
    )

    segs = []
    segs.append(_add_clip_to_track(project, top_media, start_time, duration, "PIP_Top", top_settings))
    segs.append(_add_clip_to_track(project, bottom_media, start_time, duration, "PIP_Bottom", bottom_settings))
    return segs


def layout_pip(project, bg_media: str, fg_media: str,
                start_time: str, duration: str,
                position: str = "bottom_right",
                size: float = 0.35,
                margin: float = 0.05) -> list:
    """
    画中画布局（大背景+小窗口）

    Args:
        project: JyProject实例
        bg_media: 背景素材路径
        fg_media: 前景（小窗口）素材路径
        start_time: 起始时间
        duration: 持续时长
        position: 小窗口位置 top_left/top_right/bottom_left/bottom_right/center
        size: 小窗口大小（0.2-0.5）
        margin: 边距

    Returns:
        [bg_segment, fg_segment]
    """
    positions = {
        "top_left": (-0.5 + size / 2 + margin, 0.5 - size / 2 - margin),
        "top_right": (0.5 - size / 2 - margin, 0.5 - size / 2 - margin),
        "bottom_left": (-0.5 + size / 2 + margin, -0.5 + size / 2 + margin),
        "bottom_right": (0.5 - size / 2 - margin, -0.5 + size / 2 + margin),
        "center": (0, 0),
    }
    x, y = positions.get(position, positions["bottom_right"])

    bg_settings = ClipSettings(scale_x=1.0, scale_y=1.0)
    fg_settings = ClipSettings(
        transform_x=x, transform_y=y,
        scale_x=size, scale_y=size,
    )

    segs = []
    segs.append(_add_clip_to_track(project, bg_media, start_time, duration, "PIP_BG", bg_settings))
    segs.append(_add_clip_to_track(project, fg_media, start_time, duration, "PIP_FG", fg_settings))
    return segs


def layout_triple_v(project, media_list: list, start_time: str, duration: str,
                     gap: float = 0.015) -> list:
    """
    三屏竖排布局

    Args:
        media_list: 3个素材路径 [top, middle, bottom]
        start_time: 起始时间
        duration: 持续时长
        gap: 间隙

    Returns:
        片段列表
    """
    if len(media_list) < 3:
        raise ValueError("三屏布局需要3个素材")

    scale = (1.0 - gap * 2) / 3
    y_positions = [
        (1.0 / 3) + gap,       # top
        0,                      # middle
        -(1.0 / 3) - gap,      # bottom
    ]

    segs = []
    for i, (media, y) in enumerate(zip(media_list, y_positions)):
        settings = ClipSettings(
            transform_y=y,
            scale_x=1.0, scale_y=scale * 3,
        )
        segs.append(_add_clip_to_track(project, media, start_time, duration, f"PIP_Triple_{i}", settings))
    return segs


def layout_quad(project, media_list: list, start_time: str, duration: str,
                 gap: float = 0.015) -> list:
    """
    四宫格布局

    Args:
        media_list: 4个素材路径 [tl, tr, bl, br]
        start_time: 起始时间
        duration: 持续时长
        gap: 间隙

    Returns:
        片段列表
    """
    if len(media_list) < 4:
        raise ValueError("四宫格需要4个素材")

    scale = 0.5 - gap
    positions = [
        (-0.25 - gap / 2, 0.25 + gap / 2),   # tl
        (0.25 + gap / 2, 0.25 + gap / 2),    # tr
        (-0.25 - gap / 2, -0.25 - gap / 2),  # bl
        (0.25 + gap / 2, -0.25 - gap / 2),   # br
    ]

    segs = []
    for i, (media, (x, y)) in enumerate(zip(media_list, positions)):
        settings = ClipSettings(
            transform_x=x, transform_y=y,
            scale_x=scale * 2, scale_y=scale * 2,
        )
        segs.append(_add_clip_to_track(project, media, start_time, duration, f"PIP_Quad_{i}", settings))
    return segs


def layout_comparison(project, before_media: str, after_media: str,
                       start_time: str, duration: str,
                       label_before: str = "Before",
                       label_after: str = "After") -> list:
    """
    对比布局（左右分屏+标签文字）

    Args:
        project: JyProject实例
        before_media: 左侧（Before）素材
        after_media: 右侧（After）素材
        start_time: 起始时间
        duration: 持续时长
        label_before: 左侧标签文字
        label_after: 右侧标签文字

    Returns:
        [left_seg, right_seg, label_before_seg, label_after_seg]
    """
    segs = layout_split_h(project, before_media, after_media, start_time, duration)

    # 添加标签
    try:
        project.add_text_simple(
            label_before, start_time=start_time, duration=duration,
            font_size=6.0, color_rgb=(1, 1, 1),
            style=draft.TextStyle(size=6.0, bold=True),
            border=draft.TextBorder(color=(0, 0, 0), width=30),
            clip_settings=ClipSettings(transform_x=-0.5, transform_y=0.4),
            anim_in="渐显", track_name="PIP_Label_L",
        )
        project.add_text_simple(
            label_after, start_time=start_time, duration=duration,
            font_size=6.0, color_rgb=(1, 1, 1),
            style=draft.TextStyle(size=6.0, bold=True),
            border=draft.TextBorder(color=(0, 0, 0), width=30),
            clip_settings=ClipSettings(transform_x=0.5, transform_y=0.4),
            anim_in="渐显", track_name="PIP_Label_R",
        )
    except Exception:
        pass

    return segs


# 布局类型映射
LAYOUTS = {
    "split_h": layout_split_h,
    "split_v": layout_split_v,
    "pip": layout_pip,
    "triple_v": layout_triple_v,
    "quad": layout_quad,
    "comparison": layout_comparison,
}


def apply_layout(project, layout_type: str, media_list: list,
                  start_time: str, duration: str, **kwargs):
    """
    通用布局应用接口

    Args:
        project: JyProject实例
        layout_type: 布局类型 (split_h/split_v/pip/triple_v/quad/comparison)
        media_list: 素材路径列表
        start_time: 起始时间
        duration: 持续时长
        **kwargs: 布局特定参数

    Returns:
        片段列表
    """
    func = LAYOUTS.get(layout_type)
    if func is None:
        raise ValueError(f"未知布局类型: {layout_type}, 可用: {list(LAYOUTS.keys())}")

    if layout_type in ("split_h", "split_v", "comparison"):
        return func(project, media_list[0], media_list[1], start_time, duration, **kwargs)
    elif layout_type == "pip":
        return func(project, media_list[0], media_list[1], start_time, duration, **kwargs)
    elif layout_type in ("triple_v", "quad"):
        return func(project, media_list, start_time, duration, **kwargs)


if __name__ == "__main__":
    logger.info("多轨道画中画布局模板已加载")
    logger.info("可用布局:")
    for name in LAYOUTS:
        logger.info(f"  - {name}")
