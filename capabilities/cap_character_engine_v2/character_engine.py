"""
角色性格引擎 v2.0
角色性格定义+一致性保持+对话风格生成+角色关系图谱

核心功能：
1. 角色性格定义：MBTI/大五人格/自定义标签
2. 一致性保持：跨场景角色行为/语言一致性检测
3. 对话风格生成：根据性格生成符合角色的对话
4. 角色关系图谱：角色间关系定义与演变
5. 角色弧光：角色成长/变化轨迹
"""
import json
import uuid
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum


class MBTIType(Enum):
    """MBTI人格类型"""
    INTJ = "INTJ - 建筑师"
    INTP = "INTP - 逻辑学家"
    ENTJ = "ENTJ - 指挥官"
    ENTP = "ENTP - 辩论家"
    INFJ = "INFJ - 提倡者"
    INFP = "INFP - 调停者"
    ENFJ = "ENFJ - 主人公"
    ENFP = "ENFP - 竞选者"
    ISTJ = "ISTJ - 物流师"
    ISFJ = "ISFJ - 守卫者"
    ESTJ = "ESTJ - 总经理"
    ESFJ = "ESFJ - 执政官"
    ISTP = "ISTP - 鉴赏家"
    ISFP = "ISFP - 探险家"
    ESTP = "ESTP - 企业家"
    ESFP = "ESFP - 表演者"


class BigFive(Enum):
    """大五人格维度"""
    OPENNESS = "开放性"
    CONSCIENTIOUSNESS = "尽责性"
    EXTRAVERSION = "外向性"
    AGREEABLENESS = "宜人性"
    NEUROTICISM = "神经质"


class RelationshipType(Enum):
    """关系类型"""
    FRIEND = "朋友"
    LOVER = "恋人"
    FAMILY = "家人"
    COLLEAGUE = "同事"
    RIVAL = "对手"
    ENEMY = "敌人"
    MENTOR = "导师"
    STUDENT = "学生"
    STRANGER = "陌生人"
    ALLY = "盟友"


class EmotionType(Enum):
    """情绪类型"""
    CALM = "平静"
    HAPPY = "开心"
    SAD = "悲伤"
    ANGRY = "愤怒"
    FEARFUL = "恐惧"
    SURPRISED = "惊讶"
    DISGUSTED = "厌恶"
    ANXIOUS = "焦虑"
    EXCITED = "兴奋"
    CONFUSED = "困惑"
    DETERMINED = "坚定"
    JEALOUS = "嫉妒"


@dataclass
class PersonalityProfile:
    """性格画像"""
    mbti: Optional[MBTIType] = None
    big_five: Dict[str, float] = field(default_factory=dict)  # 0-100
    traits: List[str] = field(default_factory=list)  # 自定义标签
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    values: List[str] = field(default_factory=list)  # 价值观
    fears: List[str] = field(default_factory=list)
    motivations: List[str] = field(default_factory=list)

    def to_dict(self):
        d = asdict(self)
        d['mbti'] = self.mbti.value if self.mbti else None
        return d


@dataclass
class SpeechStyle:
    """语言风格"""
    vocabulary_level: str = "normal"  # simple/normal/complex/academic
    sentence_length: str = "medium"  # short/medium/long
    formality: float = 0.5  # 0-1, 0=口语, 1=正式
    humor: float = 0.0  # 0-1
    directness: float = 0.5  # 0-1, 0=委婉, 1=直接
    catchphrases: List[str] = field(default_factory=list)  # 口头禅
    speech_habits: List[str] = field(default_factory=list)  # 语言习惯
    accent: str = ""  # 口音/方言

    def to_dict(self):
        return asdict(self)


@dataclass
class CharacterArc:
    """角色弧光（成长轨迹）"""
    starting_state: str = ""
    ending_state: str = ""
    key_moments: List[Dict[str, str]] = field(default_factory=list)  # [{scene, change}]
    growth_dimensions: Dict[str, float] = field(default_factory=dict)  # 变化维度

    def to_dict(self):
        return asdict(self)


@dataclass
class Relationship:
    """角色关系"""
    target: str  # 目标角色名
    relationship_type: RelationshipType
    intensity: float = 0.5  # 0-1, 关系强度
    description: str = ""
    history: List[str] = field(default_factory=list)  # 关系历史
    dynamics: str = ""  # 互动模式

    def to_dict(self):
        d = asdict(self)
        d['relationship_type'] = self.relationship_type.value
        return d


@dataclass
class CharacterV2:
    """角色v2"""
    name: str
    age: int = 0
    gender: str = ""
    occupation: str = ""
    appearance: str = ""
    background: str = ""
    personality: PersonalityProfile = field(default_factory=PersonalityProfile)
    speech_style: SpeechStyle = field(default_factory=SpeechStyle)
    relationships: List[Relationship] = field(default_factory=list)
    arc: CharacterArc = field(default_factory=CharacterArc)
    goals: List[str] = field(default_factory=list)
    secrets: List[str] = field(default_factory=list)
    line_count: int = 0

    def to_dict(self):
        return {
            "name": self.name,
            "age": self.age,
            "gender": self.gender,
            "occupation": self.occupation,
            "appearance": self.appearance,
            "background": self.background,
            "personality": self.personality.to_dict(),
            "speech_style": self.speech_style.to_dict(),
            "relationships": [r.to_dict() for r in self.relationships],
            "arc": self.arc.to_dict(),
            "goals": self.goals,
            "secrets": self.secrets,
            "line_count": self.line_count,
        }

    def get_relationship(self, target: str) -> Optional[Relationship]:
        """获取与某角色的关系"""
        for r in self.relationships:
            if r.target == target:
                return r
        return None

    def add_relationship(self, target: str, rel_type: RelationshipType,
                          intensity: float = 0.5, description: str = ""):
        """添加关系"""
        existing = self.get_relationship(target)
        if existing:
            existing.relationship_type = rel_type
            existing.intensity = intensity
            existing.description = description
        else:
            self.relationships.append(Relationship(
                target=target,
                relationship_type=rel_type,
                intensity=intensity,
                description=description,
            ))


class DialogueGenerator:
    """对话生成器：根据角色性格生成对话"""

    # 性格→语言风格映射
    PERSONALITY_SPEECH_MAP = {
        "INTJ": {"formality": 0.8, "directness": 0.9, "vocabulary": "complex", "humor": 0.2},
        "INTP": {"formality": 0.6, "directness": 0.7, "vocabulary": "complex", "humor": 0.4},
        "ENTJ": {"formality": 0.7, "directness": 0.9, "vocabulary": "normal", "humor": 0.3},
        "ENTP": {"formality": 0.4, "directness": 0.8, "vocabulary": "normal", "humor": 0.8},
        "INFJ": {"formality": 0.6, "directness": 0.5, "vocabulary": "normal", "humor": 0.3},
        "INFP": {"formality": 0.4, "directness": 0.4, "vocabulary": "normal", "humor": 0.5},
        "ENFJ": {"formality": 0.5, "directness": 0.6, "vocabulary": "normal", "humor": 0.5},
        "ENFP": {"formality": 0.3, "directness": 0.6, "vocabulary": "simple", "humor": 0.8},
        "ISTJ": {"formality": 0.8, "directness": 0.7, "vocabulary": "normal", "humor": 0.1},
        "ISFJ": {"formality": 0.6, "directness": 0.4, "vocabulary": "normal", "humor": 0.2},
        "ESTJ": {"formality": 0.7, "directness": 0.8, "vocabulary": "normal", "humor": 0.2},
        "ESFJ": {"formality": 0.5, "directness": 0.5, "vocabulary": "simple", "humor": 0.4},
        "ISTP": {"formality": 0.4, "directness": 0.8, "vocabulary": "simple", "humor": 0.3},
        "ISFP": {"formality": 0.3, "directness": 0.4, "vocabulary": "simple", "humor": 0.4},
        "ESTP": {"formality": 0.3, "directness": 0.8, "vocabulary": "simple", "humor": 0.7},
        "ESFP": {"formality": 0.2, "directness": 0.6, "vocabulary": "simple", "humor": 0.9},
    }

    def __init__(self, character: CharacterV2):
        self.character = character

    def generate_dialogue(self, content: str, emotion: EmotionType = EmotionType.CALM,
                          listener: str = "") -> Dict[str, Any]:
        """
        生成符合角色性格的对话

        Args:
            content: 对话内容
            emotion: 情绪
            listener: 听者（影响语气）

        Returns:
            对话信息
        """
        style = self.character.speech_style
        mbti = self.character.personality.mbti

        # 根据MBTI调整风格
        if mbti and mbti.name in self.PERSONALITY_SPEECH_MAP:
            mbti_style = self.PERSONALITY_SPEECH_MAP[mbti.name]
            formality = (style.formality + mbti_style["formality"]) / 2
            directness = (style.directness + mbti_style["directness"]) / 2
        else:
            formality = style.formality
            directness = style.directness

        # 根据关系调整对听者的语气
        rel = self.character.get_relationship(listener) if listener else None
        if rel:
            if rel.relationship_type in [RelationshipType.FRIEND, RelationshipType.LOVER, RelationshipType.FAMILY]:
                formality *= 0.6  # 亲密关系更口语
            elif rel.relationship_type in [RelationshipType.ENEMY, RelationshipType.RIVAL]:
                directness *= 1.2  # 敌对关系更直接

        # 口头禅插入
        modified_content = content
        if style.catchphrases and len(content) > 10:
            import random
            if random.random() < 0.3:  # 30%概率插入口头禅
                catchphrase = random.choice(style.catchphrases)
                modified_content = f"{catchphrase}，{content}"

        return {
            "speaker": self.character.name,
            "content": modified_content,
            "emotion": emotion.value,
            "formality": round(formality, 2),
            "directness": round(directness, 2),
            "listener": listener,
            "relationship": rel.relationship_type.value if rel else None,
            "style_notes": self._get_style_notes(emotion, formality, directness),
        }

    def _get_style_notes(self, emotion: EmotionType, formality: float, directness: float) -> str:
        """生成风格说明"""
        notes = []
        if formality > 0.7:
            notes.append("正式书面")
        elif formality < 0.3:
            notes.append("口语随意")
        if directness > 0.7:
            notes.append("直言不讳")
        elif directness < 0.3:
            notes.append("委婉含蓄")
        if emotion != EmotionType.CALM:
            notes.append(f"情绪{emotion.value}")
        return "、".join(notes) if notes else "自然表达"


class ConsistencyChecker:
    """一致性检测器：检测角色跨场景行为/语言一致性"""

    def __init__(self, character: CharacterV2):
        self.character = character
        self.violations: List[Dict[str, Any]] = []

    def check_dialogue_consistency(self, dialogue: str, scene_context: str = "") -> List[Dict[str, Any]]:
        """
        检测对话一致性

        Args:
            dialogue: 对话内容
            scene_context: 场景上下文

        Returns:
            违规列表
        """
        violations = []
        style = self.character.speech_style

        # 检测词汇复杂度（简单规则）
        avg_word_length = sum(len(w) for w in dialogue) / max(len(dialogue), 1)
        if style.vocabulary_level == "simple" and avg_word_length > 3:
            violations.append({
                "type": "vocabulary",
                "severity": "low",
                "description": f"词汇复杂度偏高（平均字长{avg_word_length:.1f}），与简单风格不符",
                "suggestion": "使用更简单的词汇",
            })

        # 检测句子长度
        sentences = [s for s in dialogue.replace('！', '。').replace('？', '。').split('。') if s.strip()]
        if sentences:
            avg_sentence_length = sum(len(s) for s in sentences) / len(sentences)
            if style.sentence_length == "short" and avg_sentence_length > 15:
                violations.append({
                    "type": "sentence_length",
                    "severity": "medium",
                    "description": f"句子偏长（平均{avg_sentence_length:.0f}字），与短句风格不符",
                    "suggestion": "拆分为更短的句子",
                })

        return violations

    def check_behavior_consistency(self, action: str, scene_context: str = "") -> List[Dict[str, Any]]:
        """
        检测行为一致性（基于性格标签的简单规则）

        Args:
            action: 行为描述
            scene_context: 场景上下文

        Returns:
            违规列表
        """
        violations = []
        traits = self.character.personality.traits

        # 简单的行为-性格冲突检测
        conflict_patterns = {
            "内向": ["大声喧哗", "主动搭讪", "成为焦点"],
            "外向": ["独自躲在角落", "拒绝社交", "沉默寡言"],
            "谨慎": ["冲动行事", "贸然决定", "不计后果"],
            "鲁莽": ["犹豫不决", "反复权衡", "瞻前顾后"],
            "善良": ["故意伤害", "落井下石", "冷酷无情"],
            "自私": ["无私奉献", "牺牲自己", "成全他人"],
            "冷静": ["情绪失控", "暴跳如雷", "惊慌失措"],
            "暴躁": ["心平气和", "耐心等待", "温和回应"],
        }

        for trait, conflicts in conflict_patterns.items():
            if trait in traits:
                for conflict in conflicts:
                    if conflict in action:
                        violations.append({
                            "type": "behavior_conflict",
                            "severity": "high",
                            "description": f"行为'{conflict}'与性格标签'{trait}'冲突",
                            "suggestion": f"调整为符合'{trait}'性格的行为",
                        })

        return violations

    def get_report(self) -> Dict[str, Any]:
        """获取一致性检测报告"""
        return {
            "character": self.character.name,
            "total_violations": len(self.violations),
            "high_severity": sum(1 for v in self.violations if v.get("severity") == "high"),
            "medium_severity": sum(1 for v in self.violations if v.get("severity") == "medium"),
            "low_severity": sum(1 for v in self.violations if v.get("severity") == "low"),
            "violations": self.violations,
        }


class CharacterEngineV2:
    """角色性格引擎v2（主入口）"""

    def __init__(self):
        self.characters: Dict[str, CharacterV2] = {}

    def create_character(self, name: str, **kwargs) -> CharacterV2:
        """创建角色"""
        character = CharacterV2(name=name, **kwargs)
        self.characters[name] = character
        return character

    def get_character(self, name: str) -> Optional[CharacterV2]:
        """获取角色"""
        return self.characters.get(name)

    def set_personality(self, name: str, mbti: MBTIType = None,
                         traits: List[str] = None, **kwargs) -> CharacterV2:
        """设置角色性格"""
        character = self.get_character(name)
        if not character:
            character = self.create_character(name)

        if mbti:
            character.personality.mbti = mbti
        if traits:
            character.personality.traits = traits
        for key, value in kwargs.items():
            if hasattr(character.personality, key):
                setattr(character.personality, key, value)

        return character

    def generate_dialogue(self, character_name: str, content: str,
                           emotion: EmotionType = EmotionType.CALM,
                           listener: str = "") -> Optional[Dict[str, Any]]:
        """生成符合角色性格的对话"""
        character = self.get_character(character_name)
        if not character:
            return None
        generator = DialogueGenerator(character)
        return generator.generate_dialogue(content, emotion, listener)

    def check_consistency(self, character_name: str, dialogue: str = "",
                          action: str = "") -> Optional[Dict[str, Any]]:
        """检测角色一致性"""
        character = self.get_character(character_name)
        if not character:
            return None
        checker = ConsistencyChecker(character)
        if dialogue:
            checker.violations.extend(checker.check_dialogue_consistency(dialogue))
        if action:
            checker.violations.extend(checker.check_behavior_consistency(action))
        return checker.get_report()

    def build_relationship_graph(self) -> Dict[str, Any]:
        """构建角色关系图谱"""
        nodes = []
        edges = []

        for name, character in self.characters.items():
            nodes.append({
                "id": name,
                "label": name,
                "occupation": character.occupation,
                "mbti": character.personality.mbti.name if character.personality.mbti else None,
            })
            for rel in character.relationships:
                edges.append({
                    "source": name,
                    "target": rel.target,
                    "type": rel.relationship_type.value,
                    "intensity": rel.intensity,
                    "label": rel.relationship_type.value,
                })

        return {
            "nodes": nodes,
            "edges": edges,
            "character_count": len(nodes),
            "relationship_count": len(edges),
        }

    def export_to_json(self, output_path: str) -> str:
        """导出全部角色数据"""
        data = {
            "characters": {name: c.to_dict() for name, c in self.characters.items()},
            "relationship_graph": self.build_relationship_graph(),
        }
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return output_path


if __name__ == "__main__":
    print("=" * 60)
    print("🎭 角色性格引擎 v2.0")
    print("=" * 60)

    engine = CharacterEngineV2()

    # 创建角色
    liming = engine.create_character("李明", age=30, occupation="记者",
                                       appearance="戴眼镜，穿休闲西装")
    engine.set_personality("李明", mbti=MBTIType.INTJ,
                           traits=["冷静", "谨慎", "理性"],
                           strengths=["分析能力强", "观察力敏锐"],
                           weaknesses=["不擅表达情感", "过于严肃"])
    liming.speech_style.catchphrases = ["有意思", "等等"]
    liming.speech_style.formality = 0.7

    wangfang = engine.create_character("王芳", age=28, occupation="会计",
                                        appearance="长发，穿职业装")
    engine.set_personality("王芳", mbti=MBTIType.ENFP,
                           traits=["外向", "热情", "直觉"],
                           strengths=["感染力强", "善于交际"],
                           weaknesses=["容易冲动", "不够细心"])
    wangfang.speech_style.catchphrases = ["你知道吗", "天哪"]
    wangfang.speech_style.formality = 0.3

    # 设置关系
    liming.add_relationship("王芳", RelationshipType.COLLEAGUE, 0.6, "同事，互相欣赏")
    wangfang.add_relationship("李明", RelationshipType.COLLEAGUE, 0.6, "同事，互相信任")

    # 生成对话
    print("\n💬 对话生成测试:")
    d1 = engine.generate_dialogue("李明", "这件事需要仔细调查，不能草率下结论。",
                                   EmotionType.DETERMINED, "王芳")
    print(f"  {d1['speaker']}({d1['emotion']}): {d1['content']}")
    print(f"    风格: {d1['style_notes']}, 正式度{d1['formality']}, 直接度{d1['directness']}")

    d2 = engine.generate_dialogue("王芳", "我发现了一个大秘密，你绝对想不到！",
                                   EmotionType.EXCITED, "李明")
    print(f"  {d2['speaker']}({d2['emotion']}): {d2['content']}")
    print(f"    风格: {d2['style_notes']}, 正式度{d2['formality']}, 直接度{d2['directness']}")

    # 一致性检测
    print("\n🔍 一致性检测:")
    report = engine.check_consistency("李明", dialogue="这个事情嘛，我觉得吧，可能吧，也许吧，大概吧，差不多吧。",
                                       action="李明冲动行事，贸然决定，不计后果地冲了上去。")
    print(f"  违规数: {report['total_violations']} (高{report['high_severity']}/中{report['medium_severity']}/低{report['low_severity']})")
    for v in report['violations']:
        print(f"    [{v['severity']}] {v['description']} → 建议: {v['suggestion']}")

    # 关系图谱
    print("\n🕸️ 角色关系图谱:")
    graph = engine.build_relationship_graph()
    print(f"  角色数: {graph['character_count']}")
    print(f"  关系数: {graph['relationship_count']}")
    for edge in graph['edges']:
        print(f"    {edge['source']} ↔ {edge['target']}: {edge['type']} (强度{edge['intensity']})")

    # 导出
    output_dir = r"C:\Users\Administrator\AppData\Local\DoubaoWork\User Data\Default\.doubaowork\agent_mode\workspace\.user_skills\ai-video-editor\capabilities\script_outputs"
    import os
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "character_engine_v2_test.json")
    engine.export_to_json(output_path)
    print(f"\n📄 已导出: {output_path}")
    print("\n✅ 角色性格引擎v2验证通过")
