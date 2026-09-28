"""
cap_audio_designer — 音频设计模块
BGM智能匹配、TTS旁白、音效推荐、多音轨管理

支持：
- BGM关键词匹配（根据主题/风格/情绪）
- TTS旁白生成（剪映云端配音）
- 音效推荐（转场/强调/氛围）
- 多音轨自动布局（旁白/BGM/音效分离）
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
    HAS_JY = True
except ImportError:
    HAS_JY = False
    draft = None


# BGM关键词库（主题 -> 推荐关键词列表）
BGM_LIBRARY = {
    "国风": ["国风", "古风", "中国风", "古筝", "二胡", "笛子", "水墨"],
    "治愈": ["治愈", "温暖", "轻音乐", "钢琴", "吉他", "民谣", "安静"],
    "卡点": ["电子", "EDM", "节奏", "鼓点", "动感", "炫酷", "beat"],
    "电影": ["电影", "史诗", "配乐", "交响乐", "大气", "震撼", "cinematic"],
    "赛博": ["赛博朋克", "电子", "合成器", "科技感", "未来", "synthwave"],
    "极简": ["极简", "氛围", "环境音", "ambient", "钢琴", "留白"],
    "复古": ["复古", "怀旧", "爵士", "lofi", "老唱片", "80年代"],
    "搞笑": ["搞笑", "欢乐", "卡通", "滑稽", "喜剧", "俏皮"],
    "悬疑": ["悬疑", "紧张", "惊悚", "推理", "神秘", "dark"],
    "励志": ["励志", "热血", "激昂", "奋斗", "正能量", "崛起"],
}

# 音效库（场景 -> 推荐音效）
SFX_LIBRARY = {
    "转场": ["嗖", "唰", "whoosh", "转场音", "过渡"],
    "强调": ["叮", "咚", "强调音", "impact", "boom"],
    "氛围": ["风声", "雨声", "鸟鸣", "环境音", "白噪音"],
    "搞笑": ["搞笑音", "弹簧", "滑稽", "失败音", "叹气"],
    "科技": ["科技音", "电子音", "哔", "扫描", "全息"],
    "自然": ["水流", "火焰", "雷电", "海浪", "森林"],
}

# TTS音色库
TTS_VOICES = {
    "女声_温柔": "zh_female_wanwanxiaohe",
    "女声_活泼": "zh_female_qingxin",
    "女声_知性": "zh_female_shuangkuaisisi",
    "男声_磁性": "zh_male_chenguangboxin",
    "男声_沉稳": "zh_male_chunhoubaozhen",
    "男声_活力": "zh_male_jiqingyangguang",
    "童声": "zh_female_xiaopengyou",
    "旁白_纪录片": "zh_male_chenguangboxin",
    "旁白_情感": "zh_female_wanwanxiaohe",
}


def match_bgm(theme: str, mood: str = None) -> list:
    """
    根据主题和情绪匹配BGM关键词

    Args:
        theme: 主题（国风/治愈/卡点等）
        mood: 情绪（可选，如"欢快"/"悲伤"/"紧张"）

    Returns:
        推荐关键词列表
    """
    keywords = BGM_LIBRARY.get(theme, BGM_LIBRARY["极简"])

    if mood:
        mood_map = {
            "欢快": ["欢快", "明亮", "愉悦"],
            "悲伤": ["悲伤", "忧郁", "抒情"],
            "紧张": ["紧张", "悬疑", "急促"],
            "浪漫": ["浪漫", "甜蜜", "爱情"],
            "激昂": ["激昂", "热血", "史诗"],
        }
        if mood in mood_map:
            keywords = mood_map[mood] + keywords

    return keywords[:5]  # 返回前5个


def add_bgm(project, theme: str, start_time="0s", duration="30s",
            mood: str = None, track_name="BGM"):
    """
    添加BGM（自动匹配关键词）

    Args:
        project: JyProject实例
        theme: 主题
        start_time: 起始时间
        duration: 持续时长
        mood: 情绪
        track_name: 轨道名
    """
    if not HAS_JY:
        return None

    keywords = match_bgm(theme, mood)

    # 尝试第一个关键词，失败则依次尝试
    for kw in keywords:
        try:
            project.add_cloud_music(kw, start_time=start_time, duration=duration, track_name=track_name)
            return kw
        except Exception:
            continue

    return None


def add_tts_narration(project, text: str, start_time="0s",
                      voice: str = "女声_温柔", track_name="Narration"):
    """
    添加TTS旁白

    Args:
        project: JyProject实例
        text: 旁白文本
        start_time: 起始时间
        voice: 音色（见TTS_VOICES）
        track_name: 轨道名
    """
    if not HAS_JY:
        return None

    speaker = TTS_VOICES.get(voice, TTS_VOICES["女声_温柔"])

    try:
        project.add_tts_intelligent(text, speaker=speaker, start_time=start_time, track_name=track_name)
        return True
    except Exception as e:
        return False


def add_sfx(project, scene: str, start_time="0s", duration="0.5s",
            track_name="SFX"):
    """
    添加音效

    Args:
        project: JyProject实例
        scene: 场景类型（转场/强调/氛围等）
        start_time: 起始时间
        duration: 持续时长
        track_name: 轨道名
    """
    if not HAS_JY:
        return None

    keywords = SFX_LIBRARY.get(scene, SFX_LIBRARY["转场"])

    for kw in keywords:
        try:
            project.add_cloud_media(kw, start_time=start_time, duration=duration, track_name=track_name)
            return kw
        except Exception:
            continue

    return None


def auto_audio_design(project, theme: str, duration: int,
                      narration_text: str = None, hook_text: str = None):
    """
    自动音频设计（一键成片用）

    Args:
        project: JyProject实例
        theme: 主题
        duration: 视频时长（秒）
        narration_text: 旁白文本（可选）
        hook_text: 钩子文案（可选，用于开头强调音效）

    Returns:
        音频设计结果字典
    """
    result = {"bgm": None, "narration": None, "sfx": []}

    # 1. BGM
    dur_str = f"{duration}s"
    result["bgm"] = add_bgm(project, theme, start_time="0s", duration=dur_str)

    # 2. 旁白
    if narration_text:
        # 按句号分割，每句间隔
        sentences = [s.strip() for s in narration_text.replace("。", "。|").split("|") if s.strip()]
        current_time = 1.0  # 1秒后开始旁白
        for sent in sentences:
            start_str = f"{current_time}s"
            add_tts_narration(project, sent, start_time=start_str, voice="女声_温柔")
            current_time += len(sent) * 0.3 + 0.5  # 估算时长
        result["narration"] = len(sentences)

    # 3. 开头强调音效
    if hook_text:
        sfx = add_sfx(project, "强调", start_time="0s", duration="0.5s")
        if sfx:
            result["sfx"].append(sfx)

    return result


def list_bgm_themes() -> list:
    """列出所有BGM主题"""
    return list(BGM_LIBRARY.keys())


def list_tts_voices() -> list:
    """列出所有TTS音色"""
    return [(k, v) for k, v in TTS_VOICES.items()]


def list_sfx_scenes() -> list:
    """列出所有音效场景"""
    return list(SFX_LIBRARY.keys())
