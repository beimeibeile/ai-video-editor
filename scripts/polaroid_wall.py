"""
拍立得照片墙特效
基于抖音教程《关键帧练习》分析封装

制作手法：
- 背景大图 + 多张拍立得风格照片画中画轨道
- 每张照片带白色/黄色边框，旋转角度错落
- 入场动画：旋转+缩放+位移依次入场
- 星星装饰贴纸

API支持：
- 多画中画轨道 + ClipSettings rotation
- Pillow预生成拍立得边框
- 入场动画
"""

import logging
logger = logging.getLogger(__name__)

import os
import sys
import math
import time
from typing import List, Dict, Tuple

skill_root = r"C:\Users\Administrator\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills\jianying-editor"
sys.path.insert(0, os.path.join(skill_root, "scripts"))
from jy_wrapper import JyProject
import pyJianYingDraft as draft

MODULE_DIR = os.path.dirname(os.path.abspath(__file__))


def create_polaroid_frame(
    image_path: str,
    output_path: str,
    border_color: Tuple[int, int, int] = (255, 255, 255),
    border_width: int = 40,
    bottom_margin: int = 120,
) -> str:
    """给照片添加拍立得边框

    Args:
        image_path: 原照片路径
        output_path: 输出路径
        border_color: 边框颜色RGB
        border_width: 边框宽度（像素）
        bottom_margin: 底部留白高度（拍立得特征）

    Returns:
        输出路径
    """
    from PIL import Image, ImageOps

    img = Image.open(image_path).convert("RGB")
    w, h = img.size

    # 拍立得比例：照片部分 + 底部留白
    total_w = w + border_width * 2
    total_h = h + border_width + bottom_margin

    canvas = Image.new("RGB", (total_w, total_h), border_color)
    canvas.paste(img, (border_width, border_width))

    canvas.save(output_path, quality=95)
    return output_path


def create_polaroid_wall(
    project_name: str,
    photos: List[str],
    background: str = None,
    width: int = 1080,
    height: int = 1920,
    photo_duration: float = 4.0,
    stagger: float = 0.5,
    border_color: Tuple[int, int, int] = (255, 240, 200),
    output_dir: str = None,
) -> Dict:
    """创建拍立得照片墙工程

    Args:
        project_name: 工程名
        photos: 照片路径列表
        background: 背景图路径（可选，None则黑色背景）
        width: 画布宽
        height: 画布高
        photo_duration: 每张照片持续时长（秒）
        stagger: 相邻照片入场时间差（秒）
        border_color: 拍立得边框颜色
        output_dir: 边框素材输出目录

    Returns:
        工程信息字典
    """
    if output_dir is None:
        output_dir = os.path.join(MODULE_DIR, "polaroid_assets")
    os.makedirs(output_dir, exist_ok=True)

    # 1. 生成拍立得边框照片
    polaroid_photos = []
    for i, photo in enumerate(photos):
        if not os.path.exists(photo):
            logger.warning(f"  ⚠️  照片不存在，跳过: {photo}")
            continue
        out_path = os.path.join(output_dir, f"polaroid_{i}.png")
        create_polaroid_frame(photo, out_path, border_color=border_color)
        polaroid_photos.append(out_path)
        logger.info(f"  ✅ 拍立得边框 [{i}]: {out_path}")

    # 2. 创建工程
    logger.info(f"\n[1/3] 创建工程: {project_name} ({width}x{height})")
    project = JyProject(project_name, width=width, height=height, overwrite=True)

    # 3. 添加背景
    total_duration = stagger * (len(polaroid_photos) - 1) + photo_duration
    if background and os.path.exists(background):
        project.add_media_safe(
            background,
            start_time="0s",
            duration=f"{total_duration}s",
            track_name="BG",
        )
        logger.info(f"  ✅ 背景: {background}")
    else:
        # 黑色背景
        from PIL import Image
        bg_path = os.path.join(output_dir, "black_bg.png")
        Image.new("RGB", (width, height), (20, 20, 20)).save(bg_path)
        project.add_media_safe(
            bg_path,
            start_time="0s",
            duration=f"{total_duration}s",
            track_name="BG",
        )
        logger.info(f"  ✅ 黑色背景")

    # 4. 添加拍立得照片（画中画轨道，旋转错落）
    logger.info(f"\n[2/3] 添加 {len(polaroid_photos)} 张拍立得照片")
    n = len(polaroid_photos)

    # 预设位置和旋转角度（错落分布）
    positions = []
    for i in range(n):
        # 环形/错落分布
        angle = (i / n) * math.pi * 2 - math.pi / 2
        radius = 0.25
        x = math.cos(angle) * radius
        y = math.sin(angle) * radius * 0.6  # 垂直方向压缩
        rotation = (i - n / 2) * 8  # 旋转角度错落
        scale = 0.55 + (i % 3) * 0.05  # 大小错落
        positions.append((x, y, rotation, scale))

    for i, (photo_path, (x, y, rot, scale)) in enumerate(zip(polaroid_photos, positions)):
        start_time = i * stagger
        track_name = f"Polaroid_{i}"

        seg = project.add_media_safe(
            photo_path,
            start_time=f"{start_time:.2f}s",
            duration=f"{photo_duration}s",
            track_name=track_name,
        )

        if seg:
            # 设置旋转和位置
            seg.clip_settings = draft.ClipSettings(
                transform_x=x,
                transform_y=y,
                rotation=rot,
                scale_x=scale,
                scale_y=scale,
            )
            # 入场动画：旋转+缩放
            seg.add_keyframe(
                draft.KeyframeProperty.uniform_scale,
                0, 0.0,
                **draft.Keyframe.EASE_OUT,
            )
            seg.add_keyframe(
                draft.KeyframeProperty.uniform_scale,
                int(0.5 * 1_000_000), scale,
                **draft.Keyframe.EASE_OUT,
            )
            seg.add_keyframe(
                draft.KeyframeProperty.rotation,
                0, rot - 30,
                **draft.Keyframe.EASE_OUT,
            )
            seg.add_keyframe(
                draft.KeyframeProperty.rotation,
                int(0.5 * 1_000_000), rot,
                **draft.Keyframe.EASE_OUT,
            )
            logger.info(f"  ✅ 照片 [{i}]: 位置({x:.2f},{y:.2f}) 旋转{rot:.0f}° 缩放{scale:.2f}")

    # 5. 保存
    logger.info(f"\n[3/3] 保存工程")
    project.save()

    return {
        "project_name": project_name,
        "photo_count": len(polaroid_photos),
        "total_duration": total_duration,
        "border_color": border_color,
    }


def add_polaroid_photos_to_project(
    project,
    photos: List[str],
    start_time: float = 0.0,
    duration: float = 4.0,
    stagger: float = 0.5,
    border_color: Tuple[int, int, int] = (255, 240, 200),
    output_dir: str = None,
) -> Dict:
    """在已有剪映工程中添加拍立得照片墙

    Args:
        project: JyProject 实例
        photos: 照片路径列表
        start_time: 起始时间（秒）
        duration: 每张照片持续时长（秒）
        stagger: 相邻照片入场时间差（秒）
        border_color: 边框颜色
        output_dir: 边框素材输出目录

    Returns:
        结果字典
    """
    if output_dir is None:
        output_dir = os.path.join(MODULE_DIR, "polaroid_assets")
    os.makedirs(output_dir, exist_ok=True)

    # 生成拍立得边框
    polaroid_photos = []
    for i, photo in enumerate(photos):
        if not os.path.exists(photo):
            continue
        out_path = os.path.join(output_dir, f"polaroid_{int(time.time())}_{i}.png")
        create_polaroid_frame(photo, out_path, border_color=border_color)
        polaroid_photos.append(out_path)

    n = len(polaroid_photos)
    positions = []
    for i in range(n):
        angle = (i / n) * math.pi * 2 - math.pi / 2
        radius = 0.25
        x = math.cos(angle) * radius
        y = math.sin(angle) * radius * 0.6
        rotation = (i - n / 2) * 8
        scale = 0.55 + (i % 3) * 0.05
        positions.append((x, y, rotation, scale))

    added = []
    for i, (photo_path, (x, y, rot, scale)) in enumerate(zip(polaroid_photos, positions)):
        seg_start = start_time + i * stagger
        track_name = f"Polaroid_{i}"

        seg = project.add_media_safe(
            photo_path,
            start_time=f"{seg_start:.2f}s",
            duration=f"{duration}s",
            track_name=track_name,
        )

        if seg:
            seg.clip_settings = draft.ClipSettings(
                transform_x=x, transform_y=y,
                rotation=rot, scale_x=scale, scale_y=scale,
            )
            seg.add_keyframe(draft.KeyframeProperty.uniform_scale, 0, 0.0, **draft.Keyframe.EASE_OUT)
            seg.add_keyframe(draft.KeyframeProperty.uniform_scale, int(0.5 * 1e6), scale, **draft.Keyframe.EASE_OUT)
            added.append({"photo": photo_path, "start": seg_start, "rotation": rot})

    return {
        "status": "success",
        "photo_count": len(added),
        "start_time": start_time,
        "duration": duration,
        "added": added,
    }


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("拍立得照片墙特效")
    logger.info("=" * 60)
    logger.info("用法:")
    logger.info("  create_polaroid_wall('测试', ['photo1.jpg', 'photo2.jpg'])")
    logger.info("  add_polaroid_photos_to_project(project, ['photo1.jpg'])")
