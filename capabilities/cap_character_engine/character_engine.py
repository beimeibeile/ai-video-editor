"""
角色性格引擎 v1.0
角色性格建模 + 关系图谱 + 分剧情重塑 + 一致性检查

核心功能：
1. 角色性格建模：基于对话和动作分析角色性格特征（MBTI/大五人格）
2. 角色关系图谱：角色之间的关系（朋友/敌人/恋人/家人/同事等）
3. 分剧情重塑：按场景/幕/集拆分，支持多轮打磨
4. 角色一致性检查：确保角色在不同场景中的性格和行为一致
5. 角色弧光分析：角色在故事中的成长和变化

使用方法：
    from character_engine import CharacterEngine
    engine = CharacterEngine()
    personalities = engine.analyze_personality(script)
    relationships = engine.build_relationship_graph(script)
    consistency = engine.check_consistency(script)
"""
import os
import re
import json
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum


class PersonalityTrait(Enum):
    """性格特质（大五人格简化版）"""
    OPENNESS = "开放性"  # 想象力/好奇心/创造力
    CONSCIENTIOUSNESS = "尽责性"  # 自律/有条理/可靠
    EXTRAVERSION = "外向性"  # 社交/活力/乐观
    AGREEABLENESS = "宜人性"  # 友善/合作/信任
    NEUROTICISM = "神经质"  # 情绪不稳定/焦虑/敏感


class RelationshipType(Enum):
    """关系类型"""
    FRIEND = "朋友"
    ENEMY = "敌人"
    LOVER = "恋人"
    FAMILY = "家人"
    COLLEAGUE = "同事"
    MENTOR = "导师"
    RIVAL = "竞争对手"
    STRANGER = "陌生人"
    ALLY = "盟友"


class Emotion(Enum):
    """情绪"""
    HAPPY = "开心"
    SAD = "悲伤"
    ANGRY = "愤怒"
    FEARFUL = "恐惧"
    SURPRISED = "惊讶"
    DISGUSTED = "厌恶"
    NEUTRAL = "平静"
    EXCITED = "兴奋"
    ANXIOUS = "焦虑"
    CONFIDENT = "自信"
    CONFUSED = "困惑"
    DETERMINED = "坚定"


@dataclass
class PersonalityProfile:
    """角色性格画像"""
    character_name: str
    traits: Dict[str, float] = field(default_factory=dict)  # 特质→分数(0-1)
    mbti: str = ""  # MBTI类型（如INTJ/ENFP）
    summary: str = ""  # 性格总结
    keywords: List[str] = field(default_factory=list)  # 性格关键词
    speech_style: str = ""  # 说话风格
    behavior_patterns: List[str] = field(default_factory=list)  # 行为模式


@dataclass
class Relationship:
    """角色关系"""
    character_a: str
    character_b: str
    relationship_type: str
    strength: float = 0.5  # 关系强度(0-1)
    description: str = ""
    interactions: List[str] = field(default_factory=list)  # 互动记录


@dataclass
class CharacterArc:
    """角色弧光"""
    character_name: str
    start_state: str = ""  # 开始状态
    end_state: str = ""  # 结束状态
    key_moments: List[str] = field(default_factory=list)  # 关键时刻
    growth: str = ""  # 成长/变化
    arc_type: str = ""  # 弧光类型（成长/堕落/救赎/转变）


@dataclass
class ConsistencyIssue:
    """一致性问题"""
    character_name: str
    issue_type: str  # personality/speech/behavior/motivation
    description: str
    scene_a: str
    scene_b: str
    severity: str = "warning"  # info/warning/error


class CharacterEngine:
    """角色性格引擎"""

    # 性格关键词映射
    TRAIT_KEYWORDS = {
        "开放性": ["好奇", "想象", "创造", "冒险", "新颖", "艺术", "思考", "梦想", "探索", "开放"],
        "尽责性": ["认真", "负责", "有条理", "自律", "计划", "可靠", "勤奋", "仔细", "严谨", "守时"],
        "外向性": ["活泼", "开朗", "社交", "热情", "健谈", "乐观", "活力", "主动", "大胆", "表现"],
        "宜人性": ["善良", "友善", "合作", "信任", "温柔", "体贴", "包容", "谦虚", "热心", "真诚"],
        "神经质": ["焦虑", "紧张", "敏感", "情绪化", "担忧", "易怒", "脆弱", "悲观", "自卑", "犹豫"],
    }

    # 情绪关键词映射
    EMOTION_KEYWORDS = {
        "开心": ["开心", "高兴", "快乐", "笑", "愉快", "喜悦", "兴奋", "幸福"],
        "悲伤": ["悲伤", "难过", "哭", "痛苦", "失落", "沮丧", "哀伤", "忧郁"],
        "愤怒": ["愤怒", "生气", "怒", "火", "暴躁", "恼火", "气愤", "怒吼"],
        "恐惧": ["恐惧", "害怕", "紧张", "担心", "焦虑", "惊恐", "畏惧", "胆怯"],
        "惊讶": ["惊讶", "吃惊", "震惊", "意外", "诧异", "愕然", "难以置信"],
        "兴奋": ["兴奋", "激动", "热血", "振奋", "亢奋", "热情高涨"],
        "自信": ["自信", "坚定", "从容", "淡定", "胸有成竹", "笃定"],
        "困惑": ["困惑", "迷茫", "疑惑", "不解", "犹豫", "纠结", "茫然"],
    }

    def __init__(self):
        self.personalities: Dict[str, PersonalityProfile] = {}
        self.relationships: List[Relationship] = []
        self.character_arcs: Dict[str, CharacterArc] = {}

    def analyze_personality(self, script) -> Dict[str, PersonalityProfile]:
        """
        分析角色性格

        Args:
            script: DramaScript对象或剧本文本

        Returns:
            角色名→性格画像
        """
        # 兼容文本输入
        if isinstance(script, str):
            from cap_drama_engine import DramaEngine
            engine = DramaEngine()
            script = engine.parse_script(script)

        personalities = {}

        for char_name, char in script.characters.items():
            profile = PersonalityProfile(character_name=char_name)

            # 收集角色的所有对话和动作
            dialogues = []
            actions = []
            for scene in script.scenes:
                for beat in scene.beats:
                    if beat.character == char_name:
                        if beat.beat_type == "dialogue":
                            dialogues.append(beat.content)
                        elif beat.beat_type == "action":
                            actions.append(beat.content)

            # 基于关键词分析性格特质
            all_text = " ".join(dialogues + actions)
            for trait, keywords in self.TRAIT_KEYWORDS.items():
                score = sum(all_text.count(kw) for kw in keywords)
                # 归一化到0-1
                profile.traits[trait] = min(1.0, score / 5.0) if score > 0 else 0.2

            # 生成MBTI（简化版）
            profile.mbti = self._calculate_mbti(profile.traits)

            # 性格总结
            dominant_traits = sorted(profile.traits.items(), key=lambda x: x[1], reverse=True)[:2]
            profile.summary = f"{char_name}的主要性格特征是{dominant_traits[0][0]}和{dominant_traits[1][0]}，MBTI类型为{profile.mbti}。"

            # 说话风格
            if dialogues:
                avg_length = sum(len(d) for d in dialogues) / len(dialogues)
                if avg_length > 30:
                    profile.speech_style = "话多且详细，喜欢表达自己的想法"
                elif avg_length < 10:
                    profile.speech_style = "话少简洁，言简意赅"
                else:
                    profile.speech_style = "说话适中，表达清晰"

            # 行为模式
            if actions:
                profile.behavior_patterns = [a[:30] for a in actions[:3]]

            personalities[char_name] = profile
            self.personalities[char_name] = profile

        print(f"✅ 性格分析完成: {len(personalities)}个角色")
        for name, p in personalities.items():
            print(f"  {name}: {p.mbti} - {p.summary[:30]}...")

        return personalities

    def _calculate_mbti(self, traits: Dict[str, float]) -> str:
        """基于大五人格计算MBTI（简化版）"""
        e = traits.get("外向性", 0.5)
        a = traits.get("宜人性", 0.5)
        c = traits.get("尽责性", 0.5)
        o = traits.get("开放性", 0.5)
        n = traits.get("神经质", 0.5)

        # E/I
        ei = "E" if e > 0.5 else "I"
        # S/N (简化：开放性高→N)
        sn = "N" if o > 0.5 else "S"
        # T/F (简化：宜人性高→F)
        tf = "F" if a > 0.5 else "T"
        # J/P (简化：尽责性高→J)
        jp = "J" if c > 0.5 else "P"

        return ei + sn + tf + jp

    def build_relationship_graph(self, script) -> List[Relationship]:
        """
        构建角色关系图谱

        Args:
            script: DramaScript对象

        Returns:
            关系列表
        """
        relationships = []
        character_names = list(script.characters.keys())

        # 分析同一场景中的角色互动
        scene_interactions = {}
        for scene in script.scenes:
            scene_chars = set()
            for beat in scene.beats:
                if beat.character:
                    scene_chars.add(beat.character)

            # 同一场景中的角色对
            chars_list = list(scene_chars)
            for i in range(len(chars_list)):
                for j in range(i+1, len(chars_list)):
                    pair = tuple(sorted([chars_list[i], chars_list[j]]))
                    if pair not in scene_interactions:
                        scene_interactions[pair] = []
                    scene_interactions[pair].append(scene.scene_id)

        # 构建关系
        for (a, b), scenes in scene_interactions.items():
            rel = Relationship(
                character_a=a,
                character_b=b,
                relationship_type="互动",
                strength=min(1.0, len(scenes) / 3.0),
                description=f"{a}和{b}在{len(scenes)}个场景中有互动",
                interactions=scenes,
            )

            # 简单推断关系类型（基于对话内容）
            rel.relationship_type = self._infer_relationship(script, a, b)
            relationships.append(rel)

        self.relationships = relationships
        print(f"✅ 关系图谱构建完成: {len(relationships)}对关系")
        for r in relationships:
            print(f"  {r.character_a} ↔ {r.character_b}: {r.relationship_type} (强度:{r.strength:.1f})")

        return relationships

    def _infer_relationship(self, script, char_a: str, char_b: str) -> str:
        """基于对话内容推断关系类型"""
        # 收集两人的对话
        dialogue_text = ""
        for scene in script.scenes:
            for beat in scene.beats:
                if beat.character in [char_a, char_b]:
                    dialogue_text += beat.content + " "

        # 关键词匹配
        if any(kw in dialogue_text for kw in ["爱", "喜欢", "想你", "亲爱的", "宝贝"]):
            return "恋人"
        if any(kw in dialogue_text for kw in ["爸", "妈", "儿子", "女儿", "哥", "姐", "弟", "妹"]):
            return "家人"
        if any(kw in dialogue_text for kw in ["恨", "讨厌", "滚", "闭嘴", "该死"]):
            return "敌人"
        if any(kw in dialogue_text for kw in ["朋友", "兄弟", "闺蜜", "哥们", "一起"]):
            return "朋友"
        if any(kw in dialogue_text for kw in ["老师", "学生", "教", "学", "指导"]):
            return "导师"
        if any(kw in dialogue_text for kw in ["同事", "工作", "项目", "老板", "员工"]):
            return "同事"
        return "互动"

    def check_consistency(self, script) -> List[ConsistencyIssue]:
        """
        检查角色一致性

        Args:
            script: DramaScript对象

        Returns:
            一致性问题列表
        """
        issues = []

        for char_name in script.characters:
            # 收集角色在不同场景的情绪
            scene_emotions = {}
            for scene in script.scenes:
                emotions = []
                for beat in scene.beats:
                    if beat.character == char_name:
                        if beat.emotion:
                            emotions.append(beat.emotion)
                        # 从对话内容推断情绪
                        for emo, keywords in self.EMOTION_KEYWORDS.items():
                            if any(kw in beat.content for kw in keywords):
                                emotions.append(emo)
                                break
                if emotions:
                    scene_emotions[scene.scene_id] = emotions

            # 检查情绪突变（相邻场景情绪差异过大）
            scenes_list = sorted(scene_emotions.keys())
            for i in range(len(scenes_list) - 1):
                s1 = scenes_list[i]
                s2 = scenes_list[i+1]
                e1 = set(scene_emotions[s1])
                e2 = set(scene_emotions[s2])

                # 检查是否有极端情绪变化（如从开心直接变愤怒）
                positive = {"开心", "兴奋", "自信"}
                negative = {"愤怒", "悲伤", "恐惧"}
                if (e1 & positive and e2 & negative) or (e1 & negative and e2 & positive):
                    issues.append(ConsistencyIssue(
                        character_name=char_name,
                        issue_type="emotion",
                        description=f"{char_name}在{s1}和{s2}之间情绪突变（{','.join(e1)} → {','.join(e2)}），需要过渡场景",
                        scene_a=s1,
                        scene_b=s2,
                        severity="warning",
                    ))

        print(f"✅ 一致性检查完成: 发现{len(issues)}个问题")
        for issue in issues:
            print(f"  [{issue.severity}] {issue.character_name}: {issue.description[:50]}...")

        return issues

    def analyze_character_arc(self, script) -> Dict[str, CharacterArc]:
        """
        分析角色弧光

        Args:
            script: DramaScript对象

        Returns:
            角色名→角色弧光
        """
        arcs = {}

        for char_name in script.characters:
            arc = CharacterArc(character_name=char_name)

            # 收集角色在第一个和最后一个场景的状态
            first_scene = None
            last_scene = None
            for scene in script.scenes:
                for beat in scene.beats:
                    if beat.character == char_name:
                        if first_scene is None:
                            first_scene = scene
                        last_scene = scene
                        break

            if first_scene:
                arc.start_state = f"在{first_scene.title}中首次出场"
            if last_scene:
                arc.end_state = f"在{last_scene.title}中最后出场"

            # 关键时刻（角色有重要对话或动作的场景）
            key_moments = []
            for scene in script.scenes:
                for beat in scene.beats:
                    if beat.character == char_name:
                        if len(beat.content) > 20 or beat.emotion in ["愤怒", "悲伤", "兴奋", "坚定"]:
                            key_moments.append(f"{scene.scene_id}: {beat.content[:30]}...")
                            break
            arc.key_moments = key_moments[:5]

            # 简单判断弧光类型
            if len(key_moments) >= 3:
                arc.arc_type = "成长型"
                arc.growth = f"{char_name}经历了{len(key_moments)}个关键时刻，有明显的角色成长"
            else:
                arc.arc_type = "扁平型"
                arc.growth = f"{char_name}的角色变化不大，较为稳定"

            arcs[char_name] = arc
            self.character_arcs[char_name] = arc

        print(f"✅ 角色弧光分析完成: {len(arcs)}个角色")
        for name, arc in arcs.items():
            print(f"  {name}: {arc.arc_type} - {arc.growth[:30]}...")

        return arcs

    def export_report(self, output_path: str, script=None):
        """导出角色分析报告"""
        if script is None:
            script = self.script if hasattr(self, 'script') else None

        report = {
            "generated_at": __import__("datetime").datetime.now().isoformat(),
            "personalities": {k: asdict(v) for k, v in self.personalities.items()},
            "relationships": [asdict(r) for r in self.relationships],
            "character_arcs": {k: asdict(v) for k, v in self.character_arcs.items()},
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"✅ 角色分析报告已导出: {output_path}")


if __name__ == "__main__":
    print("=" * 60)
    print("角色性格引擎 v1.0")
    print("=" * 60)

    # 测试用例
    test_script = """测试剧本

内景 咖啡馆 - 日

小明
（紧张）
你好，我是小明，很高兴认识你。

小红
（微笑）
你好，我也很高兴认识你。

小明
（兴奋）
这家店的咖啡真的很棒！

小红
（开心）
是啊，我也很喜欢这里。

外景 公园 - 黄昏

小明
（坚定）
我想和你一起走下去。

小红
（感动）
我也是。
"""

    from cap_drama_engine import DramaEngine
    drama = DramaEngine()
    script = drama.parse_script(test_script)

    engine = CharacterEngine()
    personalities = engine.analyze_personality(script)
    relationships = engine.build_relationship_graph(script)
    issues = engine.check_consistency(script)
    arcs = engine.analyze_character_arc(script)
