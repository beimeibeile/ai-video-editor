"""
二创编排决策引擎 v1.0
建立模板化/创意化/风格化三种改编模式的决策逻辑

根据原视频特征和用户需求，自动选择最佳改编模式并生成编排方案。

使用方式：
    from remix_decision_engine import RemixDecisionEngine
    engine = RemixDecisionEngine()
    decision = engine.decide(original_features, user_preferences)
    print(decision["mode"])  # 改编模式
    print(decision["plan"])  # 编排方案
"""
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import json


@dataclass
class OriginalFeatures:
    """原视频特征"""
    duration: float = 0.0  # 时长（秒）
    shot_count: int = 0  # 镜头数
    has_dialogue: bool = False  # 是否有对白
    has_bgm: bool = True  # 是否有BGM
    bgm_segments: int = 0  # BGM段落数
    emotion_curve: List[Dict] = field(default_factory=list)  # 情绪曲线
    camera_moves: List[str] = field(default_factory=list)  # 运镜类型
    effects: List[str] = field(default_factory=list)  # 特效类型
    complexity: str = "medium"  # 复杂度 low/medium/high
    genre: str = "general"  # 类型


@dataclass
class UserPreferences:
    """用户偏好"""
    target_duration: float = 0.0  # 目标时长（0=保持原长）
    style: str = "auto"  # 目标风格 auto/epic/warm/fun/minimal
    emotion_intensity: float = 0.5  # 情绪强度 0.0-1.0
    preserve_story: bool = True  # 保留原故事线
    add_effects: bool = True  # 添加特效
    use_ai_material: bool = False  # 使用AI生成素材
    platform: str = "douyin"  # 目标平台 douyin/xiaohongshu/bilibili


@dataclass
class RemixDecision:
    """二创决策结果"""
    mode: str  # template/creative/stylized
    confidence: float  # 0.0-1.0
    reason: str  # 决策理由
    plan: Dict  # 编排方案
    shot_plan: List[Dict] = field(default_factory=list)  # 镜头计划
    audio_plan: Dict = field(default_factory=dict)  # 音频方案
    effects_plan: List[str] = field(default_factory=list)  # 特效方案


class RemixDecisionEngine:
    """二创编排决策引擎"""

    def __init__(self):
        self.modes = {
            "template": {
                "name": "模板化改编",
                "desc": "保留原视频结构，替换素材和样式，适合快速产出",
                "suitability": {
                    "low_complexity": 0.9,
                    "medium_complexity": 0.7,
                    "high_complexity": 0.4,
                    "short_duration": 0.8,
                    "long_duration": 0.5,
                    "preserve_story": 0.9,
                },
            },
            "creative": {
                "name": "创意化改编",
                "desc": "重新编排镜头顺序和节奏，加入创意转场和特效",
                "suitability": {
                    "low_complexity": 0.6,
                    "medium_complexity": 0.9,
                    "high_complexity": 0.8,
                    "short_duration": 0.7,
                    "long_duration": 0.8,
                    "preserve_story": 0.6,
                },
            },
            "stylized": {
                "name": "风格化改编",
                "desc": "彻底改变视觉风格和叙事方式，适合深度二创",
                "suitability": {
                    "low_complexity": 0.4,
                    "medium_complexity": 0.7,
                    "high_complexity": 0.9,
                    "short_duration": 0.5,
                    "long_duration": 0.9,
                    "preserve_story": 0.3,
                },
            },
        }

    def decide(
        self,
        features: OriginalFeatures,
        preferences: UserPreferences,
    ) -> RemixDecision:
        """
        做出二创决策

        Args:
            features: 原视频特征
            preferences: 用户偏好

        Returns:
            RemixDecision 决策结果
        """
        # 计算每种模式的适配度
        scores = {}
        for mode, config in self.modes.items():
            score = self._calc_mode_score(mode, config, features, preferences)
            scores[mode] = score

        # 选择最高分模式
        best_mode = max(scores, key=scores.get)
        confidence = scores[best_mode]

        # 生成决策理由
        reason = self._generate_reason(best_mode, scores, features, preferences)

        # 生成编排方案
        plan = self._generate_plan(best_mode, features, preferences)

        # 生成镜头计划
        shot_plan = self._generate_shot_plan(best_mode, features, preferences)

        # 生成音频方案
        audio_plan = self._generate_audio_plan(best_mode, features, preferences)

        # 生成特效方案
        effects_plan = self._generate_effects_plan(best_mode, features, preferences)

        return RemixDecision(
            mode=best_mode,
            confidence=round(confidence, 2),
            reason=reason,
            plan=plan,
            shot_plan=shot_plan,
            audio_plan=audio_plan,
            effects_plan=effects_plan,
        )

    def _calc_mode_score(
        self,
        mode: str,
        config: Dict,
        features: OriginalFeatures,
        preferences: UserPreferences,
    ) -> float:
        """计算模式适配度"""
        score = 0.5  # 基础分
        suitability = config["suitability"]

        # 复杂度适配
        if features.complexity == "low":
            score += (suitability["low_complexity"] - 0.5) * 0.3
        elif features.complexity == "medium":
            score += (suitability["medium_complexity"] - 0.5) * 0.3
        else:
            score += (suitability["high_complexity"] - 0.5) * 0.3

        # 时长适配
        if features.duration < 15:
            score += (suitability["short_duration"] - 0.5) * 0.2
        elif features.duration > 60:
            score += (suitability["long_duration"] - 0.5) * 0.2

        # 故事保留偏好
        if preferences.preserve_story:
            score += (suitability["preserve_story"] - 0.5) * 0.3

        # 用户风格偏好
        if preferences.style != "auto":
            if mode == "stylized":
                score += 0.1
            elif mode == "template":
                score -= 0.05

        # AI素材偏好
        if preferences.use_ai_material and mode == "creative":
            score += 0.1

        return max(0.0, min(1.0, score))

    def _generate_reason(
        self,
        best_mode: str,
        scores: Dict[str, float],
        features: OriginalFeatures,
        preferences: UserPreferences,
    ) -> str:
        """生成决策理由"""
        mode_name = self.modes[best_mode]["name"]
        mode_desc = self.modes[best_mode]["desc"]

        reasons = [f"选择{mode_name}（置信度{scores[best_mode]:.0%}）"]

        # 复杂度原因
        if features.complexity == "low":
            reasons.append("原视频复杂度低，适合快速改编")
        elif features.complexity == "high":
            reasons.append("原视频复杂度高，需要深度处理")

        # 时长原因
        if features.duration < 15:
            reasons.append(f"原视频较短（{features.duration:.0f}秒）")
        elif features.duration > 60:
            reasons.append(f"原视频较长（{features.duration:.0f}秒）")

        # 偏好原因
        if preferences.preserve_story and best_mode == "template":
            reasons.append("用户要求保留原故事线")
        if preferences.style != "auto":
            reasons.append(f"用户指定风格：{preferences.style}")

        # 其他模式对比
        other_modes = [m for m in scores if m != best_mode]
        if other_modes:
            second_best = max(other_modes, key=lambda m: scores[m])
            reasons.append(f"次选：{self.modes[second_best]['name']}（{scores[second_best]:.0%}）")

        return "；".join(reasons)

    def _generate_plan(
        self,
        mode: str,
        features: OriginalFeatures,
        preferences: UserPreferences,
    ) -> Dict:
        """生成编排方案"""
        target_duration = preferences.target_duration or features.duration

        if mode == "template":
            return {
                "structure": "preserve",  # 保留原结构
                "shot_reorder": False,  # 不重排镜头
                "material_replace": True,  # 替换素材
                "style_override": preferences.style if preferences.style != "auto" else "keep",
                "target_duration": target_duration,
                "preserve_audio": True,
                "add_effects": preferences.add_effects,
            }
        elif mode == "creative":
            return {
                "structure": "rearrange",  # 重新编排
                "shot_reorder": True,  # 重排镜头
                "material_replace": True,
                "style_override": preferences.style if preferences.style != "auto" else "enhanced",
                "target_duration": target_duration,
                "preserve_audio": False,
                "add_effects": True,
                "creative_transitions": True,
            }
        else:  # stylized
            return {
                "structure": "rebuild",  # 重建结构
                "shot_reorder": True,
                "material_replace": True,
                "style_override": preferences.style if preferences.style != "auto" else "complete",
                "target_duration": target_duration,
                "preserve_audio": False,
                "add_effects": True,
                "color_grading": True,
                "subtitle_redesign": True,
            }

    def _generate_shot_plan(
        self,
        mode: str,
        features: OriginalFeatures,
        preferences: UserPreferences,
    ) -> List[Dict]:
        """生成镜头计划"""
        target_duration = preferences.target_duration or features.duration
        num_shots = max(4, int(target_duration / 3))  # 每3秒一个镜头

        shot_plan = []
        shot_duration = target_duration / num_shots

        # 根据模式确定镜头顺序
        if mode == "template":
            # 保持原顺序
            order = list(range(min(num_shots, features.shot_count or num_shots)))
        elif mode == "creative":
            # 创意重排：开头高潮，中间铺垫，结尾升华
            order = []
            if num_shots >= 4:
                order.append(num_shots - 1)  # 结尾放开头
                order.extend(range(1, num_shots - 1))  # 中间
                order.append(0)  # 开头放结尾
            else:
                order = list(range(num_shots))
        else:  # stylized
            # 完全重建：按情绪曲线分配
            order = list(range(num_shots))

        for i in range(num_shots):
            shot_idx = order[i] if i < len(order) else i
            start = i * shot_duration

            # 根据位置确定情绪
            if i < num_shots * 0.25:
                emotion = "开场" if mode == "creative" else "铺垫"
                intensity = 0.4
            elif i < num_shots * 0.5:
                emotion = "发展"
                intensity = 0.6
            elif i < num_shots * 0.75:
                emotion = "高潮"
                intensity = 0.9
            else:
                emotion = "结局"
                intensity = 0.5

            shot_plan.append({
                "index": i,
                "original_shot": shot_idx,
                "start_time": round(start, 2),
                "duration": round(shot_duration, 2),
                "emotion": emotion,
                "intensity": intensity,
                "camera_move": self._recommend_camera(emotion, intensity),
            })

        return shot_plan

    def _generate_audio_plan(
        self,
        mode: str,
        features: OriginalFeatures,
        preferences: UserPreferences,
    ) -> Dict:
        """生成音频方案"""
        return {
            "preserve_original_bgm": mode == "template",
            "preserve_dialogue": features.has_dialogue and preferences.preserve_story,
            "add_sfx": preferences.add_effects,
            "bgm_style": preferences.style if preferences.style != "auto" else "auto",
            "ducking": True,  # 人声闪避
            "normalize": True,  # 响度标准化
            "target_lufs": -14 if preferences.platform == "douyin" else -16,
        }

    def _generate_effects_plan(
        self,
        mode: str,
        features: OriginalFeatures,
        preferences: UserPreferences,
    ) -> List[str]:
        """生成特效方案"""
        effects = []

        if not preferences.add_effects:
            return effects

        if mode == "template":
            effects = ["淡入淡出", "基础转场"]
        elif mode == "creative":
            effects = ["闪白", "震动", "快速切换", "光效", "创意转场"]
        else:  # stylized
            effects = ["闪白", "震动", "光效", "调色", "故障风", "动态模糊", "创意转场"]

        # 根据情绪强度添加特效
        if preferences.emotion_intensity > 0.7:
            effects.extend(["高对比", "快速变焦"])

        return list(set(effects))

    def _recommend_camera(self, emotion: str, intensity: float) -> str:
        """推荐运镜"""
        if intensity > 0.7:
            return "快速推近+剧烈晃动"
        elif intensity > 0.4:
            return "推近+轻微晃动"
        else:
            return "固定+缓慢平移"

    def list_modes(self) -> List[Dict]:
        """列出所有改编模式"""
        return [
            {"id": mode, "name": config["name"], "desc": config["desc"]}
            for mode, config in self.modes.items()
        ]

    def compare_modes(
        self,
        features: OriginalFeatures,
        preferences: UserPreferences,
    ) -> Dict[str, float]:
        """对比所有模式的适配度"""
        scores = {}
        for mode, config in self.modes.items():
            scores[mode] = self._calc_mode_score(mode, config, features, preferences)
        return scores


def main():
    """命令行测试"""
    engine = RemixDecisionEngine()

    print("=" * 60)
    print("二创编排决策引擎 v1.0")
    print("=" * 60)

    # 测试1：简单短视频
    print("\n=== 测试1：简单短视频（15秒，低复杂度）===")
    features1 = OriginalFeatures(
        duration=15,
        shot_count=5,
        has_dialogue=False,
        has_bgm=True,
        complexity="low",
    )
    prefs1 = UserPreferences(
        target_duration=15,
        preserve_story=True,
        add_effects=True,
    )
    decision1 = engine.decide(features1, prefs1)
    print(f"  模式: {decision1.mode} ({decision1.confidence:.0%})")
    print(f"  理由: {decision1.reason}")
    print(f"  镜头数: {len(decision1.shot_plan)}")
    print(f"  特效: {decision1.effects_plan}")

    # 测试2：复杂长视频
    print("\n=== 测试2：复杂长视频（90秒，高复杂度）===")
    features2 = OriginalFeatures(
        duration=90,
        shot_count=30,
        has_dialogue=True,
        has_bgm=True,
        complexity="high",
    )
    prefs2 = UserPreferences(
        target_duration=60,
        style="epic",
        emotion_intensity=0.8,
        preserve_story=False,
        add_effects=True,
    )
    decision2 = engine.decide(features2, prefs2)
    print(f"  模式: {decision2.mode} ({decision2.confidence:.0%})")
    print(f"  理由: {decision2.reason}")
    print(f"  镜头数: {len(decision2.shot_plan)}")
    print(f"  特效: {decision2.effects_plan}")
    print(f"  音频方案: {decision2.audio_plan}")

    # 测试3：对比所有模式
    print("\n=== 测试3：模式对比 ===")
    scores = engine.compare_modes(features2, prefs2)
    for mode, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
        print(f"  {mode}: {score:.0%}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
