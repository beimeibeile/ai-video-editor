"""
创意模板库 - 多主题分镜模板

每个模板包含：
- 主题风格定义
- 钩子文案模板
- 分镜节奏模式（快切/舒缓/递进）
- 景别序列
- 运镜序列
- 转场序列
- 字幕风格
- BGM情绪
- 调色建议
"""

from typing import Dict, List, Any

CREATIVE_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "赛博朋克": {
        "name": "赛博朋克",
        "hook_templates": [
            "未来都市｜赛博朋克",
            "霓虹之下｜赛博纪元",
            "机械之心｜未来已来",
        ],
        "rhythm": "快切",  # 快切/舒缓/递进/混合
        "shot_sequence": ["全景", "中景", "特写", "近景", "中景", "全景"],
        "camera_sequence": ["zoom_in", "pan_right", "zoom_in", "pan_left", "zoom_out", "zoom_in"],
        "transition_sequence": ["glitch", "dissolve", "glitch", "dissolve", "glitch"],
        "subtitle_style": "fun",
        "bgm_mood": "电子/赛博朋克/科技感",
        "color_grade": "高对比+青橙色调+霓虹光效",
        "sfx_hints": ["电子脉冲", "故障音", "合成器", "低音鼓点"],
        "duration_per_shot": 2.5,
    },
    "国风": {
        "name": "国风",
        "hook_templates": [
            "东方美学｜国风古韵",
            "山水之间｜诗意东方",
            "千年风雅｜国潮新生",
        ],
        "rhythm": "舒缓",
        "shot_sequence": ["远景", "全景", "中景", "特写", "近景", "全景"],
        "camera_sequence": ["pan_right", "zoom_in", "pan_left", "zoom_in", "zoom_out", "pan_right"],
        "transition_sequence": ["dissolve", "dissolve", "fade_black", "dissolve", "dissolve"],
        "subtitle_style": "epic",
        "bgm_mood": "国风/古典/古筝/二胡",
        "color_grade": "低饱和+暖色调+柔光",
        "sfx_hints": ["古筝", "笛子", "鼓声", "流水"],
        "duration_per_shot": 3.0,
    },
    "治愈": {
        "name": "治愈",
        "hook_templates": [
            "温柔时光｜治愈系",
            "生活碎片｜小确幸",
            "慢下来｜感受美好",
        ],
        "rhythm": "舒缓",
        "shot_sequence": ["特写", "近景", "中景", "特写", "近景", "全景"],
        "camera_sequence": ["zoom_in", "pan_right", "zoom_in", "pan_left", "zoom_out", "zoom_in"],
        "transition_sequence": ["dissolve", "dissolve", "dissolve", "dissolve", "dissolve"],
        "subtitle_style": "warm",
        "bgm_mood": "轻音乐/钢琴/治愈/温暖",
        "color_grade": "暖色调+柔光+低对比",
        "sfx_hints": ["钢琴", "风铃", "鸟鸣", "雨声"],
        "duration_per_shot": 3.5,
    },
    "卡点": {
        "name": "卡点",
        "hook_templates": [
            "节奏控｜卡点盛宴",
            "踩点狂魔｜极度舒适",
            "节拍之上｜视觉冲击",
        ],
        "rhythm": "快切",
        "shot_sequence": ["特写", "近景", "中景", "特写", "近景", "中景"],
        "camera_sequence": ["zoom_in", "zoom_in", "zoom_in", "zoom_in", "zoom_in", "zoom_in"],
        "transition_sequence": ["glitch", "glitch", "glitch", "glitch", "glitch"],
        "subtitle_style": "fun",
        "bgm_mood": "电子/EDM/节奏感强/鼓点",
        "color_grade": "高饱和+高对比+鲜艳",
        "sfx_hints": ["鼓点", "bass", "电子音效", "转场音"],
        "duration_per_shot": 1.5,
    },
    "电影感": {
        "name": "电影感",
        "hook_templates": [
            "光影叙事｜电影质感",
            "帧帧如画｜ cinematic",
            "视觉诗｜电影级调色",
        ],
        "rhythm": "递进",
        "shot_sequence": ["远景", "全景", "中景", "近景", "特写", "全景"],
        "camera_sequence": ["pan_right", "zoom_in", "pan_left", "zoom_in", "zoom_out", "pan_right"],
        "transition_sequence": ["dissolve", "fade_black", "dissolve", "dissolve", "fade_black"],
        "subtitle_style": "cinema",
        "bgm_mood": "电影配乐/史诗/管弦乐",
        "color_grade": "青橙色调+高对比+暗角+颗粒",
        "sfx_hints": ["管弦乐", "鼓点", "环境音", "低音"],
        "duration_per_shot": 3.0,
    },
    "极简": {
        "name": "极简",
        "hook_templates": [
            "少即是多｜极简美学",
            "留白之美｜简约不简单",
            "纯净视觉｜极简主义",
        ],
        "rhythm": "舒缓",
        "shot_sequence": ["中景", "近景", "特写", "中景", "近景", "全景"],
        "camera_sequence": ["zoom_in", "pan_right", "zoom_in", "pan_left", "zoom_out", "zoom_in"],
        "transition_sequence": ["dissolve", "dissolve", "dissolve", "dissolve", "dissolve"],
        "subtitle_style": "minimal",
        "bgm_mood": "轻音乐/氛围/极简",
        "color_grade": "低饱和+中性色+干净",
        "sfx_hints": ["氛围音", "轻柔钢琴", "环境音"],
        "duration_per_shot": 3.0,
    },
    "复古": {
        "name": "复古",
        "hook_templates": [
            "时光倒流｜复古怀旧",
            "旧时光｜胶片记忆",
            "年代感｜复古回潮",
        ],
        "rhythm": "舒缓",
        "shot_sequence": ["全景", "中景", "特写", "近景", "中景", "全景"],
        "camera_sequence": ["pan_right", "zoom_in", "pan_left", "zoom_in", "zoom_out", "pan_right"],
        "transition_sequence": ["fade_white", "dissolve", "fade_white", "dissolve", "fade_white"],
        "subtitle_style": "warm",
        "bgm_mood": "复古/爵士/老唱片/怀旧",
        "color_grade": "暖黄调+颗粒+漏光+低对比",
        "sfx_hints": ["胶片噪音", "爵士", "老唱片", "钢琴"],
        "duration_per_shot": 3.0,
    },
}


# 主题别名映射（用户输入的简称 -> 模板标准名）
THEME_ALIASES = {
    "赛博": "赛博朋克",
    "赛博朋客": "赛博朋克",
    "cyber": "赛博朋克",
    "电影": "电影感",
    "cinematic": "电影感",
    "中国风": "国风",
    "古风": "国风",
    "温暖": "治愈",
    "快剪": "卡点",
    "踩点": "卡点",
    "简约": "极简",
    "怀旧": "复古",
}

def get_template(theme: str) -> Dict[str, Any]:
    """根据主题获取创意模板，支持别名，不存在则返回默认模板"""
    standard = THEME_ALIASES.get(theme, theme)
    return CREATIVE_TEMPLATES.get(standard, CREATIVE_TEMPLATES["极简"])


def list_themes() -> List[str]:
    """列出所有可用主题"""
    return list(CREATIVE_TEMPLATES.keys())
