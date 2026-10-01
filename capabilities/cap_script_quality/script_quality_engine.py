"""
剧本质量引擎v2
人性认知+剧情创造能力
解决"系统缺乏人性认知和剧本创造能力"的核心问题

核心能力：
1. 三幕结构深化（钩子15%→发展60%→高潮+结尾25%）
2. 角色弧光设计（角色成长变化）
3. 情感曲线设计（情绪起伏，不是平铺直叙）
4. 冲突设计（内部+外部+情感冲突）
5. 钩子优化（前3秒抓人）
6. 节奏控制（快慢交替，张弛有度）
7. 质量评估（多维度评分+改进建议）
"""
import os
import sys
import json
import random
from typing import List, Dict, Optional, Tuple

from .models import (
    EmotionType, ConflictType, HookType, PacingType,
    EmotionPoint, CharacterArc, Conflict, Hook, Beat,
    QualityReport, EnhancedScript,
)

# 类型预设库（不同视频类型的情感/冲突/节奏模板）
GENRE_PRESETS = {
    "vlog": {
        "emotion_pattern": [
            (0.0, EmotionType.EXCITEMENT, 0.7),
            (0.15, EmotionType.ANTICIPATION, 0.6),
            (0.3, EmotionType.JOY, 0.8),
            (0.5, EmotionType.SURPRISE, 0.7),
            (0.7, EmotionType.JOY, 0.9),
            (0.85, EmotionType.TRUST, 0.6),
            (1.0, EmotionType.JOY, 0.7),
        ],
        "conflict_types": [ConflictType.EXTERNAL, ConflictType.EMOTIONAL],
        "hook_types": [HookType.PROMISE, HookType.CONTRAST, HookType.EMOTION],
        "pacing": [PacingType.BUILD, PacingType.FAST, PacingType.MEDIUM, PacingType.RELEASE],
    },
    "tutorial": {
        "emotion_pattern": [
            (0.0, EmotionType.ANTICIPATION, 0.6),
            (0.2, EmotionType.TRUST, 0.7),
            (0.4, EmotionType.SURPRISE, 0.5),
            (0.6, EmotionType.TRUST, 0.8),
            (0.8, EmotionType.JOY, 0.6),
            (1.0, EmotionType.SATISFACTION if hasattr(EmotionType, 'SATISFACTION') else EmotionType.RELIEF, 0.7),
        ],
        "conflict_types": [ConflictType.EXTERNAL, ConflictType.INTERNAL],
        "hook_types": [HookType.PROMISE, HookType.QUESTION, HookType.SHOCK],
        "pacing": [PacingType.MEDIUM, PacingType.SLOW, PacingType.MEDIUM, PacingType.MEDIUM],
    },
    "story": {
        "emotion_pattern": [
            (0.0, EmotionType.MYSTERY if hasattr(EmotionType, 'MYSTERY') else EmotionType.SURPRISE, 0.6),
            (0.15, EmotionType.TENSION, 0.7),
            (0.3, EmotionType.FEAR, 0.6),
            (0.5, EmotionType.ANGER, 0.8),
            (0.65, EmotionType.TENSION, 0.9),
            (0.8, EmotionType.RELIEF, 0.7),
            (1.0, EmotionType.JOY, 0.6),
        ],
        "conflict_types": [ConflictType.INTERNAL, ConflictType.EXTERNAL, ConflictType.EMOTIONAL],
        "hook_types": [HookType.MYSTERY, HookType.SHOCK, HookType.QUESTION],
        "pacing": [PacingType.SLOW, PacingType.BUILD, PacingType.FAST, PacingType.RELEASE],
    },
    "product": {
        "emotion_pattern": [
            (0.0, EmotionType.DESIRE if hasattr(EmotionType, 'DESIRE') else EmotionType.ANTICIPATION, 0.7),
            (0.2, EmotionType.SURPRISE, 0.8),
            (0.4, EmotionType.TRUST, 0.7),
            (0.6, EmotionType.EXCITEMENT, 0.9),
            (0.8, EmotionType.ANTICIPATION, 0.8),
            (1.0, EmotionType.JOY, 0.7),
        ],
        "conflict_types": [ConflictType.EXTERNAL, ConflictType.EMOTIONAL],
        "hook_types": [HookType.SHOCK, HookType.CONTRAST, HookType.PROMISE],
        "pacing": [PacingType.FAST, PacingType.MEDIUM, PacingType.FAST, PacingType.BUILD],
    },
}

# 默认预设（兜底）
DEFAULT_PRESET = {
    "emotion_pattern": [
        (0.0, EmotionType.ANTICIPATION, 0.6),
        (0.2, EmotionType.JOY, 0.7),
        (0.4, EmotionType.SURPRISE, 0.6),
        (0.6, EmotionType.TENSION, 0.5),
        (0.8, EmotionType.RELIEF, 0.6),
        (1.0, EmotionType.JOY, 0.7),
    ],
    "conflict_types": [ConflictType.EXTERNAL, ConflictType.INTERNAL],
    "hook_types": [HookType.QUESTION, HookType.PROMISE, HookType.CONTRAST],
    "pacing": [PacingType.MEDIUM, PacingType.BUILD, PacingType.FAST, PacingType.RELEASE],
}


class ScriptQualityEngine:
    """剧本质量引擎v2"""

    def __init__(self):
        self.random_seed = None

    def _get_preset(self, genre: str) -> Dict:
        """获取类型预设"""
        genre_lower = str(genre).lower().strip()
        for key in GENRE_PRESETS:
            if key in genre_lower or genre_lower in key:
                return GENRE_PRESETS[key]
        return DEFAULT_PRESET

    # ==================== 核心方法 ====================

    def enhance_script(self, script, idea: str = "", genre: str = "vlog") -> EnhancedScript:
        """
        增强现有剧本，添加人性认知和剧情创造元素

        Args:
            script: 原始Script对象（来自cap_script_engine）
            idea: 创意描述
            genre: 视频类型

        Returns:
            EnhancedScript 增强后的高质量剧本
        """
        title = getattr(script, 'title', idea[:20] if idea else "未命名")
        duration = getattr(script, 'total_duration', 30)
        scenes = getattr(script, 'scenes', [])

        enhanced = EnhancedScript(
            title=title,
            idea=idea,
            genre=str(genre),
            duration=duration,
            original_script_ref=str(id(script)),
        )

        # 1. 设计钩子
        enhanced.hook = self.optimize_hook(idea, genre, duration)

        # 2. 设计情感曲线
        enhanced.emotion_curve = self.design_emotion_curve(duration, genre)

        # 3. 设计角色弧光（从剧本场景中提取角色）
        enhanced.character_arcs = self.design_character_arcs(scenes, duration)

        # 4. 设计冲突
        enhanced.conflicts = self.design_conflicts(scenes, duration, genre)

        # 5. 设计节拍
        enhanced.beats = self.design_beats(scenes, duration)

        # 6. 设计节奏
        enhanced.pacing_map = self.design_pacing(duration, genre)

        # 7. 质量评估
        enhanced.quality_report = self.evaluate_quality(enhanced)

        return enhanced

    def generate_quality_script(self, idea: str, genre: str = "vlog",
                                  duration: float = 30) -> EnhancedScript:
        """
        直接生成高质量剧本（不依赖原始剧本引擎）

        Args:
            idea: 创意描述
            genre: 视频类型
            duration: 目标时长（秒）

        Returns:
            EnhancedScript 高质量剧本
        """
        enhanced = EnhancedScript(
            title=self._generate_title(idea, genre),
            idea=idea,
            genre=str(genre),
            duration=duration,
        )

        enhanced.hook = self.optimize_hook(idea, genre, duration)
        enhanced.emotion_curve = self.design_emotion_curve(duration, genre)
        enhanced.character_arcs = self._generate_character_arcs(idea, duration)
        enhanced.conflicts = self._generate_conflicts(idea, duration, genre)
        enhanced.beats = self._generate_beats(idea, duration, genre)
        enhanced.pacing_map = self.design_pacing(duration, genre)
        enhanced.quality_report = self.evaluate_quality(enhanced)

        return enhanced

    # ==================== 钩子设计 ====================

    def optimize_hook(self, idea: str, genre: str, duration: float) -> Hook:
        """
        优化前3秒钩子

        钩子原则：
        1. 前1秒必须有视觉/听觉冲击
        2. 前3秒必须建立期待或悬念
        3. 钩子必须与内容相关，不能标题党
        """
        preset = self._get_preset(genre)
        hook_type = preset["hook_types"][0] if preset["hook_types"] else HookType.QUESTION

        # 根据类型生成钩子内容
        hook_content = self._generate_hook_content(idea, hook_type, genre)

        return Hook(
            hook_type=hook_type,
            content=hook_content,
            appear_time=0.0,
            duration=min(3.0, duration * 0.1),
            expected_effect=self._get_hook_effect(hook_type),
            strength=0.75,
        )

    def _generate_hook_content(self, idea: str, hook_type: HookType, genre: str) -> str:
        """生成钩子内容"""
        idea_short = idea[:30] if len(idea) > 30 else idea

        hook_templates = {
            HookType.QUESTION: f"你知道{idea_short}背后的秘密吗？",
            HookType.CONTRAST: f"以前vs现在，{idea_short}的变化太大了！",
            HookType.ACTION: f"直接开始，{idea_short}全过程记录！",
            HookType.EMOTION: f"每次看到{idea_short}，都忍不住...",
            HookType.MYSTERY: f"{idea_short}的真相，99%的人不知道",
            HookType.PROMISE: f"3分钟学会{idea_short}，看完就能用！",
            HookType.SHOCK: f"万万没想到，{idea_short}竟然是这样！",
            HookType.QUOTE: f"关于{idea_short}，有句话说得好...",
        }
        return hook_templates.get(hook_type, f"{idea_short}，精彩开始！")

    def _get_hook_effect(self, hook_type: HookType) -> str:
        """获取钩子预期效果"""
        effects = {
            HookType.QUESTION: "激发好奇心，引导观众继续观看",
            HookType.CONTRAST: "制造反差冲击，引发兴趣",
            HookType.ACTION: "直接进入主题，节省时间",
            HookType.EMOTION: "情感共鸣，建立连接",
            HookType.MYSTERY: "制造悬念，保持关注",
            HookType.PROMISE: "明确价值，给观看理由",
            HookType.SHOCK: "震撼开场，打破预期",
            HookType.QUOTE: "金句开场，提升格调",
        }
        return effects.get(hook_type, "吸引注意力")

    # ==================== 情感曲线设计 ====================

    def design_emotion_curve(self, duration: float, genre: str) -> List[EmotionPoint]:
        """
        设计情感曲线

        原则：
        1. 不能平铺直叙，必须有起伏
        2. 高潮点在60-80%位置
        3. 开头要有吸引力，结尾要有余韵
        4. 情绪转换要自然，不能突兀
        """
        preset = self._get_preset(genre)
        pattern = preset["emotion_pattern"]

        curve = []
        for ratio, emotion, intensity in pattern:
            time_sec = round(duration * ratio, 2)
            curve.append(EmotionPoint(
                time_sec=time_sec,
                emotion=emotion,
                intensity=intensity,
                description=self._get_emotion_description(emotion, intensity),
            ))

        return curve

    def _get_emotion_description(self, emotion: EmotionType, intensity: float) -> str:
        """获取情绪描述"""
        level = "强烈" if intensity > 0.7 else "中等" if intensity > 0.4 else "微弱"
        descriptions = {
            EmotionType.JOY: f"{level}的喜悦氛围",
            EmotionType.SADNESS: f"{level}的悲伤情绪",
            EmotionType.ANGER: f"{level}的愤怒张力",
            EmotionType.FEAR: f"{level}的紧张恐惧",
            EmotionType.SURPRISE: f"{level}的惊喜感",
            EmotionType.ANTICIPATION: f"{level}的期待感",
            EmotionType.TRUST: f"{level}的信任感",
            EmotionType.NEUTRAL: "平静过渡",
            EmotionType.TENSION: f"{level}的紧张感",
            EmotionType.RELIEF: f"{level}的释然感",
            EmotionType.EXCITEMENT: f"{level}的兴奋感",
        }
        return descriptions.get(emotion, f"{level}的情绪")

    # ==================== 角色弧光设计 ====================

    def design_character_arcs(self, scenes: List, duration: float) -> List[CharacterArc]:
        """从剧本场景中提取角色并设计弧光"""
        arcs = []
        # 简单策略：提取场景中的角色名（如果有）
        character_names = set()
        for scene in scenes:
            shots = getattr(scene, 'shots', [])
            for shot in shots:
                # 尝试从描述中提取角色
                desc = getattr(shot, 'description', '') or getattr(shot, 'action', '')
                # 简单提取：常见角色名模式
                import re
                names = re.findall(r'[（(]([^）)]{1,4})[）)]', desc)
                character_names.update(names)

        if not character_names:
            # 兜底：创建一个默认主角弧光
            arcs.append(CharacterArc(
                character_name="主角",
                start_state="未知/初学者",
                end_state="掌握/成长",
                key_turning_points=[
                    (duration * 0.3, "遇到挑战/发现问题"),
                    (duration * 0.6, "克服困难/关键突破"),
                    (duration * 0.85, "完成目标/获得成长"),
                ],
                growth_dimension="能力/认知",
            ))
        else:
            for name in list(character_names)[:2]:  # 最多2个角色
                arcs.append(CharacterArc(
                    character_name=name,
                    start_state="初始状态",
                    end_state="成长后的状态",
                    key_turning_points=[
                        (duration * 0.3, "关键转折1"),
                        (duration * 0.6, "关键转折2"),
                    ],
                    growth_dimension="情感/认知",
                ))

        return arcs

    def _generate_character_arcs(self, idea: str, duration: float) -> List[CharacterArc]:
        """直接生成角色弧光（无原始剧本时）"""
        return [CharacterArc(
            character_name="主角",
            start_state="初学者/未知",
            end_state="掌握者/成长",
            key_turning_points=[
                (duration * 0.25, "接触新事物/遇到挑战"),
                (duration * 0.5, "深入探索/克服困难"),
                (duration * 0.75, "关键突破/掌握要领"),
                (duration * 0.9, "完成目标/展示成果"),
            ],
            growth_dimension="能力+认知",
        )]

    # ==================== 冲突设计 ====================

    def design_conflicts(self, scenes: List, duration: float, genre: str) -> List[Conflict]:
        """设计冲突"""
        preset = self._get_preset(genre)
        conflict_types = preset["conflict_types"]

        conflicts = []
        # 主冲突
        conflicts.append(Conflict(
            conflict_type=conflict_types[0],
            description=f"核心冲突：围绕{genre}内容的主要挑战",
            intensity=0.8,
            start_time=duration * 0.15,
            peak_time=duration * 0.6,
            resolution="通过努力/方法解决",
            resolved=True,
        ))

        # 次要冲突（如果有多个类型）
        if len(conflict_types) > 1:
            conflicts.append(Conflict(
                conflict_type=conflict_types[1],
                description="次要冲突：过程中的额外障碍",
                intensity=0.5,
                start_time=duration * 0.3,
                peak_time=duration * 0.5,
                resolution="顺带解决",
                resolved=True,
            ))

        return conflicts

    def _generate_conflicts(self, idea: str, duration: float, genre: str) -> List[Conflict]:
        """直接生成冲突"""
        return [
            Conflict(
                conflict_type=ConflictType.EXTERNAL,
                description=f"主要挑战：{idea}过程中的核心障碍",
                intensity=0.75,
                start_time=duration * 0.1,
                peak_time=duration * 0.55,
                resolution="通过正确方法逐步解决",
                resolved=True,
            ),
            Conflict(
                conflict_type=ConflictType.INTERNAL,
                description="心理冲突：从不确定到自信的转变",
                intensity=0.6,
                start_time=duration * 0.2,
                peak_time=duration * 0.5,
                resolution="通过实践建立信心",
                resolved=True,
            ),
        ]

    # ==================== 节拍设计 ====================

    def design_beats(self, scenes: List, duration: float) -> List[Beat]:
        """从剧本场景生成节拍"""
        beats = []
        beat_id = 1
        for scene in scenes:
            shots = getattr(scene, 'shots', [])
            for shot in shots:
                start = getattr(shot, 'start_time', 0)
                dur = getattr(shot, 'duration', 3)
                desc = getattr(shot, 'description', '') or getattr(shot, 'action', '')
                beats.append(Beat(
                    beat_id=beat_id,
                    start_time=start,
                    duration=dur,
                    description=desc,
                    emotion=EmotionType.NEUTRAL,
                    pacing=PacingType.MEDIUM,
                ))
                beat_id += 1
        return beats

    def _generate_beats(self, idea: str, duration: float, genre: str) -> List[Beat]:
        """直接生成节拍"""
        preset = self._get_preset(genre)
        num_beats = max(6, int(duration / 3))
        beat_duration = duration / num_beats

        beat_descriptions = [
            f"开场：引入{idea}主题",
            "背景：建立场景和氛围",
            "发展1：第一个关键点",
            "发展2：深入探索",
            "高潮：核心展示/突破",
            "收尾：总结+呼吁行动",
        ]

        beats = []
        for i in range(num_beats):
            desc = beat_descriptions[i] if i < len(beat_descriptions) else f"片段{i+1}"
            # 根据位置分配情绪和节奏
            ratio = i / num_beats
            if ratio < 0.15:
                emotion = EmotionType.ANTICIPATION
                pacing = PacingType.BUILD
            elif ratio < 0.5:
                emotion = EmotionType.JOY
                pacing = PacingType.MEDIUM
            elif ratio < 0.75:
                emotion = EmotionType.EXCITEMENT
                pacing = PacingType.FAST
            else:
                emotion = EmotionType.RELIEF
                pacing = PacingType.RELEASE

            beats.append(Beat(
                beat_id=i + 1,
                start_time=round(i * beat_duration, 2),
                duration=round(beat_duration, 2),
                description=desc,
                emotion=emotion,
                pacing=pacing,
                conflict_intensity=0.5 if 0.3 < ratio < 0.7 else 0.2,
            ))

        return beats

    # ==================== 节奏设计 ====================

    def design_pacing(self, duration: float, genre: str) -> List[Tuple[float, PacingType]]:
        """
        设计节奏图

        原则：快慢交替，张弛有度
        三幕节奏：慢入→渐快→高潮→释放
        """
        preset = self._get_preset(genre)
        pacing_types = preset["pacing"]

        # 四幕节奏分配
        segments = [
            (0.0, pacing_types[0] if len(pacing_types) > 0 else PacingType.MEDIUM),
            (0.25, pacing_types[1] if len(pacing_types) > 1 else PacingType.BUILD),
            (0.5, pacing_types[2] if len(pacing_types) > 2 else PacingType.FAST),
            (0.75, pacing_types[3] if len(pacing_types) > 3 else PacingType.RELEASE),
        ]

        return [(round(t * duration, 2), p) for t, p in segments]

    # ==================== 质量评估 ====================

    def evaluate_quality(self, enhanced: EnhancedScript) -> QualityReport:
        """
        多维度质量评估

        评估维度：
        1. 钩子强度（前3秒是否抓人）
        2. 情感曲线（是否有起伏，高潮位置是否合理）
        3. 冲突设计（是否有冲突，是否解决）
        4. 角色弧光（角色是否有成长）
        5. 节奏控制（快慢是否交替）
        6. 结构完整性（三幕是否完整）
        """
        report = QualityReport()

        # 1. 钩子评分
        if enhanced.hook:
            report.hook_score = min(100, enhanced.hook.strength * 100 + 20)
            if enhanced.hook.duration <= 3:
                report.hook_score = min(100, report.hook_score + 5)
        else:
            report.hook_score = 30

        # 2. 情感曲线评分
        if len(enhanced.emotion_curve) >= 4:
            # 检查是否有起伏（强度方差）
            intensities = [e.intensity for e in enhanced.emotion_curve]
            variance = sum((x - sum(intensities)/len(intensities))**2 for x in intensities) / len(intensities)
            report.emotion_score = min(100, 50 + variance * 200)
            # 检查高潮位置（60-80%）
            max_intensity = max(intensities)
            max_idx = intensities.index(max_intensity)
            max_ratio = max_idx / (len(intensities) - 1) if len(intensities) > 1 else 0
            if 0.5 <= max_ratio <= 0.85:
                report.emotion_score = min(100, report.emotion_score + 10)
        else:
            report.emotion_score = 40

        # 3. 冲突评分
        if enhanced.conflicts:
            main_conflict = enhanced.conflicts[0]
            report.conflict_score = min(100, main_conflict.intensity * 80 + 20)
            if main_conflict.resolved:
                report.conflict_score = min(100, report.conflict_score + 10)
            if len(enhanced.conflicts) >= 2:
                report.conflict_score = min(100, report.conflict_score + 5)
        else:
            report.conflict_score = 30

        # 4. 角色弧光评分
        if enhanced.character_arcs:
            arc = enhanced.character_arcs[0]
            report.character_score = 60
            if arc.start_state and arc.end_state and arc.start_state != arc.end_state:
                report.character_score += 15
            if len(arc.key_turning_points) >= 2:
                report.character_score += 15
            report.character_score = min(100, report.character_score)
        else:
            report.character_score = 35

        # 5. 节奏评分
        if len(enhanced.pacing_map) >= 3:
            pacing_values = [p[1] for p in enhanced.pacing_map]
            # 检查是否有变化
            if len(set(pacing_values)) >= 2:
                report.pacing_score = 75
            else:
                report.pacing_score = 50
            # 检查是否有FAST和SLOW/RELEASE搭配
            if PacingType.FAST in pacing_values and (PacingType.SLOW in pacing_values or PacingType.RELEASE in pacing_values):
                report.pacing_score = min(100, report.pacing_score + 15)
        else:
            report.pacing_score = 40

        # 6. 结构评分
        has_hook = enhanced.hook is not None
        has_emotion = len(enhanced.emotion_curve) >= 4
        has_conflict = len(enhanced.conflicts) >= 1
        has_character = len(enhanced.character_arcs) >= 1
        has_beats = len(enhanced.beats) >= 4
        structure_score = sum([has_hook, has_emotion, has_conflict, has_character, has_beats]) * 20
        report.structure_score = min(100, structure_score)

        # 综合评分（加权平均）
        report.overall_score = (
            report.hook_score * 0.20 +
            report.emotion_score * 0.20 +
            report.conflict_score * 0.15 +
            report.character_score * 0.15 +
            report.pacing_score * 0.15 +
            report.structure_score * 0.15
        )

        # 优势和不足
        scores = {
            "钩子": report.hook_score,
            "情感曲线": report.emotion_score,
            "冲突设计": report.conflict_score,
            "角色弧光": report.character_score,
            "节奏控制": report.pacing_score,
            "结构完整": report.structure_score,
        }
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        report.strengths = [f"{name}表现优秀({score:.0f}分)" for name, score in sorted_scores[:2] if score >= 70]
        report.weaknesses = [f"{name}需要加强({score:.0f}分)" for name, score in sorted_scores[-2:] if score < 70]

        # 改进建议
        if report.hook_score < 70:
            report.suggestions.append("优化前3秒钩子，增强开场冲击力")
        if report.emotion_score < 70:
            report.suggestions.append("丰富情感曲线，增加情绪起伏变化")
        if report.conflict_score < 70:
            report.suggestions.append("加强冲突设计，增加故事张力")
        if report.character_score < 70:
            report.suggestions.append("深化角色弧光，展现角色成长")
        if report.pacing_score < 70:
            report.suggestions.append("调整节奏控制，做到快慢交替张弛有度")

        return report

    # ==================== 工具方法 ====================

    def _generate_title(self, idea: str, genre: str) -> str:
        """生成标题"""
        clean = idea.strip().replace("\n", " ")
        if len(clean) > 20:
            clean = clean[:20] + "..."
        return f"{clean} | {genre}视频"

    def export_json(self, enhanced: EnhancedScript, output_path: str) -> str:
        """导出增强剧本为JSON"""
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(enhanced.to_dict(), f, ensure_ascii=False, indent=2)
        return output_path

    def print_summary(self, enhanced: EnhancedScript):
        """打印增强剧本摘要"""
        print("=" * 60)
        print(f"高质量剧本: {enhanced.title}")
        print("=" * 60)
        print(f"类型: {enhanced.genre} | 时长: {enhanced.duration}秒")
        print()

        if enhanced.hook:
            print(f"🎣 钩子 [{enhanced.hook.hook_type.value}]:")
            print(f"   内容: {enhanced.hook.content}")
            print(f"   强度: {enhanced.hook.strength:.0%} | 效果: {enhanced.hook.expected_effect}")
            print()

        if enhanced.emotion_curve:
            print(f"💓 情感曲线 ({len(enhanced.emotion_curve)}个节点):")
            for e in enhanced.emotion_curve:
                bar = "█" * int(e.intensity * 10)
                print(f"   {e.time_sec:5.1f}s {e.emotion.value:12s} {bar} {e.description}")
            print()

        if enhanced.conflicts:
            print(f"⚔️ 冲突设计 ({len(enhanced.conflicts)}个):")
            for c in enhanced.conflicts:
                status = "已解决" if c.resolved else "未解决"
                print(f"   [{c.conflict_type.value}] {c.description}")
                print(f"   强度: {c.intensity:.0%} | 高峰: {c.peak_time:.1f}s | {status}")
            print()

        if enhanced.character_arcs:
            print(f"👤 角色弧光 ({len(enhanced.character_arcs)}个):")
            for arc in enhanced.character_arcs:
                print(f"   {arc.character_name}: {arc.start_state} → {arc.end_state}")
                print(f"   成长维度: {arc.growth_dimension}")
                for t, desc in arc.key_turning_points:
                    print(f"     {t:.1f}s: {desc}")
            print()

        if enhanced.pacing_map:
            print(f"🎵 节奏图:")
            for t, p in enhanced.pacing_map:
                print(f"   {t:5.1f}s: {p.value}")
            print()

        if enhanced.quality_report:
            qr = enhanced.quality_report
            print(f"📊 质量评估: {qr.overall_score:.1f}/100")
            print(f"   钩子: {qr.hook_score:.0f} | 情感: {qr.emotion_score:.0f} | "
                  f"冲突: {qr.conflict_score:.0f} | 角色: {qr.character_score:.0f} | "
                  f"节奏: {qr.pacing_score:.0f} | 结构: {qr.structure_score:.0f}")
            if qr.strengths:
                print(f"   ✅ 优势: {', '.join(qr.strengths)}")
            if qr.weaknesses:
                print(f"   ⚠️  不足: {', '.join(qr.weaknesses)}")
            if qr.suggestions:
                print(f"   💡 建议:")
                for s in qr.suggestions:
                    print(f"      - {s}")

        print("=" * 60)
