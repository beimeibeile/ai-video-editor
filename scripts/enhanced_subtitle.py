"""
创意字幕增强模块
- 半透明字幕条（背景条+文字多轨道叠加）
- 动态发光文字（多层文字叠加模拟发光）
- 文字动画组合（入场+循环+出场）
"""

import logging
logger = logging.getLogger(__name__)

import os
import sys
import subprocess

JY_SKILL = r"C:\Users\Administrator\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills\jianying-editor"
sys.path.insert(0, os.path.join(JY_SKILL, "scripts"))

import pyJianYingDraft as draft
from pyJianYingDraft import KeyframeProperty as KP


try:
    from paths import FFMPEG
except ImportError:
    FFMPEG = r"D:\Ai\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe"


def create_subtitle_bar(width: int = 1080, height: int = 120,
                         color: str = "0x000000", opacity: float = 0.6,
                         output_path: str = None) -> str:
    """
    用ffmpeg生成半透明字幕条PNG图片

    Args:
        width: 字幕条宽度
        height: 字幕条高度
        color: 背景颜色 (hex, 如 "0x000000")
        opacity: 不透明度 (0.0-1.0)
        output_path: 输出路径

    Returns:
        字幕条PNG路径
    """
    if output_path is None:
        output_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "..", "..",
                                    r"D:\DobaoWork_Project\Ai_Video_Editor",
                                    "material", "Reuse materials", "subtitle_bar.png")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # 生成纯色半透明PNG
    alpha = int(opacity * 255)
    subprocess.run([
        FFMPEG, "-y",
        "-f", "lavfi",
        "-i", f"color=c={color}:s={width}x{height}:d=1",
        "-vf", f"format=rgba,colorchannelmixer=aa={opacity}",
        "-frames:v", "1",
        output_path
    ], capture_output=True)

    return output_path


def add_subtitle_with_bar(project, text: str, start_time: str, duration: str,
                            bar_height: int = 120, bar_opacity: float = 0.6,
                            bar_color: str = "0x000000",
                            font_size: float = 8.0,
                            text_color: tuple = (1, 1, 1),
                            y_position: float = -0.7,
                            anim_in: str = "渐显",
                            anim_loop: str = None,
                            bar_path: str = None,
                            track_prefix: str = "SubBar") -> dict:
    """
    添加带半透明背景条的字幕（多轨道叠加）

    Args:
        project: JyProject实例
        text: 字幕文字
        start_time: 起始时间
        duration: 持续时长
        bar_height: 背景条高度（像素）
        bar_opacity: 背景条不透明度
        bar_color: 背景条颜色
        font_size: 文字大小
        text_color: 文字颜色RGB
        y_position: 文字Y位置（-1到1，-0.7为底部）
        anim_in: 入场动画
        anim_loop: 循环动画
        bar_path: 预生成的背景条路径（None则自动生成）
        track_prefix: 轨道名前缀

    Returns:
        {"bar_segment": ..., "text_segment": ...}
    """
    # 生成或复用背景条
    if bar_path is None or not os.path.exists(bar_path):
        bar_path = create_subtitle_bar(
            width=1080, height=bar_height,
            color=bar_color, opacity=bar_opacity
        )

    result = {}

    # 1. 背景条轨道（画中画）
    try:
        bar_seg = project.add_media_safe(
            bar_path,
            start_time=start_time,
            duration=duration,
            track_name=f"{track_prefix}_BG",
        )
        if bar_seg:
            # 设置背景条位置和缩放
            bar_seg.clip_settings = draft.ClipSettings(
                transform_y=y_position,
                scale_x=1.0,
                scale_y=bar_height / 1920 * 2,  # 适配画布高度
            )
            result["bar_segment"] = bar_seg
    except Exception as e:
        logger.error(f"  ⚠️  背景条添加失败: {e}")

    # 2. 文字轨道
    try:
        text_seg = project.add_text_simple(
            text,
            start_time=start_time,
            duration=duration,
            font_size=font_size,
            color_rgb=text_color,
            style=draft.TextStyle(size=font_size, bold=True),
            border=draft.TextBorder(color=(0, 0, 0), width=30),
            clip_settings=draft.ClipSettings(transform_y=y_position),
            anim_in=anim_in,
            anim_loop=anim_loop,
            track_name=f"{track_prefix}_Text",
        )
        result["text_segment"] = text_seg
    except Exception as e:
        logger.error(f"  ⚠️  文字添加失败: {e}")

    return result


def add_glowing_text(project, text: str, start_time: str, duration: str,
                       font_size: float = 12.0,
                       glow_color: tuple = (1, 0.85, 0.3),
                       core_color: tuple = (1, 1, 1),
                       y_position: float = 0.3,
                       anim_in: str = "放大",
                       anim_loop: str = "扫光",
                       layers: int = 3) -> list:
    """
    添加动态发光文字（多层文字叠加模拟发光效果）

    通过多层文字叠加：外层大字号低透明度发光层 + 内层核心文字

    Args:
        project: JyProject实例
        text: 文字内容
        start_time: 起始时间
        duration: 持续时长
        font_size: 核心文字大小
        glow_color: 发光颜色
        core_color: 核心文字颜色
        y_position: Y位置
        anim_in: 入场动画
        anim_loop: 循环动画
        layers: 发光层数（默认3层）

    Returns:
        文字片段列表
    """
    segments = []

    # 外层发光层（大字号，低透明度，从外向内）
    for i in range(layers, 0, -1):
        layer_size = font_size + i * 3
        layer_alpha = 0.15 + (layers - i) * 0.1

        try:
            seg = project.add_text_simple(
                text,
                start_time=start_time,
                duration=duration,
                font_size=layer_size,
                color_rgb=glow_color,
                style=draft.TextStyle(size=layer_size, bold=True),
                clip_settings=draft.ClipSettings(
                    transform_y=y_position,
                    alpha=min(layer_alpha, 0.5),
                ),
                track_name=f"GlowLayer_{i}",
            )
            if seg:
                segments.append(seg)
        except Exception:
            pass

    # 核心文字层
    try:
        core_seg = project.add_text_simple(
            text,
            start_time=start_time,
            duration=duration,
            font_size=font_size,
            color_rgb=core_color,
            style=draft.TextStyle(size=font_size, bold=True),
            border=draft.TextBorder(color=(0, 0, 0), width=40),
            shadow=draft.TextShadow(color=glow_color, distance=10, diffuse=20),
            clip_settings=draft.ClipSettings(transform_y=y_position),
            anim_in=anim_in,
            anim_loop=anim_loop,
            track_name="GlowCore",
        )
        if core_seg:
            segments.append(core_seg)
    except Exception as e:
        logger.error(f"  ⚠️  核心文字添加失败: {e}")

    return segments


# 字幕风格预设
SUBTITLE_STYLES = {
    "news": {
        "bar_height": 100, "bar_opacity": 0.7, "bar_color": "0x1a1a2e",
        "font_size": 7.0, "text_color": (1, 1, 1),
        "y_position": -0.75, "anim_in": "向上滑动",
    },
    "cinema": {
        "bar_height": 80, "bar_opacity": 0.0, "bar_color": "0x000000",
        "font_size": 6.5, "text_color": (1, 1, 1),
        "y_position": -0.7, "anim_in": "渐显",
    },
    "vlog": {
        "bar_height": 90, "bar_opacity": 0.5, "bar_color": "0x000000",
        "font_size": 7.5, "text_color": (1, 0.9, 0.7),
        "y_position": -0.65, "anim_in": "弹入",
    },
    "kawaii": {
        "bar_height": 110, "bar_opacity": 0.4, "bar_color": "0xff88cc",
        "font_size": 8.0, "text_color": (1, 1, 1),
        "y_position": -0.6, "anim_in": "弹性伸缩", "anim_loop": "彩虹",
    },
    "tech": {
        "bar_height": 90, "bar_opacity": 0.6, "bar_color": "0x0a0a1a",
        "font_size": 7.0, "text_color": (0.3, 0.9, 1.0),
        "y_position": -0.7, "anim_in": "打字机_I",
    },
}


def add_styled_subtitle(project, text: str, start_time: str, duration: str,
                          style: str = "cinema", **kwargs) -> dict:
    """
    使用预设风格添加字幕

    Args:
        project: JyProject实例
        text: 字幕文字
        start_time: 起始时间
        duration: 持续时长
        style: 风格名称 (news/cinema/vlog/kawaii/tech)
        **kwargs: 覆盖预设参数

    Returns:
        add_subtitle_with_bar的结果
    """
    cfg = SUBTITLE_STYLES.get(style, SUBTITLE_STYLES["cinema"]).copy()
    cfg.update(kwargs)

    return add_subtitle_with_bar(
        project, text, start_time, duration,
        bar_height=cfg["bar_height"],
        bar_opacity=cfg["bar_opacity"],
        bar_color=cfg["bar_color"],
        font_size=cfg["font_size"],
        text_color=cfg["text_color"],
        y_position=cfg["y_position"],
        anim_in=cfg["anim_in"],
        anim_loop=cfg.get("anim_loop"),
    )


if __name__ == "__main__":
    logger.info("创意字幕增强模块已加载")
    logger.info("可用风格: news / cinema / vlog / kawaii / tech")
    logger.info("功能:")
    logger.info("  - add_subtitle_with_bar: 半透明字幕条")
    logger.info("  - add_glowing_text: 动态发光文字")
    logger.info("  - add_styled_subtitle: 预设风格字幕")
    logger.info("  - create_subtitle_bar: 生成字幕条PNG")
