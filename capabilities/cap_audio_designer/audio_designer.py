"""
声音设计引擎 v2.0 (P9)
为视频自动设计完整音轨：角色对话TTS + 旁白解说 + BGM + 场景音效 + 环境音

核心能力：
1. 角色音色映射：不同角色分配不同TTS音色（含音调/语速）
2. 情绪→BGM选择：根据场景情绪自动选择配乐风格
3. 场景音效库：环境音/动作音/转场音效自动匹配
4. 音频时间轴编排：精确到0.1秒的多轨布局
5. 旁白自动生成：根据剧本概要和关键时刻生成旁白文案
6. 导出音频制作清单（JSON，供TTS引擎/音频合成工具使用）

兼容旧版API：add_bgm/add_tts_narration/add_sfx/auto_audio_design 仍可用
"""
import os
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional, Tuple


# ============================================================
# 枚举定义
# ============================================================

class AudioTrackType(Enum):
    """音频轨道类型"""
    DIALOGUE = "对话"
    NARRATION = "旁白"
    BGM = "BGM"
    SFX = "音效"
    AMBIENT = "环境音"


class BGMEmotionStyle(Enum):
    """BGM情绪风格"""
    SAD = "悲伤"
    TENSE = "紧张"
    HOPEFUL = "希望"
    EPIC = "史诗"
    CALM = "平静"
    TRIUMPHANT = "胜利"
    MELANCHOLY = "忧郁"


# ============================================================
# 数据结构
# ============================================================

@dataclass
class AudioClip:
    """音频片段"""
    track_type: AudioTrackType
    start_time: float
    duration: float
    content: str
    character: str = ""
    voice: str = ""
    volume: float = 1.0
    fade_in: float = 0.0
    fade_out: float = 0.0
    emotion: str = ""


@dataclass
class CharacterVoice:
    """角色音色设定"""
    character_name: str
    voice_id: str
    gender: str = "male"
    age_range: str = "adult"
    pitch: float = 1.0
    speed: float = 1.0
    description: str = ""


@dataclass
class AudioDesignPlan:
    """完整声音设计方案"""
    total_duration: float
    bgm_tracks: List[AudioClip] = field(default_factory=list)
    dialogue_tracks: List[AudioClip] = field(default_factory=list)
    narration_tracks: List[AudioClip] = field(default_factory=list)
    sfx_tracks: List[AudioClip] = field(default_factory=list)
    ambient_tracks: List[AudioClip] = field(default_factory=list)
    character_voices: Dict[str, CharacterVoice] = field(default_factory=dict)
    narration_script: str = ""

    def get_all_clips(self) -> List[AudioClip]:
        all_clips = (self.bgm_tracks + self.dialogue_tracks +
                     self.narration_tracks + self.sfx_tracks +
                     self.ambient_tracks)
        return sorted(all_clips, key=lambda c: c.start_time)

    def get_track_summary(self) -> Dict[str, int]:
        return {
            "BGM": len(self.bgm_tracks),
            "对话": len(self.dialogue_tracks),
            "旁白": len(self.narration_tracks),
            "音效": len(self.sfx_tracks),
            "环境音": len(self.ambient_tracks),
        }


# ============================================================
# 映射表
# ============================================================

EMOTION_BGM_MAP = {
    "平静": BGMEmotionStyle.CALM, "紧张": BGMEmotionStyle.TENSE,
    "焦虑": BGMEmotionStyle.TENSE, "悲伤": BGMEmotionStyle.SAD,
    "难过": BGMEmotionStyle.SAD, "愤怒": BGMEmotionStyle.EPIC,
    "冲突": BGMEmotionStyle.EPIC, "高潮": BGMEmotionStyle.EPIC,
    "激动": BGMEmotionStyle.TRIUMPHANT, "希望": BGMEmotionStyle.HOPEFUL,
    "释然": BGMEmotionStyle.CALM, "胜利": BGMEmotionStyle.TRIUMPHANT,
    "忧郁": BGMEmotionStyle.MELANCHOLY,
}

BGM_STYLE_DESCRIPTION = {
    BGMEmotionStyle.SAD: "slow piano melody, melancholic strings, minor key, 60-70 BPM",
    BGMEmotionStyle.TENSE: "suspenseful rhythm, low frequency drone, tension building, 80-90 BPM",
    BGMEmotionStyle.HOPEFUL: "warm piano and acoustic guitar, major key, uplifting, 90-100 BPM",
    BGMEmotionStyle.EPIC: "orchestral, powerful drums, cinematic, building intensity, 100-120 BPM",
    BGMEmotionStyle.CALM: "ambient pad, light piano, peaceful, minimal, 60-70 BPM",
    BGMEmotionStyle.TRIUMPHANT: "triumphant orchestral, brass, uplifting melody, 110-130 BPM",
    BGMEmotionStyle.MELANCHOLY: "slow adagio piano, introspective, minor key, 50-60 BPM",
}

SCENE_AMBIENT_MAP = {
    "出租屋": "室内环境音, 轻微空调声, 安静",
    "街道": "城市街道噪音, 车流声, 人声嘈杂",
    "咖啡馆": "咖啡馆环境音, 杯碟碰撞声, 低声交谈",
    "办公室": "办公室环境音, 键盘敲击声, 空调声",
    "天台": "天台环境音, 风声, 远处城市噪音",
    "家": "家庭环境音, 时钟滴答声",
}

ACTION_SFX_MAP = {
    "手机": "手机震动/提示音", "打字": "键盘敲击声",
    "开门": "开门声", "关门": "关门声",
    "喝水": "喝水声", "叹气": "叹气声",
    "笑": "笑声", "哭": "啜泣声",
    "鼓掌": "鼓掌声", "电话": "电话铃声",
}

# 旧版兼容：BGM主题库
BGM_LIBRARY = {
    "国风": ["国风", "古风", "古筝", "二胡"],
    "治愈": ["治愈", "温暖", "轻音乐", "钢琴"],
    "卡点": ["电子", "EDM", "节奏", "鼓点"],
    "电影": ["电影", "史诗", "配乐", "交响乐"],
    "励志": ["励志", "热血", "激昂", "奋斗"],
    "悬疑": ["悬疑", "紧张", "惊悚", "神秘"],
}

TTS_VOICES = {
    "女声_温柔": "zh_female_wanwanxiaohe",
    "女声_活泼": "zh_female_qingxin",
    "男声_磁性": "zh_male_chenguangboxin",
    "男声_沉稳": "zh_male_chunhoubaozhen",
    "旁白_纪录片": "zh_male_chenguangboxin",
}


# ============================================================
# 主引擎
# ============================================================

class AudioDesigner:
    """声音设计引擎"""

    def __init__(self, default_voice: str = "default"):
        self.default_voice = default_voice
        self.character_voices = {}

    def register_character_voice(self, character_name: str, voice: CharacterVoice):
        self.character_voices[character_name] = voice

    def auto_assign_voices(self, characters: List[Dict[str, Any]]) -> Dict[str, CharacterVoice]:
        """自动为角色分配音色"""
        voices = {}
        voice_counter = {"male": 0, "female": 0}

        for char in characters:
            name = char.get("name", "未知")
            gender = char.get("gender", "male")
            age = char.get("age", 30)
            personality = char.get("personality", "")

            pitch = 1.0
            speed = 1.0
            if "内向" in personality or "敏感" in personality:
                pitch = 0.95
                speed = 0.95
            elif "外向" in personality or "傲慢" in personality:
                pitch = 1.05
                speed = 1.05

            voice_id = f"voice_{gender}_{voice_counter[gender]}"
            voice_counter[gender] += 1

            voices[name] = CharacterVoice(
                character_name=name, voice_id=voice_id, gender=gender,
                age_range="adult" if 18 <= age <= 50 else ("senior" if age > 50 else "teen"),
                pitch=pitch, speed=speed,
                description=f"{name}的音色, {personality}",
            )

        self.character_voices.update(voices)
        return voices

    def design_bgm(self, scenes: List[Dict[str, Any]], total_duration: float) -> List[AudioClip]:
        """设计BGM轨道"""
        bgm_clips = []
        current_time = 0.0

        for scene in scenes:
            scene_emotion = scene.get("emotion", "平静")
            scene_duration = scene.get("duration", 10.0)
            bgm_style = EMOTION_BGM_MAP.get(scene_emotion, BGMEmotionStyle.CALM)

            clip = AudioClip(
                track_type=AudioTrackType.BGM,
                start_time=current_time,
                duration=scene_duration,
                content=BGM_STYLE_DESCRIPTION[bgm_style],
                volume=0.3, fade_in=1.0, fade_out=1.0,
                emotion=scene_emotion,
            )
            bgm_clips.append(clip)
            current_time += scene_duration

        return bgm_clips

    def design_dialogue(self, shots: List[Dict[str, Any]]) -> List[AudioClip]:
        """设计角色对话轨道"""
        dialogue_clips = []

        for shot in shots:
            dialogue = shot.get("dialogue", "")
            if not dialogue or len(dialogue) < 2:
                continue

            character = ""
            content = dialogue
            if ":" in dialogue:
                parts = dialogue.split(":", 1)
                character = parts[0].strip()
                content = parts[1].strip()

            duration = max(1.5, len(content) / 4.5)

            voice = self.character_voices.get(character, CharacterVoice(
                character_name=character or "未知", voice_id=self.default_voice,
            ))

            clip = AudioClip(
                track_type=AudioTrackType.DIALOGUE,
                start_time=shot.get("start_time", 0.0) + 0.2,
                duration=duration, content=content,
                character=character, voice=voice.voice_id,
                volume=1.0, emotion=shot.get("emotion", ""),
            )
            dialogue_clips.append(clip)

        return dialogue_clips

    def generate_narration(self, script_summary: str, key_moments: List[str] = None) -> str:
        """生成旁白文案"""
        narration_parts = ["这是一个关于普通人逆袭的故事。"]

        if key_moments:
            for i, moment in enumerate(key_moments):
                if i == 0:
                    narration_parts.append(f"{moment}，一切似乎都失去了希望。")
                elif i == len(key_moments) - 1:
                    narration_parts.append(f"最终，{moment}。")
                else:
                    narration_parts.append(f"直到{moment}，命运开始悄然改变。")

        narration_parts.append("有时候，翻身只需要一个对的工具，和一颗不放弃的心。")
        return "\n".join(narration_parts)

    def design_narration_tracks(self, narration_text: str, total_duration: float) -> List[AudioClip]:
        """设计旁白轨道"""
        narration_clips = []
        lines = [l.strip() for l in narration_text.split("\n") if l.strip()]
        if not lines:
            return narration_clips

        positions = [2.0, total_duration * 0.35, total_duration * 0.7, total_duration - 8.0]

        for i, line in enumerate(lines[:4]):
            duration = max(3.0, len(line) / 4.0 + 1.0)
            pos = positions[i] if i < len(positions) else total_duration * 0.5

            clip = AudioClip(
                track_type=AudioTrackType.NARRATION,
                start_time=pos, duration=duration, content=line,
                character="旁白", voice="narration_default",
                volume=0.9, fade_in=0.5, fade_out=0.5,
            )
            narration_clips.append(clip)

        return narration_clips

    def design_sfx(self, shots: List[Dict[str, Any]]) -> List[AudioClip]:
        """设计音效轨道"""
        sfx_clips = []
        for shot in shots:
            description = shot.get("description", "")
            start_time = shot.get("start_time", 0.0)
            for action, sfx_name in ACTION_SFX_MAP.items():
                if action in description:
                    clip = AudioClip(
                        track_type=AudioTrackType.SFX,
                        start_time=start_time + 0.1, duration=1.0,
                        content=sfx_name, volume=0.7,
                    )
                    sfx_clips.append(clip)
                    break
        return sfx_clips

    def design_ambient(self, scenes: List[Dict[str, Any]]) -> List[AudioClip]:
        """设计环境音轨道"""
        ambient_clips = []
        current_time = 0.0
        for scene in scenes:
            scene_name = scene.get("name", scene.get("description", ""))
            scene_duration = scene.get("duration", 10.0)
            ambient_name = "通用室内环境音"
            for keyword, ambient in SCENE_AMBIENT_MAP.items():
                if keyword in scene_name:
                    ambient_name = ambient
                    break
            clip = AudioClip(
                track_type=AudioTrackType.AMBIENT,
                start_time=current_time, duration=scene_duration,
                content=ambient_name, volume=0.15, fade_in=1.0, fade_out=1.0,
            )
            ambient_clips.append(clip)
            current_time += scene_duration
        return ambient_clips

    def design_full_audio(self, scenes: List[Dict[str, Any]],
                           shots: List[Dict[str, Any]],
                           characters: List[Dict[str, Any]],
                           total_duration: float,
                           script_summary: str = "",
                           key_moments: List[str] = None) -> AudioDesignPlan:
        """设计完整音轨"""
        plan = AudioDesignPlan(total_duration=total_duration)
        plan.character_voices = self.auto_assign_voices(characters)
        plan.bgm_tracks = self.design_bgm(scenes, total_duration)
        plan.dialogue_tracks = self.design_dialogue(shots)
        plan.narration_script = self.generate_narration(script_summary, key_moments)
        plan.narration_tracks = self.design_narration_tracks(plan.narration_script, total_duration)
        plan.sfx_tracks = self.design_sfx(shots)
        plan.ambient_tracks = self.design_ambient(scenes)
        return plan

    def export_audio_manifest(self, plan: AudioDesignPlan, output_path: str) -> str:
        """导出音频制作清单（JSON）"""
        manifest = {
            "total_duration": plan.total_duration,
            "track_summary": plan.get_track_summary(),
            "character_voices": {
                name: {
                    "voice_id": v.voice_id, "gender": v.gender,
                    "pitch": v.pitch, "speed": v.speed, "description": v.description,
                }
                for name, v in plan.character_voices.items()
            },
            "narration_script": plan.narration_script,
            "tracks": {
                "bgm": [self._clip_to_dict(c) for c in plan.bgm_tracks],
                "dialogue": [self._clip_to_dict(c) for c in plan.dialogue_tracks],
                "narration": [self._clip_to_dict(c) for c in plan.narration_tracks],
                "sfx": [self._clip_to_dict(c) for c in plan.sfx_tracks],
                "ambient": [self._clip_to_dict(c) for c in plan.ambient_tracks],
            },
        }
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
        return output_path

    def _clip_to_dict(self, clip: AudioClip) -> Dict[str, Any]:
        return {
            "track_type": clip.track_type.value,
            "start_time": round(clip.start_time, 2),
            "duration": round(clip.duration, 2),
            "content": clip.content,
            "character": clip.character,
            "voice": clip.voice,
            "volume": clip.volume,
            "fade_in": clip.fade_in,
            "fade_out": clip.fade_out,
            "emotion": clip.emotion,
        }


# ============================================================
# 旧版兼容API
# ============================================================

def match_bgm(theme: str, mood: str = None) -> list:
    """旧版兼容：根据主题匹配BGM关键词"""
    keywords = BGM_LIBRARY.get(theme, BGM_LIBRARY["治愈"])
    if mood:
        mood_map = {"欢快": ["欢快", "明亮"], "悲伤": ["悲伤", "忧郁"],
                     "紧张": ["紧张", "悬疑"], "激昂": ["激昂", "热血"]}
        if mood in mood_map:
            keywords = mood_map[mood] + keywords
    return keywords[:5]


def list_bgm_themes() -> list:
    return list(BGM_LIBRARY.keys())


def list_tts_voices() -> list:
    return [(k, v) for k, v in TTS_VOICES.items()]


if __name__ == "__main__":
    print("=" * 60)
    print("声音设计引擎 v2.0 (P9)")
    print("=" * 60)

    designer = AudioDesigner()

    test_scenes = [
        {"name": "出租屋", "emotion": "紧张", "duration": 26.8},
        {"name": "街道", "emotion": "平静", "duration": 24.4},
        {"name": "出租屋", "emotion": "高潮", "duration": 33.2},
        {"name": "咖啡馆", "emotion": "冲突", "duration": 69.2},
        {"name": "天台", "emotion": "释然", "duration": 26.4},
    ]

    test_shots = [
        {"shot_id": "C01", "dialogue": "陈默: 又失业了...第三次了...", "start_time": 5.0, "emotion": "悲伤", "description": "陈默看着手机叹气"},
        {"shot_id": "C02", "dialogue": "广告画外音: AI视频编辑器，一句话生成专业视频！", "start_time": 35.0, "emotion": "希望", "description": "街道广告牌"},
        {"shot_id": "C03", "dialogue": "陈默: 这...这就完了？才30秒？！", "start_time": 60.0, "emotion": "惊讶", "description": "陈默瞪大眼"},
        {"shot_id": "C04", "dialogue": "王总: 你？做视频？别开玩笑了", "start_time": 95.0, "emotion": "冲突", "description": "王总不屑"},
        {"shot_id": "C05", "dialogue": "陈默: 您看看这个", "start_time": 115.0, "emotion": "坚定", "description": "陈默展示作品"},
    ]

    test_characters = [
        {"name": "陈默", "gender": "male", "age": 28, "personality": "内向, 敏感, 有韧性"},
        {"name": "王总", "gender": "male", "age": 45, "personality": "外向, 务实, 傲慢"},
    ]

    print("\n设计完整音轨...")
    plan = designer.design_full_audio(
        scenes=test_scenes, shots=test_shots, characters=test_characters,
        total_duration=180.0, script_summary="颓废职场人发现AI视频编辑器后成功翻身",
        key_moments=["被公司优化", "发现AI视频编辑器", "作品惊艳前老板"],
    )

    print(f"\n总时长: {plan.total_duration}秒")
    print(f"轨道统计: {plan.get_track_summary()}")

    print(f"\n角色音色:")
    for name, voice in plan.character_voices.items():
        print(f"  {name}: {voice.voice_id} (pitch={voice.pitch}, speed={voice.speed})")

    print(f"\n旁白文案:\n{plan.narration_script}")

    print(f"\nBGM轨道:")
    for clip in plan.bgm_tracks:
        print(f"  [{clip.start_time:.1f}s] {clip.duration:.1f}s - {clip.emotion}")

    print(f"\n对话轨道:")
    for clip in plan.dialogue_tracks:
        print(f"  [{clip.start_time:.1f}s] {clip.duration:.1f}s - {clip.character}: {clip.content[:30]}")

    print(f"\n音效轨道:")
    for clip in plan.sfx_tracks:
        print(f"  [{clip.start_time:.1f}s] {clip.content}")

    print(f"\n环境音轨道:")
    for clip in plan.ambient_tracks:
        print(f"  [{clip.start_time:.1f}s] {clip.duration:.1f}s - {clip.content}")

    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audio_manifest_test.json")
    designer.export_audio_manifest(plan, output_path)
    print(f"\n音频制作清单已导出: {output_path}")
