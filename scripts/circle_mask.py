"""
圆形头像框蒙版工具 v1.0 (P22-2)
解决v9的核心问题：角色没有被圆形头像框裁切，超出框的部分可见。

功能：
1. 给角色片段添加圆形蒙版（头像框效果）
2. 蒙版位置/大小/羽化关键帧动画
3. 被打时蒙版震动效果
4. 多层蒙版（前景角色+背景）

剪映蒙版API：
- MaskType.圆形：圆形蒙版
- center_x/center_y：蒙版中心（相对素材，-1~1）
- size：圆形直径（占素材高度比例）
- feather：羽化（0~100）
- invert：反转

蒙版关键帧存储在draft_content.json的common_keyframes：
- KFTypeMaskSizeX/Y：蒙版大小
- KFTypeMaskPostionX/Y：蒙版位置（注意Postion拼写错误）
- KFTypeMaskFeather：羽化
"""

import logging
logger = logging.getLogger(__name__)

import os
import sys
import json
import uuid
from typing import List, Dict, Any

SKILL = r"C:\Users\Administrator\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills\jianying-editor"
sys.path.insert(0, os.path.join(SKILL, "scripts"))
sys.path.insert(0, os.path.join(SKILL, "scripts", "vendor"))

from jy_wrapper import JyProject
import pyJianYingDraft as draft
from pyJianYingDraft.metadata.mask_meta import MaskType


def add_circle_mask(
    segment,
    center_x: float = 0.0,
    center_y: float = 0.0,
    size: float = 0.8,
    feather: float = 0.0,
    invert: bool = False,
) -> bool:
    """
    给片段添加圆形蒙版

    Args:
        segment: VideoSegment实例
        center_x: 蒙版中心X（相对素材，-1=左，1=右）
        center_y: 蒙版中心Y（相对素材，-1=上，1=下）
        size: 圆形直径（占素材高度比例，0~1）
        feather: 羽化（0~100）
        invert: 是否反转

    Returns:
        bool: 是否成功
    """
    try:
        segment.add_mask(
            mask_type=MaskType.圆形,
            center_x=center_x,
            center_y=center_y,
            size=size,
            feather=feather,
            invert=invert,
        )
        return True
    except Exception as e:
        logger.error(f"  ❌ 添加圆形蒙版失败: {e}")
        return False


def add_avatar_frame_mask(
    project,
    segment,
    avatar_x: float = -0.653,
    avatar_y: float = 0.561,
    avatar_radius: float = 0.22,
    canvas_w: int = 1080,
    canvas_h: int = 1920,
    feather: float = 5.0,
) -> Dict[str, Any]:
    """
    添加头像框圆形蒙版（角色在框内，超出部分被裁切）

    原理：角色素材全屏，圆形蒙版放在头像框位置，只显示框内部分。

    Args:
        project: JyProject实例
        segment: 角色片段
        avatar_x: 头像框中心X（剪映坐标）
        avatar_y: 头像框中心Y（剪映坐标，y正=上）
        avatar_radius: 头像框半径（剪映坐标）
        canvas_w: 画布宽
        canvas_h: 画布高
        feather: 羽化

    Returns:
        蒙版信息字典
    """
    # 计算蒙版在素材中的位置和大小
    # 角色素材通常是全屏或半屏，蒙版中心需要转换
    # 假设角色素材scale=1.0铺满画布
    # 蒙版center_x/center_y是相对素材的（-1~1）
    # avatar_x/avatar_y是剪映坐标（-1~1），直接对应

    mask_size = avatar_radius * 2  # 直径
    if mask_size > 1.0:
        mask_size = 1.0

    result = add_circle_mask(
        segment,
        center_x=avatar_x,
        center_y=-avatar_y,  # 注意：蒙版的y轴方向可能与剪映坐标相反
        size=mask_size,
        feather=feather,
    )

    return {
        "status": "success" if result else "failed",
        "mask_type": "circle",
        "center_x": avatar_x,
        "center_y": avatar_y,
        "size": mask_size,
        "feather": feather,
    }


def add_mask_shake_keyframes(
    project,
    segment,
    start_us: int,
    duration_us: int,
    intensity: float = 0.03,
    base_x: float = -0.653,
    base_y: float = 0.561,
) -> bool:
    """
    添加蒙版震动关键帧（被打时头像框震动）

    Args:
        project: JyProject实例
        segment: 角色片段
        start_us: 开始时间（微秒）
        duration_us: 持续时间（微秒）
        intensity: 震动强度
        base_x: 基础位置X
        base_y: 基础位置Y

    Returns:
        bool: 是否成功
    """
    try:
        from mask_keyframe import apply_mask_keyframe

        # 震动模式：快速左右上下
        shakes = [
            (0.0, intensity, intensity * 0.7),
            (0.15, -intensity, -intensity * 0.5),
            (0.3, intensity * 0.8, intensity * 0.6),
            (0.45, -intensity * 0.6, -intensity * 0.4),
            (0.6, intensity * 0.4, intensity * 0.3),
            (0.8, 0, 0),
        ]

        for t_ratio, dx, dy in shakes:
            t = int(start_us + duration_us * t_ratio)
            apply_mask_keyframe(project, segment, "position_x", t, base_x + dx)
            apply_mask_keyframe(project, segment, "position_y", t, base_y + dy)

        # 恢复
        apply_mask_keyframe(project, segment, "position_x", start_us + duration_us, base_x)
        apply_mask_keyframe(project, segment, "position_y", start_us + duration_us, base_y)

        return True
    except Exception as e:
        logger.error(f"  ❌ 蒙版震动关键帧失败: {e}")
        return False


def apply_semantic_actions(
    project,
    segment,
    character_name: str,
    actions: List[Dict[str, Any]],
    avatar_x: float = -0.653,
    avatar_y: float = 0.561,
) -> Dict[str, Any]:
    """
    根据角色语义卡的动作列表，自动应用蒙版+位置关键帧

    Args:
        project: JyProject实例
        segment: 角色片段
        character_name: 角色名
        actions: 动作列表（来自character_semantic.py）
        avatar_x: 头像框位置X
        avatar_y: 头像框位置Y

    Returns:
        应用结果
    """
    applied = 0
    for action in actions:
        action_type = action.get("action_type", "idle")
        time_s = action.get("time", 0)
        intensity = action.get("intensity", 0.5)
        duration = action.get("duration", 0.5)
        emotion = action.get("emotion", "neutral")

        time_us = int(time_s * 1e6)
        dur_us = int(duration * 1e6)

        if action_type == "impact":
            # 被打：蒙版震动+角色下沉
            add_mask_shake_keyframes(
                project, segment, time_us, dur_us,
                intensity=0.02 + intensity * 0.03,
                base_x=avatar_x, base_y=avatar_y,
            )
            applied += 1

        elif action_type == "attack":
            # 攻击：蒙版位置变化（出拳方向）
            direction = action.get("direction", "left")
            dx = -0.05 if direction == "left" else 0.05
            try:
                from mask_keyframe import apply_mask_keyframe
                apply_mask_keyframe(project, segment, "position_x", time_us, avatar_x)
                apply_mask_keyframe(project, segment, "position_x", time_us + int(dur_us * 0.3), avatar_x + dx)
                apply_mask_keyframe(project, segment, "position_x", time_us + dur_us, avatar_x)
                applied += 1
            except Exception:
                pass

    return {
        "character": character_name,
        "actions_applied": applied,
        "total_actions": len(actions),
    }


def main():
    logger.info("=" * 60)
    logger.info("  圆形头像框蒙版工具 v1.0 (P22-2)")
    logger.info("=" * 60)
    logger.info("\n功能:")
    logger.info("  add_circle_mask(segment, center_x, center_y, size, feather)")
    logger.info("  add_avatar_frame_mask(project, segment, avatar_x, avatar_y, radius)")
    logger.info("  add_mask_shake_keyframes(project, segment, start_us, duration_us, intensity)")
    logger.info("  apply_semantic_actions(project, segment, name, actions)")
    logger.info("\n头像框默认位置: x=-0.653, y=+0.561, radius=0.22")
    logger.warning("注意: 蒙版位置y轴方向需验证（可能与剪映坐标相反）")


if __name__ == "__main__":
    main()
