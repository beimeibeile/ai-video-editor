"""
片头生成器 - 风格预设
5种风格：震撼/可爱/滑稽/简约/悬念
时长自适应：短视频1-3s / 中视频3-5s / 长视频5-10s
"""

# 风格预设：每种风格定义文字样式、动画、音效、背景色调
STYLES = {
    "impact": {
        "name": "震撼型",
        "desc": "黑场闪白+大标题+whoosh，适合科技/电影/游戏",
        "bg_color": "#0a0a0a",
        "bg_accent": "#ff3366",
        "main_text": {
            "size": 18.0, "color": (1.0, 1.0, 1.0), "bold": True,
            "anim_in": "放大", "anim_loop": "扫光",
            "border_w": 80, "y": 0.0,
        },
        "sub_text": {
            "size": 6.0, "color": (0.8, 0.8, 0.8), "bold": False,
            "anim_in": "向上滑动", "border_w": 0, "y": -0.3,
        },
        "sfx": ["whoosh", "boom", "riser"],
        "timing": {"main_start": 0.3, "sub_start": 1.0, "fade_out": 0.8},
    },
    "cute": {
        "name": "可爱型",
        "desc": "弹跳入场+咻~音效+卡通字体，适合萌宠/生活/亲子",
        "bg_color": "#fff5e6",
        "bg_accent": "#ff9999",
        "main_text": {
            "size": 15.0, "color": (1.0, 0.5, 0.6), "bold": True,
            "anim_in": "弹入", "anim_loop": "轻微跳动",
            "border_w": 40, "y": 0.05,
        },
        "sub_text": {
            "size": 5.5, "color": (0.9, 0.6, 0.5), "bold": False,
            "anim_in": "渐显", "border_w": 0, "y": -0.25,
        },
        "sfx": ["boing", "pop", "sparkle"],
        "timing": {"main_start": 0.2, "sub_start": 0.8, "fade_out": 0.6},
    },
    "funny": {
        "name": "滑稽型",
        "desc": "快速缩放+怪叫声效+抖动，适合搞笑/娱乐/整活",
        "bg_color": "#ffffcc",
        "bg_accent": "#ff6600",
        "main_text": {
            "size": 16.0, "color": (1.0, 0.4, 0.0), "bold": True,
            "anim_in": "弹性伸缩", "anim_loop": "晃动",
            "border_w": 60, "y": 0.0,
        },
        "sub_text": {
            "size": 5.5, "color": (0.8, 0.4, 0.0), "bold": True,
            "anim_in": "随机弹跳", "border_w": 30, "y": -0.3,
        },
        "sfx": ["whoop", "boing", "slip"],
        "timing": {"main_start": 0.15, "sub_start": 0.6, "fade_out": 0.5},
    },
    "minimal": {
        "name": "简约型",
        "desc": "淡入淡出+细字体+静音，适合知识/商务/教程",
        "bg_color": "#ffffff",
        "bg_accent": "#333333",
        "main_text": {
            "size": 12.0, "color": (0.1, 0.1, 0.1), "bold": False,
            "anim_in": "渐显", "anim_loop": None,
            "border_w": 0, "y": 0.0,
        },
        "sub_text": {
            "size": 4.5, "color": (0.5, 0.5, 0.5), "bold": False,
            "anim_in": "渐显", "border_w": 0, "y": -0.25,
        },
        "sfx": [],  # 简约型默认无音效
        "timing": {"main_start": 0.5, "sub_start": 1.2, "fade_out": 1.0},
    },
    "suspense": {
        "name": "悬念型",
        "desc": "模糊渐显+低频音效+问号，适合故事/剧情/探秘",
        "bg_color": "#1a1a2e",
        "bg_accent": "#4a4a6a",
        "main_text": {
            "size": 14.0, "color": (0.9, 0.9, 1.0), "bold": False,
            "anim_in": "渐显", "anim_loop": "闪烁",
            "border_w": 0, "y": 0.0,
        },
        "sub_text": {
            "size": 5.0, "color": (0.6, 0.6, 0.8), "bold": False,
            "anim_in": "打字机_I", "border_w": 0, "y": -0.3,
        },
        "sfx": ["boom_low", "heartbeat", "whisper"],
        "timing": {"main_start": 0.8, "sub_start": 1.8, "fade_out": 1.2},
    },
}

# 时长预设：根据视频总时长自动调整片头时长
DURATION_PRESETS = {
    "short": {"total": 2.0, "label": "短视频(15-60s)"},      # 1-3s
    "medium": {"total": 4.0, "label": "中视频(1-3min)"},     # 3-5s
    "long": {"total": 7.0, "label": "长视频(3min+)"},        # 5-10s
}


def get_style(style_name: str) -> dict:
    """获取风格预设，不存在则返回minimal"""
    return STYLES.get(style_name, STYLES["minimal"])


def get_duration(video_type: str = "short") -> float:
    """根据视频类型获取片头时长"""
    return DURATION_PRESETS.get(video_type, DURATION_PRESETS["short"])["total"]
