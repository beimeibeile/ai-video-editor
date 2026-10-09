"""
圆形日期标签特效
基于抖音教程《文字排版005》封装

效果特点：
- 圆形/圆角矩形背景标签
- 日期文字居中（支持"09.30"、"2026.10.01"、"SEP 30"等格式）
- 弹入/缩放入场动画
- 可自定义颜色、大小、位置
- 支持纯文字模式（无背景）

使用方法：
    from circular_date_badge import create_date_badge, add_date_badge_to_project
    create_date_badge("测试", date_text="10.01", style="circle")
"""

import logging
logger = logging.getLogger(__name__)


import os
import sys
import math
from typing import Tuple, Optional, Dict, Any

skill_root = r"C:\Users\Administrator\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills\jianying-editor"
sys.path.insert(0, os.path.join(skill_root, "scripts"))
from jy_wrapper import JyProject
import pyJianYingDraft as draft

try:
    from PIL import Image, ImageDraw, ImageFont
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False


# 预设风格
BADGE_STYLES = {
    "circle": {
        "name": "圆形标签",
        "shape": "circle",
        "bg_color": (255, 255, 255),
        "text_color": (20, 20, 20),
        "border": True,
        "border_color": (20, 20, 20),
        "border_width": 4,
        "anim_in": "弹入",
    },
    "circle_dark": {
        "name": "深色圆形",
        "shape": "circle",
        "bg_color": (20, 20, 20),
        "text_color": (255, 255, 255),
        "border": False,
        "anim_in": "弹入",
    },
    "circle_accent": {
        "name": "强调色圆形",
        "shape": "circle",
        "bg_color": (220, 50, 50),
        "text_color": (255, 255, 255),
        "border": False,
        "anim_in": "弹入",
    },
    "rounded": {
        "name": "圆角矩形",
        "shape": "rounded",
        "bg_color": (255, 255, 255),
        "text_color": (20, 20, 20),
        "border": True,
        "border_color": (20, 20, 20),
        "border_width": 3,
        "anim_in": "弹入",
    },
    "pill": {
        "name": "胶囊标签",
        "shape": "pill",
        "bg_color": (30, 30, 30),
        "text_color": (255, 215, 0),
        "border": False,
        "anim_in": "渐显",
    },
    "minimal": {
        "name": "极简文字",
        "shape": "none",
        "text_color": (255, 255, 255),
        "anim_in": "渐显",
    },
}


def _create_circle_badge(
    date_text: str,
    output_path: str,
    size: int = 300,
    bg_color: Tuple[int, int, int] = (255, 255, 255),
    text_color: Tuple[int, int, int] = (20, 20, 20),
    border: bool = True,
    border_color: Tuple[int, int, int] = (20, 20, 20),
    border_width: int = 4,
    shape: str = "circle",
) -> Optional[str]:
    """创建圆形/圆角标签背景图片"""
    if not _PIL_AVAILABLE:
        return None

    # 创建透明背景
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    if shape == "circle":
        # 圆形
        margin = border_width if border else 0
        draw.ellipse(
            [margin, margin, size - margin, size - margin],
            fill=bg_color + (255,),
            outline=border_color + (255,) if border else None,
            width=border_width if border else 0,
        )
    elif shape == "rounded":
        # 圆角矩形
        radius = size // 4
        margin = border_width if border else 0
        draw.rounded_rectangle(
            [margin, margin, size - margin, size - margin],
            radius=radius,
            fill=bg_color + (255,),
            outline=border_color + (255,) if border else None,
            width=border_width if border else 0,
        )
    elif shape == "pill":
        # 胶囊形（宽>高）
        w, h = size * 2, size
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        margin = border_width if border else 0
        draw.rounded_rectangle(
            [margin, margin, w - margin, h - margin],
            radius=h // 2,
            fill=bg_color + (255,),
        )
        size = w  # 更新尺寸用于文字计算

    # 添加文字
    try:
        # 尝试加载系统字体
        font_size = int(size * 0.28)
        font = None
        for font_path in [
            r"C:\Windows\Fonts\msyhbd.ttc",  # 微软雅黑粗体
            r"C:\Windows\Fonts\msyh.ttc",     # 微软雅黑
            r"C:\Windows\Fonts\arialbd.ttf",  # Arial粗体
            r"C:\Windows\Fonts\arial.ttf",    # Arial
        ]:
            if os.path.exists(font_path):
                font = ImageFont.truetype(font_path, font_size)
                break
        if font is None:
            font = ImageFont.load_default()
    except Exception:
        font = ImageFont.load_default()

    # 计算文字位置（居中）
    bbox = draw.textbbox((0, 0), date_text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    text_x = (img.width - text_w) // 2 - bbox[0]
    text_y = (img.height - text_h) // 2 - bbox[1]

    draw.text((text_x, text_y), date_text, fill=text_color + (255,), font=font)

    img.save(output_path, "PNG")
    return output_path


def create_date_badge(
    project_name: str,
    date_text: str = "10.01",
    style: str = "circle",
    duration: float = 3.0,
    width: int = 1080,
    height: int = 1920,
    position: Tuple[float, float] = (-0.6, -0.7),
    scale: float = 1.0,
    output_dir: str = None,
) -> Dict[str, Any]:
    """
    创建圆形日期标签特效工程

    Args:
        project_name: 工程名
        date_text: 日期文字（如"10.01"、"2026.10.01"、"OCT 01"）
        style: 标签风格（circle/circle_dark/circle_accent/rounded/pill/minimal）
        duration: 持续时长（秒）
        width/height: 画布尺寸
        position: 标签位置 (x, y)，-1~1，(0,0)为中心
        scale: 标签缩放比例
        output_dir: 素材输出目录

    Returns:
        工程信息字典
    """
    if output_dir is None:
        output_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "date_badge_assets"
        )
    os.makedirs(output_dir, exist_ok=True)

    style_cfg = BADGE_STYLES.get(style, BADGE_STYLES["circle"])

    logger.info(f"\n{'='*60}")
    logger.info(f"圆形日期标签特效")
    logger.info(f"{'='*60}")
    logger.info(f"日期: {date_text}, 风格: {style_cfg['name']}")

    # 1. 创建标签背景
    badge_path = None
    if style_cfg["shape"] != "none":
        badge_size = int(300 * scale)
        badge_path = os.path.join(output_dir, f"badge_{date_text.replace('.', '_')}.png")
        badge_path = _create_circle_badge(
            date_text=date_text,
            output_path=badge_path,
            size=badge_size,
            bg_color=style_cfg.get("bg_color", (255, 255, 255)),
            text_color=style_cfg.get("text_color", (20, 20, 20)),
            border=style_cfg.get("border", False),
            border_color=style_cfg.get("border_color", (20, 20, 20)),
            border_width=style_cfg.get("border_width", 0),
            shape=style_cfg["shape"],
        )
        if badge_path:
            logger.info(f"  ✅ 标签背景: {badge_path}")

    # 2. 创建工程
    logger.info(f"\n[1/2] 创建工程: {project_name}")
    project = JyProject(project_name, width=width, height=height, overwrite=True)

    # 3. 添加标签
    logger.info(f"[2/2] 添加日期标签")
    if badge_path:
        # 图片标签模式
        badge_seg = project.add_media_safe(
            badge_path,
            start_time="0s",
            duration=f"{duration}s",
            track_name="DateBadge",
        )
        if badge_seg:
            # 设置位置
            badge_seg.add_keyframe(
                draft.KeyframeProperty.position_x, 0, position[0],
                **draft.Keyframe.EASE_OUT
            )
            badge_seg.add_keyframe(
                draft.KeyframeProperty.position_y, 0, position[1],
                **draft.Keyframe.EASE_OUT
            )
            # 入场动画（弹入=缩放从0→1）
            anim = style_cfg.get("anim_in", "弹入")
            if anim == "弹入":
                badge_seg.add_keyframe(
                    draft.KeyframeProperty.scale_x, 0, 0.0,
                    **draft.Keyframe.EASE_OUT
                )
                badge_seg.add_keyframe(
                    draft.KeyframeProperty.scale_x, int(0.4 * 1e6), 1.0 * scale,
                    **draft.Keyframe.EASE_OUT
                )
                badge_seg.add_keyframe(
                    draft.KeyframeProperty.scale_y, 0, 0.0,
                    **draft.Keyframe.EASE_OUT
                )
                badge_seg.add_keyframe(
                    draft.KeyframeProperty.scale_y, int(0.4 * 1e6), 1.0 * scale,
                    **draft.Keyframe.EASE_OUT
                )
            elif anim == "渐显":
                badge_seg.add_keyframe(
                    draft.KeyframeProperty.alpha, 0, 0.0,
                    **draft.Keyframe.EASE_OUT
                )
                badge_seg.add_keyframe(
                    draft.KeyframeProperty.alpha, int(0.5 * 1e6), 1.0,
                    **draft.Keyframe.EASE_OUT
                )
            logger.info(f"  ✅ 图片标签已添加 (位置{position}, 动画:{anim})")
    else:
        # 纯文字模式
        text_style = draft.TextStyle(
            size=15.0 * scale,
            color=tuple(c / 255 for c in style_cfg.get("text_color", (255, 255, 255))),
        )
        text_seg = project.add_text_simple(
            text=date_text,
            start_time="0s",
            duration=f"{duration}s",
            track_name="DateBadge",
            style=text_style,
            anim_in=style_cfg.get("anim_in", "渐显"),
        )
        if text_seg:
            text_seg.add_keyframe(
                draft.KeyframeProperty.position_x, 0, position[0],
                **draft.Keyframe.EASE_OUT
            )
            text_seg.add_keyframe(
                draft.KeyframeProperty.position_y, 0, position[1],
                **draft.Keyframe.EASE_OUT
            )
            logger.info(f"  ✅ 纯文字标签已添加")

    # 4. 保存
    result = project.save()
    draft_path = result.get("draft_path", "")

    logger.info(f"\n✅ 圆形日期标签创建完成!")
    logger.info(f"   工程: {project_name}")
    logger.info(f"   草稿: {draft_path}")

    return {
        "status": "success",
        "project_name": project_name,
        "draft_path": draft_path,
        "date_text": date_text,
        "style": style,
        "badge_path": badge_path,
    }


def add_date_badge_to_project(
    project,
    date_text: str,
    start_time: float = 0.0,
    duration: float = 3.0,
    style: str = "circle",
    position: Tuple[float, float] = (-0.6, -0.7),
    scale: float = 1.0,
    output_dir: str = None,
) -> Dict[str, Any]:
    """
    在已有工程中添加圆形日期标签

    Args:
        project: JyProject 实例
        date_text: 日期文字
        start_time: 起始时间（秒）
        duration: 持续时长（秒）
        style: 标签风格
        position: 标签位置
        scale: 缩放比例
        output_dir: 素材输出目录

    Returns:
        效果信息字典
    """
    if output_dir is None:
        output_dir = os.path.join(project.root, project.name, "date_badge_assets")
    os.makedirs(output_dir, exist_ok=True)

    style_cfg = BADGE_STYLES.get(style, BADGE_STYLES["circle"])
    badge_path = None

    if style_cfg["shape"] != "none":
        badge_size = int(300 * scale)
        badge_path = os.path.join(output_dir, f"badge_{date_text.replace('.', '_')}.png")
        badge_path = _create_circle_badge(
            date_text=date_text,
            output_path=badge_path,
            size=badge_size,
            bg_color=style_cfg.get("bg_color", (255, 255, 255)),
            text_color=style_cfg.get("text_color", (20, 20, 20)),
            border=style_cfg.get("border", False),
            border_color=style_cfg.get("border_color", (20, 20, 20)),
            border_width=style_cfg.get("border_width", 0),
            shape=style_cfg["shape"],
        )

    if badge_path:
        badge_seg = project.add_media_safe(
            badge_path,
            start_time=f"{start_time:.2f}s",
            duration=f"{duration}s",
            track_name=f"DateBadge_{int(start_time*1000)}",
        )
        if badge_seg:
            badge_seg.add_keyframe(
                draft.KeyframeProperty.position_x, int(start_time * 1e6), position[0],
                **draft.Keyframe.EASE_OUT
            )
            badge_seg.add_keyframe(
                draft.KeyframeProperty.position_y, int(start_time * 1e6), position[1],
                **draft.Keyframe.EASE_OUT
            )
            anim = style_cfg.get("anim_in", "弹入")
            if anim == "弹入":
                badge_seg.add_keyframe(
                    draft.KeyframeProperty.scale_x, int(start_time * 1e6), 0.0,
                    **draft.Keyframe.EASE_OUT
                )
                badge_seg.add_keyframe(
                    draft.KeyframeProperty.scale_x, int((start_time + 0.4) * 1e6), 1.0 * scale,
                    **draft.Keyframe.EASE_OUT
                )
                badge_seg.add_keyframe(
                    draft.KeyframeProperty.scale_y, int(start_time * 1e6), 0.0,
                    **draft.Keyframe.EASE_OUT
                )
                badge_seg.add_keyframe(
                    draft.KeyframeProperty.scale_y, int((start_time + 0.4) * 1e6), 1.0 * scale,
                    **draft.Keyframe.EASE_OUT
                )
    else:
        text_style = draft.TextStyle(
            size=15.0 * scale,
            color=tuple(c / 255 for c in style_cfg.get("text_color", (255, 255, 255))),
        )
        badge_seg = project.add_text_simple(
            text=date_text,
            start_time=f"{start_time:.2f}s",
            duration=f"{duration}s",
            track_name=f"DateBadge_{int(start_time*1000)}",
            style=text_style,
            anim_in=style_cfg.get("anim_in", "渐显"),
        )

    return {
        "status": "success",
        "segment": badge_seg,
        "date_text": date_text,
        "badge_path": badge_path,
    }


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("圆形日期标签特效模块")
    logger.info("=" * 60)
    logger.info(f"\nPillow: {'可用' if _PIL_AVAILABLE else '不可用(纯文字模式)'}")
    logger.info("\n可用风格:")
    for name, cfg in BADGE_STYLES.items():
        logger.info(f"  {name}: {cfg['name']}")
    logger.info("\n使用示例:")
    logger.info("  create_date_badge('测试', date_text='10.01', style='circle')")
    logger.info("  create_date_badge('测试', date_text='OCT 01', style='circle_dark')")
    logger.info("  create_date_badge('测试', date_text='2026.10.01', style='pill')")
