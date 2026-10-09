"""
动态艺术组合式字幕工具函数
用于 jianying-editor 工程，实现多轨道叠加+动画+样式的艺术字幕效果
"""

import logging
logger = logging.getLogger(__name__)

import os
import sys

# 动态查找jianying-editor skill路径
def _find_jianying_skill():
    """查找jianying-editor skill路径"""
    candidates = [
        os.path.expandvars(r"%USERPROFILE%\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills\jianying-editor"),
        os.path.expandvars(r"%USERPROFILE%\AppData\Local\DoubaoWork\User Data\Default\.doubaowork\agent_mode\workspace\.user_skills\jianying-editor"),
    ]
    for p in candidates:
        if os.path.exists(os.path.join(p, "scripts", "jy_wrapper.py")):
            return p
    return None

_jy_skill = _find_jianying_skill()
if _jy_skill:
    sys.path.insert(0, os.path.join(_jy_skill, "scripts"))
    from jy_wrapper import JyProject
    import pyJianYingDraft as draft
    JIANYING_AVAILABLE = True
else:
    JIANYING_AVAILABLE = False
    logger.info("⚠️ artistic_subtitle: 未找到jianying-editor skill，字幕功能不可用")


def add_artistic_subtitle(
    project,
    main_text,
    start_time,
    duration,
    style="epic",  # epic / warm / fun / minimal
    sub_text=None,
    narration=None,
):
    """
    添加动态艺术组合式字幕（多轨道叠加）

    Args:
        project: JyProject 实例
        main_text: 主标题文字
        start_time: 起始时间 (str 如 "0s" 或 int 微秒)
        duration: 持续时长 (str 或 int)
        style: 风格预设 - epic(国风史诗) / warm(温暖治愈) / fun(趣味卡点) / minimal(极简)
        sub_text: 副标题文字 (可选)
        narration: 旁白文字 (可选，底部字幕)
    """
    styles = {
        "epic": {
            "main": {"size": 14.0, "color": (1.0, 0.85, 0.3), "bold": True, "y": 0.5,
                     "anim_in": "放大", "anim_loop": "扫光", "border_w": 60},
            "sub": {"size": 7.0, "color": (1.0, 1.0, 1.0), "bold": False, "y": 0.2,
                    "anim_in": "向上滑动", "border_w": 40},
            "narr": {"size": 5.5, "color": (1.0, 1.0, 1.0), "y": -0.8,
                     "anim_in": "打字机_I", "border_w": 40},
        },
        "warm": {
            "main": {"size": 12.0, "color": (1.0, 0.7, 0.4), "bold": True, "y": 0.5,
                     "anim_in": "弹入", "anim_loop": "彩虹", "border_w": 50},
            "sub": {"size": 6.5, "color": (1.0, 0.95, 0.85), "bold": False, "y": 0.2,
                    "anim_in": "渐显", "border_w": 30},
            "narr": {"size": 5.0, "color": (1.0, 1.0, 1.0), "y": -0.8,
                     "anim_in": "逐字显影", "border_w": 40},
        },
        "fun": {
            "main": {"size": 13.0, "color": (0.2, 0.9, 1.0), "bold": True, "y": 0.5,
                     "anim_in": "弹性伸缩", "anim_loop": "晃动", "border_w": 50},
            "sub": {"size": 7.0, "color": (1.0, 0.9, 0.2), "bold": True, "y": 0.15,
                    "anim_in": "随机弹跳", "border_w": 40},
            "narr": {"size": 5.5, "color": (1.0, 1.0, 1.0), "y": -0.8,
                     "anim_in": "逐字旋转", "border_w": 40},
        },
        "minimal": {
            "main": {"size": 10.0, "color": (1.0, 1.0, 1.0), "bold": False, "y": 0.3,
                     "anim_in": "渐显", "border_w": 0},
            "sub": {"size": 5.5, "color": (0.8, 0.8, 0.8), "bold": False, "y": 0.05,
                    "anim_in": "渐显", "border_w": 0},
            "narr": {"size": 5.0, "color": (1.0, 1.0, 1.0), "y": -0.8,
                     "anim_in": "渐显", "border_w": 30},
        },
    }

    s = styles.get(style, styles["minimal"])

    # 主标题轨道
    main_cfg = s["main"]
    project.add_text_simple(
        main_text, start_time=start_time, duration=duration,
        font_size=main_cfg["size"],
        color_rgb=main_cfg["color"],
        style=draft.TextStyle(size=main_cfg["size"], bold=main_cfg["bold"]),
        border=draft.TextBorder(color=(0, 0, 0), width=main_cfg["border_w"]) if main_cfg["border_w"] > 0 else None,
        shadow=draft.TextShadow(color=(0, 0, 0), distance=8, diffuse=15) if main_cfg["border_w"] > 30 else None,
        clip_settings=draft.ClipSettings(transform_y=main_cfg["y"]),
        anim_in=main_cfg["anim_in"],
        anim_loop=main_cfg.get("anim_loop"),
        track_name="ArtTitle",
    )

    # 副标题轨道
    if sub_text:
        sub_cfg = s["sub"]
        project.add_text_simple(
            sub_text, start_time=start_time, duration=duration,
            font_size=sub_cfg["size"],
            color_rgb=sub_cfg["color"],
            style=draft.TextStyle(size=sub_cfg["size"], bold=sub_cfg["bold"]),
            border=draft.TextBorder(color=(0, 0, 0), width=sub_cfg["border_w"]) if sub_cfg["border_w"] > 0 else None,
            clip_settings=draft.ClipSettings(transform_y=sub_cfg["y"]),
            anim_in=sub_cfg["anim_in"],
            track_name="ArtSubtitle",
        )

    # 旁白轨道
    if narration:
        narr_cfg = s["narr"]
        project.add_text_simple(
            narration, start_time=start_time, duration=duration,
            font_size=narr_cfg["size"],
            color_rgb=narr_cfg["color"],
            style=draft.TextStyle(size=narr_cfg["size"]),
            border=draft.TextBorder(color=(0, 0, 0), width=narr_cfg["border_w"]) if narr_cfg["border_w"] > 0 else None,
            clip_settings=draft.ClipSettings(transform_y=narr_cfg["y"]),
            anim_in=narr_cfg["anim_in"],
            track_name="ArtNarration",
        )


def get_available_styles() -> list:
    """获取可用的字幕风格列表"""
    return ["epic", "warm", "fun", "minimal"]


def get_style_info(style: str) -> dict:
    """获取指定风格的详细信息"""
    styles_info = {
        "epic": {"name": "国风史诗", "desc": "金色主标题+扫光动画，适合开场/高潮", "colors": ["金色", "白色"]},
        "warm": {"name": "温暖治愈", "desc": "暖色调+弹入动画，适合情感/回忆", "colors": ["暖橙", "米白"]},
        "fun": {"name": "趣味卡点", "desc": "青蓝色+弹性动画，适合搞笑/卡点", "colors": ["青蓝", "亮黄"]},
        "minimal": {"name": "极简", "desc": "白色+渐显，适合旁白/纪录片", "colors": ["白色", "灰色"]},
    }
    return styles_info.get(style, {})


def get_available_animations() -> dict:
    """获取可用的字幕动画效果列表"""
    return {
        "入场动画": ["放大", "弹入", "渐显", "向上滑动", "打字机_I", "逐字显影", "弹性伸缩", "随机弹跳", "逐字旋转"],
        "循环动画": ["扫光", "彩虹", "晃动"],
    }


def add_ken_burns(segment, start_us, duration_us, zoom_in=True, intensity=0.12):
    """给图片片段添加Ken Burns效果"""
    end_us = start_us + duration_us
    if zoom_in:
        segment.add_keyframe(draft.KeyframeProperty.uniform_scale, start_us, 1.0, **draft.Keyframe.EASE_IN_OUT)
        segment.add_keyframe(draft.KeyframeProperty.uniform_scale, end_us, 1.0 + intensity, **draft.Keyframe.EASE_IN_OUT)
    else:
        segment.add_keyframe(draft.KeyframeProperty.uniform_scale, start_us, 1.0 + intensity, **draft.Keyframe.EASE_IN_OUT)
        segment.add_keyframe(draft.KeyframeProperty.uniform_scale, end_us, 1.0, **draft.Keyframe.EASE_IN_OUT)


if __name__ == "__main__":
    # 测试
    logger.info("动态艺术组合式字幕工具已加载")
    logger.info("可用风格: epic / warm / fun / minimal")
    logger.info("用法: add_artistic_subtitle(project, '标题', '0s', '5s', style='epic', sub_text='副标题', narration='旁白')")
