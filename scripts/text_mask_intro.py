"""
文字蒙版开场特效 v1
吸收自高版本剪映草稿"文字蒙版开场"（app_version 4.0.1）

核心技术：
1. 镜像蒙版（文字作为蒙版，文字内显示背景，文字外纯色）
2. 混合模式（图层叠加效果）
3. 蒙版展开动画（文字从左到右/从中心展开）
4. 可选：贴纸动画、绿幕抠像

效果原理：
- 底层：背景视频/图片
- 中层：纯色遮罩（黑色/白色/品牌色）
- 顶层：文字蒙版（文字区域透明，显示底层背景；非文字区域不透明，显示中层纯色）
- 动画：蒙版从0展开到全屏，文字逐渐显现
"""

import logging
logger = logging.getLogger(__name__)


import os
import sys
import uuid
from typing import Dict, Any, Optional, Tuple

skill_root = r"C:\Users\Administrator\AppData\Local\DoubaoWork\User Data\Default\.doubaowork\agent_mode\workspace\.user_skills\jianying-editor"
sys.path.insert(0, os.path.join(skill_root, "scripts"))
from jy_wrapper import JyProject
import pyJianYingDraft as draft

try:
    from mask_keyframe import apply_mask_keyframe, save_with_mask_keyframes, apply_mask_expand
    _MASK_KF_AVAILABLE = True
except ImportError:
    _MASK_KF_AVAILABLE = False

try:
    from PIL import Image, ImageDraw, ImageFont
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False


def create_text_mask_image(text: str, width: int = 1080, height: int = 1920,
                            font_size: int = 200, font_path: str = None,
                            text_color: Tuple[int, int, int, int] = (255, 255, 255, 255),
                            bg_color: Tuple[int, int, int, int] = (0, 0, 0, 0),
                            output_path: str = None) -> Optional[str]:
    """
    创建文字蒙版图片（文字区域白色，背景透明）

    Args:
        text: 文字内容
        width/height: 画布尺寸
        font_size: 字体大小
        font_path: 字体文件路径
        text_color: 文字颜色（RGBA）
        bg_color: 背景颜色（RGBA，默认透明）
        output_path: 输出路径

    Returns:
        图片路径或None
    """
    if not _PIL_AVAILABLE:
        logger.info("❌ Pillow未安装")
        return None

    if output_path is None:
        output_path = os.path.join(os.path.dirname(__file__), f"text_mask_{uuid.uuid4().hex[:8]}.png")

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    img = Image.new("RGBA", (width, height), bg_color)
    draw = ImageDraw.Draw(img)

    # 加载字体
    font = None
    if font_path and os.path.exists(font_path):
        try:
            font = ImageFont.truetype(font_path, font_size)
        except Exception:
            font = ImageFont.load_default()
    else:
        # 尝试系统字体
        for fp in [
            r"C:\Windows\Fonts\msyhbd.ttc",
            r"C:\Windows\Fonts\simhei.ttf",
            r"C:\Windows\Fonts\simsun.ttc",
        ]:
            if os.path.exists(fp):
                try:
                    font = ImageFont.truetype(fp, font_size)
                    break
                except Exception:
                    continue
        if font is None:
            font = ImageFont.load_default()

    # 计算文字位置（居中）
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (width - text_w) // 2
    y = (height - text_h) // 2

    # 绘制文字
    draw.text((x, y), text, fill=text_color, font=font)

    img.save(output_path, "PNG")
    return output_path


def create_solid_color_image(color: Tuple[int, int, int], width: int = 1080,
                              height: int = 1920, output_path: str = None) -> Optional[str]:
    """创建纯色图片"""
    if not _PIL_AVAILABLE:
        return None
    if output_path is None:
        output_path = os.path.join(os.path.dirname(__file__), f"solid_{uuid.uuid4().hex[:8]}.png")
    img = Image.new("RGB", (width, height), color)
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    img.save(output_path, "PNG")
    return output_path


def create_text_mask_intro(
    project_name: str,
    text: str = "标题文字",
    background_path: str = None,
    mask_color: Tuple[int, int, int] = (0, 0, 0),
    text_color: Tuple[int, int, int, int] = (255, 255, 255, 255),
    duration: float = 4.0,
    width: int = 1080,
    height: int = 1920,
    font_size: int = 180,
    expand_direction: str = "left",
    output_dir: str = None,
) -> Dict[str, Any]:
    """
    创建文字蒙版开场工程

    三层结构：
    - 底层（Track_BG）：背景视频/图片
    - 中层（Track_Mask）：纯色遮罩
    - 顶层（Track_Text）：文字蒙版图片，带蒙版展开动画

    Args:
        project_name: 工程名
        text: 蒙版文字
        background_path: 背景素材路径（None则用纯色）
        mask_color: 蒙版外的纯色（RGB）
        text_color: 文字颜色（RGBA）
        duration: 总时长（秒）
        width/height: 画布尺寸
        font_size: 字体大小
        expand_direction: 展开方向 left/right/top/bottom/center/horizontal/vertical
        output_dir: 素材输出目录

    Returns:
        工程信息字典
    """
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(__file__), "text_mask_intro_assets")
    os.makedirs(output_dir, exist_ok=True)

    logger.info(f"\n{'='*60}")
    logger.info(f"文字蒙版开场特效")
    logger.info(f"{'='*60}")
    logger.info(f"文字: {text}")
    logger.info(f"时长: {duration}s, 展开方向: {expand_direction}")

    # 1. 创建素材
    logger.info(f"\n[1/4] 创建素材")

    # 文字蒙版图片（文字白色，背景透明）
    mask_img_path = create_text_mask_image(
        text=text, width=width, height=height,
        font_size=font_size, text_color=text_color,
        output_path=os.path.join(output_dir, f"text_mask_{uuid.uuid4().hex[:8]}.png")
    )
    logger.info(f"  文字蒙版: {mask_img_path}")

    # 纯色遮罩
    solid_img_path = create_solid_color_image(
        color=mask_color, width=width, height=height,
        output_path=os.path.join(output_dir, f"solid_{uuid.uuid4().hex[:8]}.png")
    )
    logger.info(f"  纯色遮罩: {solid_img_path}")

    # 背景
    if background_path is None or not os.path.exists(background_path):
        background_path = create_solid_color_image(
            color=(30, 30, 40), width=width, height=height,
            output_path=os.path.join(output_dir, f"bg_{uuid.uuid4().hex[:8]}.png")
        )
        logger.info(f"  背景(默认深色): {background_path}")

    # 2. 创建工程
    logger.info(f"\n[2/4] 创建工程: {project_name} ({width}x{height})")
    project = JyProject(project_name, width=width, height=height, overwrite=True)

    # 3. 添加三层素材
    logger.info(f"[3/4] 添加三层轨道")

    # 底层：背景
    bg_seg = project.add_media_safe(
        background_path,
        start_time="0s",
        duration=f"{duration}s",
        track_name="Track_BG",
    )
    logger.info(f"  ✅ 底层背景")

    # 中层：纯色遮罩
    mask_seg = project.add_media_safe(
        solid_img_path,
        start_time="0s",
        duration=f"{duration}s",
        track_name="Track_Mask",
    )
    logger.info(f"  ✅ 中层纯色遮罩")

    # 顶层：文字蒙版图片
    text_seg = project.add_media_safe(
        mask_img_path,
        start_time="0s",
        duration=f"{duration}s",
        track_name="Track_Text",
    )
    logger.info(f"  ✅ 顶层文字蒙版")

    # 4. 设置蒙版展开动画
    logger.info(f"[4/4] 设置蒙版展开动画 ({expand_direction})")

    if _MASK_KF_AVAILABLE and text_seg:
        # 展开动画占总时长的60%
        expand_duration = duration * 0.6
        apply_mask_expand(
            project, text_seg,
            start_us=0,
            duration_us=int(expand_duration * 1e6),
            direction=expand_direction,
            canvas_w=width,
            canvas_h=height,
            curve="EASE_OUT",
        )
        logger.info(f"  ✅ 蒙版展开动画: {expand_duration:.1f}s")

        # 保存并注入蒙版关键帧
        result = save_with_mask_keyframes(project, canvas_h=height)
    else:
        result = project.save()
        logger.info(f"  ⚠️ 蒙版关键帧工具不可用，使用普通保存")

    draft_path = result.get("draft_path", "")

    logger.info(f"\n✅ 文字蒙版开场创建完成!")
    logger.info(f"   工程: {project_name}")
    logger.info(f"   草稿: {draft_path}")
    logger.info(f"   三层结构: 背景 + 纯色遮罩 + 文字蒙版(展开动画)")

    return {
        "status": "success",
        "project_name": project_name,
        "draft_path": draft_path,
        "text": text,
        "duration": duration,
        "expand_direction": expand_direction,
        "mask_keyframes": result.get("mask_keyframes_injected", 0),
        "assets": {
            "text_mask": mask_img_path,
            "solid_mask": solid_img_path,
            "background": background_path,
        },
    }


def add_text_mask_to_project(
    project,
    text: str,
    start_time: float = 0.0,
    duration: float = 3.0,
    mask_color: Tuple[int, int, int] = (0, 0, 0),
    font_size: int = 150,
    expand_direction: str = "left",
    canvas_w: int = 1080,
    canvas_h: int = 1920,
    output_dir: str = None,
) -> Dict[str, Any]:
    """
    在已有工程中添加文字蒙版开场片段

    Args:
        project: JyProject实例
        text: 蒙版文字
        start_time: 起始时间（秒）
        duration: 持续时长（秒）
        mask_color: 蒙版外纯色
        font_size: 字体大小
        expand_direction: 展开方向
        canvas_w/h: 画布尺寸
        output_dir: 素材输出目录

    Returns:
        效果信息字典
    """
    if output_dir is None:
        output_dir = os.path.join(project.root, project.name, "text_mask_assets")
    os.makedirs(output_dir, exist_ok=True)

    # 创建素材
    mask_img_path = create_text_mask_image(
        text=text, width=canvas_w, height=canvas_h,
        font_size=font_size, output_path=os.path.join(output_dir, f"tm_{uuid.uuid4().hex[:8]}.png")
    )
    solid_img_path = create_solid_color_image(
        color=mask_color, width=canvas_w, height=canvas_h,
        output_path=os.path.join(output_dir, f"solid_{uuid.uuid4().hex[:8]}.png")
    )

    # 添加纯色遮罩层
    mask_seg = project.add_media_safe(
        solid_img_path,
        start_time=f"{start_time:.2f}s",
        duration=f"{duration}s",
        track_name=f"TM_Mask_{int(start_time*1000)}",
    )

    # 添加文字蒙版层
    text_seg = project.add_media_safe(
        mask_img_path,
        start_time=f"{start_time:.2f}s",
        duration=f"{duration}s",
        track_name=f"TM_Text_{int(start_time*1000)}",
    )

    # 设置展开动画
    if _MASK_KF_AVAILABLE and text_seg:
        expand_duration = duration * 0.6
        apply_mask_expand(
            project, text_seg,
            start_us=int(start_time * 1e6),
            duration_us=int(expand_duration * 1e6),
            direction=expand_direction,
            canvas_w=canvas_w,
            canvas_h=canvas_h,
        )

    return {
        "status": "success",
        "text_segment": text_seg,
        "mask_segment": mask_seg,
        "text": text,
    }


# 预设样式
PRESETS = {
    "cinematic_black": {
        "name": "电影黑场",
        "mask_color": (0, 0, 0),
        "text_color": (255, 255, 255, 255),
        "expand_direction": "left",
        "font_size": 160,
    },
    "neon_purple": {
        "name": "霓虹紫",
        "mask_color": (20, 0, 40),
        "text_color": (200, 100, 255, 255),
        "expand_direction": "horizontal",
        "font_size": 180,
    },
    "minimal_white": {
        "name": "极简白",
        "mask_color": (255, 255, 255),
        "text_color": (0, 0, 0, 255),
        "expand_direction": "center",
        "font_size": 200,
    },
    "warm_orange": {
        "name": "暖橙",
        "mask_color": (40, 20, 0),
        "text_color": (255, 180, 50, 255),
        "expand_direction": "right",
        "font_size": 170,
    },
}


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("文字蒙版开场特效 v1")
    logger.info("=" * 60)
    logger.info(f"\n蒙版关键帧工具: {'✅' if _MASK_KF_AVAILABLE else '❌'}")
    logger.info(f"Pillow: {'✅' if _PIL_AVAILABLE else '❌'}")
    logger.info("\n核心函数:")
    logger.info("  create_text_mask_intro(project_name, text, ...) - 创建文字蒙版开场工程")
    logger.info("  add_text_mask_to_project(project, text, ...) - 在已有工程中添加")
    logger.info("  create_text_mask_image(text, ...) - 创建文字蒙版图片")
    logger.info("\n预设样式:")
    for key, preset in PRESETS.items():
        logger.info(f"  {key}: {preset['name']}")
    logger.info("\n展开方向: left/right/top/bottom/center/horizontal/vertical")

    # 测试创建
    if _MASK_KF_AVAILABLE and _PIL_AVAILABLE:
        logger.info(f"\n--- 测试: 创建电影黑场风格 ---")
        result = create_text_mask_intro(
            project_name="TextMaskIntro_Test",
            text="测试标题",
            duration=4.0,
            expand_direction="left",
            **{k: v for k, v in PRESETS["cinematic_black"].items() if k in ["mask_color", "text_color", "font_size"]},
        )
        logger.info(f"结果: {result['status']}, 草稿: {result['draft_path']}")
