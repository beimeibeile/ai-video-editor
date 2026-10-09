"""
人物介绍卡片特效（狂飙风格）
基于教程《人物介绍卡片_狂飙风格》封装

效果原理：
1. 画面四周红色边框（可自定义颜色/宽度）
2. 底部角色名文字标识（特殊字体风格）
3. 可选爆闪预警动画（红黄绿灯闪烁）
4. 入场动画：边框从中心展开+文字淡入

制作手法：
- PIL生成边框PNG素材
- 文字轨道叠加角色名
- 关键帧控制入场动画
"""

import logging
logger = logging.getLogger(__name__)

import os
import sys
import uuid
from typing import Tuple, Optional, Dict, Any

skill_root = r"C:\Users\Administrator\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills\jianying-editor"
sys.path.insert(0, os.path.join(skill_root, "scripts"))
from jy_wrapper import JyProject
import pyJianYingDraft as draft

try:
    from PIL import Image, ImageDraw
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False


def create_border_frame(
    width: int = 1080,
    height: int = 1920,
    border_width: int = 12,
    border_color: Tuple[int, int, int] = (200, 30, 30),
    corner_radius: int = 0,
    output_path: str = None,
) -> Optional[str]:
    """
    创建边框PNG（中间透明，四周有色边框）

    Args:
        width: 画布宽
        height: 画布高
        border_width: 边框宽度
        border_color: 边框颜色RGB
        corner_radius: 圆角半径（0=直角）
        output_path: 输出路径

    Returns:
        图片路径或None
    """
    if not _PIL_AVAILABLE:
        return None

    try:
        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        if corner_radius > 0:
            # 外框
            draw.rounded_rectangle(
                [(0, 0), (width - 1, height - 1)],
                radius=corner_radius,
                fill=border_color + (255,),
            )
            # 内挖空
            inner = border_width
            draw.rounded_rectangle(
                [(inner, inner), (width - inner - 1, height - inner - 1)],
                radius=max(0, corner_radius - border_width),
                fill=(0, 0, 0, 0),
            )
        else:
            # 直角边框
            draw.rectangle([(0, 0), (width - 1, height - 1)], fill=border_color + (255,))
            draw.rectangle(
                [(border_width, border_width), (width - border_width - 1, height - border_width - 1)],
                fill=(0, 0, 0, 0),
            )

        img.save(output_path)
        return output_path
    except Exception as e:
        logger.error(f"创建边框失败: {e}")
        return None


def create_flash_warning(
    width: int = 600,
    height: int = 200,
    output_path: str = None,
) -> Optional[str]:
    """
    创建爆闪预警标识（红黄绿灯+文字）

    Args:
        width: 宽度
        height: 高度
        output_path: 输出路径

    Returns:
        图片路径或None
    """
    if not _PIL_AVAILABLE:
        return None

    try:
        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # 三个灯
        light_radius = height // 4
        colors = [(255, 50, 50), (255, 220, 50), (50, 220, 50)]
        spacing = width // 4

        for i, color in enumerate(colors):
            cx = spacing * (i + 1)
            cy = height // 2
            # 外发光
            for r in range(light_radius + 15, light_radius, -1):
                alpha = int(80 * (1 - (r - light_radius) / 15))
                draw.ellipse(
                    [(cx - r, cy - r), (cx + r, cy + r)],
                    fill=color + (alpha,),
                )
            # 灯体
            draw.ellipse(
                [(cx - light_radius, cy - light_radius), (cx + light_radius, cy + light_radius)],
                fill=color + (255,),
                outline=(255, 255, 255, 200),
                width=3,
            )

        img.save(output_path)
        return output_path
    except Exception as e:
        logger.error(f"创建爆闪标识失败: {e}")
        return None


# 样式预设
CARD_STYLES = {
    "kuangbiao": {
        "border_color": (200, 30, 30),
        "border_width": 12,
        "text_color": (1.0, 1.0, 1.0),
        "text_size": 12.0,
        "text_position_y": -0.75,
        "bg_gradient": True,
        "flash_warning": True,
    },
    "cyber": {
        "border_color": (0, 255, 255),
        "border_width": 8,
        "text_color": (0.0, 1.0, 1.0),
        "text_size": 10.0,
        "text_position_y": -0.75,
        "bg_gradient": False,
        "flash_warning": False,
    },
    "minimal": {
        "border_color": (255, 255, 255),
        "border_width": 4,
        "text_color": (1.0, 1.0, 1.0),
        "text_size": 8.0,
        "text_position_y": -0.75,
        "bg_gradient": False,
        "flash_warning": False,
    },
    "gold": {
        "border_color": (218, 165, 32),
        "border_width": 10,
        "text_color": (1.0, 0.9, 0.5),
        "text_size": 11.0,
        "text_position_y": -0.75,
        "bg_gradient": True,
        "flash_warning": False,
    },
}


def add_character_card(
    project,
    character_name: str,
    start_time: float = 0.0,
    duration: float = 4.0,
    style: str = "kuangbiao",
    border_color: Tuple[int, int, int] = None,
    text_color: Tuple[float, float, float] = None,
    output_dir: str = None,
) -> Dict[str, Any]:
    """
    给已有工程添加人物介绍卡片

    Args:
        project: JyProject 实例
        character_name: 角色名
        start_time: 起始时间（秒）
        duration: 持续时长（秒）
        style: 样式预设（kuangbiao/cyber/minimal/gold）
        border_color: 自定义边框色（覆盖预设）
        text_color: 自定义文字色（覆盖预设）
        output_dir: 素材输出目录

    Returns:
        效果信息字典
    """
    cfg = CARD_STYLES.get(style, CARD_STYLES["kuangbiao"]).copy()
    if border_color:
        cfg["border_color"] = border_color
    if text_color:
        cfg["text_color"] = text_color

    if output_dir is None:
        output_dir = os.path.join(project.root, project.name, "character_card_assets")
    os.makedirs(output_dir, exist_ok=True)

    canvas_w = getattr(project, "width", 1080)
    canvas_h = getattr(project, "height", 1920)
    start_us = int(start_time * 1e6)

    # 1. 创建边框
    border_path = os.path.join(output_dir, f"border_{style}_{uuid.uuid4().hex[:6]}.png")
    border_path = create_border_frame(
        width=canvas_w, height=canvas_h,
        border_width=cfg["border_width"],
        border_color=cfg["border_color"],
        output_path=border_path,
    )

    # 2. 添加边框轨道
    border_seg = None
    if border_path:
        border_seg = project.add_media_safe(
            border_path,
            start_time=f"{start_time:.2f}s",
            duration=f"{duration}s",
            track_name=f"CardBorder_{int(start_time*1000)}",
        )
        if border_seg:
            # 入场动画：缩放从0.8→1.0
            border_seg.add_keyframe(draft.KeyframeProperty.scale_x, start_us, 0.8, **draft.Keyframe.EASE_OUT)
            border_seg.add_keyframe(draft.KeyframeProperty.scale_x, start_us + 300000, 1.0, **draft.Keyframe.EASE_OUT)
            border_seg.add_keyframe(draft.KeyframeProperty.scale_y, start_us, 0.8, **draft.Keyframe.EASE_OUT)
            border_seg.add_keyframe(draft.KeyframeProperty.scale_y, start_us + 300000, 1.0, **draft.Keyframe.EASE_OUT)
            border_seg.add_keyframe(draft.KeyframeProperty.alpha, start_us, 0.0, **draft.Keyframe.EASE_OUT)
            border_seg.add_keyframe(draft.KeyframeProperty.alpha, start_us + 300000, 1.0, **draft.Keyframe.EASE_OUT)

    # 3. 添加角色名文字
    text_seg = project.add_text_simple(
        text=character_name,
        start_time=f"{start_time + 0.2:.2f}s",
        duration=f"{duration - 0.2}s",
        track_name=f"CardName_{int(start_time*1000)}",
        style=draft.TextStyle(size=cfg["text_size"], color=cfg["text_color"], bold=True),
        border=draft.TextBorder(color=(0, 0, 0), width=40),
    )
    if text_seg:
        text_us = int((start_time + 0.2) * 1e6)
        text_seg.add_keyframe(draft.KeyframeProperty.position_y, text_us, cfg["text_position_y"], **draft.Keyframe.EASE_OUT)
        text_seg.add_keyframe(draft.KeyframeProperty.alpha, text_us, 0.0, **draft.Keyframe.EASE_OUT)
        text_seg.add_keyframe(draft.KeyframeProperty.alpha, text_us + 300000, 1.0, **draft.Keyframe.EASE_OUT)

    # 4. 爆闪预警（可选）
    flash_seg = None
    if cfg.get("flash_warning"):
        flash_path = os.path.join(output_dir, f"flash_{uuid.uuid4().hex[:6]}.png")
        flash_path = create_flash_warning(width=500, height=150, output_path=flash_path)
        if flash_path:
            flash_seg = project.add_media_safe(
                flash_path,
                start_time=f"{start_time:.2f}s",
                duration="0.8s",
                track_name=f"CardFlash_{int(start_time*1000)}",
            )
            if flash_seg:
                flash_seg.add_keyframe(draft.KeyframeProperty.position_y, start_us, -0.7, **draft.Keyframe.EASE_OUT)
                # 闪烁效果：alpha 0→1→0→1
                flash_seg.add_keyframe(draft.KeyframeProperty.alpha, start_us, 0.0, **draft.Keyframe.EASE_OUT)
                flash_seg.add_keyframe(draft.KeyframeProperty.alpha, start_us + 100000, 1.0, **draft.Keyframe.EASE_OUT)
                flash_seg.add_keyframe(draft.KeyframeProperty.alpha, start_us + 300000, 0.0, **draft.Keyframe.EASE_OUT)
                flash_seg.add_keyframe(draft.KeyframeProperty.alpha, start_us + 500000, 1.0, **draft.Keyframe.EASE_OUT)
                flash_seg.add_keyframe(draft.KeyframeProperty.alpha, start_us + 700000, 0.0, **draft.Keyframe.EASE_OUT)

    return {
        "status": "success",
        "character_name": character_name,
        "style": style,
        "border_segment": border_seg,
        "text_segment": text_seg,
        "flash_segment": flash_seg,
    }


def create_character_card_demo(
    project_name: str = "CharacterCard_Demo",
    width: int = 1080,
    height: int = 1920,
) -> Dict[str, Any]:
    """创建人物介绍卡片演示工程（4种样式依次展示）"""

    output_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "character_card_assets"
    )
    os.makedirs(output_dir, exist_ok=True)

    logger.info(f"创建工程: {project_name}")
    project = JyProject(project_name, width=width, height=height, overwrite=True)

    # 黑色背景
    if _PIL_AVAILABLE:
        bg_path = os.path.join(output_dir, "bg_dark.png")
        from PIL import Image as PILImage
        bg = PILImage.new("RGB", (width, height), (20, 20, 25))
        bg.save(bg_path)
        project.add_media_safe(bg_path, start_time="0s", duration="16s", track_name="BG")

    characters = [
        ("安欣", "kuangbiao"),
        ("高启强", "gold"),
        ("李响", "cyber"),
        ("陈书婷", "minimal"),
    ]

    # 人物背景渐变色（模拟人物照片占位）
    bg_colors = [
        (60, 40, 50),   # 安欣-暗紫
        (50, 50, 30),   # 高启强-暗金
        (30, 50, 60),   # 李响-暗青
        (60, 30, 40),   # 陈书婷-暗红
    ]

    for i, (name, style) in enumerate(characters):
        start = i * 4.0
        # 添加人物背景占位块（渐变）
        bg_color = bg_colors[i]
        char_bg_path = os.path.join(output_dir, f"charbg_{i}.png")
        if _PIL_AVAILABLE:
            from PIL import Image as PILImage, ImageDraw as PILDraw
            cbg = PILImage.new("RGB", (width, height), bg_color)
            draw = PILDraw.Draw(cbg)
            # 简单渐变
            for y in range(height):
                t = y / height
                r = int(bg_color[0] * (1 - t * 0.5))
                g = int(bg_color[1] * (1 - t * 0.5))
                b = int(bg_color[2] * (1 - t * 0.3))
                draw.line([(0, y), (width, y)], fill=(r, g, b))
            cbg.save(char_bg_path)
            project.add_media_safe(
                char_bg_path,
                start_time=f"{start:.2f}s",
                duration="3.5s",
                track_name="CharBG",
            )
        add_character_card(
            project, name,
            start_time=start, duration=3.5,
            style=style, output_dir=output_dir,
        )
        logger.info(f"  [{i+1}] {name} ({style})")

    result = project.save()
    return {
        "project_name": project_name,
        "draft_path": result.get("draft_path", ""),
        "styles": len(characters),
    }


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("人物介绍卡片特效模块（狂飙风格）")
    logger.info("=" * 60)
    logger.info(f"\nPillow: {'可用' if _PIL_AVAILABLE else '不可用'}")
    logger.info("\n核心函数:")
    logger.info("  add_character_card(project, character_name, ...)")
    logger.info("  create_character_card_demo()")
    logger.info("\n预设样式:")
    for name in CARD_STYLES:
        s = CARD_STYLES[name]
        logger.warning(f"  {name}: 边框{s['border_color']}, 爆闪={'有' if s['flash_warning'] else '无'}")
