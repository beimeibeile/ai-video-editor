#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
特效组合智能编排器
基于情绪时间线自动生成特效指令序列，支持多情绪段落平滑过渡，
自动避免特效重叠和冲突，输出可直接用于jianying_executor的特效指令。

使用方式:
    from effect_composition_orchestrator import EffectCompositionOrchestrator
    orchestrator = EffectCompositionOrchestrator()
    effect_instructions = orchestrator.compose_from_emotion_timeline(
        emotion_timeline=[
            {"start": 0, "end": 5, "emotion": "舒缓", "intensity": 0.3},
            {"start": 5, "end": 10, "emotion": "激昂", "intensity": 0.8},
            {"start": 10, "end": 15, "emotion": "收束", "intensity": 0.4},
        ],
        duration=15,
        max_effects_per_segment=2,
    )
    # effect_instructions可直接传给jianying_executor.execute()
"""

import sys
import os
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# 添加skill路径
SKILL_ROOT = os.path.dirname(os.path.abspath(__file__))
if SKILL_ROOT not in sys.path:
    sys.path.insert(0, SKILL_ROOT)

from emotion_effect_mapper import EmotionEffectMapper, get_mapper


@dataclass
class EmotionSegment:
    """情绪段落"""
    start: float  # 开始时间（秒）
    end: float  # 结束时间（秒）
    emotion: str  # 情绪名称
    intensity: float = 0.5  # 情绪强度 0.0-1.0
    scene_type: str = "general"  # 场景类型


@dataclass
class EffectInstruction:
    """特效指令（与jianying_executor兼容）"""
    type: str  # 特效名称
    category: str  # "scene" / "filter"
    start_time: float  # 开始时间（秒）
    duration: float  # 持续时间（秒）
    target: str = "background"  # 目标：background / all / char_xxx
    params: Dict[str, Any] = field(default_factory=dict)
    intensity: float = 100.0  # 滤镜强度（0-100）

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "category": self.category,
            "start_time": self.start_time,
            "duration": self.duration,
            "target": self.target,
            "params": self.params,
            "intensity": self.intensity,
        }


class EffectCompositionOrchestrator:
    """特效组合智能编排器"""

    def __init__(self, mapper: EmotionEffectMapper = None):
        self.mapper = mapper or get_mapper()
        self.supported_emotions = self.mapper.list_emotions()

    def compose_from_emotion_timeline(
        self,
        emotion_timeline: List[Dict[str, Any]],
        duration: float,
        max_effects_per_segment: int = 2,
        include_filters: bool = True,
        avoid_overlap: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        根据情绪时间线生成特效指令序列

        Args:
            emotion_timeline: 情绪时间线，每个元素：
                {"start": 0, "end": 5, "emotion": "舒缓", "intensity": 0.3}
            duration: 视频总时长（秒）
            max_effects_per_segment: 每个段落最多特效数
            include_filters: 是否包含滤镜
            avoid_overlap: 是否避免特效轨道重叠

        Returns:
            特效指令列表，可直接传给jianying_executor.execute()
        """
        segments = self._parse_timeline(emotion_timeline, duration)
        instructions = []

        for seg in segments:
            seg_effects = self._compose_segment(
                seg, max_effects_per_segment, include_filters
            )
            instructions.extend(seg_effects)

        if avoid_overlap:
            instructions = self._resolve_overlaps(instructions)

        # 按开始时间排序
        instructions.sort(key=lambda x: x["start_time"])

        logger.info(
            f"特效编排完成: {len(segments)}个段落 → {len(instructions)}个特效指令"
        )
        return instructions

    def _parse_timeline(
        self, timeline: List[Dict[str, Any]], duration: float
    ) -> List[EmotionSegment]:
        """解析情绪时间线"""
        segments = []
        for item in timeline:
            emotion = item.get("emotion", "舒缓")
            if emotion not in self.supported_emotions:
                logger.warning(f"不支持的情绪 '{emotion}'，使用默认'舒缓'")
                emotion = "舒缓"

            seg = EmotionSegment(
                start=float(item.get("start", 0)),
                end=float(item.get("end", duration)),
                emotion=emotion,
                intensity=float(item.get("intensity", 0.5)),
                scene_type=item.get("scene_type", "general"),
            )
            segments.append(seg)

        # 按开始时间排序
        segments.sort(key=lambda x: x.start)
        return segments

    def _compose_segment(
        self,
        segment: EmotionSegment,
        max_effects: int,
        include_filters: bool,
    ) -> List[Dict[str, Any]]:
        """为单个情绪段落生成特效指令"""
        seg_duration = segment.end - segment.start
        if seg_duration <= 0:
            return []

        # 获取该情绪的特效推荐
        try:
            effects = self.mapper.get_effects_for_emotion(
                segment.emotion,
                intensity=segment.intensity,
                max_effects=max_effects,
                include_filters=include_filters,
            )
        except Exception as e:
            logger.warning(f"获取情绪特效失败: {e}")
            return []

        instructions = []
        scene_count = 0
        filter_count = 0
        max_filters = 1  # 每个段落最多1个滤镜

        for effect in effects:
            category = effect.get("category", "video_effect")
            effect_name = effect.get("name", "")
            params = effect.get("params", [])

            # 分别控制场景特效和滤镜数量
            if category == "filter":
                if filter_count >= max_filters:
                    continue
                filter_count += 1
            else:
                if scene_count >= max_effects:
                    continue
                scene_count += 1

            # 计算特效时长（段落时长的60-80%）
            effect_duration = min(seg_duration * 0.7, 5.0)
            effect_start = segment.start + (seg_duration - effect_duration) / 2

            if category == "filter":
                instr = EffectInstruction(
                    type=effect_name,
                    category="filter",
                    start_time=effect_start,
                    duration=effect_duration,
                    target="all",
                    intensity=80.0,
                )
            else:
                instr = EffectInstruction(
                    type=effect_name,
                    category="scene",
                    start_time=effect_start,
                    duration=effect_duration,
                    target="background",
                    params={"raw_params": params},
                )

            instructions.append(instr.to_dict())

        return instructions

    def _resolve_overlaps(
        self, instructions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        解决特效轨道重叠问题
        场景特效和滤镜分别在不同轨道，同类型特效不能重叠
        """
        scene_effects = [i for i in instructions if i["category"] == "scene"]
        filter_effects = [i for i in instructions if i["category"] == "filter"]

        # 分别解决重叠
        scene_effects = self._resolve_category_overlaps(scene_effects)
        filter_effects = self._resolve_category_overlaps(filter_effects)

        return scene_effects + filter_effects

    def _resolve_category_overlaps(
        self, instructions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """解决同一类别特效的重叠"""
        if not instructions:
            return []

        # 按开始时间排序
        instructions.sort(key=lambda x: x["start_time"])
        resolved = []

        for instr in instructions:
            overlaps = False
            for existing in resolved:
                # 检查是否重叠
                if (
                    instr["start_time"] < existing["start_time"] + existing["duration"]
                    and instr["start_time"] + instr["duration"] > existing["start_time"]
                ):
                    overlaps = True
                    # 缩短当前特效时长以避免重叠
                    gap = existing["start_time"] + existing["duration"] - instr["start_time"]
                    if gap > 0 and instr["duration"] > gap + 0.5:
                        instr["duration"] -= gap + 0.3
                        instr["start_time"] += gap + 0.3
                    else:
                        # 无法避免重叠，跳过此特效
                        instr = None
                    break

            if instr and instr["duration"] > 0.3:
                resolved.append(instr)

        return resolved

    def compose_for_scene(
        self,
        emotion: str,
        start_time: float,
        duration: float,
        intensity: float = 0.5,
        max_effects: int = 2,
    ) -> List[Dict[str, Any]]:
        """
        为单个场景生成特效指令

        Args:
            emotion: 情绪名称
            start_time: 开始时间（秒）
            duration: 持续时间（秒）
            intensity: 情绪强度 0.0-1.0
            max_effects: 最多特效数

        Returns:
            特效指令列表
        """
        timeline = [
            {"start": start_time, "end": start_time + duration, "emotion": emotion, "intensity": intensity}
        ]
        return self.compose_from_emotion_timeline(
            timeline, duration=start_time + duration, max_effects_per_segment=max_effects
        )

    def get_emotion_summary(self) -> Dict[str, Any]:
        """获取所有情绪的摘要信息"""
        summary = {}
        for emotion in self.supported_emotions:
            info = self.mapper.get_emotion_info(emotion)
            summary[emotion] = {
                "description": info["description"],
                "video_effect_count": info["video_effect_count"],
                "filter_count": info["filter_count"],
                "recommended_params": info["recommended_params"],
            }
        return summary


# 全局单例
_orchestrator = None


def get_orchestrator() -> EffectCompositionOrchestrator:
    """获取全局编排器单例"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = EffectCompositionOrchestrator()
    return _orchestrator


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    print("=== 特效组合智能编排器测试 ===")
    orchestrator = EffectCompositionOrchestrator()

    # 测试1：情绪摘要
    print("\n【支持的情绪】")
    summary = orchestrator.get_emotion_summary()
    for emotion, info in summary.items():
        print(f"  {emotion}: {info['description']} ({info['video_effect_count']}特效+{info['filter_count']}滤镜)")

    # 测试2：情绪时间线编排
    print("\n【情绪时间线编排测试】")
    timeline = [
        {"start": 0, "end": 5, "emotion": "舒缓", "intensity": 0.3},
        {"start": 5, "end": 10, "emotion": "激昂", "intensity": 0.8},
        {"start": 10, "end": 15, "emotion": "收束", "intensity": 0.4},
    ]
    instructions = orchestrator.compose_from_emotion_timeline(
        timeline, duration=15, max_effects_per_segment=2
    )

    print(f"生成 {len(instructions)} 个特效指令:")
    for i, instr in enumerate(instructions):
        print(
            f"  [{i+1}] {instr['type']} ({instr['category']}) "
            f"@{instr['start_time']:.1f}s 持续{instr['duration']:.1f}s "
            f"target={instr['target']}"
        )

    # 测试3：单场景编排
    print("\n【单场景编排测试】")
    scene_effects = orchestrator.compose_for_scene(
        "高潮", start_time=0, duration=8, intensity=0.9, max_effects=3
    )
    print(f"生成 {len(scene_effects)} 个特效指令:")
    for i, instr in enumerate(scene_effects):
        print(
            f"  [{i+1}] {instr['type']} ({instr['category']}) "
            f"@{instr['start_time']:.1f}s 持续{instr['duration']:.1f}s"
        )

    print("\n✅ 特效组合智能编排器测试完成")
