"""
cap_subtitle_designer — 字幕设计模块
动态艺术组合式字幕，多轨道叠加+动画+样式

支持：
- 4种风格预设（epic国风史诗/warm温暖治愈/fun趣味卡点/minimal极简）
- 三层字幕结构（主标题/副标题/旁白）
- 入场动画+循环动画
- 自动排版（位置/大小/颜色）
"""
import os
import sys

def _ensure_jy_path():
    candidates = [
        os.getenv("JY_SKILL_ROOT", ""),
        r"C:\Users\Administrator\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills\jianying-editor",
    ]
    for p in candidates:
        if p and os.path.exists(os.path.join(p, "scripts", "jy_wrapper.py")):
            if p not in sys.path:
                sys.path.insert(0, os.path.join(p, "scripts"))
            return True
    return False

_ensure_jy_path()

try:
    # pyJianYingDraft已迁移到适配层
    import os as _os, sys as _sys
    _AVR = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
    if _AVR not in _sys.path: _sys.path.insert(0, _AVR)
    from adapters.jianying_adapter import TextSegment, TextStyle, TextBorder, TextShadow
    from adapters.jianying_adapter import Timerange, tim, TrackType
    from adapters.jianying_adapter import IntroType, TextLoopAnim
    HAS_JY = True
except ImportError:
    HAS_JY = False
    draft = None


# 字幕风格预设
SUBTITLE_STYLES = {
    "epic": {
        "name": "国风史诗",
        "main": {"size": 14.0, "color": (1.0, 0.85, 0.3), "bold": True, "y": 0.5,
                 "anim_in": "放大", "anim_loop": "扫光", "border_w": 60},
        "sub": {"size": 7.0, "color": (1.0, 1.0, 1.0), "bold": False, "y": 0.2,
                "anim_in": "向上滑动", "border_w": 40},
        "narr": {"size": 5.5, "color": (1.0, 1.0, 1.0), "y": -0.8,
                 "anim_in": "打字机_I", "border_w": 40},
    },
    "warm": {
        "name": "温暖治愈",
        "main": {"size": 12.0, "color": (1.0, 0.7, 0.4), "bold": True, "y": 0.5,
                 "anim_in": "弹入", "anim_loop": "彩虹", "border_w": 50},
        "sub": {"size": 6.5, "color": (1.0, 0.95, 0.85), "bold": False, "y": 0.2,
                "anim_in": "渐显", "border_w": 30},
        "narr": {"size": 5.0, "color": (1.0, 1.0, 1.0), "y": -0.8,
                 "anim_in": "逐字显影", "border_w": 40},
    },
    "fun": {
        "name": "趣味卡点",
        "main": {"size": 13.0, "color": (0.2, 0.9, 1.0), "bold": True, "y": 0.5,
                 "anim_in": "弹性伸缩", "anim_loop": "晃动", "border_w": 50},
        "sub": {"size": 7.0, "color": (1.0, 0.9, 0.2), "bold": True, "y": 0.15,
                "anim_in": "随机弹跳", "border_w": 40},
        "narr": {"size": 5.5, "color": (1.0, 1.0, 1.0), "y": -0.8,
                 "anim_in": "逐字旋转", "border_w": 40},
    },
    "minimal": {
        "name": "极简",
        "main": {"size": 10.0, "color": (1.0, 1.0, 1.0), "bold": False, "y": 0.3,
                 "anim_in": "渐显", "border_w": 0},
        "sub": {"size": 5.5, "color": (0.8, 0.8, 0.8), "bold": False, "y": 0.05,
                "anim_in": "渐显", "border_w": 0},
        "narr": {"size": 5.0, "color": (1.0, 1.0, 1.0), "y": -0.8,
                 "anim_in": "渐显", "border_w": 30},
    },
    "cinema": {
        "name": "电影感",
        "main": {"size": 11.0, "color": (1.0, 1.0, 1.0), "bold": True, "y": 0.4,
                 "anim_in": "渐显", "anim_loop": "扫光", "border_w": 30},
        "sub": {"size": 6.0, "color": (0.9, 0.9, 0.9), "bold": False, "y": 0.1,
                "anim_in": "渐显", "border_w": 20},
        "narr": {"size": 5.0, "color": (1.0, 1.0, 1.0), "y": -0.85,
                 "anim_in": "打字机_I", "border_w": 30},
    },
}


def add_artistic_subtitle(project, main_text: str, start_time, duration,
                           style: str = "epic", sub_text: str = None,
                           narration: str = None):
    """
    添加动态艺术组合式字幕（多轨道叠加）

    Args:
        project: JyProject 实例
        main_text: 主标题文字
        start_time: 起始时间 ("0s" 或 微秒)
        duration: 持续时长
        style: 风格 - epic/warm/fun/minimal/cinema
        sub_text: 副标题（可选）
        narration: 旁白文字（可选，底部字幕）
    """
    if not HAS_JY:
        return

    s = SUBTITLE_STYLES.get(style, SUBTITLE_STYLES["minimal"])

    # 主标题轨道
    main_cfg = s["main"]
    project.add_text_simple(
        main_text, start_time=start_time, duration=duration,
        font_size=main_cfg["size"],
        color_rgb=main_cfg["color"],
        style=TextStyle(size=main_cfg["size"], bold=main_cfg["bold"]),
        border=TextBorder(color=(0, 0, 0), width=main_cfg["border_w"]) if main_cfg["border_w"] > 0 else None,
        shadow=draft.TextShadow(color=(0, 0, 0), distance=8, diffuse=15) if main_cfg["border_w"] > 30 else None,
        clip_settings=ClipSettings(transform_y=main_cfg["y"]),
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
            style=TextStyle(size=sub_cfg["size"], bold=sub_cfg["bold"]),
            border=TextBorder(color=(0, 0, 0), width=sub_cfg["border_w"]) if sub_cfg["border_w"] > 0 else None,
            clip_settings=ClipSettings(transform_y=sub_cfg["y"]),
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
            style=TextStyle(size=narr_cfg["size"]),
            border=TextBorder(color=(0, 0, 0), width=narr_cfg["border_w"]) if narr_cfg["border_w"] > 0 else None,
            clip_settings=ClipSettings(transform_y=narr_cfg["y"]),
            anim_in=narr_cfg["anim_in"],
            track_name="ArtNarration",
        )


def add_simple_subtitle(project, text: str, start_time, duration,
                         y: float = -0.8, size: float = 5.5,
                         color: tuple = (1.0, 1.0, 1.0)):
    """
    添加简单底部字幕（旁白用）

    Args:
        project: JyProject实例
        text: 字幕文字
        start_time: 起始时间
        duration: 持续时长
        y: Y位置（-0.8为底部）
        size: 字号
        color: 颜色RGB
    """
    if not HAS_JY:
        return

    project.add_text_simple(
        text, start_time=start_time, duration=duration,
        font_size=size,
        color_rgb=color,
        style=TextStyle(size=size),
        border=TextBorder(color=(0, 0, 0), width=30),
        clip_settings=ClipSettings(transform_y=y),
        anim_in="渐显",
        track_name="Subtitle",
    )


def add_hook_title(project, text: str, start_time="0s", duration="3s",
                    style: str = "epic"):
    """
    添加开篇钩子标题（大字幕+动画）

    Args:
        project: JyProject实例
        text: 钩子文案
        start_time: 起始时间
        duration: 持续时长
        style: 风格
    """
    add_artistic_subtitle(project, text, start_time, duration, style=style)


def list_styles() -> list:
    """列出所有字幕风格"""
    return [(k, v["name"]) for k, v in SUBTITLE_STYLES.items()]
