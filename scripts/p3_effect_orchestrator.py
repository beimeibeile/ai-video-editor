#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P3-2 AI智能特效编排引擎
输入：剧本节拍序列 + 视频分析结果 → 输出：特效/转场/动画指令序列（可解释）
基于P2-4情绪映射 + P2-5特效预设扩展为"情绪×场景×节奏"三维决策
"""
import os
import json
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# ============ 知识库：情绪×场景×节奏 三维特效映射 ============

# 风格动画偏好（用于重排序候选动画）
STYLE_ANIMATION_PREFERENCE = {
    "cinematic": {
        "intro_preferred": ["淡入", "渐显", "叠化", "放大"],
        "intro_avoid": ["弹入", "旋转进入", "滑入"],
        "outro_preferred": ["淡出", "渐隐", "叠化"],
        "outro_avoid": ["缩小消失", "旋转消失", "滑出"],
    },
    "douyin": {
        "intro_preferred": ["弹入", "放大", "滑入", "旋转进入", "渐显"],
        "intro_avoid": ["淡入"],
        "outro_preferred": ["缩小消失", "滑出", "旋转消失", "渐隐"],
        "outro_avoid": ["淡出"],
    },
    "vlog": {
        "intro_preferred": ["渐显", "淡入", "放大", "滑入"],
        "intro_avoid": ["旋转进入", "弹入"],
        "outro_preferred": ["渐隐", "淡出", "缩小"],
        "outro_avoid": ["旋转消失", "滑出"],
    },
    "product": {
        "intro_preferred": ["放大", "渐显", "淡入"],
        "intro_avoid": ["弹入", "旋转进入", "滑入"],
        "outro_preferred": ["渐隐", "淡出", "缩小"],
        "outro_avoid": ["旋转消失", "滑出"],
    },
}


def _reorder_by_style(candidates: list, style: str, anim_type: str) -> list:
    """根据风格偏好好重排序候选动画"""
    pref = STYLE_ANIMATION_PREFERENCE.get(style, {})
    preferred = pref.get(f"{anim_type}_preferred", [])
    avoid = pref.get(f"{anim_type}_avoid", [])

    def sort_key(name):
        if name in preferred:
            return (0, preferred.index(name))
        elif name in avoid:
            return (2, avoid.index(name))
        return (1, 0)

    return sorted(candidates, key=sort_key)


# 入场动画映射（情绪×节奏）
INTRO_ANIMATION_MAP = {
    ("happy", "fast"): ["放大", "弹入", "滑入"],
    ("happy", "medium"): ["渐显", "放大", "淡入"],
    ("happy", "slow"): ["渐显", "淡入"],
    ("sad", "fast"): ["缩小", "渐显"],
    ("sad", "medium"): ["渐显", "淡入", "缩小"],
    ("sad", "slow"): ["淡入", "渐显"],
    ("energetic", "fast"): ["放大", "弹入", "旋转进入", "滑入"],
    ("energetic", "medium"): ["放大", "弹入", "渐显"],
    ("energetic", "slow"): ["渐显", "放大"],
    ("calm", "fast"): ["渐显", "淡入"],
    ("calm", "medium"): ["渐显", "淡入", "放大"],
    ("calm", "slow"): ["淡入", "渐显"],
    ("tense", "fast"): ["缩小", "弹入", "闪入"],
    ("tense", "medium"): ["渐显", "缩小"],
    ("tense", "slow"): ["淡入", "渐显"],
    ("romantic", "fast"): ["渐显", "放大"],
    ("romantic", "medium"): ["渐显", "淡入", "放大"],
    ("romantic", "slow"): ["淡入", "渐显"],
    ("neutral", "medium"): ["渐显", "淡入", "放大"],
}

# 出场动画映射
OUTRO_ANIMATION_MAP = {
    ("happy", "fast"): ["缩小消失", "滑出", "旋转消失"],
    ("happy", "medium"): ["渐隐", "缩小消失"],
    ("happy", "slow"): ["渐隐", "淡出"],
    ("sad", "fast"): ["渐隐", "缩小"],
    ("sad", "medium"): ["渐隐", "淡出", "缩小"],
    ("sad", "slow"): ["淡出", "渐隐"],
    ("energetic", "fast"): ["缩小消失", "滑出", "旋转消失"],
    ("energetic", "medium"): ["缩小消失", "渐隐"],
    ("energetic", "slow"): ["渐隐", "淡出"],
    ("calm", "fast"): ["渐隐", "淡出"],
    ("calm", "medium"): ["渐隐", "淡出", "缩小"],
    ("calm", "slow"): ["淡出", "渐隐"],
    ("tense", "fast"): ["渐隐", "闪灭"],
    ("tense", "medium"): ["渐隐", "缩小"],
    ("tense", "slow"): ["淡出", "渐隐"],
    ("romantic", "fast"): ["渐隐", "淡出"],
    ("romantic", "medium"): ["渐隐", "淡出", "缩小"],
    ("romantic", "slow"): ["淡出", "渐隐"],
    ("neutral", "medium"): ["渐隐", "淡出", "缩小"],
}

# 场景特效映射（情绪×场景类型）
SCENE_EFFECT_MAP = {
    ("happy", "outdoor_sunny"): ["暖阳", "光晕"],
    ("happy", "general"): ["光斑", "光晕"],
    ("sad", "general"): ["下雨", "暗角"],
    ("sad", "indoor"): ["暗角", "朦胧"],
    ("energetic", "general"): ["震动", "闪白", "毛刺"],
    ("energetic", "high_contrast"): ["震动", "闪白"],
    ("calm", "general"): ["柔光", "朦胧"],
    ("calm", "outdoor_sunny"): ["柔光", "光晕"],
    ("tense", "general"): ["暗角", "抖动", "毛刺"],
    ("tense", "indoor_dark"): ["暗角", "抖动"],
    ("romantic", "general"): ["柔光", "光斑", "光晕"],
    ("romantic", "outdoor_sunny"): ["光晕", "光斑"],
    ("neutral", "general"): [],
}

# 滤镜映射（情绪×风格）
FILTER_MAP = {
    ("happy", "cinematic"): ["清新", "暖阳"],
    ("happy", "pop"): ["鲜艳", "清新"],
    ("happy", "vlog"): ["清新", "自然"],
    ("sad", "cinematic"): ["冷调", "电影感"],
    ("sad", "pop"): ["冷调", "灰度"],
    ("sad", "vlog"): ["冷调", "自然"],
    ("energetic", "cinematic"): ["高对比", "电影感"],
    ("energetic", "pop"): ["鲜艳", "高对比"],
    ("energetic", "vlog"): ["鲜艳", "清新"],
    ("calm", "cinematic"): ["柔光", "电影感"],
    ("calm", "pop"): ["自然", "柔光"],
    ("calm", "vlog"): ["自然", "清新"],
    ("tense", "cinematic"): ["暗调", "高对比"],
    ("tense", "pop"): ["冷调", "高对比"],
    ("tense", "vlog"): ["冷调", "暗调"],
    ("romantic", "cinematic"): ["暖调", "柔光"],
    ("romantic", "pop"): ["暖调", "鲜艳"],
    ("romantic", "vlog"): ["暖调", "柔光"],
    ("neutral", "cinematic"): ["电影感"],
    ("neutral", "pop"): ["自然"],
    ("neutral", "vlog"): ["自然"],
}

# 转场映射（前后情绪关系）
TRANSITION_MAP = {
    ("happy", "happy"): ["叠化", "闪白"],
    ("happy", "energetic"): ["闪白", "震动"],
    ("happy", "calm"): ["叠化", "淡入淡出"],
    ("sad", "sad"): ["叠化", "淡入淡出"],
    ("sad", "calm"): ["叠化", "淡入淡出"],
    ("sad", "tense"): ["闪黑", "叠化"],
    ("energetic", "energetic"): ["闪白", "震动", "快切"],
    ("energetic", "happy"): ["闪白", "叠化"],
    ("energetic", "calm"): ["叠化", "淡入淡出"],
    ("calm", "calm"): ["叠化", "淡入淡出"],
    ("calm", "happy"): ["叠化", "淡入"],
    ("calm", "energetic"): ["闪白", "叠化"],
    ("tense", "tense"): ["闪黑", "快切"],
    ("tense", "calm"): ["叠化", "淡入淡出"],
    ("romantic", "romantic"): ["叠化", "柔光过渡"],
    ("romantic", "happy"): ["叠化", "闪白"],
    ("neutral", "neutral"): ["叠化", "淡入淡出"],
}

# 禁忌规则库
FORBIDDEN_RULES = [
    {"condition": "emotion == 'sad' and effect in ['闪光', '闪白', '震动']",
     "reason": "悲伤场景不宜使用强烈刺激特效"},
    {"condition": "emotion == 'calm' and effect in ['震动', '毛刺', '闪白']",
     "reason": "平静场景不宜使用躁动特效"},
    {"condition": "pace == 'slow' and animation in ['弹入', '旋转进入']",
     "reason": "慢节奏不宜使用快速动画"},
    {"condition": "scene_type == 'portrait' and effect in ['暗角']",
     "reason": "人像场景慎用暗角（可能影响面部）"},
    {"condition": "duration < 1.0 and has_transition",
     "reason": "短于1秒的镜头不宜加转场"},
]

# 风格预设
STYLE_PRESETS = {
    "cinematic": {
        "name": "电影感",
        "intro_duration": 0.8,
        "outro_duration": 1.0,
        "transition_preference": ["叠化", "淡入淡出", "闪黑"],
        "filter_intensity": 70,
        "effect_intensity": 60,
        "max_concurrent_effects": 2,
    },
    "douyin": {
        "name": "抖音风",
        "intro_duration": 0.4,
        "outro_duration": 0.5,
        "transition_preference": ["闪白", "震动", "快切", "缩放"],
        "filter_intensity": 80,
        "effect_intensity": 80,
        "max_concurrent_effects": 3,
    },
    "vlog": {
        "name": "Vlog风",
        "intro_duration": 0.6,
        "outro_duration": 0.8,
        "transition_preference": ["叠化", "淡入淡出", "滑动"],
        "filter_intensity": 50,
        "effect_intensity": 50,
        "max_concurrent_effects": 2,
    },
    "product": {
        "name": "产品宣传片",
        "intro_duration": 1.0,
        "outro_duration": 1.2,
        "transition_preference": ["叠化", "淡入淡出", "缩放"],
        "filter_intensity": 60,
        "effect_intensity": 50,
        "max_concurrent_effects": 2,
    },
}


@dataclass
class EffectDecision:
    """单个特效决策"""
    segment_index: int
    decision_type: str  # intro / outro / scene_effect / filter / transition
    effect_name: str
    effect_category: str  # animation / scene_effect / filter / transition
    start: float
    duration: float
    params: Dict[str, Any] = field(default_factory=dict)
    reason: str = ""
    confidence: float = 0.0
    forbidden_checked: bool = True


@dataclass
class EffectPlan:
    """完整特效编排方案"""
    style: str
    total_segments: int
    decisions: List[EffectDecision] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)


class EffectOrchestrator:
    """AI智能特效编排引擎"""

    def __init__(self, style: str = "vlog"):
        self.style = style
        self.preset = STYLE_PRESETS.get(style, STYLE_PRESETS["vlog"])

    def orchestrate(self, segments: List[Dict[str, Any]],
                     video_analysis: Dict[str, Any] = None) -> EffectPlan:
        """
        为每个镜头生成特效决策

        Args:
            segments: 镜头序列 [{index, start, end, duration, emotion, scene_type, pace, intensity}]
            video_analysis: P3-1视频分析结果（可选，用于补充信息）

        Returns:
            完整特效编排方案
        """
        plan = EffectPlan(
            style=self.style,
            total_segments=len(segments),
        )

        for i, seg in enumerate(segments):
            emotion = seg.get("emotion", "neutral")
            scene_type = seg.get("scene_type", "general")
            pace = seg.get("pace", "medium")
            duration = seg.get("duration", 3.0)
            intensity = seg.get("intensity", 0.5)

            # 1. 入场动画
            intro = self._decide_intro(emotion, pace, duration, i)
            if intro:
                intro.segment_index = i
                plan.decisions.append(intro)

            # 2. 出场动画
            outro = self._decide_outro(emotion, pace, duration, i, len(segments))
            if outro:
                outro.segment_index = i
                plan.decisions.append(outro)

            # 3. 场景特效
            scene_effect = self._decide_scene_effect(emotion, scene_type, intensity, i)
            if scene_effect:
                scene_effect.segment_index = i
                plan.decisions.append(scene_effect)

            # 4. 滤镜
            filt = self._decide_filter(emotion, i)
            if filt:
                filt.segment_index = i
                plan.decisions.append(filt)

            # 5. 转场（与下一个镜头之间）
            if i < len(segments) - 1:
                next_emotion = segments[i + 1].get("emotion", "neutral")
                transition = self._decide_transition(emotion, next_emotion, duration, i)
                if transition:
                    transition.segment_index = i
                    plan.decisions.append(transition)

        # 生成摘要
        plan.summary = self._generate_summary(plan)
        return plan

    def _decide_intro(self, emotion: str, pace: str, duration: float,
                       seg_idx: int) -> Optional[EffectDecision]:
        """决定入场动画"""
        key = (emotion, pace)
        candidates = INTRO_ANIMATION_MAP.get(key, INTRO_ANIMATION_MAP.get(("neutral", "medium"), ["渐显"]))

        if not candidates:
            return None

        # 风格感知重排序
        candidates = _reorder_by_style(candidates, self.style, "intro")

        # 选择第一个候选（可后续改为基于历史偏好的选择）
        effect_name = candidates[0]
        intro_duration = min(self.preset["intro_duration"], duration * 0.3)

        return EffectDecision(
            segment_index=seg_idx,
            decision_type="intro",
            effect_name=effect_name,
            effect_category="animation",
            start=0,
            duration=intro_duration,
            params={"anim_type": "in", "anim_name": effect_name},
            reason=f"情绪={emotion}, 节奏={pace} → 入场动画'{effect_name}'",
            confidence=0.7,
        )

    def _decide_outro(self, emotion: str, pace: str, duration: float,
                       seg_idx: int, total_segs: int) -> Optional[EffectDecision]:
        """决定出场动画"""
        key = (emotion, pace)
        candidates = OUTRO_ANIMATION_MAP.get(key, OUTRO_ANIMATION_MAP.get(("neutral", "medium"), ["渐隐"]))

        if not candidates:
            return None

        # 风格感知重排序
        candidates = _reorder_by_style(candidates, self.style, "outro")

        effect_name = candidates[0]
        outro_duration = min(self.preset["outro_duration"], duration * 0.3)
        start = max(0, duration - outro_duration)

        # 最后一个镜头出场动画可以稍长
        if seg_idx == total_segs - 1:
            outro_duration = min(outro_duration * 1.5, duration * 0.5)
            start = max(0, duration - outro_duration)

        return EffectDecision(
            segment_index=seg_idx,
            decision_type="outro",
            effect_name=effect_name,
            effect_category="animation",
            start=start,
            duration=outro_duration,
            params={"anim_type": "out", "anim_name": effect_name},
            reason=f"情绪={emotion}, 节奏={pace} → 出场动画'{effect_name}'",
            confidence=0.7,
        )

    def _decide_scene_effect(self, emotion: str, scene_type: str,
                              intensity: float, seg_idx: int) -> Optional[EffectDecision]:
        """决定场景特效"""
        key = (emotion, scene_type)
        candidates = SCENE_EFFECT_MAP.get(key, [])

        if not candidates:
            return None

        # 高情绪强度才加场景特效
        if intensity < 0.4:
            return None

        effect_name = candidates[0]
        effect_duration = 2.0  # 特效默认持续2秒

        return EffectDecision(
            segment_index=seg_idx,
            decision_type="scene_effect",
            effect_name=effect_name,
            effect_category="scene_effect",
            start=0,
            duration=effect_duration,
            params={"intensity": int(self.preset["effect_intensity"] * intensity)},
            reason=f"情绪={emotion}, 场景={scene_type}, 强度={intensity:.1f} → 场景特效'{effect_name}'",
            confidence=0.6,
        )

    def _decide_filter(self, emotion: str, seg_idx: int) -> Optional[EffectDecision]:
        """决定滤镜"""
        key = (emotion, self.style)
        candidates = FILTER_MAP.get(key, FILTER_MAP.get(("neutral", self.style), ["自然"]))

        if not candidates:
            return None

        effect_name = candidates[0]

        return EffectDecision(
            segment_index=seg_idx,
            decision_type="filter",
            effect_name=effect_name,
            effect_category="filter",
            start=0,
            duration=999,  # 全片段
            params={"intensity": self.preset["filter_intensity"]},
            reason=f"情绪={emotion}, 风格={self.style} → 滤镜'{effect_name}'",
            confidence=0.65,
        )

    def _decide_transition(self, from_emotion: str, to_emotion: str,
                            duration: float, seg_idx: int) -> Optional[EffectDecision]:
        """决定转场"""
        # 短镜头不加转场
        if duration < 1.0:
            return None

        key = (from_emotion, to_emotion)
        candidates = TRANSITION_MAP.get(key, ["叠化"])

        # 风格偏好优先
        preferred = [t for t in self.preset["transition_preference"] if t in candidates]
        effect_name = preferred[0] if preferred else candidates[0]

        return EffectDecision(
            segment_index=seg_idx,
            decision_type="transition",
            effect_name=effect_name,
            effect_category="transition",
            start=duration - 0.3,
            duration=0.6,
            params={},
            reason=f"情绪变化 {from_emotion}→{to_emotion} → 转场'{effect_name}'",
            confidence=0.65,
        )

    def _generate_summary(self, plan: EffectPlan) -> Dict[str, Any]:
        """生成方案摘要"""
        type_count = {}
        for d in plan.decisions:
            type_count[d.decision_type] = type_count.get(d.decision_type, 0) + 1

        avg_confidence = sum(d.confidence for d in plan.decisions) / max(len(plan.decisions), 1)

        return {
            "style": self.style,
            "total_decisions": len(plan.decisions),
            "by_type": type_count,
            "avg_confidence": round(avg_confidence, 2),
            "intro_count": type_count.get("intro", 0),
            "outro_count": type_count.get("outro", 0),
            "scene_effect_count": type_count.get("scene_effect", 0),
            "filter_count": type_count.get("filter", 0),
            "transition_count": type_count.get("transition", 0),
        }

    def export_json(self, plan: EffectPlan, output_path: str):
        """导出方案为JSON"""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        data = {
            "style": plan.style,
            "total_segments": plan.total_segments,
            "summary": plan.summary,
            "decisions": [
                {
                    "segment_index": d.segment_index,
                    "decision_type": d.decision_type,
                    "effect_name": d.effect_name,
                    "effect_category": d.effect_category,
                    "start": d.start,
                    "duration": d.duration,
                    "params": d.params,
                    "reason": d.reason,
                    "confidence": d.confidence,
                }
                for d in plan.decisions
            ],
        }
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return output_path


def main():
    import argparse
    parser = argparse.ArgumentParser(description="AI智能特效编排引擎")
    parser.add_argument("--style", default="vlog",
                        choices=["cinematic", "douyin", "vlog", "product"],
                        help="风格预设")
    parser.add_argument("-o", "--output", help="输出JSON路径")
    parser.add_argument("--test", action="store_true", help="运行测试")
    args = parser.parse_args()

    if args.test:
        # 测试用镜头序列
        test_segments = [
            {"index": 0, "start": 0, "end": 3, "duration": 3, "emotion": "calm",
             "scene_type": "indoor", "pace": "slow", "intensity": 0.3},
            {"index": 1, "start": 3, "end": 6, "duration": 3, "emotion": "happy",
             "scene_type": "outdoor_sunny", "pace": "medium", "intensity": 0.7},
            {"index": 2, "start": 6, "end": 9, "duration": 3, "emotion": "energetic",
             "scene_type": "general", "pace": "fast", "intensity": 0.9},
            {"index": 3, "start": 9, "end": 12, "duration": 3, "emotion": "calm",
             "scene_type": "general", "pace": "slow", "intensity": 0.4},
        ]

        logging.basicConfig(level=logging.INFO, format="%(message)s")
        orchestrator = EffectOrchestrator(style=args.style)
        plan = orchestrator.orchestrate(test_segments)

        logger.info(f"=== 特效编排方案（风格: {args.style}）===")
        logger.info(f"镜头数: {plan.total_segments}")
        logger.info(f"决策总数: {plan.summary['total_decisions']}")
        logger.info(f"平均置信度: {plan.summary['avg_confidence']}")
        logger.info(f"  入场: {plan.summary['intro_count']} | 出场: {plan.summary['outro_count']} | "
              f"场景特效: {plan.summary['scene_effect_count']} | 滤镜: {plan.summary['filter_count']} | "
              f"转场: {plan.summary['transition_count']}")
        logger.info(f"\n=== 决策详情 ===")
        for d in plan.decisions:
            logger.info(f"  [镜头{d.segment_index}] {d.decision_type}: {d.effect_name} "
                  f"({d.start:.1f}-{d.start+d.duration:.1f}s) 置信度={d.confidence}")
            logger.info(f"    原因: {d.reason}")

        if args.output:
            path = orchestrator.export_json(plan, args.output)
            logger.info(f"\n方案已保存: {path}")
    else:
        logger.info("使用 --test 运行测试，或通过API调用 EffectOrchestrator")


if __name__ == "__main__":
    main()
