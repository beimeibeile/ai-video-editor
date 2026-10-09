"""
Blender片头生成器
使用Blender生成3D文字动画+粒子+辉光片头视频

使用方法：
    from blender_intro import create_blender_intro
    video_path = create_blender_intro(
        title="精彩开始",
        subtitle="2024年度回顾",
        output_dir="./output",
        style="cinematic",  # cinematic/neon/minimal/epic
    )
"""

import logging
logger = logging.getLogger(__name__)


import os
import sys
from typing import Optional

# 导入Blender运行器
_skill_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_cap_dir = os.path.join(_skill_root, "capabilities")
if _cap_dir not in sys.path:
    sys.path.insert(0, _cap_dir)

from cap_blender_runner import (
    BlenderRunner, BlenderScene, BlenderText, BlenderParticles, BlenderGlow
)


# 片头风格预设
INTRO_STYLES = {
    "cinematic": {
        "title_color": (1.0, 0.85, 0.4, 1.0),  # 金色
        "title_emission": 3.0,
        "subtitle_color": (0.9, 0.9, 0.9, 1.0),
        "subtitle_emission": 1.0,
        "particle_color": (0.8, 0.6, 0.3, 1.0),
        "particle_count": 150,
        "bg_color": (0.02, 0.02, 0.05),
        "glow_threshold": 0.15,
        "glow_size": 8.0,
        "title_size": 2.2,
        "subtitle_size": 0.8,
    },
    "neon": {
        "title_color": (0.0, 1.0, 0.8, 1.0),  # 青色
        "title_emission": 5.0,
        "subtitle_color": (1.0, 0.2, 0.6, 1.0),  # 品红
        "subtitle_emission": 3.0,
        "particle_color": (0.0, 0.8, 1.0, 1.0),
        "particle_count": 200,
        "bg_color": (0.01, 0.01, 0.03),
        "glow_threshold": 0.1,
        "glow_size": 10.0,
        "title_size": 2.0,
        "subtitle_size": 0.7,
    },
    "minimal": {
        "title_color": (1.0, 1.0, 1.0, 1.0),  # 白色
        "title_emission": 1.0,
        "subtitle_color": (0.7, 0.7, 0.7, 1.0),
        "subtitle_emission": 0.5,
        "particle_color": (1.0, 1.0, 1.0, 0.5),
        "particle_count": 50,
        "bg_color": (0.05, 0.05, 0.05),
        "glow_threshold": 0.3,
        "glow_size": 3.0,
        "title_size": 1.8,
        "subtitle_size": 0.6,
    },
    "epic": {
        "title_color": (1.0, 0.2, 0.1, 1.0),  # 红色
        "title_emission": 4.0,
        "subtitle_color": (1.0, 0.8, 0.2, 1.0),  # 金色
        "subtitle_emission": 2.0,
        "particle_color": (1.0, 0.5, 0.0, 1.0),  # 橙色
        "particle_count": 300,
        "bg_color": (0.03, 0.01, 0.01),
        "glow_threshold": 0.12,
        "glow_size": 12.0,
        "title_size": 2.5,
        "subtitle_size": 0.9,
    },
}


def create_blender_intro(
    title: str,
    subtitle: str = "",
    output_dir: str = None,
    style: str = "cinematic",
    width: int = 1920,
    height: int = 1080,
    duration: float = 3.0,
    fps: int = 30,
    blender_path: str = None,
    ffmpeg_path: str = None,
) -> Optional[str]:
    """
    使用Blender生成片头视频

    Args:
        title: 主标题文字
        subtitle: 副标题文字（可选）
        output_dir: 输出目录
        style: 风格预设（cinematic/neon/minimal/epic）
        width: 视频宽度
        height: 视频高度
        duration: 时长（秒）
        fps: 帧率
        blender_path: Blender可执行文件路径（None=默认）
        ffmpeg_path: ffmpeg可执行文件路径（None=默认）

    Returns:
        生成的MP4视频路径，失败返回None
    """
    # 获取风格配置
    cfg = INTRO_STYLES.get(style, INTRO_STYLES["cinematic"])

    # 设置输出目录
    if output_dir is None:
        output_dir = os.path.join(os.getcwd(), "blender_intro_output")
    os.makedirs(output_dir, exist_ok=True)

    # 创建Blender运行器
    runner = BlenderRunner(
        blender_path=blender_path,
        ffmpeg_path=ffmpeg_path,
    )

    if not runner.is_available():
        logger.info(f"❌ Blender不可用: {runner.blender_path}")
        return None

    # 构建文字列表
    texts = [
        BlenderText(
            text=title,
            size=cfg["title_size"],
            location=(0, 0, 0),
            color=cfg["title_color"],
            emission_strength=cfg["title_emission"],
            extrude=0.15,
            bevel_depth=0.03,
        )
    ]

    if subtitle:
        texts.append(
            BlenderText(
                text=subtitle,
                size=cfg["subtitle_size"],
                location=(0, -1.5, 0),
                color=cfg["subtitle_color"],
                emission_strength=cfg["subtitle_emission"],
                extrude=0.05,
                bevel_depth=0.01,
            )
        )

    # 构建场景
    scene = BlenderScene(
        width=width,
        height=height,
        fps=fps,
        frame_end=int(duration * fps),
        background_color=cfg["bg_color"],
        texts=texts,
        particles=BlenderParticles(
            count=cfg["particle_count"],
            lifetime=int(duration * fps),
            color=cfg["particle_color"],
            emission_strength=2.0,
            normal_factor=2.5,
        ),
        glow=BlenderGlow(
            enabled=True,
            threshold=cfg["glow_threshold"],
            size=cfg["glow_size"],
        ),
        camera_location=(0, 0, 10),
    )

    # 生成并渲染
    logger.info(f"[Blender片头] 风格: {style}, 标题: {title}")
    logger.info(f"  分辨率: {width}x{height}, 时长: {duration}s, 粒子: {cfg['particle_count']}")

    mp4_path = runner.create_and_render(scene, output_dir)

    if mp4_path and os.path.exists(mp4_path):
        size_kb = os.path.getsize(mp4_path) / 1024
        logger.info(f"✅ Blender片头生成成功: {mp4_path} ({size_kb:.1f}KB)")
        return mp4_path
    else:
        logger.error(f"❌ Blender片头生成失败")
        return None


def create_blender_intro_batch(
    items: list,
    output_dir: str = None,
) -> list:
    """
    批量生成Blender片头

    Args:
        items: 配置列表，每项如 {"title": "...", "subtitle": "...", "style": "cinematic"}
        output_dir: 输出目录

    Returns:
        结果列表，每项包含配置和生成的视频路径
    """
    results = []
    for i, item in enumerate(items):
        item_output = os.path.join(output_dir or "./blender_intro_batch", f"intro_{i:02d}")
        video_path = create_blender_intro(
            title=item.get("title", "标题"),
            subtitle=item.get("subtitle", ""),
            output_dir=item_output,
            style=item.get("style", "cinematic"),
            width=item.get("width", 1920),
            height=item.get("height", 1080),
            duration=item.get("duration", 3.0),
        )
        results.append({
            "config": item,
            "video_path": video_path,
            "status": "success" if video_path else "failed",
        })
    return results


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Blender片头生成器")
    logger.info("=" * 60)
    logger.info("\n可用风格:")
    for name in INTRO_STYLES:
        cfg = INTRO_STYLES[name]
        logger.info(f"  - {name}: 标题色{cfg['title_color'][:3]}, 粒子{cfg['particle_count']}个")

    logger.info("\n使用方法:")
    logger.info("  create_blender_intro(")
    logger.info("    title='精彩开始',")
    logger.info("    subtitle='2024年度回顾',")
    logger.info("    style='cinematic',")
    logger.info("    duration=3.0")
    logger.info("  )")
