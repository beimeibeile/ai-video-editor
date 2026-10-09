# -*- coding: utf-8 -*-
"""
情绪-镜头视觉映射表 v2.0
覆盖34种情绪类型，每种情绪包含：
- 镜头时长范围（秒）
- 运镜方式
- 运镜强度（0-1）
- 转场方式
- 视觉特效
- 字幕风格
- 音效提示

使用方式：
    from emotion_visual_map import EMOTION_VISUAL_MAP_V2
    visual = EMOTION_VISUAL_MAP_V2.get("快乐", EMOTION_VISUAL_MAP_V2["舒缓"])
"""

import logging
logger = logging.getLogger(__name__)


EMOTION_VISUAL_MAP_V2 = {
    # ===== 基础情绪（6种，保留原有） =====
    "激昂": {
        "shot_duration_range": (0.6, 1.5),
        "camera_moves": ["快推", "快移", "手持", "跟拍"],
        "camera_intensity": (0.08, 0.15),
        "transitions": ["快切", "闪白", "震动"],
        "effects": ["高对比", "锐化", "色彩增强"],
        "subtitle_style": "bold_impact",
        "sfx_hints": ["重击", "上升音效", "节奏鼓点"],
        "color_grade": "high_contrast_warm",
        "pacing": "fast",
    },
    "舒缓": {
        "shot_duration_range": (2.0, 4.0),
        "camera_moves": ["慢推", "慢拉", "固定", "横移"],
        "camera_intensity": (0.02, 0.05),
        "transitions": ["叠化", "淡入淡出"],
        "effects": ["柔焦", "低饱和", "暖色调"],
        "subtitle_style": "elegant_serif",
        "sfx_hints": ["环境音", "轻柔钢琴", "自然声"],
        "color_grade": "soft_warm",
        "pacing": "slow",
    },
    "紧张": {
        "shot_duration_range": (0.5, 1.2),
        "camera_moves": ["手持", "快切", "急推", "甩镜"],
        "camera_intensity": (0.10, 0.20),
        "transitions": ["快切", "闪黑", "跳切"],
        "effects": ["高对比", "冷色调", "暗角"],
        "subtitle_style": "sharp_condensed",
        "sfx_hints": ["心跳", "紧张弦乐", "低频嗡鸣"],
        "color_grade": "cold_contrast",
        "pacing": "fast",
    },
    "温馨": {
        "shot_duration_range": (1.5, 3.0),
        "camera_moves": ["慢推", "环绕", "固定"],
        "camera_intensity": (0.03, 0.06),
        "transitions": ["叠化", "柔光转场"],
        "effects": ["暖色调", "柔焦", "光晕"],
        "subtitle_style": "warm_round",
        "sfx_hints": ["温暖钢琴", "吉他", "轻笑"],
        "color_grade": "warm_glow",
        "pacing": "medium",
    },
    "高潮": {
        "shot_duration_range": (0.4, 1.0),
        "camera_moves": ["快推", "手持", "甩镜", "急拉"],
        "camera_intensity": (0.12, 0.25),
        "transitions": ["闪白", "震动", "快切"],
        "effects": ["过曝", "高饱和", "动态模糊"],
        "subtitle_style": "massive_bold",
        "sfx_hints": ["爆发", "重击", "全屏音效"],
        "color_grade": "overexposed_vibrant",
        "pacing": "very_fast",
    },
    "收束": {
        "shot_duration_range": (2.0, 4.0),
        "camera_moves": ["慢拉", "固定", "上升"],
        "camera_intensity": (0.02, 0.05),
        "transitions": ["叠化", "淡出"],
        "effects": ["渐暗", "低饱和", "柔焦"],
        "subtitle_style": "minimal_fade",
        "sfx_hints": ["尾音", "回声", "静默"],
        "color_grade": "dimmed_muted",
        "pacing": "slow",
    },

    # ===== 扩展情绪（28种） =====

    # 快乐/喜悦
    "快乐": {
        "shot_duration_range": (1.0, 2.0),
        "camera_moves": ["跟拍", "横移", "快推", "环绕"],
        "camera_intensity": (0.05, 0.10),
        "transitions": ["快切", "叠化", "闪白"],
        "effects": ["高饱和", "暖色调", "光晕"],
        "subtitle_style": "bright_round",
        "sfx_hints": ["轻快钢琴", "笑声", "铃鼓"],
        "color_grade": "bright_warm",
        "pacing": "medium_fast",
    },
    "喜悦": {
        "shot_duration_range": (0.8, 1.8),
        "camera_moves": ["快推", "跟拍", "上升", "环绕"],
        "camera_intensity": (0.06, 0.12),
        "transitions": ["闪白", "快切", "缩放转场"],
        "effects": ["过曝", "高饱和", "光晕", "粒子"],
        "subtitle_style": "glowing_bold",
        "sfx_hints": ["欢呼", "上升音效", "铃铛"],
        "color_grade": "glowing_warm",
        "pacing": "fast",
    },

    # 悲伤
    "悲伤": {
        "shot_duration_range": (2.5, 5.0),
        "camera_moves": ["慢推", "固定", "慢拉", "下降"],
        "camera_intensity": (0.01, 0.03),
        "transitions": ["叠化", "淡入淡出", "黑场"],
        "effects": ["低饱和", "冷色调", "柔焦", "暗角"],
        "subtitle_style": "thin_serif",
        "sfx_hints": ["悲伤钢琴", "雨声", "大提琴"],
        "color_grade": "cold_desaturated",
        "pacing": "very_slow",
    },
    "忧伤": {
        "shot_duration_range": (2.0, 4.0),
        "camera_moves": ["慢移", "固定", "慢推"],
        "camera_intensity": (0.02, 0.04),
        "transitions": ["叠化", "淡入淡出"],
        "effects": ["低饱和", "冷色调", "柔焦"],
        "subtitle_style": "elegant_fade",
        "sfx_hints": ["轻柔钢琴", "风声", "弦乐"],
        "color_grade": "muted_cool",
        "pacing": "slow",
    },

    # 愤怒
    "愤怒": {
        "shot_duration_range": (0.4, 1.0),
        "camera_moves": ["手持", "急推", "甩镜", "快切"],
        "camera_intensity": (0.12, 0.25),
        "transitions": ["快切", "闪黑", "震动", "跳切"],
        "effects": ["高对比", "暖红色调", "锐化", "暗角"],
        "subtitle_style": "sharp_impact",
        "sfx_hints": ["重击", "怒吼", "低频鼓点"],
        "color_grade": "red_contrast",
        "pacing": "very_fast",
    },

    # 恐惧
    "恐惧": {
        "shot_duration_range": (0.6, 1.5),
        "camera_moves": ["手持", "慢推", "急拉", "甩镜"],
        "camera_intensity": (0.08, 0.18),
        "transitions": ["快切", "闪黑", "跳切"],
        "effects": ["冷色调", "暗角", "高对比", "模糊"],
        "subtitle_style": "trembling_thin",
        "sfx_hints": ["心跳", "尖叫", "低频嗡鸣", "风声"],
        "color_grade": "dark_cold",
        "pacing": "fast",
    },
    "恐怖": {
        "shot_duration_range": (1.0, 3.0),
        "camera_moves": ["慢推", "固定", "手持", "慢移"],
        "camera_intensity": (0.03, 0.08),
        "transitions": ["叠化", "闪黑", "黑场"],
        "effects": ["暗角", "冷色调", "低饱和", "噪点"],
        "subtitle_style": "horror_blood",
        "sfx_hints": ["诡异音效", "心跳", "金属声", "低语"],
        "color_grade": "dark_desaturated",
        "pacing": "slow_tense",
    },

    # 惊讶
    "惊讶": {
        "shot_duration_range": (0.5, 1.2),
        "camera_moves": ["急推", "快拉", "固定", "甩镜"],
        "camera_intensity": (0.10, 0.20),
        "transitions": ["闪白", "快切", "缩放转场"],
        "effects": ["过曝", "高对比", "动态模糊"],
        "subtitle_style": "sudden_bold",
        "sfx_hints": ["惊叹", "上升音效", "重击"],
        "color_grade": "high_contrast_flash",
        "pacing": "fast",
    },

    # 期待
    "期待": {
        "shot_duration_range": (1.5, 3.0),
        "camera_moves": ["慢推", "跟拍", "上升"],
        "camera_intensity": (0.04, 0.08),
        "transitions": ["叠化", "淡入"],
        "effects": ["暖色调", "柔焦", "光晕"],
        "subtitle_style": "hopeful_serif",
        "sfx_hints": ["上升弦乐", "钢琴", "心跳"],
        "color_grade": "warm_hopeful",
        "pacing": "medium",
    },

    # 浪漫
    "浪漫": {
        "shot_duration_range": (2.0, 4.0),
        "camera_moves": ["慢推", "环绕", "横移", "上升"],
        "camera_intensity": (0.03, 0.06),
        "transitions": ["叠化", "柔光转场", "淡入淡出"],
        "effects": ["柔焦", "暖色调", "光晕", "散景"],
        "subtitle_style": "elegant_script",
        "sfx_hints": ["浪漫钢琴", "弦乐", "轻柔吉他"],
        "color_grade": "soft_pink_warm",
        "pacing": "slow",
    },

    # 神秘
    "神秘": {
        "shot_duration_range": (1.5, 3.5),
        "camera_moves": ["慢推", "慢移", "固定", "环绕"],
        "camera_intensity": (0.03, 0.07),
        "transitions": ["叠化", "淡入淡出", "黑场"],
        "effects": ["暗角", "冷色调", "低饱和", "雾效"],
        "subtitle_style": "mysterious_serif",
        "sfx_hints": ["氛围音", "钟声", "低频嗡鸣", "风声"],
        "color_grade": "dark_mysterious",
        "pacing": "slow",
    },

    # 搞笑
    "搞笑": {
        "shot_duration_range": (0.6, 1.5),
        "camera_moves": ["快切", "跟拍", "快推", "固定"],
        "camera_intensity": (0.05, 0.12),
        "transitions": ["快切", "闪白", "缩放转场", "跳切"],
        "effects": ["高饱和", "暖色调", "动态模糊"],
        "subtitle_style": "comic_bold",
        "sfx_hints": ["搞笑音效", "笑声", "弹簧声", "鼓点"],
        "color_grade": "bright_vibrant",
        "pacing": "fast",
    },

    # 励志
    "励志": {
        "shot_duration_range": (1.0, 2.5),
        "camera_moves": ["上升", "慢推", "跟拍", "环绕"],
        "camera_intensity": (0.04, 0.10),
        "transitions": ["叠化", "闪白", "淡入"],
        "effects": ["暖色调", "高对比", "光晕", "镜头光晕"],
        "subtitle_style": "bold_inspiring",
        "sfx_hints": ["史诗弦乐", "鼓点", "钢琴", "合唱"],
        "color_grade": "epic_warm",
        "pacing": "medium",
    },

    # 怀旧
    "怀旧": {
        "shot_duration_range": (2.0, 4.0),
        "camera_moves": ["慢推", "慢拉", "固定", "横移"],
        "camera_intensity": (0.02, 0.05),
        "transitions": ["叠化", "淡入淡出", "模糊转场"],
        "effects": ["柔焦", "暖黄色调", "低饱和", "颗粒感"],
        "subtitle_style": "vintage_serif",
        "sfx_hints": ["老唱片", "钢琴", "雨声", "风声"],
        "color_grade": "vintage_warm",
        "pacing": "slow",
    },

    # 孤独
    "孤独": {
        "shot_duration_range": (2.5, 5.0),
        "camera_moves": ["固定", "慢拉", "慢移", "下降"],
        "camera_intensity": (0.01, 0.03),
        "transitions": ["叠化", "淡入淡出", "黑场"],
        "effects": ["冷色调", "低饱和", "暗角", "柔焦"],
        "subtitle_style": "lonely_thin",
        "sfx_hints": ["风声", "雨声", "孤独钢琴", "回声"],
        "color_grade": "cold_isolated",
        "pacing": "very_slow",
    },

    # 希望
    "希望": {
        "shot_duration_range": (1.5, 3.0),
        "camera_moves": ["上升", "慢推", "跟拍", "环绕"],
        "camera_intensity": (0.03, 0.07),
        "transitions": ["叠化", "淡入", "闪白"],
        "effects": ["暖色调", "光晕", "高饱和", "镜头光晕"],
        "subtitle_style": "hopeful_bright",
        "sfx_hints": ["上升弦乐", "钢琴", "合唱", "钟声"],
        "color_grade": "bright_hopeful",
        "pacing": "medium",
    },

    # 绝望
    "绝望": {
        "shot_duration_range": (2.5, 5.0),
        "camera_moves": ["下降", "固定", "慢拉", "手持"],
        "camera_intensity": (0.01, 0.04),
        "transitions": ["叠化", "黑场", "淡入淡出"],
        "effects": ["冷色调", "低饱和", "暗角", "高对比"],
        "subtitle_style": "despair_thin",
        "sfx_hints": ["低沉弦乐", "雨声", "低频嗡鸣", "静默"],
        "color_grade": "dark_desolate",
        "pacing": "very_slow",
    },

    # 平静
    "平静": {
        "shot_duration_range": (2.5, 5.0),
        "camera_moves": ["固定", "慢移", "慢推", "横移"],
        "camera_intensity": (0.01, 0.03),
        "transitions": ["叠化", "淡入淡出"],
        "effects": ["柔焦", "低饱和", "自然色调"],
        "subtitle_style": "calm_minimal",
        "sfx_hints": ["自然声", "轻柔钢琴", "环境音"],
        "color_grade": "natural_soft",
        "pacing": "very_slow",
    },
    "放松": {
        "shot_duration_range": (2.0, 4.0),
        "camera_moves": ["慢移", "固定", "慢推", "横移"],
        "camera_intensity": (0.02, 0.04),
        "transitions": ["叠化", "淡入淡出"],
        "effects": ["柔焦", "暖色调", "低饱和"],
        "subtitle_style": "relaxed_round",
        "sfx_hints": ["环境音", "轻柔音乐", "自然声"],
        "color_grade": "soft_relaxed",
        "pacing": "slow",
    },

    # 兴奋
    "兴奋": {
        "shot_duration_range": (0.5, 1.2),
        "camera_moves": ["快推", "跟拍", "手持", "快移"],
        "camera_intensity": (0.08, 0.15),
        "transitions": ["快切", "闪白", "震动"],
        "effects": ["高饱和", "暖色调", "动态模糊", "光晕"],
        "subtitle_style": "excited_bold",
        "sfx_hints": ["欢呼", "快节奏鼓点", "上升音效"],
        "color_grade": "vibrant_energetic",
        "pacing": "very_fast",
    },

    # 焦虑
    "焦虑": {
        "shot_duration_range": (0.8, 1.8),
        "camera_moves": ["手持", "快切", "慢推", "甩镜"],
        "camera_intensity": (0.06, 0.14),
        "transitions": ["快切", "跳切", "闪黑"],
        "effects": ["高对比", "冷色调", "暗角", "噪点"],
        "subtitle_style": "anxious_shaky",
        "sfx_hints": ["心跳", "紧张弦乐", "呼吸声", "低频嗡鸣"],
        "color_grade": "tense_cold",
        "pacing": "medium_fast",
    },

    # 困惑
    "困惑": {
        "shot_duration_range": (1.5, 3.0),
        "camera_moves": ["慢推", "固定", "慢移", "手持"],
        "camera_intensity": (0.03, 0.06),
        "transitions": ["叠化", "淡入淡出", "模糊转场"],
        "effects": ["柔焦", "低饱和", "冷色调", "模糊"],
        "subtitle_style": "confused_serif",
        "sfx_hints": ["疑问音效", "钢琴", "氛围音"],
        "color_grade": "muted_confused",
        "pacing": "medium",
    },

    # 骄傲
    "骄傲": {
        "shot_duration_range": (1.0, 2.5),
        "camera_moves": ["上升", "慢推", "环绕", "跟拍"],
        "camera_intensity": (0.04, 0.09),
        "transitions": ["叠化", "闪白", "淡入"],
        "effects": ["暖色调", "高对比", "光晕", "镜头光晕"],
        "subtitle_style": "proud_elegant",
        "sfx_hints": ["史诗音乐", "鼓点", "号角"],
        "color_grade": "proud_warm",
        "pacing": "medium",
    },

    # 感激
    "感激": {
        "shot_duration_range": (1.5, 3.0),
        "camera_moves": ["慢推", "环绕", "固定", "上升"],
        "camera_intensity": (0.03, 0.06),
        "transitions": ["叠化", "淡入淡出", "柔光转场"],
        "effects": ["暖色调", "柔焦", "光晕"],
        "subtitle_style": "grateful_warm",
        "sfx_hints": ["温暖钢琴", "弦乐", "合唱"],
        "color_grade": "warm_grateful",
        "pacing": "medium",
    },

    # 同情
    "同情": {
        "shot_duration_range": (2.0, 4.0),
        "camera_moves": ["慢推", "固定", "慢移"],
        "camera_intensity": (0.02, 0.05),
        "transitions": ["叠化", "淡入淡出"],
        "effects": ["柔焦", "暖色调", "低饱和"],
        "subtitle_style": "sympathetic_soft",
        "sfx_hints": ["温柔钢琴", "弦乐", "环境音"],
        "color_grade": "soft_sympathetic",
        "pacing": "slow",
    },

    # 无聊
    "无聊": {
        "shot_duration_range": (2.5, 5.0),
        "camera_moves": ["固定", "慢移", "慢拉"],
        "camera_intensity": (0.01, 0.02),
        "transitions": ["叠化", "淡入淡出"],
        "effects": ["低饱和", "冷色调", "柔焦"],
        "subtitle_style": "boring_plain",
        "sfx_hints": ["时钟滴答", "环境音", "静默"],
        "color_grade": "muted_boring",
        "pacing": "very_slow",
    },

    # 信任
    "信任": {
        "shot_duration_range": (1.5, 3.0),
        "camera_moves": ["慢推", "固定", "环绕"],
        "camera_intensity": (0.03, 0.06),
        "transitions": ["叠化", "淡入淡出"],
        "effects": ["暖色调", "柔焦", "自然色调"],
        "subtitle_style": "trust_serif",
        "sfx_hints": ["温暖钢琴", "吉他", "轻柔弦乐"],
        "color_grade": "warm_trusting",
        "pacing": "medium",
    },

    # 厌恶
    "厌恶": {
        "shot_duration_range": (0.8, 1.8),
        "camera_moves": ["快拉", "固定", "快切", "甩镜"],
        "camera_intensity": (0.05, 0.12),
        "transitions": ["快切", "闪黑", "跳切"],
        "effects": ["高对比", "冷绿色调", "暗角", "锐化"],
        "subtitle_style": "disgust_sharp",
        "sfx_hints": ["干呕声", "刺耳音效", "低频"],
        "color_grade": "greenish_contrast",
        "pacing": "medium_fast",
    },

    # 羞愧
    "羞愧": {
        "shot_duration_range": (1.5, 3.0),
        "camera_moves": ["下降", "固定", "慢拉", "慢移"],
        "camera_intensity": (0.02, 0.05),
        "transitions": ["叠化", "淡入淡出", "黑场"],
        "effects": ["暖红色调", "柔焦", "暗角", "低饱和"],
        "subtitle_style": "ashamed_small",
        "sfx_hints": ["轻柔钢琴", "心跳", "静默"],
        "color_grade": "warm_ashamed",
        "pacing": "slow",
    },

    # 嫉妒
    "嫉妒": {
        "shot_duration_range": (1.0, 2.5),
        "camera_moves": ["慢推", "固定", "手持", "慢移"],
        "camera_intensity": (0.04, 0.08),
        "transitions": ["叠化", "快切", "淡入淡出"],
        "effects": ["冷绿色调", "高对比", "暗角", "低饱和"],
        "subtitle_style": "jealous_sharp",
        "sfx_hints": ["紧张弦乐", "低频嗡鸣", "钢琴"],
        "color_grade": "green_tense",
        "pacing": "medium",
    },
}


def get_emotion_list() -> list:
    """获取所有支持的情绪列表"""
    return list(EMOTION_VISUAL_MAP_V2.keys())


def get_emotion_visual(emotion: str, intensity: float = 0.5) -> dict:
    """
    获取指定情绪的视觉参数（带强度调整）

    Args:
        emotion: 情绪类型
        intensity: 情绪强度 0-1

    Returns:
        视觉参数字典
    """
    template = EMOTION_VISUAL_MAP_V2.get(emotion, EMOTION_VISUAL_MAP_V2["舒缓"])
    intensity_factor = 0.5 + intensity * 0.5  # 0.5-1.0

    shot_min, shot_max = template["shot_duration_range"]
    cam_min, cam_max = template["camera_intensity"]

    return {
        "emotion": emotion,
        "intensity": intensity,
        "shot_duration": {
            "min": round(shot_min / intensity_factor, 2),
            "max": round(shot_max / intensity_factor, 2),
            "recommended": round((shot_min + shot_max) / 2 / intensity_factor, 2),
        },
        "camera_moves": template["camera_moves"],
        "camera_intensity": {
            "min": round(cam_min * intensity_factor, 3),
            "max": round(cam_max * intensity_factor, 3),
            "recommended": round((cam_min + cam_max) / 2 * intensity_factor, 3),
        },
        "transitions": template["transitions"],
        "effects": template["effects"],
        "subtitle_style": template["subtitle_style"],
        "sfx_hints": template["sfx_hints"],
        "color_grade": template.get("color_grade", "default"),
        "pacing": template.get("pacing", "medium"),
    }


def get_emotion_categories() -> dict:
    """获取情绪分类"""
    return {
        "积极": ["快乐", "喜悦", "温馨", "浪漫", "希望", "兴奋", "骄傲", "感激", "信任", "励志"],
        "消极": ["悲伤", "忧伤", "愤怒", "恐惧", "恐怖", "绝望", "孤独", "焦虑", "厌恶", "羞愧", "嫉妒", "无聊"],
        "中性": ["舒缓", "平静", "放松", "神秘", "困惑", "期待", "惊讶", "怀旧", "同情"],
        "叙事": ["激昂", "紧张", "高潮", "收束", "搞笑"],
    }


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("情绪-镜头视觉映射表 v2.0")
    logger.info("=" * 60)
    emotions = get_emotion_list()
    logger.info(f"\n支持情绪数: {len(emotions)}种")
    logger.info(f"\n情绪列表:")
    for i, e in enumerate(emotions, 1):
        logger.info(f"  {i:2d}. {e}")

    logger.info(f"\n情绪分类:")
    for cat, emos in get_emotion_categories().items():
        logger.info(f"  {cat}: {', '.join(emos)}")

    logger.info(f"\n测试: 快乐(强度0.8)")
    visual = get_emotion_visual("快乐", 0.8)
    logger.info(f"  推荐镜头时长: {visual['shot_duration']['recommended']}s")
    logger.info(f"  运镜: {visual['camera_moves']}")
    logger.info(f"  转场: {visual['transitions']}")
    logger.info(f"  调色: {visual['color_grade']}")
    logger.info(f"  节奏: {visual['pacing']}")
