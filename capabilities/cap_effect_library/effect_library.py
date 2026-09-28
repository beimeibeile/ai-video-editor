"""
cap_effect_library — 特效库模块
转场/滤镜预设，自动匹配风格

支持：
- 转场预设（叠化/闪黑/模糊/滑动等）
- 滤镜预设（清新/复古/电影/赛博等）
- 风格自动匹配（根据视频主题推荐转场+滤镜）
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
    import pyJianYingDraft as draft
    from pyJianYingDraft import TransitionType
    HAS_JY = True
except ImportError:
    HAS_JY = False
    draft = None
    TransitionType = None


# 转场预设
TRANSITIONS = {
    "dissolve": {"name": "叠化", "duration": "0.4s", "style": "柔和"},
    "fade_black": {"name": "闪黑", "duration": "0.3s", "style": "电影感"},
    "fade_white": {"name": "闪白", "duration": "0.2s", "style": "炫酷"},
    "blur": {"name": "模糊", "duration": "0.4s", "style": "柔和"},
    "slide_left": {"name": "左滑动", "duration": "0.3s", "style": "动感"},
    "slide_right": {"name": "右滑动", "duration": "0.3s", "style": "动感"},
    "zoom": {"name": "缩放", "duration": "0.3s", "style": "炫酷"},
    "rotate": {"name": "旋转", "duration": "0.4s", "style": "创意"},
    "glitch": {"name": "故障", "duration": "0.2s", "style": "赛博"},
    "none": {"name": "无转场", "duration": "0s", "style": "硬切"},
}

# 滤镜预设（剪映滤镜名称，需要在剪映中手动应用或通过API）
FILTERS = {
    "fresh": {"name": "清新", "adjust": {"brightness": 0.05, "contrast": 0.05, "saturation": 0.1}},
    "warm": {"name": "暖色", "adjust": {"brightness": 0.05, "contrast": 0.0, "saturation": 0.05, "warmth": 0.1}},
    "cool": {"name": "冷色", "adjust": {"brightness": 0.0, "contrast": 0.05, "saturation": 0.0, "warmth": -0.1}},
    "vintage": {"name": "复古", "adjust": {"brightness": -0.05, "contrast": 0.1, "saturation": -0.15}},
    "cinema": {"name": "电影感", "adjust": {"brightness": -0.05, "contrast": 0.15, "saturation": -0.05}},
    "cyber": {"name": "赛博", "adjust": {"brightness": -0.1, "contrast": 0.2, "saturation": 0.15}},
    "bw": {"name": "黑白", "adjust": {"saturation": -1.0, "contrast": 0.1}},
    "vivid": {"name": "鲜艳", "adjust": {"saturation": 0.2, "contrast": 0.1}},
}

# 主题风格匹配（主题 -> 推荐转场+滤镜+字幕风格）
STYLE_PRESETS = {
    "国风": {
        "transition": "dissolve",
        "filter": "warm",
        "subtitle": "epic",
        "bgm": "国风",
        "desc": "国风史诗感",
    },
    "治愈": {
        "transition": "dissolve",
        "filter": "warm",
        "subtitle": "warm",
        "bgm": "治愈",
        "desc": "温暖治愈",
    },
    "卡点": {
        "transition": "zoom",
        "filter": "vivid",
        "subtitle": "fun",
        "bgm": "电子",
        "desc": "炫酷卡点",
    },
    "电影": {
        "transition": "fade_black",
        "filter": "cinema",
        "subtitle": "cinema",
        "bgm": "电影",
        "desc": "电影叙事感",
    },
    "赛博": {
        "transition": "glitch",
        "filter": "cyber",
        "subtitle": "fun",
        "bgm": "电子",
        "desc": "赛博朋克",
    },
    "极简": {
        "transition": "dissolve",
        "filter": "fresh",
        "subtitle": "minimal",
        "bgm": "轻音乐",
        "desc": "极简文艺",
    },
    "复古": {
        "transition": "fade_white",
        "filter": "vintage",
        "subtitle": "warm",
        "bgm": "复古",
        "desc": "复古怀旧",
    },
}


def add_transition(project, segment, transition_type: str = "dissolve", duration: str = None):
    """
    给片段添加转场

    Args:
        project: JyProject实例
        segment: 目标片段（转场应用在此片段的入点）
        transition_type: 转场类型
        duration: 持续时长（None则用默认）
    """
    if not HAS_JY:
        return

    t = TRANSITIONS.get(transition_type, TRANSITIONS["dissolve"])
    dur = duration or t["duration"]

    if transition_type == "none":
        return

    try:
        project.add_transition_simple(t["name"], video_segment=segment, duration=dur)
    except Exception as e:
        # 转场添加失败时静默跳过（不影响主流程）
        pass


def auto_add_transitions(project, segments: list, transition_type: str = "dissolve"):
    """
    为多个片段自动添加转场（除第一个外）

    Args:
        project: JyProject实例
        segments: 片段列表
        transition_type: 转场类型
    """
    for i, seg in enumerate(segments):
        if i > 0:  # 第一个片段不加转场
            add_transition(project, seg, transition_type)


def get_style_preset(theme: str) -> dict:
    """
    根据主题获取风格预设

    Args:
        theme: 主题关键词（国风/治愈/卡点/电影等）

    Returns:
        风格预设字典（transition/filter/subtitle/bgm）
    """
    # 模糊匹配
    theme_lower = theme.lower()
    for key, preset in STYLE_PRESETS.items():
        if key in theme or theme in key:
            return preset

    # 默认用清新风格
    return STYLE_PRESETS["极简"]


def list_transitions() -> list:
    """列出所有转场类型"""
    return [(k, v["name"], v["style"]) for k, v in TRANSITIONS.items()]


def list_filters() -> list:
    """列出所有滤镜类型"""
    return [(k, v["name"]) for k, v in FILTERS.items()]


def list_style_presets() -> list:
    """列出所有风格预设"""
    return [(k, v["desc"]) for k, v in STYLE_PRESETS.items()]
