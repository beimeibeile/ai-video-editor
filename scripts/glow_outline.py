"""
动态发光轮廓效果
基于抖音教程《剪映进阶篇--制作动态发光轮廓效果》封装

制作手法：
1. AI生成黑底白边轮廓图（或使用用户提供的轮廓图）
2. 彩色素材放轮廓图下层
3. 轮廓图设"正片叠底"混合模式→彩色轮廓
4. 彩色轨道加"梦幻辉光"特效
5. 整体加"梦境"特效

依赖：
- mix_mode.py（正片叠底混合模式）
- Pillow（生成轮廓图）
"""

import logging
logger = logging.getLogger(__name__)


import os
import sys
import uuid
from typing import Dict, Any, Optional

skill_root = r"C:\Users\Administrator\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills\jianying-editor"
sys.path.insert(0, os.path.join(skill_root, "scripts"))
from jy_wrapper import JyProject
import pyJianYingDraft as draft

try:
    from PIL import Image, ImageFilter, ImageOps
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False

try:
    from mix_mode import apply_mix_mode, save_with_mix_modes, MIX_MODES
    _MIX_MODE_AVAILABLE = True
except ImportError:
    _MIX_MODE_AVAILABLE = False


def generate_outline_image(source_path: str, output_path: str,
                           threshold: int = 128,
                           edge_width: int = 2,
                           invert: bool = True) -> Optional[str]:
    """
    从图片生成黑底白边轮廓图

    Args:
        source_path: 源图片路径
        output_path: 输出轮廓图路径
        threshold: 二值化阈值（0-255）
        edge_width: 边缘宽度
        invert: 是否反色（True=黑底白边，False=白底黑边）

    Returns:
        输出路径或None
    """
    if not _PIL_AVAILABLE:
        logger.info("❌ Pillow未安装，无法生成轮廓图")
        return None

    try:
        img = Image.open(source_path).convert("L")

        # 二值化
        binary = img.point(lambda x: 255 if x > threshold else 0, '1')

        # 边缘检测
        edges = binary.filter(ImageFilter.FIND_EDGES)

        # 膨胀边缘
        for _ in range(edge_width):
            edges = edges.filter(ImageFilter.MaxFilter(3))

        if invert:
            edges = ImageOps.invert(edges.convert("L"))

        # 转为RGB
        result = edges.convert("RGB")
        result.save(output_path)
        logger.info(f"  ✅ 轮廓图已生成: {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"❌ 生成轮廓图失败: {e}")
        return None


def create_glow_outline(
    project_name: str,
    base_image: str,
    outline_image: str = None,
    width: int = 1080,
    height: int = 1920,
    duration: float = 5.0,
    glow_effect: str = "梦幻辉光",
    dream_effect: str = "梦境",
    output_dir: str = None,
) -> Dict[str, Any]:
    """
    创建动态发光轮廓效果工程

    Args:
        project_name: 工程名
        base_image: 底层彩色素材图片路径
        outline_image: 上层轮廓图路径（None则自动生成）
        width: 画布宽
        height: 画布高
        duration: 持续时长（秒）
        glow_effect: 辉光特效名称
        dream_effect: 梦境特效名称
        output_dir: 素材输出目录

    Returns:
        工程信息字典
    """
    if output_dir is None:
        output_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "glow_outline_assets"
        )
    os.makedirs(output_dir, exist_ok=True)

    # 1. 生成轮廓图（如果未提供）
    if outline_image is None:
        outline_path = os.path.join(output_dir, f"outline_{uuid.uuid4().hex[:8]}.png")
        outline_image = generate_outline_image(base_image, outline_path)
        if outline_image is None:
            return {"status": "failed", "reason": "轮廓图生成失败"}

    # 2. 创建工程
    logger.info(f"\n[1/4] 创建工程: {project_name} ({width}x{height})")
    project = JyProject(project_name, width=width, height=height, overwrite=True)

    # 3. 添加底层彩色素材
    logger.info(f"[2/4] 添加底层彩色素材")
    base_seg = project.add_media_safe(
        base_image,
        start_time="0s",
        duration=f"{duration}s",
        track_name="BaseLayer"
    )
    if not base_seg:
        return {"status": "failed", "reason": "底层素材添加失败"}

    # 4. 添加上层轮廓图
    logger.info(f"[3/4] 添加上层轮廓图 + 正片叠底混合模式")
    outline_seg = project.add_media_safe(
        outline_image,
        start_time="0s",
        duration=f"{duration}s",
        track_name="OutlineLayer"
    )
    if not outline_seg:
        return {"status": "failed", "reason": "轮廓图添加失败"}

    # 5. 应用正片叠底混合模式
    if _MIX_MODE_AVAILABLE:
        apply_mix_mode(project, outline_seg, mode="multiply", intensity=1.0)
    else:
        logger.info("  ⚠️  mix_mode模块不可用，正片叠底需手动设置")

    # 6. 添加梦幻辉光特效（到底层）
    logger.info(f"[4/4] 添加特效: {glow_effect} + {dream_effect}")
    try:
        project.add_effect_simple(
            glow_effect,
            start_time="0s",
            duration=f"{duration}s",
            track_name="GlowEffect"
        )
        logger.info(f"  ✅ {glow_effect}特效已添加")
    except Exception as e:
        logger.error(f"  ⚠️  {glow_effect}特效添加失败: {e}")

    # 7. 添加梦境特效（全局）
    try:
        dream_seg = project.add_effect_simple(
            dream_effect,
            start_time="0s",
            duration=f"{duration}s",
            track_name="DreamEffect"
        )
        # 设置为全局特效
        if dream_seg:
            dream_seg.render_index = 10000
        logger.info(f"  ✅ {dream_effect}特效已添加")
    except Exception as e:
        logger.error(f"  ⚠️  {dream_effect}特效添加失败: {e}")

    # 8. 保存工程并自动注入混合模式
    if _MIX_MODE_AVAILABLE:
        result = save_with_mix_modes(project)
    else:
        result = project.save()
    draft_path = result.get("draft_path", "")

    return {
        "status": "success",
        "project_name": project_name,
        "draft_path": draft_path,
        "duration": duration,
        "outline_image": outline_image,
        "mix_mode": "正片叠底" if _MIX_MODE_AVAILABLE else "需手动设置",
        "effects": [glow_effect, dream_effect],
    }


def add_glow_outline_to_project(
    project,
    base_image: str,
    outline_image: str = None,
    start_time: float = 0.0,
    duration: float = 5.0,
    output_dir: str = None,
) -> Dict[str, Any]:
    """
    在已有剪映工程中添加发光轮廓效果

    Args:
        project: JyProject 实例
        base_image: 底层彩色素材图片路径
        outline_image: 上层轮廓图路径（None则自动生成）
        start_time: 起始时间（秒）
        duration: 持续时长（秒）
        output_dir: 素材输出目录

    Returns:
        效果信息字典
    """
    if output_dir is None:
        output_dir = os.path.join(project.root, project.name, "glow_outline_assets")
    os.makedirs(output_dir, exist_ok=True)

    # 生成轮廓图
    if outline_image is None:
        outline_path = os.path.join(output_dir, f"outline_{uuid.uuid4().hex[:8]}.png")
        outline_image = generate_outline_image(base_image, outline_path)
        if outline_image is None:
            return {"status": "failed", "reason": "轮廓图生成失败"}

    # 添加底层
    base_seg = project.add_media_safe(
        base_image,
        start_time=f"{start_time}s",
        duration=f"{duration}s",
        track_name="GlowBase"
    )

    # 添加上层轮廓
    outline_seg = project.add_media_safe(
        outline_image,
        start_time=f"{start_time}s",
        duration=f"{duration}s",
        track_name="GlowOutline"
    )

    # 应用混合模式
    if _MIX_MODE_AVAILABLE and outline_seg:
        apply_mix_mode(project, outline_seg, mode="multiply", intensity=1.0)

    # 添加辉光特效
    try:
        project.add_effect_simple(
            "梦幻辉光",
            start_time=f"{start_time}s",
            duration=f"{duration}s",
            track_name="GlowEffect"
        )
    except Exception:
        pass

    return {
        "status": "success",
        "base_segment": base_seg,
        "outline_segment": outline_seg,
        "outline_image": outline_image,
    }


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("动态发光轮廓效果")
    logger.info("=" * 60)
    logger.info("\n使用方法:")
    logger.info("  create_glow_outline(")
    logger.info("    project_name='测试',")
    logger.info("    base_image='photo.jpg',")
    logger.info("    outline_image='outline.png',  # 可选")
    logger.info("    duration=5.0")
    logger.info("  )")
    logger.info("\n依赖:")
    logger.info(f"  Pillow: {'✅' if _PIL_AVAILABLE else '❌'}")
    logger.info(f"  mix_mode: {'✅' if _MIX_MODE_AVAILABLE else '❌'}")
    logger.info(f"  正片叠底: {'✅ 已逆向' if MIX_MODES['multiply']['effect_id'] else '⏳ 待逆向'}")
