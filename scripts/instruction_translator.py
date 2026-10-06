"""
P24: 指令翻译器（Instruction Translator）
导演引擎的第二模块：把结构化分镜JSON翻译成各工具的精准指令序列

核心映射库：
1. 情绪 → TTS参数（音色、语速、音调）
2. 动作 → 剪映关键帧（位移、缩放、旋转、透明度）
3. 场景 → 环境音（音效类型、音量）
4. 节奏 → 剪辑参数（转场、时长、镜头切换）
5. 文字 → 排版参数（位置、样式、动画）

输出：指令序列JSON，供P25中央调度器执行
"""

import json
import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict


# ============ 情绪→TTS参数映射（voice_style与tts_executor的EMOTION_INSTRUCT_MAP对齐） ============
EMOTION_TO_TTS = {
    "开心": {"pitch": 1.2, "speed": 1.1, "energy": 0.8, "voice_style": "happy"},
    "委屈": {"pitch": 0.8, "speed": 0.9, "energy": 0.4, "voice_style": "委屈抱怨"},
    "愤怒": {"pitch": 1.3, "speed": 1.2, "energy": 1.0, "voice_style": "angry"},
    "惊恐": {"pitch": 1.4, "speed": 1.3, "energy": 0.9, "voice_style": "fear"},
    "得意": {"pitch": 1.1, "speed": 1.0, "energy": 0.7, "voice_style": "得意洋洋"},
    "平静": {"pitch": 1.0, "speed": 1.0, "energy": 0.5, "voice_style": "calm"},
    "惊讶": {"pitch": 1.3, "speed": 1.1, "energy": 0.8, "voice_style": "surprise"},
    "害羞": {"pitch": 1.1, "speed": 0.9, "energy": 0.4, "voice_style": "温柔"},
    "无奈": {"pitch": 0.9, "speed": 0.9, "energy": 0.5, "voice_style": "无奈"},
    "严肃": {"pitch": 1.0, "speed": 0.9, "energy": 0.7, "voice_style": "严肃"},
    "慌张": {"pitch": 1.2, "speed": 1.3, "energy": 0.8, "voice_style": "慌张"},
    "坚定": {"pitch": 1.0, "speed": 1.0, "energy": 0.9, "voice_style": "坚定"},
}

# ============ 台词情绪自动检测（根据文本内容判断语气） ============
EMOTION_KEYWORDS = {
    "暴跳如雷": ["凭啥", "岂有此理", "太过分", "混蛋", "滚", "气死我了", "什么玩意", "可恶", "不许", "不准"],
    "angry": ["!", "！", "生气", "愤怒", "讨厌", "烦死", "闭嘴", "别吵", "为啥不", "为什么不", "怎么能"],
    "委屈抱怨": ["呜呜", "哭", "好惨", "可怜", "为什么", "凭什么对我", "不公平", "饿坏了"],
    "得意洋洋": ["哈哈", "嘿嘿", "呵呵", "怎么样", "看吧", "我就说", "厉害吧", "服了吧", "对了"],
    "冷笑嘲讽": ["哼", "切", "嘁", "就这", "不过如此", "可笑", "天真", "行，那我", "那我自己", "行吧那"],
    "心慌意乱": ["怎么办", "完了", "糟了", "坏了", "出事了", "来不及", "完蛋"],
    "低声下气": ["求求你", "拜托", "麻烦您", "不好意思", "对不起", "请您"],
    "不紧不慢": ["嗯", "哦", "好的", "行吧", "知道了", "稍等", "别急", "规定"],
    "结结巴巴": ["那个", "这个", "我我", "就是", "嗯...", "呃", "...", "正在"],
    "happy": ["开心", "高兴", "太好了", "棒", "赞", "喜欢", "爱你"],
    "surprise": ["?", "？", "哇", "天哪", "真的假的", "不会吧", "什么", "咋回事"],
    "坚定": ["必须", "一定", "我保证", "绝对", "毫无疑问", "肯定"],
    "严肃": ["注意", "听好了", "我再说一遍", "严肃", "认真"],
    "无奈": ["唉", "算了", "随便吧", "就这样", "没办法"],
    "质问": ["为啥", "为什么", "怎么不", "凭什么", "难道"],
}


def detect_emotion_from_text(text: str) -> str:
    """根据台词内容自动检测情绪/语气，返回tts_executor兼容的voice_style"""
    if not text:
        return "calm"

    scores = {}
    for emotion, keywords in EMOTION_KEYWORDS.items():
        score = 0
        for kw in keywords:
            if kw in text:
                # 标点符号权重低，词语权重高
                score += 3 if len(kw) > 1 else 1
        if score > 0:
            scores[emotion] = score

    if not scores:
        return "calm"

    # 返回得分最高的情绪
    return max(scores, key=scores.get)


# ============ 角色性格配置（影响情绪波动范围） ============
# stability: 情绪稳定性 0-1，越高越稳定（情绪上限越低）
# allowed_emotions: 该角色允许出现的情绪列表，None表示不限制
# baseline: 基线情绪（无明确情绪时的默认）
CHARACTER_PERSONALITY = {
    "顾客": {"stability": 0.3, "allowed_emotions": None, "baseline": "calm"},
    "前台": {"stability": 0.8, "allowed_emotions": ["calm", "不紧不慢", "低声下气", "结结巴巴", "无奈", "angry"], "baseline": "calm"},
    "机器人": {"stability": 0.95, "allowed_emotions": ["calm", "不紧不慢", "surprise"], "baseline": "calm"},
    "豆包": {"stability": 0.4, "allowed_emotions": None, "baseline": "happy"},
    "女杀手": {"stability": 0.7, "allowed_emotions": ["calm", "冷笑嘲讽", "严肃", "angry"], "baseline": "calm"},
    "旁白": {"stability": 0.9, "allowed_emotions": ["calm", "严肃", "不紧不慢"], "baseline": "calm"},
}

# 高情绪→低情绪的降级映射（稳定型角色遇到激烈情绪时收敛）
EMOTION_DOWNGRADE = {
    "暴跳如雷": "angry",
    "得意洋洋": "happy",
    "冷笑嘲讽": "无奈",
    "心慌意乱": "紧张",
    "怒吼": "angry",
}


def apply_personality_to_emotion(emotion: str, character: str) -> str:
    """根据角色性格调整情绪（稳定型角色收敛激烈情绪）"""
    personality = CHARACTER_PERSONALITY.get(character)
    if not personality:
        return emotion  # 未配置性格的角色不调整

    allowed = personality.get("allowed_emotions")
    if allowed and emotion not in allowed:
        # 尝试降级映射
        if emotion in EMOTION_DOWNGRADE:
            downgraded = EMOTION_DOWNGRADE[emotion]
            if downgraded in allowed:
                return downgraded
        # 降级后仍不允许，用基线情绪
        return personality.get("baseline", "calm")

    return emotion


# ============ 角色→音色映射 ============
CHARACTER_TO_VOICE = {
    "豆包": {"voice_id": "female_young", "base_pitch": 1.0, "base_speed": 1.0},
    "机器人": {"voice_id": "robot_male", "base_pitch": 0.8, "base_speed": 0.9},
    "女杀手": {"voice_id": "female_cold", "base_pitch": 0.9, "base_speed": 0.95},
}

# ============ 情绪→画面特效映射（自动生成） ============
EMOTION_TO_EFFECT = {
    # 震动类
    "愤怒": {"type": "shake", "duration": 0.5, "params": {"intensity": 0.15, "frequency": 8}},
    "暴怒": {"type": "shake", "duration": 0.8, "params": {"intensity": 0.25, "frequency": 12}},
    "紧张": {"type": "shake", "duration": 0.4, "params": {"intensity": 0.05, "frequency": 15}},
    "慌张": {"type": "shake", "duration": 0.5, "params": {"intensity": 0.08, "frequency": 12}},
    "害怕": {"type": "shake", "duration": 0.6, "params": {"intensity": 0.1, "frequency": 10}},
    "恐惧": {"type": "shake", "duration": 0.8, "params": {"intensity": 0.15, "frequency": 8}},
    "崩溃": {"type": "shake", "duration": 1.0, "params": {"intensity": 0.2, "frequency": 6}},
    # 闪白类
    "惊恐": {"type": "flash_white", "duration": 0.2, "params": {"intensity": 1.0}},
    "震惊": {"type": "flash_white", "duration": 0.15, "params": {"intensity": 0.8}},
    "惊讶": {"type": "flash_white", "duration": 0.1, "params": {"intensity": 0.5}},
    "意外": {"type": "flash_white", "duration": 0.15, "params": {"intensity": 0.6}},
    # 模糊类
    "哭泣": {"type": "blur", "duration": 1.0, "params": {"intensity": 0.3}},
    "难过": {"type": "blur", "duration": 0.8, "params": {"intensity": 0.2}},
    "悲伤": {"type": "blur", "duration": 1.0, "params": {"intensity": 0.25}},
    "绝望": {"type": "blur", "duration": 1.2, "params": {"intensity": 0.4}},
    "头晕": {"type": "blur", "duration": 0.6, "params": {"intensity": 0.35}},
    # 脉冲类
    "得意": {"type": "pulse", "duration": 0.6, "params": {"intensity": 0.05}},
    "嚣张": {"type": "pulse", "duration": 0.8, "params": {"intensity": 0.08}},
    "兴奋": {"type": "pulse", "duration": 0.5, "params": {"intensity": 0.06}},
    "激动": {"type": "pulse", "duration": 0.6, "params": {"intensity": 0.07}},
    "期待": {"type": "pulse", "duration": 0.8, "params": {"intensity": 0.04}},
    # 推镜类
    "开心": {"type": "zoom_in", "duration": 0.5, "params": {"intensity": 0.08}},
    "高兴": {"type": "zoom_in", "duration": 0.5, "params": {"intensity": 0.06}},
    "温柔": {"type": "zoom_in", "duration": 1.0, "params": {"intensity": 0.04}},
    "认真": {"type": "zoom_in", "duration": 0.8, "params": {"intensity": 0.05}},
    # 拉镜类
    "尴尬": {"type": "zoom_out", "duration": 0.6, "params": {"intensity": 0.08}},
    "害羞": {"type": "zoom_out", "duration": 0.8, "params": {"intensity": 0.06}},
    "无奈": {"type": "zoom_out", "duration": 0.8, "params": {"intensity": 0.05}},
    # 淡入淡出类
    "平静": {"type": "fade_in", "duration": 0.5, "params": {"intensity": 1.0}},
    "淡定": {"type": "fade_in", "duration": 0.6, "params": {"intensity": 1.0}},
    "严肃": {"type": "fade_in", "duration": 0.4, "params": {"intensity": 1.0}},
    # 旋转类
    "疑惑": {"type": "rotate", "duration": 0.5, "params": {"intensity": 5}},
    "困惑": {"type": "rotate", "duration": 0.6, "params": {"intensity": 8}},
    "晕眩": {"type": "rotate", "duration": 0.8, "params": {"intensity": 15}},
}

# ============ 动作→剪映关键帧映射 ============
ACTION_TO_KEYFRAMES = {
    "比耶": {
        "animation": "弹入",
        "keyframes": [
            {"time": 0, "property": "scale", "value": 0.8},
            {"time": 0.3, "property": "scale", "value": 1.1},
            {"time": 0.5, "property": "scale", "value": 1.0},
        ],
        "sfx": ["轻松弹响"],
    },
    "被打": {
        "animation": "闪白+位移+震动",
        "keyframes": [
            {"time": 0, "property": "alpha", "value": 1.0},
            {"time": 0.05, "property": "alpha", "value": 0.0},
            {"time": 0.15, "property": "alpha", "value": 1.0},
            {"time": 0, "property": "position_x", "value": 0.0},
            {"time": 0.1, "property": "position_x", "value": 0.15},
            {"time": 0.3, "property": "position_x", "value": 0.0},
            {"time": 0, "property": "rotation", "value": 0},
            {"time": 0.1, "property": "rotation", "value": -5},
            {"time": 0.3, "property": "rotation", "value": 0},
        ],
        "sfx": ["击打声", "闪白"],
        "flash_white": {"start": 0, "duration": 0.15},
    },
    "摸头": {
        "animation": "缓慢下移+轻微震动",
        "keyframes": [
            {"time": 0, "property": "position_y", "value": 0.0},
            {"time": 0.5, "property": "position_y", "value": -0.05},
            {"time": 1.0, "property": "position_y", "value": -0.03},
        ],
        "sfx": ["委屈呜咽"],
    },
    "掉下": {
        "animation": "加速下落+旋转",
        "keyframes": [
            {"time": 0, "property": "position_y", "value": 0.0},
            {"time": 0.5, "property": "position_y", "value": -0.3},
            {"time": 1.0, "property": "position_y", "value": -0.8},
            {"time": 0, "property": "rotation", "value": 0},
            {"time": 1.0, "property": "rotation", "value": 180},
        ],
        "sfx": ["坠落声"],
    },
    "爬上": {
        "animation": "缓慢上移+探头",
        "keyframes": [
            {"time": 0, "property": "position_y", "value": -0.5},
            {"time": 1.0, "property": "position_y", "value": 0.0},
            {"time": 0, "property": "scale", "value": 0.7},
            {"time": 1.0, "property": "scale", "value": 1.0},
        ],
        "sfx": ["攀爬声"],
    },
    "攻击": {
        "animation": "快速前冲+收回",
        "keyframes": [
            {"time": 0, "property": "position_x", "value": 0.0},
            {"time": 0.1, "property": "position_x", "value": 0.2},
            {"time": 0.3, "property": "position_x", "value": 0.0},
        ],
        "sfx": ["挥拳声"],
    },
    "站立": {
        "animation": "静止",
        "keyframes": [],
        "sfx": [],
    },
    "说话": {
        "animation": "轻微呼吸缩放",
        "keyframes": [
            {"time": 0, "property": "scale", "value": 1.0},
            {"time": 0.5, "property": "scale", "value": 1.02},
            {"time": 1.0, "property": "scale", "value": 1.0},
        ],
        "sfx": [],
    },
    "拍桌": {
        "animation": "快速下移+震动",
        "keyframes": [
            {"time": 0, "property": "position_y", "value": 0.0},
            {"time": 0.1, "property": "position_y", "value": -0.08},
            {"time": 0.2, "property": "position_y", "value": 0.0},
            {"time": 0.1, "property": "rotation", "value": -2},
            {"time": 0.2, "property": "rotation", "value": 0},
        ],
        "sfx": ["击打声"],
    },
    "挠头": {
        "animation": "轻微上移+左右晃动",
        "keyframes": [
            {"time": 0, "property": "position_y", "value": 0.0},
            {"time": 0.3, "property": "position_y", "value": 0.03},
            {"time": 0.6, "property": "position_y", "value": 0.0},
            {"time": 0.2, "property": "position_x", "value": -0.02},
            {"time": 0.4, "property": "position_x", "value": 0.02},
            {"time": 0.6, "property": "position_x", "value": 0.0},
        ],
        "sfx": [],
    },
    "指": {
        "animation": "快速前伸+收回",
        "keyframes": [
            {"time": 0, "property": "scale", "value": 1.0},
            {"time": 0.15, "property": "scale", "value": 1.08},
            {"time": 0.3, "property": "scale", "value": 1.0},
        ],
        "sfx": [],
    },
    "低头": {
        "animation": "缓慢下移",
        "keyframes": [
            {"time": 0, "property": "position_y", "value": 0.0},
            {"time": 0.5, "property": "position_y", "value": -0.06},
        ],
        "sfx": [],
    },
    "微笑": {
        "animation": "轻微放大",
        "keyframes": [
            {"time": 0, "property": "scale", "value": 1.0},
            {"time": 0.3, "property": "scale", "value": 1.03},
        ],
        "sfx": ["笑声"],
    },
    "抱臂": {
        "animation": "静止",
        "keyframes": [],
        "sfx": [],
    },
    "叹气": {
        "animation": "轻微下移+恢复",
        "keyframes": [
            {"time": 0, "property": "position_y", "value": 0.0},
            {"time": 0.4, "property": "position_y", "value": -0.04},
            {"time": 0.8, "property": "position_y", "value": 0.0},
        ],
        "sfx": ["叹气声"],
    },
    "踱步": {
        "animation": "左右移动",
        "keyframes": [
            {"time": 0, "property": "position_x", "value": -0.1},
            {"time": 1.0, "property": "position_x", "value": 0.1},
            {"time": 2.0, "property": "position_x", "value": -0.1},
        ],
        "sfx": ["脚步声"],
    },
    "拿": {
        "animation": "轻微上移",
        "keyframes": [
            {"time": 0, "property": "position_y", "value": 0.0},
            {"time": 0.3, "property": "position_y", "value": 0.04},
        ],
        "sfx": [],
    },
    "整理衣服": {
        "animation": "轻微缩放",
        "keyframes": [
            {"time": 0, "property": "scale", "value": 1.0},
            {"time": 0.3, "property": "scale", "value": 1.01},
            {"time": 0.6, "property": "scale", "value": 1.0},
        ],
        "sfx": [],
    },
    "搓手": {
        "animation": "轻微左右晃动",
        "keyframes": [
            {"time": 0, "property": "position_x", "value": -0.01},
            {"time": 0.2, "property": "position_x", "value": 0.01},
            {"time": 0.4, "property": "position_x", "value": -0.01},
            {"time": 0.6, "property": "position_x", "value": 0.0},
        ],
        "sfx": [],
    },
    "鞠躬": {
        "animation": "快速下移+恢复",
        "keyframes": [
            {"time": 0, "property": "position_y", "value": 0.0},
            {"time": 0.3, "property": "position_y", "value": -0.1},
            {"time": 0.6, "property": "position_y", "value": 0.0},
        ],
        "sfx": [],
    },
    "握拳": {
        "animation": "轻微放大",
        "keyframes": [
            {"time": 0, "property": "scale", "value": 1.0},
            {"time": 0.2, "property": "scale", "value": 1.05},
        ],
        "sfx": [],
    },
    "张嘴": {
        "animation": "轻微放大",
        "keyframes": [
            {"time": 0, "property": "scale", "value": 1.0},
            {"time": 0.15, "property": "scale", "value": 1.06},
            {"time": 0.3, "property": "scale", "value": 1.0},
        ],
        "sfx": [],
    },
    "挑眉": {
        "animation": "轻微上移",
        "keyframes": [
            {"time": 0, "property": "position_y", "value": 0.0},
            {"time": 0.2, "property": "position_y", "value": 0.02},
            {"time": 0.4, "property": "position_y", "value": 0.0},
        ],
        "sfx": [],
    },
    "躲闪": {
        "animation": "快速侧移+恢复",
        "keyframes": [
            {"time": 0, "property": "position_x", "value": 0.0},
            {"time": 0.1, "property": "position_x", "value": -0.12},
            {"time": 0.3, "property": "position_x", "value": 0.0},
        ],
        "sfx": ["风声"],
    },
}

# ============ 场景→环境音映射 ============
SCENE_TO_AMBIENT = {
    "头像框内": {"ambient": "轻微室内音", "volume": 0.2},
    "抖音主页": {"ambient": "室内环境音", "volume": 0.15},
    "商品橱窗": {"ambient": "商场环境音", "volume": 0.2},
    "室外": {"ambient": "户外环境音", "volume": 0.3},
    "室内": {"ambient": "室内环境音", "volume": 0.2},
    "寺庙": {"ambient": "佛寺气氛+颂钵", "volume": 0.4},
    "草原": {"ambient": "风声+牛铃", "volume": 0.35},
    "湖泊": {"ambient": "水声+微风", "volume": 0.3},
    "酒店": {"ambient": "酒店大堂环境音+轻柔背景音乐", "volume": 0.15},
    "餐厅": {"ambient": "餐厅嘈杂声+餐具碰撞", "volume": 0.3},
    "办公室": {"ambient": "办公室环境音+键盘声", "volume": 0.2},
    "家里": {"ambient": "居家环境音+时钟滴答", "volume": 0.1},
    "街道": {"ambient": "街道嘈杂声+汽车鸣笛", "volume": 0.35},
    "学校": {"ambient": "校园环境音+铃声", "volume": 0.25},
    "医院": {"ambient": "医院环境音+心电监护", "volume": 0.2},
    "商场": {"ambient": "商场环境音+背景音乐", "volume": 0.25},
    "车站": {"ambient": "车站广播+人流嘈杂", "volume": 0.3},
    "森林": {"ambient": "鸟鸣+风声+树叶沙沙", "volume": 0.25},
    "海边": {"ambient": "海浪声+海鸥叫", "volume": 0.3},
    "夜晚": {"ambient": "夜晚虫鸣+微风", "volume": 0.15},
    "白天": {"ambient": "白天环境音+鸟鸣", "volume": 0.2},
}

# ============ 转场→剪映参数映射 ============
TRANSITION_TO_PARAMS = {
    "硬切": {"type": "none", "duration": 0},
    "叠化": {"type": "叠化", "duration": 0.3},
    "闪白": {"type": "闪白", "duration": 0.15},
    "缩放": {"type": "缩放", "duration": 0.2},
    "左滑": {"type": "左滑", "duration": 0.2},
    "右滑": {"type": "右滑", "duration": 0.2},
}

# ============ 文字样式→排版参数映射 ============
TEXT_STYLE_TO_PARAMS = {
    "诗意留白": {
        "font": "宋体简",
        "size": 5.0,
        "color": (1.0, 1.0, 1.0),
        "position_y": -0.3,
        "letter_spacing": 1.5,
        "anim_in": "渐显",
    },
    "竖排地名": {
        "font": "楷体简",
        "size": 6.0,
        "color": (1.0, 1.0, 1.0),
        "position_x": 0.7,
        "position_y": 0.3,
        "direction": "vertical",
        "anim_in": "打字机",
    },
    "手写logo": {
        "font": "手写体",
        "size": 8.0,
        "color": (1.0, 0.9, 0.3),
        "position_x": -0.6,
        "position_y": 0.7,
        "border": {"color": (0.8, 0.2, 0.2), "width": 2},
        "anim_in": "弹入",
    },
    "底部对白": {
        "font": "黑体简",
        "size": 5.5,
        "color": (1.0, 1.0, 1.0),
        "position_y": -0.75,
        "background": {"color": (0, 0, 0, 0.5), "height": 0.08},
        "anim_in": "渐显",
    },
}


@dataclass
class TTSInstruction:
    """TTS配音指令"""
    character: str
    text: str
    voice_id: str
    pitch: float
    speed: float
    energy: float
    voice_style: str
    start_time: float
    duration: float


@dataclass
class KeyframeInstruction:
    """剪映关键帧指令"""
    track: str
    property: str
    time: float
    value: float
    curve: str = "EASE_OUT"


@dataclass
class EffectInstruction:
    """特效/转场指令"""
    type: str
    start_time: float
    duration: float
    params: Dict = field(default_factory=dict)


@dataclass
class AudioInstruction:
    """音轨指令"""
    type: str  # bgm/ambient/sfx/dialogue
    name: str
    start_time: float
    duration: float
    volume: float = 0.5
    channel: str = "stereo"


@dataclass
class TextInstruction:
    """文字排版指令"""
    text: str
    style: str
    start_time: float
    duration: float
    params: Dict = field(default_factory=dict)


@dataclass
class MaskInstruction:
    """蒙版指令"""
    target: str           # 目标轨道（如 char_豆包）
    type: str             # 蒙版类型（circle/rect）
    start_time: float
    duration: float
    params: Dict = field(default_factory=dict)  # center_x/center_y/size/feather等


@dataclass
class SFXInstruction:
    """音效指令"""
    type: str
    emotion: str = "normal"
    duration: float = 1.0
    start_time: float = 0.0
    volume: float = 0.7


@dataclass
class InstructionSequence:
    """指令序列（P25调度器的输入）"""
    project: Dict
    tts_instructions: List[TTSInstruction] = field(default_factory=list)
    keyframe_instructions: List[KeyframeInstruction] = field(default_factory=list)
    effect_instructions: List[EffectInstruction] = field(default_factory=list)
    audio_instructions: List[AudioInstruction] = field(default_factory=list)
    sfx_instructions: List[SFXInstruction] = field(default_factory=list)
    text_instructions: List[TextInstruction] = field(default_factory=list)
    mask_instructions: List[MaskInstruction] = field(default_factory=list)
    comfyui_instructions: List[Dict] = field(default_factory=list)
    blender_instructions: List[Dict] = field(default_factory=list)


class InstructionTranslator:
    """指令翻译器：结构化分镜 → 工具指令序列"""

    def __init__(self):
        self.sequence = None

    def translate(self, parsed_script: Dict[str, Any]) -> InstructionSequence:
        """
        把P23输出的结构化分镜翻译成指令序列

        Args:
            parsed_script: P23剧本解析器输出的标准分镜JSON

        Returns:
            InstructionSequence 指令序列
        """
        self.sequence = InstructionSequence(
            project=parsed_script.get("project", {}),
        )
        # 把characters和scenes放进project，供P25调度器创建ASSET任务
        self.sequence.project["characters"] = parsed_script.get("characters", [])
        self.sequence.project["scenes"] = parsed_script.get("scenes", [])

        # 1. 翻译角色信息（建立角色→音色映射）
        characters = parsed_script.get("characters", [])
        char_voice_map = {}
        for char in characters:
            name = char.get("name", "")
            if name in CHARACTER_TO_VOICE:
                char_voice_map[name] = CHARACTER_TO_VOICE[name]
            else:
                char_voice_map[name] = {"voice_id": "default", "base_pitch": 1.0, "base_speed": 1.0}

        # 2. 逐场景逐镜头翻译
        for scene in parsed_script.get("scenes", []):
            scene_start = scene.get("start", 0)
            scene_location = scene.get("location", "")

            # 2.1 场景环境音
            if scene_location in SCENE_TO_AMBIENT:
                ambient = SCENE_TO_AMBIENT[scene_location]
                self.sequence.audio_instructions.append(AudioInstruction(
                    type="ambient",
                    name=ambient["ambient"],
                    start_time=scene_start,
                    duration=scene.get("duration", 5),
                    volume=ambient["volume"],
                ))

            # 2.1.1 场景蒙版（头像框内场景 → 圆形蒙版）
            if scene_location == "头像框内":
                # 找到该场景的主角（第一个出现的角色）
                main_char = None
                for shot in scene.get("shots", []):
                    for char_action in shot.get("characters", []):
                        char_name = self._resolve_char_name(char_action.get("character_id", ""), characters)
                        if char_name:
                            main_char = char_name
                            break
                    if main_char:
                        break

                if main_char:
                    self.sequence.mask_instructions.append(MaskInstruction(
                        target=f"char_{main_char}",
                        type="circle",
                        start_time=scene_start,
                        duration=scene.get("duration", 5),
                        params={
                            "center_x": -0.542,
                            "center_y": 0.516,
                            "size": 0.203,
                            "feather": 0.001,
                        },
                    ))

            # 2.2 场景转场
            transition = scene.get("transition", "硬切")
            if transition != "硬切" and scene_start > 0:
                trans_params = TRANSITION_TO_PARAMS.get(transition, TRANSITION_TO_PARAMS["硬切"])
                self.sequence.effect_instructions.append(EffectInstruction(
                    type=f"transition_{trans_params['type']}",
                    start_time=scene_start - trans_params["duration"],
                    duration=trans_params["duration"],
                    params=trans_params,
                ))
                # 转场音效
                trans_sfx_map = {"叠化": "叮", "闪白": "闪白", "划像": "嗖", "模糊": "嗖"}
                trans_sfx = trans_sfx_map.get(transition, "嗖")
                self.sequence.sfx_instructions.append(SFXInstruction(
                    type=trans_sfx,
                    emotion="normal",
                    duration=0.3,
                    start_time=scene_start,
                    volume=0.85,
                ))

            # 2.3 逐镜头翻译
            for shot in scene.get("shots", []):
                shot_start = shot.get("start", 0)
                shot_duration = shot.get("duration", 2)

                # 角色动作→关键帧
                for char_action in shot.get("characters", []):
                    char_name = self._resolve_char_name(char_action.get("character_id", ""), characters)
                    action = char_action.get("action", "站立")
                    emotion = char_action.get("emotion", "平静")
                    dialogue = char_action.get("dialogue", "")

                    # 动作关键帧
                    if action in ACTION_TO_KEYFRAMES:
                        action_def = ACTION_TO_KEYFRAMES[action]
                        for kf in action_def.get("keyframes", []):
                            self.sequence.keyframe_instructions.append(KeyframeInstruction(
                                track=f"char_{char_name}",
                                property=kf["property"],
                                time=shot_start + kf["time"],
                                value=kf["value"],
                            ))

                        # 动作音效（独立SFX指令）
                        for sfx in action_def.get("sfx", []):
                            self.sequence.sfx_instructions.append(SFXInstruction(
                                type=sfx,
                                emotion=emotion,
                                duration=0.5,
                                start_time=shot_start,
                                volume=0.7,
                            ))

                        # 情绪音效（强烈情绪触发）
                        emotion_sfx_map = {
                            "惊讶": "惊讶", "震惊": "惊讶", "惊恐": "尖叫",
                            "愤怒": None, "冷笑": "冷笑", "叹气": "叹气",
                            "哭泣": "哭泣", "开心": "笑声", "得意": "笑声",
                        }
                        emotion_sfx = emotion_sfx_map.get(emotion)
                        if emotion_sfx and not dialogue:
                            self.sequence.sfx_instructions.append(SFXInstruction(
                                type=emotion_sfx,
                                emotion=emotion,
                                duration=0.5,
                                start_time=shot_start,
                                volume=0.6,
                            ))

                        # 闪白特效
                        if "flash_white" in action_def:
                            fw = action_def["flash_white"]
                            self.sequence.effect_instructions.append(EffectInstruction(
                                type="flash_white",
                                start_time=shot_start + fw["start"],
                                duration=fw["duration"],
                            ))

                    # 情绪驱动画面特效（自动生成，独立于动作映射和台词）
                    emotion_effect = EMOTION_TO_EFFECT.get(emotion)
                    if emotion_effect:
                        eff = emotion_effect
                        self.sequence.effect_instructions.append(EffectInstruction(
                            type=eff["type"],
                            start_time=shot_start + eff.get("start_offset", 0),
                            duration=eff["duration"],
                            params=eff.get("params", {}),
                        ))

                    # 台词→TTS
                    if dialogue:
                        voice_info = char_voice_map.get(char_name, CHARACTER_TO_VOICE.get("豆包", {}))
                        # 情绪判断：优先用P23指定的，默认"平静"时用台词内容自动检测
                        if emotion == "平静":
                            detected = detect_emotion_from_text(dialogue)
                            # 反向映射到EMOTION_TO_TTS的key
                            emotion_reverse = {v["voice_style"]: k for k, v in EMOTION_TO_TTS.items()}
                            emotion_key = emotion_reverse.get(detected, "平静")
                            emotion_params = EMOTION_TO_TTS.get(emotion_key, EMOTION_TO_TTS["平静"])
                            voice_style = detected
                        else:
                            emotion_params = EMOTION_TO_TTS.get(emotion, EMOTION_TO_TTS["平静"])
                            voice_style = emotion_params["voice_style"]
                        # 应用角色性格（稳定型角色收敛激烈情绪）
                        voice_style = apply_personality_to_emotion(voice_style, char_name)
                        tts_duration = min(len(dialogue) * 0.15 + 0.5, shot_duration)
                        self.sequence.tts_instructions.append(TTSInstruction(
                            character=char_name,
                            text=dialogue,
                            voice_id=voice_info.get("voice_id", "default"),
                            pitch=voice_info.get("base_pitch", 1.0) * emotion_params["pitch"],
                            speed=voice_info.get("base_speed", 1.0) * emotion_params["speed"],
                            energy=emotion_params["energy"],
                            voice_style=voice_style,
                            start_time=shot_start,
                            duration=tts_duration,
                        ))

                        # 对白字幕
                        self.sequence.text_instructions.append(TextInstruction(
                            text=dialogue,
                            style="底部对白",
                            start_time=shot_start,
                            duration=tts_duration,
                            params=TEXT_STYLE_TO_PARAMS["底部对白"],
                        ))

                # 镜头音效
                for sfx in shot.get("sfx", []):
                    self.sequence.audio_instructions.append(AudioInstruction(
                        type="sfx",
                        name=sfx,
                        start_time=shot_start,
                        duration=0.5,
                        volume=0.85,
                    ))

        # 3. 全局BGM
        bgm = parsed_script.get("audio_mix", {}).get("bgm", "通用BGM")
        total_duration = parsed_script.get("project", {}).get("duration", 20)
        self.sequence.audio_instructions.append(AudioInstruction(
            type="bgm",
            name=bgm,
            start_time=0,
            duration=total_duration,
            volume=0.4,
        ))

        # 4. 文字排版（logo等）
        text_layout = parsed_script.get("text_layout", {})
        if text_layout.get("logo"):
            logo = text_layout["logo"]
            self.sequence.text_instructions.append(TextInstruction(
                text=logo.get("text", ""),
                style="手写logo",
                start_time=0,
                duration=total_duration,
                params=TEXT_STYLE_TO_PARAMS.get("手写logo", {}),
            ))

        return self.sequence

    def _resolve_char_name(self, char_id: str, characters: List[Dict]) -> str:
        """根据角色ID解析角色名"""
        for char in characters:
            if char.get("id") == char_id:
                return char.get("name", char_id)
        return char_id

    def to_json(self) -> Dict[str, Any]:
        """输出指令序列JSON"""
        if not self.sequence:
            return {}
        # 关键帧按时间排序（同轨道内）
        sorted_keyframes = sorted(
            [asdict(k) for k in self.sequence.keyframe_instructions],
            key=lambda x: (x.get("track", ""), x.get("time", 0))
        )
        return {
            "project": self.sequence.project,
            "tts_instructions": [asdict(t) for t in self.sequence.tts_instructions],
            "keyframe_instructions": sorted_keyframes,
            "effect_instructions": [asdict(e) for e in self.sequence.effect_instructions],
            "audio_instructions": [asdict(a) for a in self.sequence.audio_instructions],
            "sfx_instructions": [asdict(s) for s in self.sequence.sfx_instructions],
            "text_instructions": [asdict(t) for t in self.sequence.text_instructions],
            "mask_instructions": [asdict(m) for m in self.sequence.mask_instructions],
            "summary": {
                "tts_count": len(self.sequence.tts_instructions),
                "keyframe_count": len(self.sequence.keyframe_instructions),
                "effect_count": len(self.sequence.effect_instructions),
                "audio_count": len(self.sequence.audio_instructions),
                "sfx_count": len(self.sequence.sfx_instructions),
                "text_count": len(self.sequence.text_instructions),
                "mask_count": len(self.sequence.mask_instructions),
            },
        }

    def save_json(self, output_path: str):
        """保存指令序列到JSON文件"""
        result = self.to_json()
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"✅ 指令序列已保存: {output_path}")
        return output_path

    def print_summary(self):
        """打印翻译摘要"""
        if not self.sequence:
            print("❌ 未翻译")
            return

        print(f"\n{'='*60}")
        print(f"指令翻译摘要")
        print(f"{'='*60}")
        print(f"项目: {self.sequence.project.get('title', '未命名')}")
        print(f"\nTTS配音指令: {len(self.sequence.tts_instructions)}条")
        for t in self.sequence.tts_instructions:
            print(f"  [{t.start_time:.1f}s] {t.character}({t.voice_style}): \"{t.text[:20]}\"")
        print(f"\n关键帧指令: {len(self.sequence.keyframe_instructions)}条")
        for k in self.sequence.keyframe_instructions[:5]:
            print(f"  [{k.time:.1f}s] {k.track}.{k.property} = {k.value}")
        if len(self.sequence.keyframe_instructions) > 5:
            print(f"  ... 还有{len(self.sequence.keyframe_instructions)-5}条")
        print(f"\n特效指令: {len(self.sequence.effect_instructions)}条")
        for e in self.sequence.effect_instructions:
            print(f"  [{e.start_time:.1f}s] {e.type} ({e.duration}s)")
        print(f"\n音轨指令: {len(self.sequence.audio_instructions)}条")
        for a in self.sequence.audio_instructions[:5]:
            print(f"  [{a.start_time:.1f}s] {a.type}: {a.name} (vol={a.volume})")
        if len(self.sequence.audio_instructions) > 5:
            print(f"  ... 还有{len(self.sequence.audio_instructions)-5}条")
        print(f"\n音效指令: {len(self.sequence.sfx_instructions)}条")
        for s in self.sequence.sfx_instructions:
            print(f"  [{s.start_time:.1f}s] {s.type} (情绪={s.emotion}, {s.duration}s, vol={s.volume})")
        print(f"\n文字指令: {len(self.sequence.text_instructions)}条")
        for t in self.sequence.text_instructions:
            print(f"  [{t.start_time:.1f}s] {t.style}: \"{t.text[:20]}\"")
        print(f"\n蒙版指令: {len(self.sequence.mask_instructions)}条")
        for m in self.sequence.mask_instructions:
            print(f"  [{m.start_time:.1f}s] {m.type} → {m.target}")
        print(f"{'='*60}\n")


if __name__ == "__main__":
    # 测试：用P23解析的豆包被打分镜做翻译
    try:
        from paths import PATHS
        test_dir = PATHS.get("test_dir", "")
    except ImportError:
        _up = os.environ.get("USERPROFILE", r"C:\Users\Administrator")
        test_dir = os.path.join(_up, "Videos", "剪映导出", "Doubao_Jianying-editor", "director_engine_test")
    parsed_path = os.path.join(test_dir, "parsed_script.json")

    if os.path.exists(parsed_path):
        with open(parsed_path, "r", encoding="utf-8") as f:
            parsed_script = json.load(f)

        translator = InstructionTranslator()
        sequence = translator.translate(parsed_script)
        translator.print_summary()

        out_path = os.path.join(test_dir, "instruction_sequence.json")
        translator.save_json(out_path)
    else:
        print(f"❌ 分镜文件不存在: {parsed_path}")
        print("请先运行 script_parser.py 生成分镜JSON")
