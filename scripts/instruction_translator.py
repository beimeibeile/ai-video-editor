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


# ============ 情绪→TTS参数映射 ============
EMOTION_TO_TTS = {
    "开心": {"pitch": 1.2, "speed": 1.1, "energy": 0.8, "voice_style": "活泼"},
    "委屈": {"pitch": 0.8, "speed": 0.9, "energy": 0.4, "voice_style": "委屈"},
    "愤怒": {"pitch": 1.3, "speed": 1.2, "energy": 1.0, "voice_style": "愤怒"},
    "惊恐": {"pitch": 1.4, "speed": 1.3, "energy": 0.9, "voice_style": "惊恐"},
    "得意": {"pitch": 1.1, "speed": 1.0, "energy": 0.7, "voice_style": "得意"},
    "平静": {"pitch": 1.0, "speed": 1.0, "energy": 0.5, "voice_style": "平静"},
    "惊讶": {"pitch": 1.3, "speed": 1.1, "energy": 0.8, "voice_style": "惊讶"},
    "害羞": {"pitch": 1.1, "speed": 0.9, "energy": 0.4, "voice_style": "害羞"},
}

# ============ 角色→音色映射 ============
CHARACTER_TO_VOICE = {
    "豆包": {"voice_id": "female_young", "base_pitch": 1.0, "base_speed": 1.0},
    "机器人": {"voice_id": "robot_male", "base_pitch": 0.8, "base_speed": 0.9},
    "女杀手": {"voice_id": "female_cold", "base_pitch": 0.9, "base_speed": 0.95},
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
class InstructionSequence:
    """指令序列（P25调度器的输入）"""
    project: Dict
    tts_instructions: List[TTSInstruction] = field(default_factory=list)
    keyframe_instructions: List[KeyframeInstruction] = field(default_factory=list)
    effect_instructions: List[EffectInstruction] = field(default_factory=list)
    audio_instructions: List[AudioInstruction] = field(default_factory=list)
    text_instructions: List[TextInstruction] = field(default_factory=list)
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

                        # 动作音效
                        for sfx in action_def.get("sfx", []):
                            self.sequence.audio_instructions.append(AudioInstruction(
                                type="sfx",
                                name=sfx,
                                start_time=shot_start,
                                duration=0.5,
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

                    # 台词→TTS
                    if dialogue:
                        voice_info = char_voice_map.get(char_name, CHARACTER_TO_VOICE.get("豆包", {}))
                        emotion_params = EMOTION_TO_TTS.get(emotion, EMOTION_TO_TTS["平静"])
                        tts_duration = min(len(dialogue) * 0.15 + 0.5, shot_duration)
                        self.sequence.tts_instructions.append(TTSInstruction(
                            character=char_name,
                            text=dialogue,
                            voice_id=voice_info.get("voice_id", "default"),
                            pitch=voice_info.get("base_pitch", 1.0) * emotion_params["pitch"],
                            speed=voice_info.get("base_speed", 1.0) * emotion_params["speed"],
                            energy=emotion_params["energy"],
                            voice_style=emotion_params["voice_style"],
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
                        volume=0.5,
                    ))

        # 3. 全局BGM
        bgm = parsed_script.get("audio_mix", {}).get("bgm", "通用BGM")
        total_duration = parsed_script.get("project", {}).get("duration", 20)
        self.sequence.audio_instructions.append(AudioInstruction(
            type="bgm",
            name=bgm,
            start_time=0,
            duration=total_duration,
            volume=0.3,
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
            "text_instructions": [asdict(t) for t in self.sequence.text_instructions],
            "summary": {
                "tts_count": len(self.sequence.tts_instructions),
                "keyframe_count": len(self.sequence.keyframe_instructions),
                "effect_count": len(self.sequence.effect_instructions),
                "audio_count": len(self.sequence.audio_instructions),
                "text_count": len(self.sequence.text_instructions),
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
        print(f"\n文字指令: {len(self.sequence.text_instructions)}条")
        for t in self.sequence.text_instructions:
            print(f"  [{t.start_time:.1f}s] {t.style}: \"{t.text[:20]}\"")
        print(f"{'='*60}\n")


if __name__ == "__main__":
    # 测试：用P23解析的豆包被打分镜做翻译
    parsed_path = r"C:\Users\Administrator\Videos\剪映导出\Doubao_Jianying-editor\director_engine_test\parsed_script.json"

    if os.path.exists(parsed_path):
        with open(parsed_path, "r", encoding="utf-8") as f:
            parsed_script = json.load(f)

        translator = InstructionTranslator()
        sequence = translator.translate(parsed_script)
        translator.print_summary()

        out_path = r"C:\Users\Administrator\Videos\剪映导出\Doubao_Jianying-editor\director_engine_test\instruction_sequence.json"
        translator.save_json(out_path)
    else:
        print(f"❌ 分镜文件不存在: {parsed_path}")
        print("请先运行 script_parser.py 生成分镜JSON")
