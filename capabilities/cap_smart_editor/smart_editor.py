"""
智能剪辑决策引擎 v1.0 (P5-3)
AI自动决定特效分配、转场选择、节奏控制、运镜方案，无需人工干预

核心功能：
1. 情绪曲线分析：分析剧本情绪变化，生成情绪曲线
2. 节奏控制：基于情绪曲线自动调整镜头时长和剪辑节奏
3. 特效自动分配：基于场景内容/情绪/景别自动选择特效
4. 转场策略：基于场景关系自动选择转场类型
5. 运镜方案：基于内容类型自动生成运镜方案
6. 色彩方案：基于情绪/风格自动生成调色方案

决策维度：
- 情绪强度：决定节奏快慢和特效强度
- 场景类型：决定转场和运镜
- 景别：决定特效类型
- 视频类型：决定整体风格
- 时长约束：决定镜头数量和时长分配

使用方法：
    from smart_editor import SmartEditor
    editor = SmartEditor()
    decisions = editor.make_decisions(script_data)
    print(decisions)
"""
import os
import sys
import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class ShotDecision:
    """单个镜头的剪辑决策"""
    shot_index: int
    # 节奏
    duration: float = 3.0
    pace: str = "normal"  # fast/normal/slow
    # 特效
    effect: str = ""  # 特效名称
    effect_intensity: float = 0.5  # 0-1
    # 转场
    transition: str = "cut"  # cut/fade/dissolve/wipe/slide/zoom
    transition_duration: float = 0.3
    # 运镜
    camera_move: str = "static"  # static/zoom_in/zoom_out/pan/tilt/handheld
    camera_intensity: float = 0.12
    # 调色
    color_grade: str = "cinematic"  # cinematic/warm/cool/vintage/noir
    # 字幕
    subtitle_style: str = "normal"  # normal/emphasis/highlight/none
    # 置信度
    confidence: float = 0.0


@dataclass
class EditPlan:
    """完整剪辑方案"""
    total_duration: float = 0.0
    shot_count: int = 0
    average_shot_duration: float = 0.0
    pace_profile: List[str] = field(default_factory=list)  # 每段节奏
    emotion_curve: List[float] = field(default_factory=list)  # 情绪曲线
    shot_decisions: List[ShotDecision] = field(default_factory=list)
    overall_style: str = "cinematic"
    bgm_mood: str = "neutral"  # neutral/upbeat/emotional/tense/calm
    notes: List[str] = field(default_factory=list)


# 情绪到节奏映射
EMOTION_PACE_MAP = {
    "joy": "fast",
    "excitement": "fast",
    "anger": "fast",
    "tension": "fast",
    "neutral": "normal",
    "calm": "slow",
    "sad": "slow",
    "peaceful": "slow",
    "love": "slow",
}

# 情绪到特效映射
EMOTION_EFFECT_MAP = {
    "joy": ["subtitle_bar", "date_badge"],
    "excitement": ["character_card", "subtitle_bar"],
    "anger": ["character_card"],
    "tension": ["character_card"],
    "neutral": ["wipe", "bg_slide"],
    "calm": ["bg_slide", "layout"],
    "sad": ["bg_slide"],
    "peaceful": ["bg_slide"],
    "love": ["layout", "subtitle_bar"],
}

# 场景关系到转场映射
SCENE_TRANSITION_MAP = {
    "same_location": "cut",
    "time_skip": "dissolve",
    "location_change": "wipe",
    "emotional_shift": "fade",
    "flashback": "dissolve",
    "parallel": "cut",
    "climax": "cut",
}

# 视频类型到运镜偏好
VIDEO_TYPE_CAMERA_MAP = {
    "exploration": ["pan", "zoom_in", "static"],
    "vlog": ["handheld", "static", "pan"],
    "tutorial": ["static", "zoom_in", "tilt"],
    "product": ["zoom_in", "rotate", "static"],
    "emotional": ["static", "slow_zoom", "pan"],
    "story": ["static", "pan", "zoom_in"],
    "ecommerce": ["zoom_in", "static", "pan"],
    "talking": ["static", "slow_zoom"],
    "promo": ["zoom_in", "pan", "rotate"],
}

# 视频类型到调色偏好
VIDEO_TYPE_COLOR_MAP = {
    "exploration": "warm",
    "vlog": "warm",
    "tutorial": "cinematic",
    "product": "cinematic",
    "emotional": "warm",
    "story": "cinematic",
    "ecommerce": "cinematic",
    "talking": "cinematic",
    "promo": "cool",
}


class SmartEditor:
    """智能剪辑决策引擎"""

    def __init__(self, skill_root: str = None):
        self.skill_root = skill_root or r"C:\Users\Administrator\AppData\Local\DoubaoWork\User Data\Default\.doubaowork\agent_mode\workspace\.user_skills\ai-video-editor"

    # ==================== 主决策入口 ====================

    def make_decisions(self, script_data: Dict[str, Any],
                       video_type: str = "exploration",
                       total_duration: float = 30.0,
                       style: str = "cinematic") -> EditPlan:
        """
        为剧本生成完整剪辑方案

        Args:
            script_data: 剧本数据（包含scenes/shots）
            video_type: 视频类型
            total_duration: 总时长
            style: 整体风格

        Returns:
            EditPlan 完整剪辑方案
        """
        plan = EditPlan(
            total_duration=total_duration,
            overall_style=style,
            bgm_mood=self._infer_bgm_mood(script_data, video_type),
        )

        # 1. 提取镜头列表
        shots = self._extract_shots(script_data)
        plan.shot_count = len(shots)

        if plan.shot_count == 0:
            plan.notes.append("⚠️ 未提取到镜头，使用默认方案")
            return plan

        # 2. 生成情绪曲线
        plan.emotion_curve = self._generate_emotion_curve(shots)

        # 3. 分配镜头时长（基于情绪曲线和总时长）
        durations = self._allocate_durations(shots, plan.emotion_curve, total_duration)

        # 4. 为每个镜头生成决策
        for i, shot in enumerate(shots):
            decision = self._decide_shot(
                shot=shot,
                index=i,
                total_count=len(shots),
                duration=durations[i] if i < len(durations) else 3.0,
                emotion=plan.emotion_curve[i] if i < len(plan.emotion_curve) else "neutral",
                video_type=video_type,
                style=style,
            )
            plan.shot_decisions.append(decision)
            plan.pace_profile.append(decision.pace)

        # 5. 计算平均时长
        if plan.shot_count > 0:
            plan.average_shot_duration = total_duration / plan.shot_count

        # 6. 生成备注
        plan.notes.extend(self._generate_notes(plan))

        return plan

    # ==================== 镜头提取 ====================

    def _extract_shots(self, script_data: Dict[str, Any]) -> List[Dict]:
        """从剧本数据中提取镜头列表"""
        shots = []

        # 支持多种剧本格式
        if "scenes" in script_data:
            for scene in script_data["scenes"]:
                if "shots" in scene:
                    for shot in scene["shots"]:
                        shot_data = dict(shot)
                        shot_data["scene_index"] = scene.get("index", 0)
                        shots.append(shot_data)
                else:
                    # 场景本身作为一个镜头
                    shots.append({
                        "description": scene.get("description", ""),
                        "emotion": scene.get("emotion", "neutral"),
                        "shot_size": scene.get("shot_size", "medium"),
                        "scene_index": scene.get("index", 0),
                    })

        elif "shots" in script_data:
            shots = script_data["shots"]

        return shots

    # ==================== 情绪曲线 ====================

    def _generate_emotion_curve(self, shots: List[Dict]) -> List[str]:
        """生成情绪曲线"""
        curve = []
        for i, shot in enumerate(shots):
            # 优先使用剧本中指定的情绪
            emotion = shot.get("emotion", "")
            if emotion:
                curve.append(emotion)
                continue

            # 基于位置推断（三幕结构）
            position = i / max(1, len(shots) - 1)
            if position < 0.15:
                curve.append("neutral")  # 开场
            elif position < 0.3:
                curve.append("excitement")  # 钩子
            elif position < 0.7:
                curve.append("neutral")  # 内容
            elif position < 0.85:
                curve.append("joy")  # 高潮
            else:
                curve.append("calm")  # 结尾

        return curve

    # ==================== 时长分配 ====================

    def _allocate_durations(self, shots: List[Dict], emotions: List[str],
                            total_duration: float) -> List[float]:
        """基于情绪曲线分配镜头时长"""
        n = len(shots)
        if n == 0:
            return []

        # 计算每个镜头的权重（情绪越强烈，时长越短）
        weights = []
        for emotion in emotions:
            pace = EMOTION_PACE_MAP.get(emotion, "normal")
            if pace == "fast":
                weights.append(0.7)
            elif pace == "slow":
                weights.append(1.3)
            else:
                weights.append(1.0)

        total_weight = sum(weights)
        durations = [(w / total_weight) * total_duration for w in weights]

        # 确保最小时长（1秒）和最大时长（10秒）
        durations = [max(1.0, min(10.0, d)) for d in durations]

        # 重新归一化到总时长
        current_total = sum(durations)
        if current_total > 0:
            scale = total_duration / current_total
            durations = [d * scale for d in durations]

        return durations

    # ==================== 单镜头决策 ====================

    def _decide_shot(self, shot: Dict, index: int, total_count: int,
                     duration: float, emotion: str, video_type: str,
                     style: str) -> ShotDecision:
        """为单个镜头生成剪辑决策"""
        decision = ShotDecision(
            shot_index=index,
            duration=round(duration, 2),
        )

        # 1. 节奏
        decision.pace = EMOTION_PACE_MAP.get(emotion, "normal")

        # 2. 特效选择
        effect_options = EMOTION_EFFECT_MAP.get(emotion, ["wipe"])
        # 开场和结尾使用特殊特效
        if index == 0:
            decision.effect = "wipe"  # 开场用擦除
            decision.effect_intensity = 0.8
        elif index == total_count - 1:
            decision.effect = "bg_slide"  # 结尾用背景滑动
            decision.effect_intensity = 0.6
        else:
            decision.effect = effect_options[index % len(effect_options)]
            decision.effect_intensity = 0.3 + (0.5 if emotion in ["joy", "excitement"] else 0.2)

        # 3. 转场选择
        decision.transition = self._decide_transition(shot, index, total_count, emotion)
        decision.transition_duration = 0.2 if decision.pace == "fast" else 0.5

        # 4. 运镜选择
        camera_options = VIDEO_TYPE_CAMERA_MAP.get(video_type, ["static", "zoom_in"])
        decision.camera_move = camera_options[index % len(camera_options)]
        # 情绪强烈时增加运镜强度
        decision.camera_intensity = 0.12 + (0.05 if emotion in ["joy", "excitement", "anger"] else 0)

        # 5. 调色
        decision.color_grade = VIDEO_TYPE_COLOR_MAP.get(video_type, "cinematic")
        if style and style != "cinematic":
            decision.color_grade = style

        # 6. 字幕风格
        if emotion in ["joy", "excitement"]:
            decision.subtitle_style = "emphasis"
        elif emotion in ["sad", "calm"]:
            decision.subtitle_style = "normal"
        else:
            decision.subtitle_style = "normal"

        # 7. 置信度
        base_confidence = 0.6
        if shot.get("emotion"):
            base_confidence += 0.2
        if shot.get("shot_size"):
            base_confidence += 0.1
        decision.confidence = min(1.0, base_confidence)

        return decision

    def _decide_transition(self, shot: Dict, index: int, total_count: int,
                            emotion: str) -> str:
        """决定转场类型"""
        # 第一个镜头无转场
        if index == 0:
            return "cut"

        # 基于场景关系
        scene_relation = shot.get("scene_relation", "same_location")
        transition = SCENE_TRANSITION_MAP.get(scene_relation, "cut")

        # 情绪强烈时用更明显的转场
        if emotion in ["joy", "excitement"] and transition == "cut":
            transition = "wipe"

        return transition

    # ==================== 辅助方法 ====================

    def _infer_bgm_mood(self, script_data: Dict[str, Any], video_type: str) -> str:
        """推断背景音乐情绪"""
        type_mood_map = {
            "exploration": "upbeat",
            "vlog": "upbeat",
            "tutorial": "calm",
            "product": "neutral",
            "emotional": "emotional",
            "story": "emotional",
            "ecommerce": "upbeat",
            "talking": "calm",
            "promo": "tense",
        }
        return type_mood_map.get(video_type, "neutral")

    def _generate_notes(self, plan: EditPlan) -> List[str]:
        """生成剪辑方案备注"""
        notes = []

        # 节奏分析
        fast_count = plan.pace_profile.count("fast")
        slow_count = plan.pace_profile.count("slow")
        if fast_count > plan.shot_count * 0.5:
            notes.append("💡 整体节奏偏快，适合短视频平台")
        elif slow_count > plan.shot_count * 0.5:
            notes.append("💡 整体节奏偏慢，适合情感类内容")

        # 时长分析
        if plan.average_shot_duration < 2.0:
            notes.append("⚠️ 平均镜头时长较短，注意信息密度")
        elif plan.average_shot_duration > 5.0:
            notes.append("⚠️ 平均镜头时长较长，考虑增加剪辑点")

        # 特效使用
        effects_used = set(d.effect for d in plan.shot_decisions if d.effect)
        notes.append(f"🎬 使用特效: {', '.join(effects_used) if effects_used else '无'}")

        return notes

    # ==================== 导出 ====================

    def to_dict(self, plan: EditPlan) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(plan)

    def export_json(self, plan: EditPlan, output_path: str):
        """导出为JSON文件"""
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(asdict(plan), f, ensure_ascii=False, indent=2)
        print(f"✅ 剪辑方案已导出: {output_path}")


if __name__ == "__main__":
    print("=" * 60)
    print("🎬 智能剪辑决策引擎 v1.0")
    print("=" * 60)

    editor = SmartEditor()

    # 模拟剧本数据
    test_script = {
        "scenes": [
            {
                "index": 0,
                "shots": [
                    {"description": "开场：店铺外观", "emotion": "neutral", "shot_size": "wide"},
                    {"description": "钩子：美食特写", "emotion": "excitement", "shot_size": "closeup"},
                    {"description": "菜品展示1", "emotion": "joy", "shot_size": "medium"},
                    {"description": "菜品展示2", "emotion": "joy", "shot_size": "closeup"},
                    {"description": "用餐场景", "emotion": "neutral", "shot_size": "medium"},
                    {"description": "结尾：店铺招牌", "emotion": "calm", "shot_size": "wide"},
                ]
            }
        ]
    }

    # 生成剪辑方案
    plan = editor.make_decisions(
        script_data=test_script,
        video_type="exploration",
        total_duration=30.0,
        style="warm",
    )

    print(f"\n📋 剪辑方案:")
    print(f"  总时长: {plan.total_duration}秒")
    print(f"  镜头数: {plan.shot_count}")
    print(f"  平均时长: {plan.average_shot_duration:.2f}秒")
    print(f"  整体风格: {plan.overall_style}")
    print(f"  BGM情绪: {plan.bgm_mood}")
    print(f"  情绪曲线: {plan.emotion_curve}")
    print(f"  节奏分布: {plan.pace_profile}")

    print(f"\n🎯 镜头决策:")
    for d in plan.shot_decisions:
        print(f"  镜头{d.shot_index}: {d.duration}s, {d.pace}, 特效={d.effect}, 转场={d.transition}, 运镜={d.camera_move}")

    print(f"\n📝 备注:")
    for note in plan.notes:
        print(f"  {note}")

    print(f"\n{'='*60}")
    print("✅ 智能剪辑决策引擎测试完成")
    print(f"{'='*60}")
