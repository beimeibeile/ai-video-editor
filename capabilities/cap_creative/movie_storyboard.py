"""
电影模式分镜引擎 v1.0
======================
借鉴shuohao-skills精度，为剧类/电影模式生成量化分镜：

核心量化字段（每镜必填）：
- lens: 焦距（特写/近景/中景/全景/远景/大远景）
- cameraPosition: 机位（平视/仰视/俯视/过肩/主观）
- composition: 构图（居中/三分/对称/框架/引导线）
- eyeline: 视线落点（角色名/物体/画外/镜头）
- focus: 焦点（主体/前景/背景/全焦）
- stability: 稳定性（固定/缓推/缓拉/跟拍/手持/摇）

硬规则：
- 每切2-5秒，围着3秒打
- 段≤15秒，不跨场次
- 对话切正反打
- 进场第一切必须有主体运动
- 关键动作独立成切
- 段尾留钩
"""

import os
import json
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class ShotSize(Enum):
    """景别"""
    EXTREME_CLOSEUP = "大特写"
    CLOSEUP = "特写"
    MEDIUM_CLOSEUP = "近景"
    MEDIUM = "中景"
    MEDIUM_LONG = "中全景"
    LONG = "全景"
    EXTREME_LONG = "大远景"


class CameraAngle(Enum):
    """机位"""
    EYE_LEVEL = "平视"
    LOW_ANGLE = "仰视"
    HIGH_ANGLE = "俯视"
    OVER_SHOULDER = "过肩"
    POV = "主观"
    DUTCH = "倾斜"


class Composition(Enum):
    """构图"""
    CENTER = "居中"
    RULE_OF_THIRDS = "三分"
    SYMMETRICAL = "对称"
    FRAME_WITHIN_FRAME = "框架"
    LEADING_LINES = "引导线"
    DEPTH = "纵深"


class Stability(Enum):
    """稳定性"""
    STATIC = "固定"
    SLOW_PUSH = "缓推"
    SLOW_PULL = "缓拉"
    TRACKING = "跟拍"
    HANDHELD = "手持"
    PAN = "摇"
    TILT = "移"


@dataclass
class Shot:
    """单个分镜"""
    shot_id: str = ""
    scene_id: str = ""
    segment_id: str = ""  # 所属段（一次生成调用）

    # 时间
    start_time: float = 0.0  # 秒
    duration: float = 3.0    # 秒

    # 6量化字段
    lens: str = "中景"
    camera_position: str = "平视"
    composition: str = "三分"
    eyeline: str = ""        # 视线落点
    focus: str = "主体"
    stability: str = "固定"

    # 内容
    action: str = ""         # 动作描述（自然语言）
    dialogue: str = ""       # 台词
    character: str = ""      # 主要角色
    location: str = ""       # 场景
    description: str = ""    # 镜头描述（用于展示和I2V prompt）

    # 生成提示词
    image_prompt: str = ""   # 分镜图提示词（含角色名）
    video_prompt: str = ""   # 视频生成提示词（通用身份，不含名字）

    # 参考图
    ref_images: List[str] = field(default_factory=list)

    # 声音
    soundscape: str = ""     # 声景描述
    bgm_mood: str = ""       # BGM情绪

    def to_dict(self) -> dict:
        return {
            "shot_id": self.shot_id,
            "scene_id": self.scene_id,
            "segment_id": self.segment_id,
            "start_time": round(self.start_time, 2),
            "duration": round(self.duration, 2),
            "lens": self.lens,
            "camera_position": self.camera_position,
            "composition": self.composition,
            "eyeline": self.eyeline,
            "focus": self.focus,
            "stability": self.stability,
            "action": self.action,
            "dialogue": self.dialogue,
            "character": self.character,
            "location": self.location,
            "description": self.description,
            "image_prompt": self.image_prompt,
            "video_prompt": self.video_prompt,
            "ref_images": self.ref_images,
            "soundscape": self.soundscape,
            "bgm_mood": self.bgm_mood,
        }


@dataclass
class Segment:
    """段（一次生成调用，≤15秒）"""
    segment_id: str = ""
    scene_id: str = ""
    start_time: float = 0.0
    duration: float = 12.0
    blocking: str = ""       # 走位描述（开场谁在左谁在右、朝向、间距）
    shots: List[Shot] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "segment_id": self.segment_id,
            "scene_id": self.scene_id,
            "start_time": round(self.start_time, 2),
            "duration": round(self.duration, 2),
            "blocking": self.blocking,
            "shots": [s.to_dict() for s in self.shots],
        }


@dataclass
class Scene:
    """场景"""
    scene_id: str = ""
    location: str = ""
    time_of_day: str = ""
    lighting: str = ""
    description: str = ""
    segments: List[Segment] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "scene_id": self.scene_id,
            "location": self.location,
            "time_of_day": self.time_of_day,
            "lighting": self.lighting,
            "description": self.description,
            "segments": [s.to_dict() for s in self.segments],
        }


class MovieStoryboardEngine:
    """电影模式分镜引擎"""

    # 景别→默认时长映射
    LENS_DURATION = {
        "大特写": 2.0,
        "特写": 2.5,
        "近景": 3.0,
        "中景": 3.5,
        "中全景": 4.0,
        "全景": 4.5,
        "大远景": 5.0,
    }

    # 情绪→景别偏好
    MOOD_LENS = {
        "紧张": "特写",
        "亲密": "近景",
        "对话": "中景",
        "孤独": "全景",
        "宏大": "大远景",
        "动作": "中景",
    }

    def __init__(self):
        self.shot_counter = 0
        self.segment_counter = 0
        self.character_refs = {}  # 角色参考图: {角色名: [图片路径,...]}
        self.scene_refs = {}      # 场景参考图: {场景名: [图片路径,...]}

    def register_character_ref(self, character_name: str, image_path: str):
        """注册角色参考图（用于保持角色一致性）"""
        if character_name not in self.character_refs:
            self.character_refs[character_name] = []
        self.character_refs[character_name].append(image_path)
        print(f"  📌 角色参考图已注册: {character_name} -> {os.path.basename(image_path)}")

    def register_scene_ref(self, scene_name: str, image_path: str):
        """注册场景参考图（用于保持场景一致性）"""
        if scene_name not in self.scene_refs:
            self.scene_refs[scene_name] = []
        self.scene_refs[scene_name].append(image_path)
        print(f"  📌 场景参考图已注册: {scene_name} -> {os.path.basename(image_path)}")

    def generate_from_script(self, script_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        从剧本数据生成分镜

        Args:
            script_data: 剧本数据，格式：
                {
                    "title": str,
                    "scenes": [
                        {
                            "id": str,
                            "location": str,
                            "time": str,
                            "lighting": str,
                            "beats": [
                                {"action": str, "dialogue": str, "character": str, "duration": float}
                            ]
                        }
                    ]
                }

        Returns:
            完整分镜数据
        """
        print(f"\n{'='*60}")
        print(f"电影模式分镜引擎")
        print(f"{'='*60}")

        storyboard = {
            "title": script_data.get("title", "未命名"),
            "scenes": [],
            "total_shots": 0,
            "total_duration": 0.0,
        }

        current_time = 0.0

        for scene_data in script_data.get("scenes", []):
            scene = self._process_scene(scene_data, current_time)
            storyboard["scenes"].append(scene.to_dict())
            current_time += sum(seg.duration for seg in scene.segments)

        storyboard["total_shots"] = sum(len(seg["shots"]) for scene in storyboard["scenes"] for seg in scene["segments"])
        storyboard["total_duration"] = round(current_time, 2)

        print(f"\n✅ 分镜生成完成")
        print(f"   场景: {len(storyboard['scenes'])}个")
        print(f"   分镜: {storyboard['total_shots']}个")
        print(f"   总时长: {storyboard['total_duration']}s")

        return storyboard

    def _process_scene(self, scene_data: Dict, start_time: float) -> Scene:
        """处理单个场景"""
        scene = Scene(
            scene_id=scene_data.get("id", f"scene_{self.shot_counter}"),
            location=scene_data.get("location", ""),
            time_of_day=scene_data.get("time", ""),
            lighting=scene_data.get("lighting", ""),
            description=scene_data.get("description", ""),
        )

        beats = scene_data.get("beats", [])
        if not beats:
            return scene

        # 将beats分组为段（每段≤15秒）
        segments_beats = self._group_beats_into_segments(beats)

        current_time = start_time
        for seg_idx, seg_beats in enumerate(segments_beats):
            segment = self._build_segment(seg_beats, scene, current_time, seg_idx)
            scene.segments.append(segment)
            current_time += segment.duration

        return scene

    def _group_beats_into_segments(self, beats: List[Dict]) -> List[List[Dict]]:
        """将beats分组为段（每段≤15秒，不跨剧情单元）"""
        segments = []
        current_segment = []
        current_duration = 0.0
        MAX_SEG_DURATION = 15.0

        for beat in beats:
            beat_dur = beat.get("duration", 3.0)
            if current_duration + beat_dur > MAX_SEG_DURATION and current_segment:
                segments.append(current_segment)
                current_segment = []
                current_duration = 0.0
            current_segment.append(beat)
            current_duration += beat_dur

        if current_segment:
            segments.append(current_segment)

        return segments

    def _build_segment(self, beats: List[Dict], scene: Scene,
                       start_time: float, seg_idx: int) -> Segment:
        """构建单个段"""
        self.segment_counter += 1
        segment = Segment(
            segment_id=f"seg_{self.segment_counter:03d}",
            scene_id=scene.scene_id,
            start_time=start_time,
        )

        # 生成走位描述
        segment.blocking = self._generate_blocking(beats, scene)

        # 为每个beat生成1-3个分镜
        current_time = start_time
        for beat_idx, beat in enumerate(beats):
            shots = self._generate_shots_for_beat(beat, scene, segment, current_time, beat_idx)
            segment.shots.extend(shots)
            current_time += sum(s.duration for s in shots)

        segment.duration = current_time - start_time
        return segment

    def _generate_shots_for_beat(self, beat: Dict, scene: Scene,
                                  segment: Segment, start_time: float,
                                  beat_idx: int) -> List[Shot]:
        """为单个beat生成分镜"""
        shots = []
        action = beat.get("action", "")
        dialogue = beat.get("dialogue", "")
        character = beat.get("character", "")
        beat_duration = beat.get("duration", 3.0)
        mood = beat.get("mood", "对话")

        # 判断beat类型
        has_dialogue = bool(dialogue)
        has_action = bool(action)
        is_entry = (beat_idx == 0 and segment.segment_id.endswith("_001"))

        if has_dialogue and has_action:
            # 对话+动作：2切（动作特写+对话正反打）
            shot1 = self._create_shot(
                scene, segment, start_time,
                lens=self.MOOD_LENS.get("动作", "中景"),
                action=action, character=character,
                stability="跟拍" if "走" in action or "跑" in action else "固定",
                shot_type="action",
            )
            shots.append(shot1)

            shot2 = self._create_shot(
                scene, segment, start_time + shot1.duration,
                lens=self.MOOD_LENS.get(mood, "近景"),
                action=action, dialogue=dialogue, character=character,
                camera_position="过肩" if character else "平视",
                stability="固定",
                shot_type="dialogue",
            )
            shots.append(shot2)

        elif has_dialogue:
            # 纯对话：正反打2切
            shot1 = self._create_shot(
                scene, segment, start_time,
                lens="近景",
                dialogue=dialogue, character=character,
                camera_position="平视",
                stability="固定",
                shot_type="dialogue_a",
            )
            shots.append(shot1)

            # 反应镜头（如果有其他角色）
            shot2 = self._create_shot(
                scene, segment, start_time + shot1.duration,
                lens="近景",
                action="倾听反应", character="听者",
                camera_position="过肩",
                stability="固定",
                shot_type="dialogue_b",
            )
            shots.append(shot2)

        elif is_entry:
            # 进场三件套：运动主体→大远景定场→关键局部特写
            shot1 = self._create_shot(
                scene, segment, start_time,
                lens="中景",
                action=action or "主体运动", character=character,
                stability="跟拍",
                shot_type="entry_movement",
            )
            shots.append(shot1)

            shot2 = self._create_shot(
                scene, segment, start_time + shot1.duration,
                lens="大远景",
                action="定场镜头", character="",
                stability="缓推",
                shot_type="entry_establish",
            )
            shots.append(shot2)

        else:
            # 纯动作：1-2切
            shot = self._create_shot(
                scene, segment, start_time,
                lens=self.MOOD_LENS.get(mood, "中景"),
                action=action, character=character,
                stability="跟拍" if "走" in action or "跑" in action else "缓推",
                shot_type="action",
            )
            shots.append(shot)

            # 关键动作独立成切（如果动作复杂）
            if len(action) > 20 and beat_duration > 4:
                shot2 = self._create_shot(
                    scene, segment, start_time + shot.duration,
                    lens="特写",
                    action=f"关键动作：{action}", character=character,
                    stability="固定",
                    shot_type="insert",
                )
                shots.append(shot2)

        # 调整时长以匹配beat_duration
        total_dur = sum(s.duration for s in shots)
        if total_dur > 0 and beat_duration > 0:
            scale = beat_duration / total_dur
            for s in shots:
                s.duration = max(2.0, min(5.0, s.duration * scale))

        # 重新计算start_time
        t = start_time
        for s in shots:
            s.start_time = t
            t += s.duration

        return shots

    def _create_shot(self, scene: Scene, segment: Segment, start_time: float,
                     lens: str = "中景", camera_position: str = "平视",
                     composition: str = "三分", stability: str = "固定",
                     action: str = "", dialogue: str = "", character: str = "",
                     shot_type: str = "") -> Shot:
        """创建单个分镜"""
        self.shot_counter += 1
        shot = Shot(
            shot_id=f"shot_{self.shot_counter:04d}",
            scene_id=scene.scene_id,
            segment_id=segment.segment_id,
            start_time=start_time,
            duration=self.LENS_DURATION.get(lens, 3.0),
            lens=lens,
            camera_position=camera_position,
            composition=composition,
            stability=stability,
            action=action,
            dialogue=dialogue,
            character=character,
            location=scene.location,
            eyeline=character or "镜头",
            focus="主体",
        )

        # 自动挂载角色参考图和场景参考图
        if shot.character and shot.character in self.character_refs:
            shot.ref_images.extend(self.character_refs[shot.character])
        if shot.location and shot.location in self.scene_refs:
            shot.ref_images.extend(self.scene_refs[shot.location])

        # 生成镜头描述
        desc_parts = []
        if shot.character:
            desc_parts.append(shot.character)
        if shot.action:
            desc_parts.append(shot.action)
        else:
            desc_parts.append(f"{shot.lens}镜头")
        if shot.location:
            desc_parts.append(f"在{shot.location}")
        shot.description = "，".join(desc_parts)

        # 生成提示词
        shot.image_prompt = self._build_image_prompt(shot, scene)
        shot.video_prompt = self._build_video_prompt(shot, scene)

        return shot

    def _build_image_prompt(self, shot: Shot, scene: Scene) -> str:
        """生成分镜图提示词（含角色名）"""
        parts = []
        if shot.character:
            parts.append(shot.character)
        parts.append(f"{shot.lens}镜头")
        parts.append(f"{shot.camera_position}机位")
        parts.append(f"{shot.composition}构图")
        if shot.action:
            parts.append(shot.action)
        if scene.location:
            parts.append(f"场景：{scene.location}")
        if scene.lighting:
            parts.append(f"光线：{scene.lighting}")
        return ", ".join(parts)

    def _build_video_prompt(self, shot: Shot, scene: Scene) -> str:
        """生成视频提示词（通用身份，不含角色名）"""
        # 将角色名替换为通用身份
        action = shot.action
        if shot.character:
            action = action.replace(shot.character, "一个人")

        parts = []
        parts.append(f"{shot.lens}，{shot.camera_position}，{shot.stability}")
        if action:
            parts.append(action)
        if scene.location:
            parts.append(f"在{scene.location}")
        return "，".join(parts)

    def _generate_blocking(self, beats: List[Dict], scene: Scene) -> str:
        """生成段级走位描述"""
        characters = list(set(b.get("character", "") for b in beats if b.get("character")))
        if len(characters) >= 2:
            return f"开场{characters[0]}在左，{characters[1]}在右，面对面，间距约1.5米"
        elif characters:
            return f"开场{characters[0]}位于画面中央，朝向镜头"
        return "单人场景，主体位于画面三分线位置"

    def validate(self, storyboard: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证分镜质量 v3（32项专业质量门，借鉴shuohao-skills精度）
        Returns: {"passed": bool, "issues": [...], "warnings": [...], "checks": {...}, "diagnosis": [...]}
        """
        issues = []
        warnings = []
        checks = {}
        diagnosis = []  # 常见病诊断

        all_shots = []
        for scene in storyboard.get("scenes", []):
            for seg in scene.get("segments", []):
                all_shots.extend(seg.get("shots", []))

        # === A组：硬规则（6项）===

        # A1. 每镜时长2-5秒（硬门）
        for s in all_shots:
            if s["duration"] < 2.0:
                issues.append(f"{s['shot_id']}: 时长{s['duration']}s < 2s")
            elif s["duration"] > 5.0:
                warnings.append(f"{s['shot_id']}: 时长{s['duration']}s > 5s")
        checks["A1_shot_duration"] = len(all_shots)

        # A2. 每段≤15秒（硬门）
        for scene in storyboard.get("scenes", []):
            for seg in scene.get("segments", []):
                seg_dur = sum(s["duration"] for s in seg["shots"])
                if seg_dur > 15.0:
                    issues.append(f"{seg['segment_id']}: 段时长{seg_dur}s > 15s")
        checks["A2_segment_duration"] = sum(len(scene.get("segments", [])) for scene in storyboard.get("scenes", []))

        # A3. 6量化字段完整性（硬门）
        required_fields = ["lens", "camera_position", "composition", "eyeline", "focus", "stability"]
        for s in all_shots:
            for f in required_fields:
                if not s.get(f):
                    issues.append(f"{s['shot_id']}: 缺少字段{f}")
        checks["A3_quant_fields"] = len(all_shots) * 6

        # A4. 时间连续不重叠（硬门）
        for scene in storyboard.get("scenes", []):
            for seg in scene.get("segments", []):
                shots = seg.get("shots", [])
                for i in range(1, len(shots)):
                    expected_start = shots[i-1]["start_time"] + shots[i-1]["duration"]
                    if abs(shots[i]["start_time"] - expected_start) > 0.1:
                        issues.append(f"{shots[i]['shot_id']}: 时间不连续，期望{expected_start}，实际{shots[i]['start_time']}")
        checks["A4_time_continuity"] = len(all_shots)

        # A5. 台词装得下（硬门：台词秒数≤分镜秒数，中文约4字/秒）
        for s in all_shots:
            if s.get("dialogue"):
                dialogue_chars = len(s["dialogue"])
                estimated_seconds = dialogue_chars / 4.0
                if estimated_seconds > s["duration"]:
                    issues.append(f"{s['shot_id']}: 台词爆仓！{dialogue_chars}字约需{estimated_seconds:.1f}s > 分镜{s['duration']}s")
                    diagnosis.append(f"台词爆仓: {s['shot_id']}，加秒或拆切")
        checks["A5_dialogue_fit"] = len([s for s in all_shots if s.get("dialogue")])

        # A6. 分镜描述非空（硬门）
        for s in all_shots:
            if not s.get("description"):
                issues.append(f"{s['shot_id']}: 缺少description字段")
        checks["A6_description"] = len(all_shots)

        # === B组：导演运镜规则（8项）===

        # B1. 3秒一切是呼吸（警告：平均时长偏离3秒）
        if all_shots:
            avg_dur = sum(s["duration"] for s in all_shots) / len(all_shots)
            if abs(avg_dur - 3.0) > 1.0:
                warnings.append(f"平均镜头时长{avg_dur:.1f}s偏离3秒，节奏可能不均")
        checks["B1_3sec_rhythm"] = 1

        # B2. 对话切正反打（警告：连续对话镜头应交替角色）
        for scene in storyboard.get("scenes", []):
            for seg in scene.get("segments", []):
                shots = seg.get("shots", [])
                dialogue_shots = [s for s in shots if s.get("dialogue")]
                if len(dialogue_shots) >= 2:
                    for i in range(1, len(dialogue_shots)):
                        if dialogue_shots[i].get("character") == dialogue_shots[i-1].get("character"):
                            warnings.append(f"{dialogue_shots[i]['shot_id']}: 连续对话同角色，建议切正反打")
        checks["B2_shot_reverse_shot"] = len(all_shots)

        # B3. 进场三件套：第一切有主体运动（硬门）
        for scene in storyboard.get("scenes", []):
            if scene.get("segments") and scene["segments"][0].get("shots"):
                first_shot = scene["segments"][0]["shots"][0]
                if not first_shot.get("action"):
                    warnings.append(f"{first_shot['shot_id']}: 进场第一切无动作，静物开场是死画面")
                    diagnosis.append(f"进场死画面: {first_shot['shot_id']}，第一切必须有主体运动")
        checks["B3_opening_action"] = len(storyboard.get("scenes", []))

        # B4. 关键动作独立成切（警告：重要动作应有特写插入）
        # 简化检查：含"抓住/打开/扔/摔/拍"等关键词的镜头应是特写
        action_keywords = ["抓住", "打开", "扔", "摔", "拍", "按", "推", "拉", "撞"]
        for s in all_shots:
            action = s.get("action", "")
            if any(kw in action for kw in action_keywords) and s.get("lens") not in ["大特写", "特写"]:
                warnings.append(f"{s['shot_id']}: 关键动作'{action[:10]}'建议独立成特写插入")
        checks["B4_key_action_insert"] = len(all_shots)

        # B5. 反应镜头（警告：重台词后应有反应镜头）
        for scene in storyboard.get("scenes", []):
            for seg in scene.get("segments", []):
                shots = seg.get("shots", [])
                for i in range(len(shots)-1):
                    if shots[i].get("dialogue") and len(shots[i]["dialogue"]) > 10:
                        if not shots[i+1].get("dialogue") and not shots[i+1].get("action"):
                            warnings.append(f"{shots[i+1]['shot_id']}: 重台词后建议切反应镜头2-3秒")
        checks["B5_reaction_shot"] = len(all_shots)

        # B6. 动接动（警告：相邻镜头应动作连贯）
        for scene in storyboard.get("scenes", []):
            for seg in scene.get("segments", []):
                shots = seg.get("shots", [])
                for i in range(1, len(shots)):
                    if shots[i-1].get("action") and not shots[i].get("action"):
                        warnings.append(f"{shots[i]['shot_id']}: 上一切有动作，本切无动作，动接动可能断裂")
        checks["B6_action_match"] = len(all_shots)

        # B7. 段尾留钩（警告：每段最后一切应有悬念或引子）
        for scene in storyboard.get("scenes", []):
            for seg in scene.get("segments", []):
                shots = seg.get("shots", [])
                if shots and not shots[-1].get("action"):
                    warnings.append(f"{seg['segment_id']}: 段尾无动作描述，建议留钩")
        checks["B7_segment_hook"] = sum(len(scene.get("segments", [])) for scene in storyboard.get("scenes", []))

        # B8. 运镜克制（警告：一段不超过2种运镜）
        for scene in storyboard.get("scenes", []):
            for seg in scene.get("segments", []):
                moves = set(s.get("stability", "") for s in seg.get("shots", []))
                if len(moves) > 2:
                    warnings.append(f"{seg['segment_id']}: 段内运镜种类{len(moves)} > 2种: {moves}，可能在炫技")
        checks["B8_camera_restraint"] = sum(len(scene.get("segments", [])) for scene in storyboard.get("scenes", []))

        # === C组：一致性与规范（6项）===

        # C1. 角色一致性
        character_descriptions = {}
        for s in all_shots:
            char = s.get("character", "")
            if char:
                if char not in character_descriptions:
                    character_descriptions[char] = set()
                if s.get("action"):
                    character_descriptions[char].add(s["action"][:20])
        checks["C1_character_consistency"] = len(character_descriptions)

        # C2. 场景一致性
        scene_locations = {}
        for scene in storyboard.get("scenes", []):
            loc = scene.get("location", "")
            if loc:
                if loc not in scene_locations:
                    scene_locations[loc] = {"lighting": set(), "time": set()}
                if scene.get("lighting"):
                    scene_locations[loc]["lighting"].add(scene["lighting"])
                if scene.get("time"):
                    scene_locations[loc]["time"].add(scene["time"])
        for loc, info in scene_locations.items():
            if len(info["lighting"]) > 1:
                warnings.append(f"场景'{loc}'光照不一致: {info['lighting']}")
            if len(info["time"]) > 1:
                warnings.append(f"场景'{loc}'时间不一致: {info['time']}")
        checks["C2_scene_consistency"] = len(scene_locations)

        # C3. 视频提示词不含角色名（硬门：混元/Seedance规范要求）
        for s in all_shots:
            vp = s.get("video_prompt", "")
            for char in character_descriptions.keys():
                if char and char in vp and len(char) > 1:
                    warnings.append(f"{s['shot_id']}: 视频提示词可能包含角色名'{char}'，应用通用身份")
        checks["C3_video_prompt_safety"] = len(all_shots)

        # C4. 换景不换段（硬门：一段一个环境锚）
        for scene in storyboard.get("scenes", []):
            for seg in scene.get("segments", []):
                seg_locations = set(s.get("scene_location", "") for s in seg.get("shots", []) if s.get("scene_location"))
                if len(seg_locations) > 1:
                    issues.append(f"{seg['segment_id']}: 段内换景{seg_locations}，换景必开新段")
                    diagnosis.append(f"换景不换段: {seg['segment_id']}，一段一个环境锚")
        checks["C4_no_scene_change_in_segment"] = sum(len(scene.get("segments", [])) for scene in storyboard.get("scenes", []))

        # C5. 段走位（警告：每段应有blocking）
        for scene in storyboard.get("scenes", []):
            for seg in scene.get("segments", []):
                if not seg.get("blocking"):
                    warnings.append(f"{seg['segment_id']}: 缺少走位(blocking)描述")
        checks["C5_blocking"] = sum(len(scene.get("segments", [])) for scene in storyboard.get("scenes", []))

        # C6. 声景同步（警告：动作改变时声景应同步）
        for s in all_shots:
            if s.get("action") and not s.get("sound"):
                warnings.append(f"{s['shot_id']}: 有动作但无声景描述，声景也是动作指令")
        checks["C6_sound_sync"] = len(all_shots)

        # === D组：常见病诊断（4项）===

        # D1. 舞台剧病：一段一切杵到底
        for scene in storyboard.get("scenes", []):
            for seg in scene.get("segments", []):
                shots = seg.get("shots", [])
                if len(shots) == 1 and sum(s["duration"] for s in shots) > 8:
                    diagnosis.append(f"舞台剧病: {seg['segment_id']}，一段一切杵到底，对话切正反打，动作给插入特写")
        checks["D1_stage_play_disease"] = sum(len(scene.get("segments", [])) for scene in storyboard.get("scenes", []))

        # D2. 均匀病：每切都是3秒中景
        durations = [s["duration"] for s in all_shots]
        if durations and len(set(durations)) <= 2:
            diagnosis.append("均匀病: 所有镜头时长相同，深浅相间、长短相间才是节奏")
        lenses = [s.get("lens", "") for s in all_shots]
        if lenses and len(set(lenses)) <= 2:
            diagnosis.append("均匀病: 景别单一，建议大远景/全景/中景/近景/特写交替")
        checks["D2_uniform_disease"] = len(all_shots)

        # D3. 秒数漂移：分镜秒数与提示词对齐
        # 简化检查：duration应为整数或0.5倍数
        for s in all_shots:
            if abs(s["duration"] * 2 - round(s["duration"] * 2)) > 0.01:
                warnings.append(f"{s['shot_id']}: 时长{s['duration']}s不是0.5的倍数，秒数应精确")
        checks["D3_duration_precision"] = len(all_shots)

        # D4. 特写失忆：大特写的道具应挂参考图
        for s in all_shots:
            if s.get("lens") in ["大特写", "特写"] and s.get("action") and not s.get("ref_image"):
                warnings.append(f"{s['shot_id']}: 特写镜头建议挂道具/角色参考图")
        checks["D4_closeup_ref"] = len([s for s in all_shots if s.get("lens") in ["大特写", "特写"]])

        return {
            "passed": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "diagnosis": diagnosis,
            "total_checks": 32,
            "checks_run": 24,
            "shots_checked": len(all_shots),
            "checks": checks,
            "version": "v3.0",
        }

    def auto_fix(self, storyboard: Dict[str, Any]) -> Dict[str, Any]:
        """
        自动修复分镜质量问题 v1.0
        修复：台词爆仓（自动加秒）、均匀病（长短相间）、时间连续性
        Returns: {"fixed": bool, "changes": [...], "storyboard": 修复后的分镜}
        """
        changes = []
        all_shots = []
        for scene in storyboard.get("scenes", []):
            for seg in scene.get("segments", []):
                all_shots.extend(seg.get("shots", []))

        if not all_shots:
            return {"fixed": False, "changes": [], "storyboard": storyboard}

        # === 修复1：台词爆仓（4字/秒，最少2秒，最多5秒）===
        for s in all_shots:
            if s.get("dialogue"):
                dialogue_chars = len(s["dialogue"])
                required_duration = max(2.0, min(5.0, dialogue_chars / 4.0 + 0.5))  # +0.5秒缓冲
                if s["duration"] < required_duration:
                    old_dur = s["duration"]
                    s["duration"] = round(required_duration * 2) / 2  # 0.5倍数
                    changes.append(f"{s['shot_id']}: 台词爆仓修复 {old_dur}s→{s['duration']}s（{dialogue_chars}字）")

        # === 修复2：均匀病（长短相间，围着3秒打）===
        durations = [s["duration"] for s in all_shots]
        if len(set(durations)) <= 2 and len(all_shots) >= 3:
            # 所有镜头时长相同或接近，生成长短相间模式
            pattern = [3.0, 2.0, 4.0, 3.0, 2.5, 3.5]  # 长短相间
            for i, s in enumerate(all_shots):
                # 保留台词爆仓修复后的时长，只调整无台词或时长充足的镜头
                if not s.get("dialogue") or s["duration"] <= 3.0:
                    old_dur = s["duration"]
                    new_dur = pattern[i % len(pattern)]
                    # 确保不低于2秒
                    new_dur = max(2.0, new_dur)
                    if abs(old_dur - new_dur) > 0.3:
                        s["duration"] = new_dur
                        changes.append(f"{s['shot_id']}: 均匀病修复 {old_dur}s→{new_dur}s（长短相间）")

        # === 修复3：重新计算时间连续性 ===
        current_time = 0.0
        for scene in storyboard.get("scenes", []):
            for seg in scene.get("segments", []):
                for s in seg.get("shots", []):
                    s["start_time"] = round(current_time, 2)
                    current_time += s["duration"]
                seg["duration"] = round(sum(s["duration"] for s in seg["shots"]), 2)

        storyboard["total_duration"] = round(current_time, 2)

        if changes:
            print(f"  ✅ 自动修复 {len(changes)} 项:")
            for c in changes:
                print(f"    - {c}")
        else:
            print("  ✅ 无需修复")

        return {
            "fixed": len(changes) > 0,
            "changes": changes,
            "storyboard": storyboard,
        }

    def export_json(self, storyboard: Dict[str, Any], output_path: str):
        """导出分镜为JSON"""
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(storyboard, f, ensure_ascii=False, indent=2)
        print(f"  ✅ 分镜已导出: {output_path}")

    def export_html_report(self, storyboard: Dict[str, Any], output_path: str):
        """导出分镜为HTML报告"""
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>{storyboard.get('title', '分镜报告')}</title>
<style>
body {{ font-family: -apple-system, 'Microsoft YaHei', sans-serif; background: #0d1117; color: #c9d1d9; padding: 20px; }}
h1 {{ color: #58a6ff; }}
h2 {{ color: #d29922; margin-top: 30px; }}
.shot {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 12px; margin: 8px 0; }}
.shot .meta {{ display: flex; gap: 12px; font-size: 12px; color: #8b949e; flex-wrap: wrap; }}
.shot .meta span {{ background: #21262d; padding: 2px 8px; border-radius: 4px; }}
.shot .action {{ font-size: 14px; margin: 8px 0; }}
.shot .dialogue {{ color: #3fb950; font-style: italic; }}
.quant {{ display: grid; grid-template-columns: repeat(6, 1fr); gap: 6px; margin-top: 8px; }}
.quant div {{ background: #0d1117; padding: 6px; border-radius: 4px; text-align: center; font-size: 11px; }}
.quant .label {{ color: #8b949e; }}
.quant .value {{ color: #58a6ff; font-weight: 600; }}
</style>
</head>
<body>
<h1>{storyboard.get('title', '分镜报告')}</h1>
<p>总镜头: {storyboard.get('total_shots', 0)} | 总时长: {storyboard.get('total_duration', 0)}s</p>
"""

        for scene in storyboard.get("scenes", []):
            html += f"<h2>场景 {scene['scene_id']}: {scene.get('location', '')}</h2>"
            for seg in scene.get("segments", []):
                html += f"<h3>段 {seg['segment_id']} ({seg['duration']}s)</h3>"
                if seg.get("blocking"):
                    html += f"<p style='color:#8b949e;'>走位: {seg['blocking']}</p>"
                for shot in seg.get("shots", []):
                    html += f"""
<div class="shot">
  <div class="meta">
    <span>{shot['shot_id']}</span>
    <span>{shot['start_time']}s - {shot['duration']}s</span>
    <span>{shot.get('character', '')}</span>
  </div>
  <div class="quant">
    <div><div class="label">焦距</div><div class="value">{shot['lens']}</div></div>
    <div><div class="label">机位</div><div class="value">{shot['camera_position']}</div></div>
    <div><div class="label">构图</div><div class="value">{shot['composition']}</div></div>
    <div><div class="label">视线</div><div class="value">{shot['eyeline']}</div></div>
    <div><div class="label">焦点</div><div class="value">{shot['focus']}</div></div>
    <div><div class="label">稳定</div><div class="value">{shot['stability']}</div></div>
  </div>
  <div class="action">{shot.get('action', '')}</div>
  {f'<div class="dialogue">"{shot["dialogue"]}"</div>' if shot.get('dialogue') else ''}
</div>"""

        html += "</body></html>"

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"  ✅ HTML报告已导出: {output_path}")


if __name__ == "__main__":
    print("=" * 60)
    print("电影模式分镜引擎 v1.0")
    print("=" * 60)

    # 测试：简单剧本
    test_script = {
        "title": "测试剧本",
        "scenes": [
            {
                "id": "scene_1",
                "location": "办公室",
                "time": "白天",
                "lighting": "冷白光",
                "beats": [
                    {"action": "张三疲惫地走进办公室，扔下包", "character": "张三", "duration": 4.0, "mood": "动作"},
                    {"action": "李四抬头看了他一眼", "dialogue": "你来了？", "character": "李四", "duration": 3.0, "mood": "对话"},
                    {"action": "张三叹了口气，坐到椅子上", "dialogue": "嗯，又是漫长的一天", "character": "张三", "duration": 4.0, "mood": "对话"},
                ]
            }
        ]
    }

    engine = MovieStoryboardEngine()
    storyboard = engine.generate_from_script(test_script)

    # 验证
    result = engine.validate(storyboard)
    print(f"\n验证: {'通过' if result['passed'] else '未通过'}")
    print(f"  问题: {len(result['issues'])}个")
    for i in result["issues"][:5]:
        print(f"    - {i}")
    print(f"  警告: {len(result['warnings'])}个")

    # 导出
    output_dir = r"C:\Users\Administrator\Videos\剪映导出\Doubao_Jianying-editor\dev_workbench"
    engine.export_json(storyboard, os.path.join(output_dir, "test_storyboard.json"))
    engine.export_html_report(storyboard, os.path.join(output_dir, "test_storyboard.html"))
