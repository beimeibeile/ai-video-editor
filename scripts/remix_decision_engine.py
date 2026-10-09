# -*- coding: utf-8 -*-
"""
二创编排决策引擎 v1.0
根据原视频分析结果，自动决策二创改编策略。

核心能力：
1. 改编模式决策（模板化/创意化/风格化）
2. 镜头保留/替换/重组决策
3. 素材替换建议
4. 节奏调整建议
5. 风格迁移建议
6. 风险评估（版权/相似度）

使用方式：
    from remix_decision_engine import RemixDecisionEngine
    engine = RemixDecisionEngine()
    decision = engine.decide(original_analysis, user_requirements)
    plan = engine.generate_plan(decision)
"""

import logging
logger = logging.getLogger(__name__)

import os
import json
from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class RemixDecision:
    """二创决策"""
    mode: str = "template"           # template/creative/stylized
    similarity_target: float = 0.6   # 目标相似度 0-1
    keep_original_shots: List[int] = field(default_factory=list)
    replace_shots: List[int] = field(default_factory=list)
    recombine_shots: List[Dict] = field(default_factory=list)
    style_transfer: Optional[str] = None
    pace_adjustment: str = "keep"    # speed_up/slow_down/keep
    material_replacements: List[Dict] = field(default_factory=list)
    risk_level: str = "low"          # low/medium/high
    risk_notes: List[str] = field(default_factory=list)


@dataclass
class RemixPlan:
    """二创执行计划"""
    title: str = ""
    mode: str = "template"
    total_shots: int = 0
    shots_to_keep: int = 0
    shots_to_replace: int = 0
    shots_to_recombine: int = 0
    estimated_duration: float = 0.0
    material_list: List[Dict] = field(default_factory=list)
    timeline: List[Dict] = field(default_factory=list)
    style_guide: Dict = field(default_factory=dict)
    risk_assessment: Dict = field(default_factory=dict)


class RemixDecisionEngine:
    """二创编排决策引擎"""

    def __init__(self):
        self.mode_rules = {
            "template": {
                "description": "模板化改编：保留原结构，替换素材",
                "similarity_range": (0.5, 0.8),
                "keep_ratio": 0.6,
                "replace_ratio": 0.4,
                "recombine_ratio": 0.0,
            },
            "creative": {
                "description": "创意化改编：保留核心，重组镜头",
                "similarity_range": (0.3, 0.6),
                "keep_ratio": 0.3,
                "replace_ratio": 0.4,
                "recombine_ratio": 0.3,
            },
            "stylized": {
                "description": "风格化改编：大幅改编，仅保留灵感",
                "similarity_range": (0.1, 0.4),
                "keep_ratio": 0.1,
                "replace_ratio": 0.6,
                "recombine_ratio": 0.3,
            },
        }

    def decide(self, original_analysis: Dict,
               user_requirements: Optional[Dict] = None) -> RemixDecision:
        """
        根据原视频分析和用户需求，生成二创决策

        Args:
            original_analysis: 原视频分析结果（来自video_reverse_analyzer）
            user_requirements: 用户需求（可选）

        Returns:
            二创决策
        """
        user_requirements = user_requirements or {}

        # 1. 确定改编模式
        mode = user_requirements.get("mode", self._auto_select_mode(original_analysis))

        # 2. 确定目标相似度
        similarity_target = user_requirements.get("similarity",
                                                  self._default_similarity(mode))

        # 3. 镜头决策
        shots = original_analysis.get("shots", [])
        total_shots = len(shots)

        mode_rule = self.mode_rules.get(mode, self.mode_rules["template"])
        keep_count = max(1, int(total_shots * mode_rule["keep_ratio"]))
        replace_count = int(total_shots * mode_rule["replace_ratio"])
        recombine_count = total_shots - keep_count - replace_count

        # 选择保留的镜头（保留关键镜头：开头、高潮、结尾）
        keep_shots = self._select_key_shots(shots, keep_count)
        replace_shots = [i for i in range(total_shots) if i not in keep_shots][:replace_count]
        recombine_shots = [i for i in range(total_shots)
                          if i not in keep_shots and i not in replace_shots]

        # 4. 风格迁移建议
        style_transfer = user_requirements.get("style")
        if not style_transfer:
            style_transfer = self._suggest_style(original_analysis)

        # 5. 节奏调整建议
        pace_adjustment = user_requirements.get("pace", self._suggest_pace(original_analysis))

        # 6. 素材替换建议
        material_replacements = self._suggest_material_replacements(shots, replace_shots)

        # 7. 风险评估
        risk_level, risk_notes = self._assess_risk(mode, similarity_target, keep_shots)

        return RemixDecision(
            mode=mode,
            similarity_target=similarity_target,
            keep_original_shots=keep_shots,
            replace_shots=replace_shots,
            recombine_shots=[{"index": i, "action": "recombine"} for i in recombine_shots],
            style_transfer=style_transfer,
            pace_adjustment=pace_adjustment,
            material_replacements=material_replacements,
            risk_level=risk_level,
            risk_notes=risk_notes,
        )

    def _auto_select_mode(self, analysis: Dict) -> str:
        """自动选择改编模式"""
        shot_count = len(analysis.get("shots", []))
        pace = analysis.get("editing_pace", "medium")

        # 镜头少、节奏慢 -> 模板化
        if shot_count < 5 or pace == "slow":
            return "template"
        # 镜头多、节奏快 -> 创意化
        elif shot_count > 15 or pace == "fast":
            return "creative"
        # 中等 -> 模板化
        else:
            return "template"

    def _default_similarity(self, mode: str) -> float:
        """默认目标相似度"""
        return sum(self.mode_rules[mode]["similarity_range"]) / 2

    def _select_key_shots(self, shots: List[Dict], count: int) -> List[int]:
        """选择关键镜头（开头、高潮、结尾）"""
        if not shots:
            return []

        total = len(shots)
        if count >= total:
            return list(range(total))

        # 总是保留第一个和最后一个
        key_shots = {0, total - 1}

        # 选择高潮镜头（亮度/对比度/饱和度最高的）
        scored = []
        for i, shot in enumerate(shots):
            score = (shot.get("brightness", 0.5) +
                    shot.get("contrast", 0.5) +
                    shot.get("saturation", 0.5))
            scored.append((i, score))
        scored.sort(key=lambda x: -x[1])

        for i, _ in scored:
            if len(key_shots) >= count:
                break
            key_shots.add(i)

        return sorted(key_shots)

    def _suggest_style(self, analysis: Dict) -> Optional[str]:
        """建议风格迁移"""
        avg_saturation = analysis.get("average_saturation", 0.5)
        avg_brightness = analysis.get("average_brightness", 0.5)

        if avg_saturation > 0.7:
            return "vibrant_enhance"
        elif avg_saturation < 0.3:
            return "muted_cinematic"
        elif avg_brightness < 0.3:
            return "brighten_warm"
        else:
            return None

    def _suggest_pace(self, analysis: Dict) -> str:
        """建议节奏调整"""
        avg_shot = analysis.get("average_shot_duration", 3.0)
        if avg_shot > 4.0:
            return "speed_up"
        elif avg_shot < 1.0:
            return "slow_down"
        else:
            return "keep"

    def _suggest_material_replacements(self, shots: List[Dict],
                                       replace_indices: List[int]) -> List[Dict]:
        """建议素材替换"""
        replacements = []
        for idx in replace_indices:
            if idx < len(shots):
                shot = shots[idx]
                replacements.append({
                    "shot_index": idx,
                    "original_duration": shot.get("duration", 3.0),
                    "suggested_type": "video" if shot.get("duration", 0) > 1.0 else "image",
                    "dominant_color": shot.get("dominant_color", "#000000"),
                    "note": f"替换第{idx+1}个镜头",
                })
        return replacements

    def _assess_risk(self, mode: str, similarity: float,
                     keep_shots: List[int]) -> tuple:
        """评估版权/相似度风险"""
        notes = []
        risk_level = "low"

        if similarity > 0.7:
            risk_level = "high"
            notes.append("目标相似度过高，存在版权风险")
        elif similarity > 0.5:
            risk_level = "medium"
            notes.append("目标相似度中等，建议增加原创元素")

        if len(keep_shots) > 10:
            notes.append("保留镜头较多，建议增加替换比例")

        if mode == "template":
            notes.append("模板化改编需注意素材替换的原创性")

        return risk_level, notes

    def generate_plan(self, decision: RemixDecision,
                      original_analysis: Dict,
                      output_title: str = "二创作品") -> RemixPlan:
        """
        生成二创执行计划

        Args:
            decision: 二创决策
            original_analysis: 原视频分析
            output_title: 输出标题

        Returns:
            二创执行计划
        """
        shots = original_analysis.get("shots", [])
        total_duration = original_analysis.get("duration", 0)

        # 构建时间线
        timeline = []
        for i, shot in enumerate(shots):
            if i in decision.keep_original_shots:
                action = "keep"
            elif i in decision.replace_shots:
                action = "replace"
            else:
                action = "recombine"

            timeline.append({
                "shot_index": i,
                "start_time": shot.get("start_time", 0),
                "duration": shot.get("duration", 3.0),
                "action": action,
                "camera_move": shot.get("camera_move", "unknown"),
                "dominant_color": shot.get("dominant_color", "#000000"),
            })

        # 素材清单
        material_list = []
        for rep in decision.material_replacements:
            material_list.append({
                "type": rep["suggested_type"],
                "duration": rep["original_duration"],
                "color_reference": rep["dominant_color"],
                "purpose": rep["note"],
            })

        # 风格指南
        style_guide = {
            "mode": decision.mode,
            "style_transfer": decision.style_transfer,
            "pace_adjustment": decision.pace_adjustment,
            "target_similarity": decision.similarity_target,
            "color_palette": original_analysis.get("color_palette", []),
        }

        # 风险评估
        risk_assessment = {
            "level": decision.risk_level,
            "notes": decision.risk_notes,
            "recommendations": [
                "保留镜头不超过总镜头的50%",
                "替换素材需确保版权合规",
                "建议添加原创片头/片尾",
            ],
        }

        return RemixPlan(
            title=output_title,
            mode=decision.mode,
            total_shots=len(shots),
            shots_to_keep=len(decision.keep_original_shots),
            shots_to_replace=len(decision.replace_shots),
            shots_to_recombine=len(decision.recombine_shots),
            estimated_duration=total_duration,
            material_list=material_list,
            timeline=timeline,
            style_guide=style_guide,
            risk_assessment=risk_assessment,
        )

    def print_decision(self, decision: RemixDecision):
        """打印决策摘要"""
        logger.info("\n" + "=" * 60)
        logger.info("二创编排决策")
        logger.info("=" * 60)
        logger.info(f"改编模式: {decision.mode} ({self.mode_rules[decision.mode]['description']})")
        logger.info(f"目标相似度: {decision.similarity_target:.0%}")
        logger.info(f"保留镜头: {len(decision.keep_original_shots)}个")
        logger.info(f"替换镜头: {len(decision.replace_shots)}个")
        logger.info(f"重组镜头: {len(decision.recombine_shots)}个")
        logger.info(f"风格迁移: {decision.style_transfer or '无'}")
        logger.info(f"节奏调整: {decision.pace_adjustment}")
        logger.info(f"风险等级: {decision.risk_level}")
        if decision.risk_notes:
            logger.info("风险提示:")
            for note in decision.risk_notes:
                logger.info(f"  - {note}")
        logger.info("=" * 60)

    def print_plan(self, plan: RemixPlan):
        """打印执行计划"""
        logger.info("\n" + "=" * 60)
        logger.info(f"二创执行计划: {plan.title}")
        logger.info("=" * 60)
        logger.info(f"总镜头数: {plan.total_shots}")
        logger.info(f"  保留: {plan.shots_to_keep}")
        logger.info(f"  替换: {plan.shots_to_replace}")
        logger.info(f"  重组: {plan.shots_to_recombine}")
        logger.info(f"预计时长: {plan.estimated_duration:.1f}秒")
        logger.info(f"\n需要素材: {len(plan.material_list)}个")
        for m in plan.material_list[:5]:
            logger.info(f"  - {m['type']} ({m['duration']:.1f}s) - {m['purpose']}")
        if len(plan.material_list) > 5:
            logger.info(f"  ... 还有{len(plan.material_list)-5}个")
        logger.info(f"\n风险等级: {plan.risk_assessment['level']}")
        logger.info("=" * 60)


def main():
    """命令行测试"""
    logger.info("二创编排决策引擎 v1.0 测试")
    logger.info("=" * 60)

    # 模拟原视频分析
    mock_analysis = {
        "duration": 20.0,
        "total_frames": 600,
        "fps": 30.0,
        "editing_pace": "medium",
        "average_shot_duration": 2.5,
        "average_brightness": 0.6,
        "average_contrast": 0.5,
        "average_saturation": 0.7,
        "color_palette": ["#FF6B6B", "#4ECDC4", "#45B7D1"],
        "shots": [
            {"index": i, "start_time": i * 2.5, "duration": 2.5,
             "brightness": 0.5 + i * 0.02, "contrast": 0.5,
             "saturation": 0.6, "dominant_color": "#FF6B6B",
             "camera_move": "固定"}
            for i in range(8)
        ],
    }

    engine = RemixDecisionEngine()

    # 测试1: 自动决策
    logger.info("\n测试1: 自动决策")
    decision = engine.decide(mock_analysis)
    engine.print_decision(decision)

    # 测试2: 生成计划
    logger.info("\n测试2: 生成执行计划")
    plan = engine.generate_plan(decision, mock_analysis, "测试二创作品")
    engine.print_plan(plan)

    # 测试3: 指定模式
    logger.info("\n测试3: 指定创意化模式")
    decision2 = engine.decide(mock_analysis, {"mode": "creative", "similarity": 0.4})
    engine.print_decision(decision2)

    logger.info("\n✅ 二创编排决策引擎验证通过")


if __name__ == "__main__":
    main()
