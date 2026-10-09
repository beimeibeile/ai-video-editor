#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P3-3 镜头语言决策引擎
输入：剧本分镜+情绪曲线 → 输出：运镜/景别/构图/节奏曲线+关键帧参数
关键帧参数可直接传入剪映工程（缩放/位移/旋转）
"""
import os
import json
import math
import logging
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# ============ 知识库 ============

# 情绪→运镜方式映射
CAMERA_MOVE_MAP = {
    "happy": ["push_in", "static", "pan"],
    "sad": ["static", "pull_out", "slow_pan"],
    "energetic": ["push_in", "handheld", "whip_pan", "dolly_zoom"],
    "excited": ["handheld", "whip_pan", "push_in", "rapid_zoom", "dolly_zoom"],
    "calm": ["static", "slow_pan", "slow_push"],
    "tense": ["handheld", "slow_push", "dutch_angle"],
    "romantic": ["slow_push", "orbit", "static"],
    "warm": ["slow_push", "static", "orbit", "slow_pan"],
    "neutral": ["static", "slow_push"],
}

# 情绪→景别映射
SHOT_SIZE_MAP = {
    "happy": ["medium", "close_up", "medium_close"],
    "sad": ["close_up", "medium_close", "medium"],
    "energetic": ["close_up", "medium", "wide"],
    "calm": ["medium", "wide", "medium_wide"],
    "tense": ["close_up", "extreme_close_up", "medium_close"],
    "romantic": ["medium_close", "close_up", "medium"],
    "neutral": ["medium", "medium_close", "wide"],
}

# 景别→缩放比例映射（剪映中1.0=原始大小）
SHOT_SIZE_SCALE = {
    "extreme_close_up": 2.5,
    "close_up": 1.8,
    "medium_close": 1.4,
    "medium": 1.0,
    "medium_wide": 0.85,
    "wide": 0.7,
    "extreme_wide": 0.5,
}

# 情绪→构图映射
COMPOSITION_MAP = {
    "happy": ["center", "rule_of_thirds"],
    "sad": ["rule_of_thirds", "center"],
    "energetic": ["center", "dutch", "rule_of_thirds"],
    "calm": ["rule_of_thirds", "symmetric", "center"],
    "tense": ["dutch", "rule_of_thirds", "off_center"],
    "romantic": ["rule_of_thirds", "symmetric", "center"],
    "neutral": ["center", "rule_of_thirds"],
}

# 运镜→关键帧参数映射
CAMERA_MOVE_KEYFRAMES = {
    "static": {
        "description": "固定镜头",
        "keyframes": [],
    },
    "push_in": {
        "description": "推镜头（缓慢放大）",
        "keyframes": [
            {"time": 0, "scale": 1.0},
            {"time": 1.0, "scale": 1.15},
        ],
    },
    "pull_out": {
        "description": "拉镜头（缓慢缩小）",
        "keyframes": [
            {"time": 0, "scale": 1.15},
            {"time": 1.0, "scale": 1.0},
        ],
    },
    "slow_push": {
        "description": "慢推（极缓慢放大）",
        "keyframes": [
            {"time": 0, "scale": 1.0},
            {"time": 1.0, "scale": 1.08},
        ],
    },
    "pan_left": {
        "description": "左摇",
        "keyframes": [
            {"time": 0, "x": 0.05},
            {"time": 1.0, "x": -0.05},
        ],
    },
    "pan_right": {
        "description": "右摇",
        "keyframes": [
            {"time": 0, "x": -0.05},
            {"time": 1.0, "x": 0.05},
        ],
    },
    "slow_pan": {
        "description": "慢摇",
        "keyframes": [
            {"time": 0, "x": 0.03},
            {"time": 1.0, "x": -0.03},
        ],
    },
    "handheld": {
        "description": "手持晃动（模拟手持效果）",
        "keyframes": [
            {"time": 0, "x": 0, "y": 0, "rotation": 0},
            {"time": 0.25, "x": 0.01, "y": -0.008, "rotation": 0.5},
            {"time": 0.5, "x": -0.008, "y": 0.01, "rotation": -0.3},
            {"time": 0.75, "x": 0.006, "y": -0.005, "rotation": 0.4},
            {"time": 1.0, "x": 0, "y": 0, "rotation": 0},
        ],
    },
    "dolly_zoom": {
        "description": "滑动变焦（眩晕效果）",
        "keyframes": [
            {"time": 0, "scale": 1.0, "x": 0},
            {"time": 0.5, "scale": 1.3, "x": -0.1},
            {"time": 1.0, "scale": 1.0, "x": 0},
        ],
    },
    "whip_pan": {
        "description": "甩摇（快速横摇）",
        "keyframes": [
            {"time": 0, "x": 0.1, "rotation": 0},
            {"time": 0.15, "x": -0.1, "rotation": -2},
            {"time": 0.3, "x": 0, "rotation": 0},
        ],
    },
    "orbit": {
        "description": "环绕（模拟环绕运镜）",
        "keyframes": [
            {"time": 0, "x": -0.05, "scale": 1.0},
            {"time": 0.5, "x": 0, "scale": 1.05},
            {"time": 1.0, "x": 0.05, "scale": 1.0},
        ],
    },
    "dutch_angle": {
        "description": "荷兰角（倾斜构图）",
        "keyframes": [
            {"time": 0, "rotation": -3},
            {"time": 1.0, "rotation": -3},
        ],
    },
    "rapid_zoom": {
        "description": "快速变焦（冲击感 zoom punch）",
        "keyframes": [
            {"time": 0, "scale": 1.0},
            {"time": 0.1, "scale": 1.5},
            {"time": 0.2, "scale": 1.3},
            {"time": 1.0, "scale": 1.3},
        ],
    },
}


@dataclass
class ShotDecision:
    """单个镜头决策"""
    shot_index: int
    start: float
    end: float
    duration: float
    camera_move: str
    shot_size: str
    composition: str
    pace: str  # slow/medium/fast
    emotion: str
    keyframes: List[Dict[str, Any]] = field(default_factory=list)
    scale: float = 1.0
    reason: str = ""
    confidence: float = 0.0


@dataclass
class CameraPlan:
    """完整镜头语言方案"""
    total_shots: int
    total_duration: float
    pace_curve: List[Dict[str, Any]] = field(default_factory=list)
    shots: List[ShotDecision] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)


class CameraDecisionEngine:
    """镜头语言决策引擎"""

    def __init__(self, style: str = "cinematic"):
        self.style = style

    def decide(self, shots: List[Dict[str, Any]]) -> CameraPlan:
        """
        为每个镜头生成运镜/景别/构图决策

        Args:
            shots: 镜头序列 [{index, start, end, duration, emotion, content_type, dialogue}]

        Returns:
            完整镜头语言方案
        """
        plan = CameraPlan(
            total_shots=len(shots),
            total_duration=max((s["end"] for s in shots), default=0),
        )

        # 1. 生成节奏曲线
        plan.pace_curve = self._generate_pace_curve(shots)

        # 2. 为每个镜头决策
        for i, shot in enumerate(shots):
            emotion = shot.get("emotion", "neutral")
            duration = shot.get("duration", 3.0)
            content_type = shot.get("content_type", "general")
            dialogue = shot.get("dialogue", "")

            # 获取该镜头的节奏
            pace = self._get_shot_pace(plan.pace_curve, shot["start"], duration)

            # 运镜决策
            camera_move = self._decide_camera_move(emotion, pace, content_type, i, len(shots))

            # 景别决策
            shot_size = self._decide_shot_size(emotion, content_type, dialogue, i)

            # 构图决策
            composition = self._decide_composition(emotion, content_type)

            # 生成关键帧
            keyframes, scale = self._generate_keyframes(camera_move, shot_size, duration)

            # 原因
            reason = (f"情绪={emotion}, 节奏={pace}, 内容={content_type} → "
                      f"运镜={camera_move}, 景别={shot_size}, 构图={composition}")

            plan.shots.append(ShotDecision(
                shot_index=i,
                start=shot["start"],
                end=shot["end"],
                duration=duration,
                camera_move=camera_move,
                shot_size=shot_size,
                composition=composition,
                pace=pace,
                emotion=emotion,
                keyframes=keyframes,
                scale=scale,
                reason=reason,
                confidence=0.65,
            ))

        # 摘要
        plan.summary = self._generate_summary(plan)
        return plan

    def _generate_pace_curve(self, shots: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """生成节奏曲线（基于三幕结构+情绪强度）"""
        if not shots:
            return []

        total_duration = max(s["end"] for s in shots)
        curve = []

        # 三幕结构节奏模板
        for shot in shots:
            progress = shot["start"] / max(total_duration, 1)
            emotion = shot.get("emotion", "neutral")
            intensity = shot.get("intensity", 0.5)

            # 基础节奏（三幕结构）
            if progress < 0.3:
                base_pace = "slow"  # 开场铺垫
            elif progress < 0.7:
                base_pace = "medium"  # 发展
            else:
                base_pace = "fast"  # 高潮/结尾

            # 情绪调节
            if emotion in ["energetic", "tense"]:
                base_pace = "fast"
            elif emotion in ["sad", "calm"]:
                base_pace = "slow"

            # 强度调节
            pace_value = {"slow": 0.3, "medium": 0.6, "fast": 0.9}[base_pace]
            pace_value = pace_value * 0.5 + intensity * 0.5

            if pace_value < 0.4:
                pace = "slow"
            elif pace_value < 0.7:
                pace = "medium"
            else:
                pace = "fast"

            curve.append({
                "shot_index": shot.get("index", len(curve)),
                "start": shot["start"],
                "end": shot["end"],
                "pace": pace,
                "pace_value": round(pace_value, 2),
                "emotion": emotion,
            })

        return curve

    def _get_shot_pace(self, curve: List[Dict[str, Any]],
                        start: float, duration: float) -> str:
        """获取镜头的节奏"""
        for point in curve:
            if point["start"] <= start < point["end"]:
                return point["pace"]
        return "medium"

    def _decide_camera_move(self, emotion: str, pace: str,
                             content_type: str, shot_idx: int,
                             total_shots: int) -> str:
        """决定运镜方式"""
        candidates = CAMERA_MOVE_MAP.get(emotion, ["static"])

        # 第一个和最后一个镜头用更稳定的运镜
        if shot_idx == 0 or shot_idx == total_shots - 1:
            stable = [c for c in candidates if c in ["static", "slow_push", "slow_pan"]]
            if stable:
                return stable[0]

        # 快节奏用更动感的运镜
        if pace == "fast":
            dynamic = [c for c in candidates if c in ["push_in", "handheld", "whip_pan", "dolly_zoom", "rapid_zoom"]]
            if dynamic:
                return dynamic[0]

        return candidates[0]

    def _decide_shot_size(self, emotion: str, content_type: str,
                           dialogue: str, shot_idx: int) -> str:
        """决定景别"""
        candidates = SHOT_SIZE_MAP.get(emotion, ["medium"])

        # 有对话时用中近景
        if dialogue and len(dialogue) > 5:
            dialogue_sizes = ["medium_close", "close_up", "medium"]
            for s in dialogue_sizes:
                if s in candidates:
                    return s
            return "medium_close"

        # 产品展示用中景
        if content_type == "product":
            return "medium"

        # 风景用全景
        if content_type == "landscape":
            return "wide"

        return candidates[0]

    def _decide_composition(self, emotion: str, content_type: str) -> str:
        """决定构图"""
        candidates = COMPOSITION_MAP.get(emotion, ["center"])

        # 产品用居中构图
        if content_type == "product":
            return "center"

        return candidates[0]

    def _generate_keyframes(self, camera_move: str, shot_size: str,
                             duration: float) -> Tuple[List[Dict[str, Any]], float]:
        """
        生成剪映关键帧参数

        Returns:
            (keyframes, base_scale)
            keyframes: [{time(相对0-1), scale, x, y, rotation}]
            base_scale: 基础缩放（景别）
        """
        base_scale = SHOT_SIZE_SCALE.get(shot_size, 1.0)
        move_template = CAMERA_MOVE_KEYFRAMES.get(camera_move, CAMERA_MOVE_KEYFRAMES["static"])

        # 将模板关键帧的时间从0-1映射到实际时长，并叠加景别缩放
        keyframes = []
        for kf in move_template["keyframes"]:
            actual_time = kf["time"] * duration
            scale = base_scale * kf.get("scale", 1.0)
            keyframe = {
                "time": round(actual_time, 3),
                "scale": round(scale, 3),
                "x": kf.get("x", 0),
                "y": kf.get("y", 0),
                "rotation": kf.get("rotation", 0),
            }
            keyframes.append(keyframe)

        return keyframes, base_scale

    def _generate_summary(self, plan: CameraPlan) -> Dict[str, Any]:
        """生成方案摘要"""
        move_count = {}
        size_count = {}
        for shot in plan.shots:
            move_count[shot.camera_move] = move_count.get(shot.camera_move, 0) + 1
            size_count[shot.shot_size] = size_count.get(shot.shot_size, 0) + 1

        return {
            "total_shots": plan.total_shots,
            "total_duration": round(plan.total_duration, 1),
            "camera_moves": move_count,
            "shot_sizes": size_count,
            "avg_confidence": round(sum(s.confidence for s in plan.shots) / max(len(plan.shots), 1), 2),
            "pace_curve_points": len(plan.pace_curve),
        }

    def export_json(self, plan: CameraPlan, output_path: str):
        """导出方案为JSON"""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        data = {
            "total_shots": plan.total_shots,
            "total_duration": plan.total_duration,
            "summary": plan.summary,
            "pace_curve": plan.pace_curve,
            "shots": [
                {
                    "shot_index": s.shot_index,
                    "start": s.start,
                    "end": s.end,
                    "duration": s.duration,
                    "camera_move": s.camera_move,
                    "shot_size": s.shot_size,
                    "composition": s.composition,
                    "pace": s.pace,
                    "emotion": s.emotion,
                    "scale": s.scale,
                    "keyframes": s.keyframes,
                    "reason": s.reason,
                    "confidence": s.confidence,
                }
                for s in plan.shots
            ],
        }
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return output_path


def main():
    import argparse
    parser = argparse.ArgumentParser(description="镜头语言决策引擎")
    parser.add_argument("--test", action="store_true", help="运行测试")
    parser.add_argument("-o", "--output", help="输出JSON路径")
    args = parser.parse_args()

    if args.test:
        # 测试用镜头序列（30秒视频，8个镜头）
        test_shots = [
            {"index": 0, "start": 0, "end": 4, "duration": 4, "emotion": "calm",
             "content_type": "landscape", "dialogue": "", "intensity": 0.3},
            {"index": 1, "start": 4, "end": 8, "duration": 4, "emotion": "happy",
             "content_type": "portrait", "dialogue": "大家好，欢迎来到今天的分享", "intensity": 0.6},
            {"index": 2, "start": 8, "end": 12, "duration": 4, "emotion": "energetic",
             "content_type": "product", "dialogue": "这款产品真的太棒了", "intensity": 0.9},
            {"index": 3, "start": 12, "end": 16, "duration": 4, "emotion": "energetic",
             "content_type": "general", "dialogue": "", "intensity": 0.85},
            {"index": 4, "start": 16, "end": 20, "duration": 4, "emotion": "tense",
             "content_type": "general", "dialogue": "但是等等", "intensity": 0.7},
            {"index": 5, "start": 20, "end": 24, "duration": 4, "emotion": "happy",
             "content_type": "product", "dialogue": "现在下单还有优惠", "intensity": 0.75},
            {"index": 6, "start": 24, "end": 27, "duration": 3, "emotion": "romantic",
             "content_type": "portrait", "dialogue": "", "intensity": 0.5},
            {"index": 7, "start": 27, "end": 30, "duration": 3, "emotion": "calm",
             "content_type": "landscape", "dialogue": "感谢观看", "intensity": 0.4},
        ]

        logging.basicConfig(level=logging.INFO, format="%(message)s")
        engine = CameraDecisionEngine(style="cinematic")
        plan = engine.decide(test_shots)

        logger.info(f"=== 镜头语言决策方案 ===")
        logger.info(f"镜头数: {plan.total_shots} | 总时长: {plan.total_duration}秒")
        logger.info(f"运镜分布: {plan.summary['camera_moves']}")
        logger.info(f"景别分布: {plan.summary['shot_sizes']}")
        logger.info(f"平均置信度: {plan.summary['avg_confidence']}")
        logger.info(f"\n=== 节奏曲线 ===")
        for p in plan.pace_curve:
            logger.info(f"  镜头{p['shot_index']}: {p['start']:.0f}-{p['end']:.0f}s "
                  f"节奏={p['pace']}({p['pace_value']}) 情绪={p['emotion']}")
        logger.info(f"\n=== 镜头决策 ===")
        for s in plan.shots:
            logger.info(f"  [镜头{s.shot_index}] {s.start:.0f}-{s.end:.0f}s "
                  f"运镜={s.camera_move} 景别={s.shot_size} 构图={s.composition} "
                  f"缩放={s.scale} 关键帧={len(s.keyframes)}个")
            if s.keyframes:
                for kf in s.keyframes[:3]:
                    logger.info(f"    t={kf['time']:.1f}s scale={kf['scale']:.2f} "
                          f"x={kf['x']:.3f} rot={kf['rotation']}")
                if len(s.keyframes) > 3:
                    logger.info(f"    ... 共{len(s.keyframes)}个关键帧")

        if args.output:
            path = engine.export_json(plan, args.output)
            logger.info(f"\n方案已保存: {path}")
    else:
        logger.info("使用 --test 运行测试")


if __name__ == "__main__":
    main()
