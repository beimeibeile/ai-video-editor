"""
文字背景块滑入特效
基于抖音教程《文字排版004》封装

制作手法：
1. 创建纯色背景块（矩形）
2. 背景块从左向右滑入（位置关键帧）
3. 文字叠加在背景块上
4. 可选：文字大小/位置关键帧动画

使用方法：
    from text_background_slide import create_text_bg_slide
    create_text_bg_slide(
        project_name="测试",
        text="ATTENTION",
        bg_color=(180, 0, 0),  # 深红色
        text_color=(255, 255, 255),
        direction="left",  # left/right/top/bottom
        duration=2.0,
    )
"""

import logging
logger = logging.getLogger(__name__)


import os
import sys
import uuid
from typing import Dict, Any, Optional, Tuple

skill_root = r"C:\Users\Administrator\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills\jianying-editor"
sys.path.insert(0, os.path.join(skill_root, "scripts"))
from jy_wrapper import JyProject
import pyJianYingDraft as draft

try:
    from PIL import Image
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False


def create_color_block(color: Tuple[int, int, int], width: int, height: int,
                       output_path: str) -> Optional[str]:
    """
    创建纯色背景块图片

    Args:
        color: RGB颜色
        width: 宽度
        height: 高度
        output_path: 输出路径

    Returns:
        输出路径或None
    """
    if not _PIL_AVAILABLE:
        logger.info("❌ Pillow未安装，无法创建背景块")
        return None

    try:
        img = Image.new("RGB", (width, height), color)
        img.save(output_path)
        return output_path
    except Exception as e:
        logger.error(f"❌ 创建背景块失败: {e}")
        return None


def create_text_bg_slide(
    project_name: str,
    text: str,
    bg_color: Tuple[int, int, int] = (180, 0, 0),
    text_color: Tuple[int, int, int] = (255, 255, 255),
    direction: str = "left",
    duration: float = 2.0,
    slide_duration: float = 0.5,
    width: int = 1080,
    height: int = 1920,
    font_size: float = 12.0,
    bg_width_ratio: float = 0.8,
    bg_height_ratio: float = 0.15,
    output_dir: str = None,
) -> Dict[str, Any]:
    """
    创建文字背景块滑入特效工程

    Args:
        project_name: 工程名
        text: 文字内容
        bg_color: 背景块颜色 (R,G,B)
        text_color: 文字颜色 (R,G,B)
        direction: 滑入方向 (left/right/top/bottom)
        duration: 总时长（秒）
        slide_duration: 滑入动画时长（秒）
        width: 画布宽
        height: 画布高
        font_size: 字号
        bg_width_ratio: 背景块宽度比例（相对画布宽度）
        bg_height_ratio: 背景块高度比例（相对画布高度）
        output_dir: 素材输出目录

    Returns:
        工程信息字典
    """
    if output_dir is None:
        output_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "text_bg_slide_assets"
        )
    os.makedirs(output_dir, exist_ok=True)

    # 1. 创建背景块图片
    logger.info(f"\n[1/4] 创建背景块: {bg_color}")
    bg_w = int(width * bg_width_ratio)
    bg_h = int(height * bg_height_ratio)
    bg_path = os.path.join(output_dir, f"bg_{uuid.uuid4().hex[:8]}.png")
    bg_path = create_color_block(bg_color, bg_w, bg_h, bg_path)
    if not bg_path:
        return {"status": "failed", "reason": "背景块创建失败"}

    # 2. 创建工程
    logger.info(f"[2/4] 创建工程: {project_name} ({width}x{height})")
    project = JyProject(project_name, width=width, height=height, overwrite=True)

    # 3. 添加背景块并设置滑入动画
    logger.info(f"[3/4] 添加背景块滑入动画 ({direction})")
    bg_seg = project.add_media_safe(
        bg_path,
        start_time="0s",
        duration=f"{duration}s",
        track_name="BgBlock"
    )
    if not bg_seg:
        return {"status": "failed", "reason": "背景块添加失败"}

    # 设置滑入关键帧
    slide_us = int(slide_duration * 1e6)
    if direction == "left":
        # 从左滑入：位置X从-1.5→0
        bg_seg.add_keyframe(draft.KeyframeProperty.position_x, 0, -1.5, **draft.Keyframe.EASE_OUT)
        bg_seg.add_keyframe(draft.KeyframeProperty.position_x, slide_us, 0.0, **draft.Keyframe.EASE_OUT)
    elif direction == "right":
        # 从右滑入：位置X从1.5→0
        bg_seg.add_keyframe(draft.KeyframeProperty.position_x, 0, 1.5, **draft.Keyframe.EASE_OUT)
        bg_seg.add_keyframe(draft.KeyframeProperty.position_x, slide_us, 0.0, **draft.Keyframe.EASE_OUT)
    elif direction == "top":
        # 从上滑入：位置Y从-1.5→0
        bg_seg.add_keyframe(draft.KeyframeProperty.position_y, 0, -1.5, **draft.Keyframe.EASE_OUT)
        bg_seg.add_keyframe(draft.KeyframeProperty.position_y, slide_us, 0.0, **draft.Keyframe.EASE_OUT)
    elif direction == "bottom":
        # 从下滑入：位置Y从1.5→0
        bg_seg.add_keyframe(draft.KeyframeProperty.position_y, 0, 1.5, **draft.Keyframe.EASE_OUT)
        bg_seg.add_keyframe(draft.KeyframeProperty.position_y, slide_us, 0.0, **draft.Keyframe.EASE_OUT)

    # 4. 添加文字
    logger.info(f"[4/4] 添加文字: {text}")
    text_seg = project.add_text_simple(
        text,
        start_time=f"{slide_duration * 0.3:.2f}s",  # 文字延迟出现
        duration=f"{duration - slide_duration * 0.3:.2f}s",
        track_name="Text",
        style=draft.TextStyle(size=font_size, color=(text_color[0]/255, text_color[1]/255, text_color[2]/255)),
    )

    # 文字淡入动画
    if text_seg:
        text_start_us = int(slide_duration * 0.3 * 1e6)
        text_fade_us = int(0.3 * 1e6)
        text_seg.add_keyframe(draft.KeyframeProperty.alpha, text_start_us, 0.0, **draft.Keyframe.EASE_OUT)
        text_seg.add_keyframe(draft.KeyframeProperty.alpha, text_start_us + text_fade_us, 1.0, **draft.Keyframe.EASE_OUT)

    # 5. 保存工程
    result = project.save()
    draft_path = result.get("draft_path", "")

    logger.info(f"\n✅ 文字背景块滑入特效创建完成")
    logger.info(f"   工程: {project_name}")
    logger.info(f"   背景块: {bg_w}x{bg_h} {bg_color}")
    logger.info(f"   文字: {text} ({font_size}px {text_color})")
    logger.info(f"   滑入方向: {direction} ({slide_duration}s)")
    logger.info(f"   草稿路径: {draft_path}")

    return {
        "status": "success",
        "project_name": project_name,
        "draft_path": draft_path,
        "text": text,
        "bg_color": bg_color,
        "direction": direction,
        "duration": duration,
    }


def add_text_bg_slide_to_project(
    project,
    text: str,
    start_time: float = 0.0,
    duration: float = 2.0,
    bg_color: Tuple[int, int, int] = (180, 0, 0),
    text_color: Tuple[int, int, int] = (255, 255, 255),
    direction: str = "left",
    slide_duration: float = 0.5,
    font_size: float = 12.0,
    output_dir: str = None,
) -> Dict[str, Any]:
    """
    在已有剪映工程中添加文字背景块滑入特效

    Args:
        project: JyProject 实例
        text: 文字内容
        start_time: 起始时间（秒）
        duration: 持续时长（秒）
        bg_color: 背景块颜色
        text_color: 文字颜色
        direction: 滑入方向
        slide_duration: 滑入动画时长
        font_size: 字号
        output_dir: 素材输出目录

    Returns:
        效果信息字典
    """
    if output_dir is None:
        output_dir = os.path.join(project.root, project.name, "text_bg_slide_assets")
    os.makedirs(output_dir, exist_ok=True)

    # 创建背景块
    canvas_w = getattr(project, "width", 1080)
    canvas_h = getattr(project, "height", 1920)
    bg_w = int(canvas_w * 0.8)
    bg_h = int(canvas_h * 0.15)
    bg_path = os.path.join(output_dir, f"bg_{uuid.uuid4().hex[:8]}.png")
    bg_path = create_color_block(bg_color, bg_w, bg_h, bg_path)

    # 添加背景块
    bg_seg = project.add_media_safe(
        bg_path,
        start_time=f"{start_time}s",
        duration=f"{duration}s",
        track_name="BgBlock"
    )

    # 滑入动画
    slide_us = int(slide_duration * 1e6)
    start_us = int(start_time * 1e6)
    if direction == "left":
        bg_seg.add_keyframe(draft.KeyframeProperty.position_x, start_us, -1.5, **draft.Keyframe.EASE_OUT)
        bg_seg.add_keyframe(draft.KeyframeProperty.position_x, start_us + slide_us, 0.0, **draft.Keyframe.EASE_OUT)
    elif direction == "right":
        bg_seg.add_keyframe(draft.KeyframeProperty.position_x, start_us, 1.5, **draft.Keyframe.EASE_OUT)
        bg_seg.add_keyframe(draft.KeyframeProperty.position_x, start_us + slide_us, 0.0, **draft.Keyframe.EASE_OUT)

    # 添加文字
    text_start = start_time + slide_duration * 0.3
    text_seg = project.add_text_simple(
        text,
        start_time=f"{text_start:.2f}s",
        duration=f"{duration - slide_duration * 0.3:.2f}s",
        track_name="Text",
        style=draft.TextStyle(size=font_size, color=(text_color[0]/255, text_color[1]/255, text_color[2]/255)),
    )

    return {
        "status": "success",
        "bg_segment": bg_seg,
        "text_segment": text_seg,
        "text": text,
    }


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("文字背景块滑入特效")
    logger.info("=" * 60)
    logger.info("\n使用方法:")
    logger.info("  create_text_bg_slide(")
    logger.info("    project_name='测试',")
    logger.info("    text='ATTENTION',")
    logger.info("    bg_color=(180, 0, 0),")
    logger.info("    direction='left',")
    logger.info("    duration=2.0")
    logger.info("  )")
    logger.info(f"\nPillow: {'✅' if _PIL_AVAILABLE else '❌'}")
    logger.info("滑入方向: left / right / top / bottom")
