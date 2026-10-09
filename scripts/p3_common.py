#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P3统一数据接口层
定义所有P3模块共用的数据结构和转换函数，实现模块间无缝集成
"""
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
import json
import logging
logger = logging.getLogger(__name__)


@dataclass
class Segment:
    """统一镜头片段数据结构 - 所有P3模块的通用输入/输出"""
    index: int = 0
    start: float = 0.0
    end: float = 0.0
    duration: float = 0.0
    emotion: str = "neutral"       # calm/happy/excited/sad/warm/tense/neutral
    scene_type: str = "unknown"    # indoor/outdoor_sunny/action/closeup/landscape/portrait
    pace: str = "medium"           # slow/medium/fast
    intensity: float = 0.5         # 0.0-1.0 情绪强度
    content_type: str = "general"  # establishing/portrait/action/closeup/landscape/general
    dialogue: str = ""             # 台词/旁白文本
    # 视频分析结果填充
    brightness: float = 0.0
    contrast: float = 0.0
    motion_level: float = 0.0
    dominant_color: str = "#000000"
    color_temperature: str = "neutral"
    detected_effects: List[str] = field(default_factory=list)
    # 特效编排结果填充
    effect_decisions: List[Dict[str, Any]] = field(default_factory=list)
    # 镜头决策结果填充
    camera_move: str = "static"
    shot_size: str = "medium"
    composition: str = "center"
    keyframes: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PipelineResult:
    """端到端pipeline完整结果"""
    segments: List[Segment] = field(default_factory=list)
    video_analysis: Optional[Dict[str, Any]] = None
    effect_plan: Optional[Dict[str, Any]] = None
    camera_plan: Optional[Dict[str, Any]] = None
    music_plan: Optional[Dict[str, Any]] = None
    quality_report: Optional[Dict[str, Any]] = None
    jianying_instructions: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "segments": [s.to_dict() for s in self.segments],
            "video_analysis": self.video_analysis,
            "effect_plan": self.effect_plan,
            "camera_plan": self.camera_plan,
            "music_plan": self.music_plan,
            "quality_report": self.quality_report,
            "jianying_instructions": self.jianying_instructions,
        }

    def export_json(self, path: str):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)


# ============ 转换函数 ============

def video_analysis_to_segments(analysis_result) -> List[Segment]:
    """P3-1 VideoAnalysisResult → Segment列表"""
    segments = []
    for i, scene in enumerate(analysis_result.scenes):
        seg = Segment(
            index=i,
            start=scene.start,
            end=scene.end,
            duration=scene.duration,
            emotion=getattr(scene, 'emotion', 'neutral'),
            scene_type=getattr(scene, 'scene_type', 'unknown'),
            pace=infer_pace(scene),
            intensity=getattr(scene, 'emotion_confidence', 0.5),
            brightness=getattr(scene, 'avg_brightness', 0),
            contrast=getattr(scene, 'avg_contrast', 0),
            motion_level=getattr(scene, 'motion_level', 0),
            dominant_color=getattr(scene, 'dominant_color', '#000000'),
            color_temperature=getattr(scene, 'color_temperature', 'neutral'),
            detected_effects=getattr(analysis_result, 'detected_effects', []),
        )
        segments.append(seg)
    return segments


def infer_pace(scene) -> str:
    """从运动水平推断节奏"""
    motion = getattr(scene, 'motion_level', 0)
    if motion < 0.2:
        return "slow"
    elif motion < 0.5:
        return "medium"
    else:
        return "fast"


def segments_to_effect_orchestrator_input(segments: List[Segment]) -> List[Dict[str, Any]]:
    """Segment列表 → P3-2 EffectOrchestrator输入格式"""
    return [
        {
            "index": s.index,
            "start": s.start,
            "end": s.end,
            "duration": s.duration,
            "emotion": s.emotion,
            "scene_type": s.scene_type,
            "pace": s.pace,
            "intensity": s.intensity,
            "content_type": s.content_type,
            "dialogue": s.dialogue,
        }
        for s in segments
    ]


def segments_to_camera_decision_input(segments: List[Segment]) -> List[Dict[str, Any]]:
    """Segment列表 → P3-3 CameraDecisionEngine输入格式"""
    return [
        {
            "index": s.index,
            "start": s.start,
            "end": s.end,
            "duration": s.duration,
            "emotion": s.emotion,
            "content_type": s.content_type,
            "dialogue": s.dialogue,
            "intensity": s.intensity,
        }
        for s in segments
    ]


def merge_effect_plan_into_segments(segments: List[Segment], effect_plan) -> List[Segment]:
    """将P3-2特效决策合并回Segment"""
    for decision in effect_plan.decisions:
        idx = decision.segment_index
        if 0 <= idx < len(segments):
            segments[idx].effect_decisions.append({
                "type": decision.decision_type,
                "name": decision.effect_name,
                "category": decision.effect_category,
                "confidence": decision.confidence,
                "start": decision.start,
                "duration": decision.duration,
                "params": decision.params,
                "reason": decision.reason,
            })
    return segments


def merge_camera_plan_into_segments(segments: List[Segment], camera_plan) -> List[Segment]:
    """将P3-3镜头决策合并回Segment"""
    for shot in camera_plan.shots:
        idx = shot.shot_index
        if 0 <= idx < len(segments):
            segments[idx].camera_move = shot.camera_move
            segments[idx].shot_size = shot.shot_size
            segments[idx].composition = shot.composition
            segments[idx].keyframes = shot.keyframes or []
    return segments


def generate_jianying_instructions(segments: List[Segment], project_name: str = "p3_pipeline_output") -> Dict[str, Any]:
    """从完整Segment生成剪映工程构建指令"""
    instructions = {
        "project_name": project_name,
        "duration": sum(s.duration for s in segments),
        "tracks": [],
        "effects": [],
        "animations": [],
        "keyframes": [],
        "transitions": [],
    }

    for seg in segments:
        # 视频片段
        instructions["tracks"].append({
            "type": "video",
            "segment_index": seg.index,
            "start": seg.start,
            "duration": seg.duration,
            "shot_size": seg.shot_size,
            "composition": seg.composition,
        })

        # 特效决策
        for eff in seg.effect_decisions:
            if eff["type"] in ("intro", "outro", "group"):
                instructions["animations"].append({
                    "segment_index": seg.index,
                    "anim_type": eff["type"],
                    "anim_name": eff["name"],
                    "start": eff["start"],
                    "duration": eff["duration"],
                })
            elif eff["type"] == "filter":
                instructions["effects"].append({
                    "segment_index": seg.index,
                    "type": "filter",
                    "name": eff["name"],
                    "intensity": eff.get("params", {}).get("intensity", 50),
                })
            elif eff["type"] == "scene_effect":
                instructions["effects"].append({
                    "segment_index": seg.index,
                    "type": "scene_effect",
                    "name": eff["name"],
                })
            elif eff["type"] == "transition":
                instructions["transitions"].append({
                    "from_segment": seg.index,
                    "to_segment": seg.index + 1,
                    "name": eff["name"],
                    "duration": eff["duration"],
                })

        # 关键帧（运镜）
        for kf in seg.keyframes:
            instructions["keyframes"].append({
                "segment_index": seg.index,
                "time": kf.get("time", 0),
                "scale": kf.get("scale", 1.0),
                "x": kf.get("x", 0),
                "y": kf.get("y", 0),
                "rotation": kf.get("rotation", 0),
            })

    return instructions


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    # 自检
    logger.info("=== P3统一数据接口层自检 ===")
    test_segs = [
        Segment(index=0, start=0, end=4, duration=4, emotion="calm", pace="slow"),
        Segment(index=1, start=4, end=8, duration=4, emotion="happy", pace="medium"),
    ]
    logger.info(f"Segment创建: {len(test_segs)}个")
    eff_input = segments_to_effect_orchestrator_input(test_segs)
    logger.info(f"特效编排输入: {len(eff_input)}个片段")
    cam_input = segments_to_camera_decision_input(test_segs)
    logger.info(f"镜头决策输入: {len(cam_input)}个片段")
    instructions = generate_jianying_instructions(test_segs)
    logger.info(f"剪映指令: {len(instructions['tracks'])}轨道, {len(instructions['animations'])}动画")
    logger.info("✅ 统一数据接口层自检通过")
