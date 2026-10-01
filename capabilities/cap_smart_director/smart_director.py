"""
智能调度器 cap_smart_director
输入剧本(Script) → 输出调度计划(DirectionPlan)
根据每个镜头的情绪/景别/特效建议，自动匹配可用特效和素材
"""
import os
import sys
import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime

# 导入剧本引擎模型（绝对导入，依赖capabilities在sys.path中）
from cap_script_engine.models import Script, Scene, Shot, Emotion, ShotSize


@dataclass
class EffectAssignment:
    """特效分配"""
    shot_id: str
    effect_name: str           # 特效名称
    effect_type: str           # 特效类型(transition/text/visual/overlay)
    params: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0    #匹配置信度


@dataclass
class MaterialAssignment:
    """素材分配"""
    shot_id: str
    material_type: str         # bg/video/image/ai_generated
    source: str                # 素材来源或AI生成提示词
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ShotDirection:
    """单镜头调度指令"""
    shot_id: str
    start_time: float
    duration: float
    effects: List[EffectAssignment] = field(default_factory=list)
    materials: List[MaterialAssignment] = field(default_factory=list)
    transition_in: str = "硬切"
    transition_out: str = "硬切"
    track_hint: str = ""       # 轨道建议


@dataclass
class DirectionPlan:
    """完整调度计划"""
    script_title: str
    total_duration: float
    shot_directions: List[ShotDirection] = field(default_factory=list)
    bgm_mood: str = ""
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "script_title": self.script_title,
            "total_duration": self.total_duration,
            "bgm_mood": self.bgm_mood,
            "notes": self.notes,
            "shots": [
                {
                    "shot_id": sd.shot_id,
                    "start_time": sd.start_time,
                    "duration": sd.duration,
                    "transition_in": sd.transition_in,
                    "transition_out": sd.transition_out,
                    "track_hint": sd.track_hint,
                    "effects": [{"name": e.effect_name, "type": e.effect_type, "params": e.params, "confidence": e.confidence} for e in sd.effects],
                    "materials": [{"type": m.material_type, "source": m.source, "params": m.params} for m in sd.materials],
                } for sd in self.shot_directions
            ],
        }

    def summary(self) -> str:
        """调度计划摘要"""
        effect_counts = {}
        for sd in self.shot_directions:
            for e in sd.effects:
                effect_counts[e.effect_name] = effect_counts.get(e.effect_name, 0) + 1
        lines = [
            f"=== 调度计划: {self.script_title} ===",
            f"总时长: {self.total_duration:.1f}s",
            f"镜头数: {len(self.shot_directions)}",
            f"配乐情绪: {self.bgm_mood}",
            f"",
            f"特效分配统计:",
        ]
        for name, count in sorted(effect_counts.items(), key=lambda x: -x[1]):
            lines.append(f"  {name}: {count}次")
        return "\n".join(lines)


class SmartDirector:
    """智能调度器"""

    # 特效库（名称→类型→适用场景）
    EFFECT_LIBRARY = {
        "蒙版快闪": {"type": "transition", "emotions": [Emotion.HOOK, Emotion.CLIMAX], "shot_sizes": [ShotSize.CLOSEUP, ShotSize.MEDIUM]},
        "发光轮廓": {"type": "visual", "emotions": [Emotion.CLIMAX, Emotion.HOOK], "shot_sizes": [ShotSize.CLOSEUP]},
        "字幕条动画": {"type": "text", "emotions": [Emotion.TENSION, Emotion.CALM], "shot_sizes": [ShotSize.MEDIUM, ShotSize.WIDE]},
        "人物介绍卡": {"type": "overlay", "emotions": [Emotion.TENSION, Emotion.CALM], "shot_sizes": [ShotSize.MEDIUM]},
        "文字擦开": {"type": "text", "emotions": [Emotion.RELIEF, Emotion.RESOLUTION], "shot_sizes": [ShotSize.MEDIUM, ShotSize.WIDE]},
        "背景滑入": {"type": "transition", "emotions": [Emotion.RELIEF, Emotion.CALM], "shot_sizes": [ShotSize.WIDE]},
        "百叶窗分屏": {"type": "transition", "emotions": [Emotion.CLIMAX, Emotion.TENSION], "shot_sizes": [ShotSize.WIDE, ShotSize.MEDIUM]},
        "文字排版": {"type": "text", "emotions": [Emotion.CALM, Emotion.RELIEF], "shot_sizes": [ShotSize.MEDIUM, ShotSize.WIDE]},
        "日期标签": {"type": "overlay", "emotions": [Emotion.CALM], "shot_sizes": [ShotSize.WIDE, ShotSize.MEDIUM]},
    }

    # 转场映射
    TRANSITION_MAP = {
        "硬切": "cut",
        "快切": "quick_cut",
        "淡入淡出": "fade",
        "蒙版快闪": "mask_flash",
        "百叶窗": "blinds",
    }

    def __init__(self):
        self.effect_library = self.EFFECT_LIBRARY

    def direct(self, script: Script) -> DirectionPlan:
        """
        根据剧本生成调度计划

        Args:
            script: 剧本引擎输出的Script对象

        Returns:
            DirectionPlan调度计划
        """
        plan = DirectionPlan(
            script_title=script.title,
            total_duration=script.total_duration,
            bgm_mood=script.bgm_mood,
            notes=f"基于剧本自动调度，共{len(script.scenes)}幕{script.total_shots}镜头",
        )

        for scene in script.scenes:
            for shot in scene.shots:
                sd = self._direct_shot(shot, scene)
                plan.shot_directions.append(sd)

        return plan

    def _direct_shot(self, shot: Shot, scene: Scene) -> ShotDirection:
        """调度单个镜头"""
        sd = ShotDirection(
            shot_id=shot.shot_id,
            start_time=shot.start_time,
            duration=shot.duration,
            transition_in=scene.transition_in,
            transition_out=scene.transition_out,
        )

        # 1. 特效匹配：优先使用shot.effect_hint，否则根据情绪/景别匹配
        if shot.effect_hint:
            # 解析effect_hint（可能是"特效A+特效B"格式）
            for hint in shot.effect_hint.replace("+", ",").split(","):
                hint = hint.strip()
                matched = self._match_effect_by_name(hint, shot, scene)
                if matched:
                    sd.effects.append(matched)
        else:
            # 自动匹配：根据情绪和景别
            matched = self._match_effect_auto(shot, scene)
            if matched:
                sd.effects.append(matched)

        # 2. 素材分配：根据visual_ref和shot内容
        if shot.visual_ref:
            sd.materials.append(MaterialAssignment(
                shot_id=shot.shot_id,
                material_type="ai_generated",
                source=shot.visual_ref,
                params={"width": 1080, "height": 1920, "model": "sd_xl_turbo"},
            ))
        else:
            # 默认背景
            sd.materials.append(MaterialAssignment(
                shot_id=shot.shot_id,
                material_type="bg",
                source=f"auto_bg_{scene.emotion.value}",
                params={"style": "gradient"},
            ))

        # 3. 轨道建议
        if any(e.effect_type == "text" for e in sd.effects):
            sd.track_hint = "text+bg"
        elif any(e.effect_type == "overlay" for e in sd.effects):
            sd.track_hint = "overlay+bg"
        else:
            sd.track_hint = "bg"

        return sd

    def _match_effect_by_name(self, name: str, shot: Shot, scene: Scene) -> Optional[EffectAssignment]:
        """按名称匹配特效"""
        for effect_name, info in self.effect_library.items():
            if effect_name in name or name in effect_name:
                return EffectAssignment(
                    shot_id=shot.shot_id,
                    effect_name=effect_name,
                    effect_type=info["type"],
                    confidence=0.9,
                )
        return None

    def _match_effect_auto(self, shot: Shot, scene: Scene) -> Optional[EffectAssignment]:
        """自动匹配特效（基于情绪+景别打分）"""
        best = None
        best_score = 0
        for name, info in self.effect_library.items():
            score = 0
            if shot.emotion in info["emotions"]:
                score += 0.6
            if shot.shot_size in info["shot_sizes"]:
                score += 0.4
            if score > best_score:
                best_score = score
                best = (name, info)
        if best and best_score > 0.3:
            return EffectAssignment(
                shot_id=shot.shot_id,
                effect_name=best[0],
                effect_type=best[1]["type"],
                confidence=best_score,
            )
        return None

    def save(self, plan: DirectionPlan, output_dir: str) -> str:
        """保存调度计划"""
        os.makedirs(output_dir, exist_ok=True)
        path = os.path.join(output_dir, f"direction_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(plan.to_dict(), f, ensure_ascii=False, indent=2)
        return path


if __name__ == "__main__":
    print("=" * 60)
    print("智能调度器 cap_smart_director")
    print("=" * 60)

    # 先用剧本引擎生成剧本
    from script_engine import ScriptEngine, VideoGenre
    engine = ScriptEngine()
    script = engine.generate(
        idea="做一条探店视频，介绍一家藏在巷子里的火锅店",
        genre=VideoGenre.EXPLORATION,
        duration=60.0,
    )
    print(f"\n剧本: {script.title} ({script.total_shots}镜头)")

    # 调度
    director = SmartDirector()
    plan = director.direct(script)

    print(f"\n{plan.summary()}")

    print("\n前3镜头调度详情:")
    for sd in plan.shot_directions[:3]:
        print(f"\n  {sd.shot_id} ({sd.start_time:.1f}s+{sd.duration:.1f}s)")
        print(f"    转场: {sd.transition_in}→{sd.transition_out}")
        print(f"    轨道: {sd.track_hint}")
        for e in sd.effects:
            print(f"    特效: {e.effect_name} [{e.effect_type}] (置信度{e.confidence:.0%})")
        for m in sd.materials:
            print(f"    素材: {m.material_type} - {m.source[:30]}")

    # 保存
    out_dir = os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "script_outputs")
    path = director.save(plan, out_dir)
    print(f"\n✅ 调度计划已保存: {path}")
