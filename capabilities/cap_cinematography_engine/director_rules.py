"""
导演运镜规则引擎 v1.0
借鉴shuohao-skills的8条导演运镜规则，集成到镜头语言决策引擎

8条导演规则：
1. 3秒一切是短剧的呼吸 — 竖屏观众注意力粒度，深浅相间、长短相间
2. 对话切正反打 — 问话给问话人近景，答话切答话人近景
3. 进场三件套 — 运动主体→大远景定场→关键局部特写
4. 关键动作独立成切 — insert特写插入，是节奏的重音
5. 反应镜头是免费的戏 — 重台词后切听者的脸2-3秒
6. 动接动 — 上一切结尾的动势接下一切开头的动势
7. 段的最后一切留钩 — 悬念具象或下一段引子
8. 运镜克制 — 固定是默认，推给情绪、拉给收场、跟给移动
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional, Tuple


class DirectorRuleType(Enum):
    """导演规则类型"""
    RHYTHM_3SEC = "3秒一切"
    DIALOGUE_REVERSE = "对话正反打"
    OPENING_TRIPLE = "进场三件套"
    KEY_ACTION_INSERT = "关键动作独立成切"
    REACTION_SHOT = "反应镜头"
    ACTION_MATCH = "动接动"
    SEGMENT_HOOK = "段尾留钩"
    CAMERA_RESTRAINT = "运镜克制"


@dataclass
class DirectorRuleResult:
    """单条导演规则的应用结果"""
    rule_type: DirectorRuleType
    applied: bool
    description: str
    modifications: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class DirectorPlan:
    """导演规则整体方案"""
    rules_applied: List[DirectorRuleResult] = field(default_factory=list)
    shot_modifications: Dict[int, Dict[str, Any]] = field(default_factory=dict)
    inserted_shots: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def applied_count(self) -> int:
        return sum(1 for r in self.rules_applied if r.applied)

    @property
    def warning_count(self) -> int:
        return sum(len(r.warnings) for r in self.rules_applied)

    def summary(self) -> str:
        lines = ["=" * 60, "导演运镜规则应用报告", "=" * 60]
        for r in self.rules_applied:
            icon = "✅" if r.applied else "⏭️"
            lines.append(f"{icon} [{r.rule_type.value}] {r.description}")
            for w in r.warnings:
                lines.append(f"   ⚠️ {w}")
        lines.append(f"{'=' * 60}")
        lines.append(f"应用规则: {self.applied_count}/{len(self.rules_applied)} | "
                     f"警告: {self.warning_count} | 插入镜头: {len(self.inserted_shots)}")
        return "\n".join(lines)


class DirectorRulesEngine:
    """导演运镜规则引擎"""

    def __init__(self):
        self.rules = [
            self._rule_rhythm_3sec,
            self._rule_dialogue_reverse,
            self._rule_opening_triple,
            self._rule_key_action_insert,
            self._rule_reaction_shot,
            self._rule_action_match,
            self._rule_segment_hook,
            self._rule_camera_restraint,
        ]

    def apply_all(self, shots: List[Dict[str, Any]],
                  scene_description: str = "",
                  is_first_scene: bool = False,
                  is_last_scene: bool = False) -> DirectorPlan:
        """
        应用所有导演规则

        Args:
            shots: 镜头列表（会被直接修改）
            scene_description: 场景描述
            is_first_scene: 是否是第一个场景
            is_last_scene: 是否是最后一个场景

        Returns:
            DirectorPlan
        """
        plan = DirectorPlan()
        # 直接修改传入的shots，不创建拷贝（调用方需要知道这一点）
        for rule_func in self.rules:
            result = rule_func(shots, scene_description, is_first_scene, is_last_scene)
            plan.rules_applied.append(result)

        return plan

    # ──────────────────────────────────────────
    # 规则1: 3秒一切是短剧的呼吸
    # ──────────────────────────────────────────
    def _rule_rhythm_3sec(self, shots: List[Dict[str, Any]],
                           scene_desc: str = "",
                           is_first: bool = False,
                           is_last: bool = False) -> DirectorRuleResult:
        """3秒一切：竖屏观众注意力粒度，深浅相间、长短相间"""
        if not shots:
            return DirectorRuleResult(DirectorRuleType.RHYTHM_3SEC, False, "无镜头数据")

        warnings = []
        modifications = []

        # 检查时长分布
        durations = [s.get("duration", 3) for s in shots]
        avg = sum(durations) / len(durations)

        # 过于均匀警告
        if len(durations) >= 4:
            variance = sum((d - avg) ** 2 for d in durations) / len(durations)
            if variance < 0.3:
                warnings.append(f"镜头时长过于均匀（平均{avg:.1f}s，方差{variance:.2f}），建议深浅相间")

        # 过长镜头警告
        for i, d in enumerate(durations):
            if d > 8:
                warnings.append(f"镜头#{i}时长{d}s超过8秒，短剧建议≤6秒")

        # 应用：调整时长到3秒左右（保留情绪驱动的长短变化）
        for i, shot in enumerate(shots):
            if "duration" not in shot or shot.get("duration", 0) <= 0:
                shot["duration"] = 3.0
                modifications.append({"shot_index": i, "field": "duration", "value": 3.0})

        return DirectorRuleResult(
            DirectorRuleType.RHYTHM_3SEC,
            applied=True,
            description=f"时长控制：平均{avg:.1f}s，围绕3秒打",
            modifications=modifications,
            warnings=warnings
        )

    # ──────────────────────────────────────────
    # 规则2: 对话切正反打
    # ──────────────────────────────────────────
    def _rule_dialogue_reverse(self, shots: List[Dict[str, Any]],
                                scene_desc: str = "",
                                is_first: bool = False,
                                is_last: bool = False) -> DirectorRuleResult:
        """对话切正反打：问话给问话人近景，答话切答话人近景"""
        dialogue_shots = [(i, s) for i, s in enumerate(shots) if s.get("dialogue")]
        if len(dialogue_shots) < 2:
            return DirectorRuleResult(DirectorRuleType.DIALOGUE_REVERSE, False,
                                      "对话镜头少于2个，无需正反打")

        modifications = []
        warnings = []

        # 为连续对话镜头设置正反打
        for idx in range(len(dialogue_shots) - 1):
            i, shot_a = dialogue_shots[idx]
            j, shot_b = dialogue_shots[idx + 1]
            if j - i == 1:  # 连续对话镜头
                # A镜头：说话人视角
                if "shot_size" not in shot_a or shot_a["shot_size"] in ("全景", "中景"):
                    shot_a["shot_size"] = "近景"
                    modifications.append({"shot_index": i, "field": "shot_size", "value": "近景"})
                if "camera_angle" not in shot_a:
                    shot_a["camera_angle"] = "平视"
                    modifications.append({"shot_index": i, "field": "camera_angle", "value": "平视"})

                # B镜头：听者过肩（正反打）
                if "shot_size" not in shot_b or shot_b["shot_size"] in ("全景", "中景"):
                    shot_b["shot_size"] = "近景"
                    modifications.append({"shot_index": j, "field": "shot_size", "value": "近景"})
                if "camera_angle" not in shot_b:
                    shot_b["camera_angle"] = "过肩"
                    modifications.append({"shot_index": j, "field": "camera_angle", "value": "过肩"})

        return DirectorRuleResult(
            DirectorRuleType.DIALOGUE_REVERSE,
            applied=len(modifications) > 0,
            description=f"为{len(dialogue_shots)}个对话镜头设置正反打",
            modifications=modifications,
            warnings=warnings
        )

    # ──────────────────────────────────────────
    # 规则3: 进场三件套
    # ──────────────────────────────────────────
    def _rule_opening_triple(self, shots: List[Dict[str, Any]],
                              scene_desc: str = "",
                              is_first: bool = False,
                              is_last: bool = False) -> DirectorRuleResult:
        """进场三件套：运动主体→大远景定场→关键局部特写"""
        if not shots or not is_first:
            return DirectorRuleResult(DirectorRuleType.OPENING_TRIPLE, False,
                                      "非首场景，无需进场三件套")

        modifications = []
        warnings = []
        first_shot = shots[0]

        # 首镜头必须有主体运动
        has_movement = any(k in first_shot for k in ["movement", "action", "主体运动", "has_movement"])
        camera_move = first_shot.get("camera_move", "固定")

        if not has_movement and camera_move == "固定":
            warnings.append("首镜头无主体运动且固定机位，静物特写开场是死画面")
            # 建议：首镜头用跟拍或移动
            first_shot["camera_move"] = "跟拍"
            modifications.append({"shot_index": 0, "field": "camera_move", "value": "跟拍"})

        # 如果只有1个镜头，建议添加定场和特写
        if len(shots) == 1:
            warnings.append("首场景仅1个镜头，建议进场三件套：运动主体→大远景定场→关键局部特写")

        return DirectorRuleResult(
            DirectorRuleType.OPENING_TRIPLE,
            applied=len(modifications) > 0,
            description="进场三件套检查：运动主体→大远景定场→关键局部特写",
            modifications=modifications,
            warnings=warnings
        )

    # ──────────────────────────────────────────
    # 规则4: 关键动作独立成切
    # ──────────────────────────────────────────
    def _rule_key_action_insert(self, shots: List[Dict[str, Any]],
                                 scene_desc: str = "",
                                 is_first: bool = False,
                                 is_last: bool = False) -> DirectorRuleResult:
        """关键动作独立成切：重要动作应有insert特写插入，是节奏的重音"""
        key_actions = [(i, s) for i, s in enumerate(shots)
                        if s.get("is_key_action") or s.get("key_action")]
        if not key_actions:
            return DirectorRuleResult(DirectorRuleType.KEY_ACTION_INSERT, False,
                                      "未标记关键动作")

        modifications = []
        warnings = []

        for i, shot in key_actions:
            is_closeup = shot.get("shot_size", "") in ("特写", "近景", "大特写")
            if not is_closeup:
                warnings.append(f"镜头#{i}关键动作非特写，建议独立成切为insert特写")
                shot["shot_size"] = "特写"
                modifications.append({"shot_index": i, "field": "shot_size", "value": "特写"})
                if "duration" not in shot or shot.get("duration", 0) > 3:
                    shot["duration"] = 2.0
                    modifications.append({"shot_index": i, "field": "duration", "value": 2.0})

        return DirectorRuleResult(
            DirectorRuleType.KEY_ACTION_INSERT,
            applied=len(modifications) > 0,
            description=f"{len(key_actions)}个关键动作检查是否独立成切",
            modifications=modifications,
            warnings=warnings
        )

    # ──────────────────────────────────────────
    # 规则5: 反应镜头是免费的戏
    # ──────────────────────────────────────────
    def _rule_reaction_shot(self, shots: List[Dict[str, Any]],
                             scene_desc: str = "",
                             is_first: bool = False,
                             is_last: bool = False) -> DirectorRuleResult:
        """反应镜头：重台词后切听者的脸2-3秒，不用写词"""
        heavy_dialogue = [(i, s) for i, s in enumerate(shots)
                           if s.get("dialogue") and len(s.get("dialogue", "")) > 10]
        if not heavy_dialogue:
            return DirectorRuleResult(DirectorRuleType.REACTION_SHOT, False,
                                      "无重台词镜头")

        modifications = []
        warnings = []
        inserted = []

        for i, shot in heavy_dialogue:
            if i + 1 < len(shots):
                next_shot = shots[i + 1]
                is_reaction = (next_shot.get("is_reaction") or
                               next_shot.get("reaction") or
                               (not next_shot.get("dialogue") and
                                next_shot.get("shot_size") in ("特写", "近景")))
                if not is_reaction:
                    warnings.append(f"镜头#{i}重台词后无反应镜头，建议插入听者反应2-3秒")
                    # 标记建议插入
                    inserted.append({
                        "after_shot": i,
                        "type": "reaction",
                        "shot_size": "特写",
                        "duration": 2.5,
                        "camera_angle": "过肩",
                        "description": "听者反应镜头"
                    })
            else:
                warnings.append(f"镜头#{i}是最后一个镜头，重台词后无法插入反应镜头")

        return DirectorRuleResult(
            DirectorRuleType.REACTION_SHOT,
            applied=len(inserted) > 0,
            description=f"{len(heavy_dialogue)}处重台词检查反应镜头",
            modifications=modifications,
            warnings=warnings
        )

    # ──────────────────────────────────────────
    # 规则6: 动接动
    # ──────────────────────────────────────────
    def _rule_action_match(self, shots: List[Dict[str, Any]],
                            scene_desc: str = "",
                            is_first: bool = False,
                            is_last: bool = False) -> DirectorRuleResult:
        """动接动：上一切结尾的动势接下一切开头的动势"""
        if len(shots) < 2:
            return DirectorRuleResult(DirectorRuleType.ACTION_MATCH, False,
                                      "镜头少于2个，无需动接动检查")

        warnings = []
        # 简单检查：相邻镜头是否都有动作描述
        for i in range(len(shots) - 1):
            has_action_a = any(k in shots[i] for k in ["action", "movement", "description"])
            has_action_b = any(k in shots[i + 1] for k in ["action", "movement", "description"])
            if has_action_a and not has_action_b:
                warnings.append(f"镜头#{i}有动作但镜头#{i+1}无动作描述，建议动接动")

        return DirectorRuleResult(
            DirectorRuleType.ACTION_MATCH,
            applied=len(warnings) == 0,
            description="动接动检查：上一切结尾的动势接下一切开头的动势",
            warnings=warnings
        )

    # ──────────────────────────────────────────
    # 规则7: 段尾留钩
    # ──────────────────────────────────────────
    def _rule_segment_hook(self, shots: List[Dict[str, Any]],
                            scene_desc: str = "",
                            is_first: bool = False,
                            is_last: bool = False) -> DirectorRuleResult:
        """段尾留钩：每段最后一分镜应有悬念具象或下一段引子"""
        if not shots or is_last:
            return DirectorRuleResult(DirectorRuleType.SEGMENT_HOOK, False,
                                      "最后场景无需留钩")

        last_shot = shots[-1]
        has_hook = any(k in last_shot for k in ["hook", "suspense", "cliffhanger", "悬念", "引子", "transition_out"])

        modifications = []
        warnings = []

        if not has_hook:
            warnings.append("段尾镜头无钩子，建议设置悬念具象或下一段引子")
            last_shot["hook"] = True
            modifications.append({"shot_index": len(shots) - 1, "field": "hook", "value": True})

        return DirectorRuleResult(
            DirectorRuleType.SEGMENT_HOOK,
            applied=len(modifications) > 0,
            description="段尾留钩检查：悬念具象或下一段引子",
            modifications=modifications,
            warnings=warnings
        )

    # ──────────────────────────────────────────
    # 规则8: 运镜克制
    # ──────────────────────────────────────────
    def _rule_camera_restraint(self, shots: List[Dict[str, Any]],
                                 scene_desc: str = "",
                                 is_first: bool = False,
                                 is_last: bool = False) -> DirectorRuleResult:
        """运镜克制：固定是默认，推给情绪、拉给收场、跟给移动，一段超过两种运镜就是炫技"""
        if not shots:
            return DirectorRuleResult(DirectorRuleType.CAMERA_RESTRAINT, False,
                                      "无镜头数据")

        moves = set(s.get("camera_move", "固定") for s in shots)
        static_count = sum(1 for s in shots if s.get("camera_move", "固定") == "固定")
        static_ratio = static_count / len(shots)

        modifications = []
        warnings = []

        if len(moves) > 3:
            warnings.append(f"全片{len(moves)}种运镜，可能过于花哨（{', '.join(moves)}）")

        if static_ratio < 0.3:
            warnings.append(f"固定镜头仅{static_ratio:.0%}，运镜克制原则：固定是默认")

        # 应用：确保至少30%固定镜头
        if static_ratio < 0.3:
            target_static = int(len(shots) * 0.3)
            added = 0
            for i, shot in enumerate(shots):
                if added >= target_static:
                    break
                if shot.get("camera_move", "固定") != "固定":
                    # 只改非情绪高潮的镜头
                    emotion = shot.get("emotion", "")
                    if emotion not in ("高潮", "冲突"):
                        shot["camera_move"] = "固定"
                        modifications.append({"shot_index": i, "field": "camera_move", "value": "固定"})
                        added += 1

        return DirectorRuleResult(
            DirectorRuleType.CAMERA_RESTRAINT,
            applied=len(modifications) > 0,
            description=f"运镜克制：{len(moves)}种运镜，固定镜头{static_ratio:.0%}",
            modifications=modifications,
            warnings=warnings
        )


# 全局实例
_director_engine = DirectorRulesEngine()


def get_director_engine() -> DirectorRulesEngine:
    """获取全局导演规则引擎"""
    return _director_engine


def apply_director_rules(shots: List[Dict[str, Any]],
                          scene_description: str = "",
                          is_first_scene: bool = False,
                          is_last_scene: bool = False) -> DirectorPlan:
    """便捷函数：应用所有导演规则"""
    return _director_engine.apply_all(shots, scene_description, is_first_scene, is_last_scene)


if __name__ == "__main__":
    print("=" * 60)
    print("导演运镜规则引擎自测")
    print("=" * 60)

    # 测试数据
    test_shots = [
        {"description": "陈默坐在办公桌前，眼神空洞", "dialogue": "", "duration": 5},
        {"description": "老板走过来", "dialogue": "陈默，你这个月的业绩又是倒数第一", "duration": 4},
        {"description": "陈默低头", "dialogue": "我知道了", "duration": 3},
        {"description": "陈默回到家，瘫在沙发上", "dialogue": "", "duration": 4},
    ]

    plan = apply_director_rules(test_shots, "办公室场景", is_first_scene=True, is_last_scene=False)
    print(plan.summary())
