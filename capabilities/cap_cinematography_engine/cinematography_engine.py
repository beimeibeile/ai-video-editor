"""
镜头语言决策引擎 v1.0
根据剧情情绪、动作类型、对话关系自动分配景别/运镜/角度/节奏

核心能力：
1. 情绪→景别映射：颓废用远景/全景，冲突用特写，高潮用大特写
2. 动作→运镜映射：跟随用跟拍，情绪爆发用手持，平静用固定/缓推
3. 对话→角度映射：正反打、过肩、主观视角
4. 情绪曲线→节奏映射：高潮快剪(1-2s)，铺垫长镜头(5-10s)
5. 场景转场决策：匹配剪辑、动作转场、情绪转场
"""
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional, Tuple

# 导入导演运镜规则引擎
try:
    from .director_rules import DirectorRulesEngine, get_director_engine, DirectorPlan
    _DIRECTOR_RULES_AVAILABLE = True
except ImportError:
    try:
        from director_rules import DirectorRulesEngine, get_director_engine, DirectorPlan
        _DIRECTOR_RULES_AVAILABLE = True
    except ImportError:
        _DIRECTOR_RULES_AVAILABLE = False


class EmotionLevel(Enum):
    """情绪强度等级"""
    CALM = "平静"          # 铺垫、日常
    TENSION = "紧张"       # 矛盾积累
    CONFLICT = "冲突"      # 正面冲突
    CLIMAX = "高潮"        # 情绪爆发
    RESOLUTION = "释然"    # 结局、升华


class ShotIntent(Enum):
    """镜头意图"""
    ESTABLISHING = "场景建立"   # 全景/远景，交代环境
    NARRATION = "叙事"          # 中景/近景，推进剧情
    EMOTION = "情绪"           # 特写/大特写，表现内心
    ACTION = "动作"            # 全景/中景，表现动作
    REACTION = "反应"          # 特写，听者反应
    TRANSITION = "转场"        # 空镜/细节，过渡


# 情绪→景别映射
EMOTION_SHOT_SIZE_MAP = {
    EmotionLevel.CALM: ["全景", "中景", "近景"],
    EmotionLevel.TENSION: ["近景", "特写", "中景"],
    EmotionLevel.CONFLICT: ["特写", "近景", "大特写"],
    EmotionLevel.CLIMAX: ["大特写", "特写", "近景"],
    EmotionLevel.RESOLUTION: ["全景", "远景", "中景"],
}

# 情绪→运镜映射
EMOTION_CAMERA_MOVE_MAP = {
    EmotionLevel.CALM: ["固定", "缓推", "缓拉"],
    EmotionLevel.TENSION: ["缓推", "手持", "固定"],
    EmotionLevel.CONFLICT: ["手持", "快推", "摇"],
    EmotionLevel.CLIMAX: ["手持", "快推", "旋转"],
    EmotionLevel.RESOLUTION: ["缓拉", "固定", "升"],
}

# 镜头意图→景别映射
INTENT_SHOT_SIZE_MAP = {
    ShotIntent.ESTABLISHING: ["远景", "全景"],
    ShotIntent.NARRATION: ["中景", "近景"],
    ShotIntent.EMOTION: ["特写", "大特写"],
    ShotIntent.ACTION: ["全景", "中景"],
    ShotIntent.REACTION: ["特写", "近景"],
    ShotIntent.TRANSITION: ["全景", "中景"],
}

# 情绪→单镜头时长映射（秒）
EMOTION_SHOT_DURATION_MAP = {
    EmotionLevel.CALM: (5.0, 10.0),      # 长镜头
    EmotionLevel.TENSION: (3.0, 6.0),     # 中等
    EmotionLevel.CONFLICT: (1.5, 4.0),    # 较快
    EmotionLevel.CLIMAX: (0.8, 2.5),      # 快剪
    EmotionLevel.RESOLUTION: (4.0, 8.0),  # 较长
}

# 关键词→情绪识别
EMOTION_KEYWORDS = {
    EmotionLevel.CLIMAX: ["爆发", "崩溃", "怒吼", "震惊", "激动", "终于", "成功", "翻身", "高潮"],
    EmotionLevel.CONFLICT: ["争吵", "冲突", "对抗", "质疑", "不屑", "嘲讽", "愤怒", "争执"],
    EmotionLevel.TENSION: ["犹豫", "焦虑", "紧张", "担心", "压力", "失业", "迷茫", "困惑"],
    EmotionLevel.RESOLUTION: ["释然", "平静", "微笑", "希望", "未来", "夕阳", "远方", "升华"],
    EmotionLevel.CALM: ["日常", "平静", "普通", "坐在", "走在", "看着", "安静"],
}


@dataclass
class CinematicDecision:
    """单个镜头的电影化决策"""
    shot_id: str
    emotion: EmotionLevel
    intent: ShotIntent
    shot_size: str           # 景别
    camera_move: str         # 运镜
    camera_angle: str        # 角度
    duration: float          # 时长（秒）
    reasoning: str           # 决策理由


@dataclass
class SceneCinematicPlan:
    """场景级电影化方案"""
    scene_id: str
    dominant_emotion: EmotionLevel
    pacing: str              # 节奏描述
    transition_in: str       # 入场转场
    transition_out: str      # 出场转场
    decisions: List[CinematicDecision] = field(default_factory=list)


class CinematographyEngine:
    """镜头语言决策引擎"""

    def __init__(self):
        self.emotion_curve = []  # 全剧情绪曲线

    def detect_emotion(self, text: str, context: str = "") -> EmotionLevel:
        """
        从文本中识别情绪等级

        Args:
            text: 镜头描述/对话文本
            context: 上下文（场景描述）

        Returns:
            EmotionLevel
        """
        full_text = (text + " " + context).lower()

        # 按优先级匹配（高潮>冲突>紧张>释然>平静）
        for emotion in [EmotionLevel.CLIMAX, EmotionLevel.CONFLICT,
                         EmotionLevel.TENSION, EmotionLevel.RESOLUTION]:
            for keyword in EMOTION_KEYWORDS[emotion]:
                if keyword in full_text:
                    return emotion

        return EmotionLevel.CALM

    def determine_intent(self, description: str, dialogue: str = "",
                          is_first_in_scene: bool = False,
                          is_reaction: bool = False) -> ShotIntent:
        """
        判断镜头意图

        Args:
            description: 画面描述
            dialogue: 对话内容
            is_first_in_scene: 是否是场景第一个镜头
            is_reaction: 是否是反应镜头

        Returns:
            ShotIntent
        """
        if is_first_in_scene:
            return ShotIntent.ESTABLISHING
        if is_reaction:
            return ShotIntent.REACTION
        if dialogue and len(dialogue) > 5:
            # 有对话的镜头，根据情绪判断
            return ShotIntent.EMOTION if any(kw in dialogue for kw in EMOTION_KEYWORDS[EmotionLevel.CLIMAX] + EMOTION_KEYWORDS[EmotionLevel.CONFLICT]) else ShotIntent.NARRATION
        if any(kw in description for kw in ["跑", "打", "摔", "冲", "动作", "追逐"]):
            return ShotIntent.ACTION
        return ShotIntent.NARRATION

    def decide_shot_size(self, emotion: EmotionLevel, intent: ShotIntent,
                          index_in_scene: int = 0) -> str:
        """
        决策景别

        Args:
            emotion: 情绪等级
            intent: 镜头意图
            index_in_scene: 场景内第几个镜头

        Returns:
            景别名称
        """
        # 意图优先
        intent_sizes = INTENT_SHOT_SIZE_MAP.get(intent, [])
        if intent_sizes:
            # 根据情绪在候选中选择
            emotion_sizes = EMOTION_SHOT_SIZE_MAP.get(emotion, [])
            # 找交集
            intersection = [s for s in emotion_sizes if s in intent_sizes]
            if intersection:
                return intersection[index_in_scene % len(intersection)]
            return intent_sizes[index_in_scene % len(intent_sizes)]

        # 纯情绪驱动
        sizes = EMOTION_SHOT_SIZE_MAP.get(emotion, ["中景"])
        return sizes[index_in_scene % len(sizes)]

    def decide_camera_move(self, emotion: EmotionLevel, intent: ShotIntent,
                            index_in_scene: int = 0) -> str:
        """
        决策运镜

        Args:
            emotion: 情绪等级
            intent: 镜头意图
            index_in_scene: 场景内第几个镜头

        Returns:
            运镜名称
        """
        # 场景建立用固定或缓推
        if intent == ShotIntent.ESTABLISHING:
            return "固定" if index_in_scene == 0 else "缓推"

        moves = EMOTION_CAMERA_MOVE_MAP.get(emotion, ["固定"])
        return moves[index_in_scene % len(moves)]

    def decide_camera_angle(self, intent: ShotIntent, dialogue: str = "",
                             is_listener: bool = False) -> str:
        """
        决策拍摄角度

        Args:
            intent: 镜头意图
            dialogue: 对话内容
            is_listener: 是否是听者

        Returns:
            角度名称
        """
        if intent == ShotIntent.ESTABLISHING:
            return "平视"
        if is_listener:
            return "过肩"
        if intent == ShotIntent.EMOTION:
            return "平视"
        if intent == ShotIntent.REACTION:
            return "过肩"
        return "平视"

    def decide_duration(self, emotion: EmotionLevel, intent: ShotIntent,
                        dialogue_length: int = 0) -> float:
        """
        决策镜头时长

        Args:
            emotion: 情绪等级
            intent: 镜头意图
            dialogue_length: 对话字数

        Returns:
            时长（秒）
        """
        min_dur, max_dur = EMOTION_SHOT_DURATION_MAP.get(emotion, (3.0, 6.0))

        # 有对话的镜头，时长至少覆盖对话（每秒约4字）
        if dialogue_length > 0:
            dialogue_dur = dialogue_length / 4.0 + 1.0
            return max(min_dur, min(max_dur, dialogue_dur))

        # 场景建立镜头稍长
        if intent == ShotIntent.ESTABLISHING:
            return max_dur * 0.8

        return (min_dur + max_dur) / 2

    def decide_transition(self, from_emotion: EmotionLevel, to_emotion: EmotionLevel,
                          from_scene: str, to_scene: str) -> str:
        """
        决策场景间转场

        Args:
            from_emotion: 出场情绪
            to_emotion: 入场情绪
            from_scene: 出场场景
            to_scene: 入场场景

        Returns:
            转场类型
        """
        # 同场景内硬切
        if from_scene == to_scene:
            return "硬切"

        # 情绪跃升用匹配剪辑
        if from_emotion in [EmotionLevel.CALM, EmotionLevel.TENSION] and to_emotion in [EmotionLevel.CLIMAX, EmotionLevel.CONFLICT]:
            return "匹配剪辑"

        # 时间流逝用溶解
        if "蒙太奇" in to_scene or "montage" in to_scene.lower():
            return "溶解"

        # 结局升华用淡入淡出
        if to_emotion == EmotionLevel.RESOLUTION:
            return "淡入淡出"

        # 默认硬切
        return "硬切"

    def plan_scene(self, scene_id: str, shots: List[Dict[str, Any]],
                    scene_description: str = "") -> SceneCinematicPlan:
        """
        为单个场景生成电影化方案

        Args:
            scene_id: 场景ID
            shots: 镜头列表（每个含description/dialogue等）
            scene_description: 场景描述

        Returns:
            SceneCinematicPlan
        """
        # 检测场景主导情绪
        all_text = scene_description + " " + " ".join(
            s.get("description", "") + " " + s.get("dialogue", "") for s in shots
        )
        dominant_emotion = self.detect_emotion(all_text, scene_description)

        # 决策每个镜头
        decisions = []
        for i, shot in enumerate(shots):
            text = shot.get("description", "")
            dialogue = shot.get("dialogue", "")
            is_first = (i == 0)
            is_reaction = "反应" in text or "听者" in text

            emotion = self.detect_emotion(text + " " + dialogue, scene_description)
            intent = self.determine_intent(text, dialogue, is_first, is_reaction)
            shot_size = self.decide_shot_size(emotion, intent, i)
            camera_move = self.decide_camera_move(emotion, intent, i)
            camera_angle = self.decide_camera_angle(intent, dialogue, is_reaction)
            duration = self.decide_duration(emotion, intent, len(dialogue))

            reasoning = f"情绪={emotion.value}, 意图={intent.value} → 景别={shot_size}, 运镜={camera_move}"

            decisions.append(CinematicDecision(
                shot_id=shot.get("shot_id", f"shot_{i}"),
                emotion=emotion,
                intent=intent,
                shot_size=shot_size,
                camera_move=camera_move,
                camera_angle=camera_angle,
                duration=round(duration, 1),
                reasoning=reasoning,
            ))

        # 节奏描述
        avg_dur = sum(d.duration for d in decisions) / len(decisions) if decisions else 5
        if avg_dur < 2.5:
            pacing = "快剪"
        elif avg_dur < 5:
            pacing = "中等节奏"
        else:
            pacing = "长镜头"

        return SceneCinematicPlan(
            scene_id=scene_id,
            dominant_emotion=dominant_emotion,
            pacing=pacing,
            transition_in="硬切",
            transition_out="硬切",
            decisions=decisions,
        )

    def plan_full_video(self, scenes: List[Dict[str, Any]],
                        apply_director_rules: bool = True) -> List[SceneCinematicPlan]:
        """
        为全剧生成电影化方案

        Args:
            scenes: 场景列表，每个含scene_id/shots/description
            apply_director_rules: 是否应用8条导演运镜规则（默认True）

        Returns:
            场景方案列表
        """
        plans = []
        director_reports = []  # 保存每个场景的导演规则报告

        for i, scene in enumerate(scenes):
            scene_id = scene.get("scene_id", f"scene_{i}")
            scene_shots = scene.get("shots", [])
            scene_desc = scene.get("description", "")
            is_first = (i == 0)
            is_last = (i == len(scenes) - 1)

            # 生成基础场景方案
            plan = self.plan_scene(scene_id, scene_shots, scene_desc)

            # 应用8条导演运镜规则
            if apply_director_rules and _DIRECTOR_RULES_AVAILABLE and scene_shots:
                # 将decisions转换为shots格式供导演规则使用
                director_shots = []
                for d in plan.decisions:
                    # 找到原始shot数据
                    orig_shot = next((s for s in scene_shots
                                       if s.get("shot_id", "") == d.shot_id), {})
                    director_shots.append({
                        "shot_id": d.shot_id,
                        "description": orig_shot.get("description", ""),
                        "dialogue": orig_shot.get("dialogue", ""),
                        "shot_size": d.shot_size,
                        "camera_move": d.camera_move,
                        "camera_angle": d.camera_angle,
                        "duration": d.duration,
                        "emotion": d.emotion.value,
                        "intent": d.intent.value,
                    })

                # 应用导演规则
                director_engine = get_director_engine()
                director_plan = director_engine.apply_all(
                    director_shots, scene_desc, is_first, is_last
                )
                director_reports.append({
                    "scene_id": scene_id,
                    "plan": director_plan,
                })

                # 将导演规则的修改应用回decisions
                for d in plan.decisions:
                    modified_shot = next((s for s in director_shots
                                           if s.get("shot_id", "") == d.shot_id), None)
                    if modified_shot:
                        d.shot_size = modified_shot.get("shot_size", d.shot_size)
                        d.camera_move = modified_shot.get("camera_move", d.camera_move)
                        d.camera_angle = modified_shot.get("camera_angle", d.camera_angle)
                        d.duration = modified_shot.get("duration", d.duration)
                        # 在reasoning中追加导演规则标记
                        if modified_shot.get("hook"):
                            d.reasoning += " [导演规则:段尾留钩]"

            # 决策场景间转场
            if i > 0:
                prev_plan = plans[i - 1]
                plan.transition_in = self.decide_transition(
                    prev_plan.dominant_emotion, plan.dominant_emotion,
                    prev_plan.scene_id, plan.scene_id,
                )
                prev_plan.transition_out = plan.transition_in
            plans.append(plan)

        # 记录情绪曲线
        self.emotion_curve = [(p.scene_id, p.dominant_emotion.value, p.pacing) for p in plans]

        # 保存导演规则报告
        self._director_reports = director_reports

        return plans

    def apply_to_shots(self, plans: List[SceneCinematicPlan],
                        shots: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        将电影化决策应用到镜头数据

        Args:
            plans: 场景方案列表
            shots: 原始镜头列表

        Returns:
            增强后的镜头列表（含shot_size/camera_move/camera_angle/duration）
        """
        # 建立shot_id→decision映射
        decision_map = {}
        for plan in plans:
            for d in plan.decisions:
                decision_map[d.shot_id] = d

        enhanced = []
        for shot in shots:
            shot_id = shot.get("shot_id", "")
            decision = decision_map.get(shot_id)
            new_shot = dict(shot)
            if decision:
                new_shot["shot_size"] = decision.shot_size
                new_shot["camera_move"] = decision.camera_move
                new_shot["camera_angle"] = decision.camera_angle
                new_shot["duration"] = decision.duration
                new_shot["emotion"] = decision.emotion.value
                new_shot["intent"] = decision.intent.value
                new_shot["cinematic_reasoning"] = decision.reasoning
            enhanced.append(new_shot)

        return enhanced

    def get_emotion_curve_report(self) -> str:
        """获取情绪曲线报告"""
        if not self.emotion_curve:
            return "暂无情绪曲线数据"

        lines = ["=" * 50, "全剧情绪曲线", "=" * 50]
        for scene_id, emotion, pacing in self.emotion_curve:
            lines.append(f"  {scene_id}: {emotion} ({pacing})")
        return "\n".join(lines)

    def get_director_rules_report(self) -> str:
        """获取导演运镜规则应用报告"""
        if not hasattr(self, '_director_reports') or not self._director_reports:
            return "暂无导演规则报告（plan_full_video时apply_director_rules=False）"

        lines = ["=" * 60, "导演运镜规则应用报告（全剧）", "=" * 60]
        total_applied = 0
        total_warnings = 0
        for report in self._director_reports:
            scene_id = report["scene_id"]
            plan: DirectorPlan = report["plan"]
            lines.append(f"\n--- {scene_id} ---")
            lines.append(f"  应用规则: {plan.applied_count}/8 | 警告: {plan.warning_count}")
            for r in plan.rules_applied:
                icon = "✅" if r.applied else "⏭️"
                lines.append(f"  {icon} [{r.rule_type.value}] {r.description}")
                for w in r.warnings:
                    lines.append(f"     ⚠️ {w}")
            total_applied += plan.applied_count
            total_warnings += plan.warning_count

        lines.append(f"\n{'=' * 60}")
        lines.append(f"总计: {len(self._director_reports)}个场景 | "
                     f"规则应用{total_applied}次 | 警告{total_warnings}条")
        return "\n".join(lines)


if __name__ == "__main__":
    print("=" * 60)
    print("镜头语言决策引擎 v1.0")
    print("=" * 60)

    engine = CinematographyEngine()

    # 测试：模拟《翻身》的场景
    test_scenes = [
        {
            "scene_id": "S01",
            "description": "昏暗的出租屋，陈默失业后颓废地坐在电脑前",
            "shots": [
                {"shot_id": "S01_01", "description": "出租屋场景建立，昏暗的房间", "dialogue": ""},
                {"shot_id": "S01_02", "description": "手机屏幕亮起：您已被公司优化", "dialogue": ""},
                {"shot_id": "S01_03", "description": "陈默苦笑", "dialogue": "又失业了...第三次了..."},
            ],
        },
        {
            "scene_id": "S02",
            "description": "陈默在街道上看到AI视频编辑器广告",
            "shots": [
                {"shot_id": "S02_01", "description": "街道场景建立", "dialogue": ""},
                {"shot_id": "S02_02", "description": "橱窗电视播放广告", "dialogue": "AI视频编辑器，一句话生成专业视频！"},
            ],
        },
        {
            "scene_id": "S03",
            "description": "陈默尝试AI视频编辑器，震惊于效果",
            "shots": [
                {"shot_id": "S03_01", "description": "出租屋场景建立", "dialogue": ""},
                {"shot_id": "S03_02", "description": "陈默输入指令，视频自动生成", "dialogue": ""},
                {"shot_id": "S03_03", "description": "陈默瞪大眼，激动", "dialogue": "这...这就完了？才30秒？！"},
            ],
        },
        {
            "scene_id": "S04",
            "description": "咖啡馆，陈默遇到前老板王总，被打脸",
            "shots": [
                {"shot_id": "S04_01", "description": "咖啡馆场景建立", "dialogue": ""},
                {"shot_id": "S04_02", "description": "王总不屑", "dialogue": "你？做视频？别开玩笑了"},
                {"shot_id": "S04_03", "description": "陈默平静展示作品", "dialogue": "您看看这个"},
                {"shot_id": "S04_04", "description": "王总震惊，表情变化", "dialogue": "这...这真是你做的？"},
            ],
        },
        {
            "scene_id": "S05",
            "description": "天台，陈默看着夕阳，释然升华",
            "shots": [
                {"shot_id": "S05_01", "description": "天台场景建立，夕阳", "dialogue": ""},
                {"shot_id": "S05_02", "description": "陈默微笑，背影", "dialogue": "翻身只需要一个对的工具"},
            ],
        },
    ]

    plans = engine.plan_full_video(test_scenes)

    print("\n场景级方案:")
    for plan in plans:
        print(f"\n  {plan.scene_id}: 主导情绪={plan.dominant_emotion.value}, 节奏={plan.pacing}")
        print(f"    转场: 入={plan.transition_in}, 出={plan.transition_out}")
        for d in plan.decisions:
            print(f"    {d.shot_id}: {d.shot_size}/{d.camera_move}/{d.camera_angle}, {d.duration}s")
            print(f"      理由: {d.reasoning}")

    print("\n" + engine.get_emotion_curve_report())
