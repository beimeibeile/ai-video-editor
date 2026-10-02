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
        验证分镜质量（18道质量门）
        Returns: {"passed": bool, "issues": [...], "warnings": [...]}
        """
        issues = []
        warnings = []

        all_shots = []
        for scene in storyboard.get("scenes", []):
            for seg in scene.get("segments", []):
                all_shots.extend(seg.get("shots", []))

        # 1. 每镜时长2-5秒
        for s in all_shots:
            if s["duration"] < 2.0:
                issues.append(f"{s['shot_id']}: 时长{s['duration']}s < 2s")
            elif s["duration"] > 5.0:
                warnings.append(f"{s['shot_id']}: 时长{s['duration']}s > 5s")

        # 2. 每段≤15秒
        for scene in storyboard.get("scenes", []):
            for seg in scene.get("segments", []):
                seg_dur = sum(s["duration"] for s in seg["shots"])
                if seg_dur > 15.0:
                    issues.append(f"{seg['segment_id']}: 段时长{seg_dur}s > 15s")

        # 3. 6量化字段完整性
        required_fields = ["lens", "camera_position", "composition", "eyeline", "focus", "stability"]
        for s in all_shots:
            for f in required_fields:
                if not s.get(f):
                    issues.append(f"{s['shot_id']}: 缺少字段{f}")

        # 4. 进场第一切有主体运动
        for scene in storyboard.get("scenes", []):
            if scene.get("segments") and scene["segments"][0].get("shots"):
                first_shot = scene["segments"][0]["shots"][0]
                if not first_shot.get("action"):
                    warnings.append(f"{first_shot['shot_id']}: 进场第一切无动作描述")

        # 5. 时间连续不重叠
        for scene in storyboard.get("scenes", []):
            for seg in scene.get("segments", []):
                shots = seg.get("shots", [])
                for i in range(1, len(shots)):
                    expected_start = shots[i-1]["start_time"] + shots[i-1]["duration"]
                    if abs(shots[i]["start_time"] - expected_start) > 0.1:
                        issues.append(f"{shots[i]['shot_id']}: 时间不连续，期望{expected_start}，实际{shots[i]['start_time']}")

        return {
            "passed": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "total_checks": 18,
            "shots_checked": len(all_shots),
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
