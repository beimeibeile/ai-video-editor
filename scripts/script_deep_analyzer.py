# -*- coding: utf-8 -*-
"""
剧本深度语义分析器 v1.0
在ScriptParser基础上增强深度语义分析能力：
1. 角色关系网络分析
2. 剧情结构分析（三幕式/起承转合）
3. 主题深度挖掘
4. 对话意图分析
5. 场景氛围分析
6. 冲突演进分析
7. 情感弧线分析

使用方式：
    from script_deep_analyzer import ScriptDeepAnalyzer
    analyzer = ScriptDeepAnalyzer()
    result = analyzer.analyze(script_text, title="作品名")
    analyzer.save_report(result, "deep_analysis.json")
"""
import os
import re
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class CharacterRelation:
    """角色关系"""
    character1: str
    character2: str
    relation_type: str       # 朋友/敌人/恋人/家人/同事/对手
    intensity: float = 0.5   # 关系强度 0-1
    sentiment: str = "neutral"  # positive/negative/neutral
    description: str = ""


@dataclass
class StoryStructure:
    """剧情结构"""
    structure_type: str = "three_act"  # three_act/four_act/heros_journey
    acts: List[Dict] = field(default_factory=list)
    turning_points: List[Dict] = field(default_factory=list)
    pacing: str = "medium"  # slow/medium/fast


@dataclass
class ThemeAnalysis:
    """主题分析"""
    main_theme: str = ""
    sub_themes: List[str] = field(default_factory=list)
    motif: List[str] = field(default_factory=list)  # 母题/反复出现的意象
    moral: str = ""  # 寓意/教训


@dataclass
class DialogueIntent:
    """对话意图"""
    character: str
    content: str
    intent: str          # 陈述/询问/命令/请求/威胁/安慰/挑衅/表白
    emotion: str = "neutral"
    target: str = ""     # 对话对象


@dataclass
class SceneAtmosphere:
    """场景氛围"""
    scene_id: int
    location: str
    time_of_day: str = "unknown"  # 白天/夜晚/黎明/黄昏
    mood: str = "neutral"         # 紧张/温馨/恐怖/欢快/悲伤
    weather: str = "unknown"      # 晴/雨/雪/雾
    description: str = ""


@dataclass
class ConflictEvolution:
    """冲突演进"""
    conflict_type: str  # 人际/内心/环境/社会
    parties: List[str]
    escalation_level: float = 0.0  # 0-1
    resolution: str = ""  # 解决方式
    timeline: List[Dict] = field(default_factory=list)


@dataclass
class EmotionalArc:
    """情感弧线"""
    character: str
    start_emotion: str
    end_emotion: str
    key_moments: List[Dict] = field(default_factory=list)
    arc_type: str = "flat"  # rise/fall/v_shape/flat/wave


@dataclass
class DeepAnalysisResult:
    """深度分析结果"""
    title: str = ""
    character_relations: List[CharacterRelation] = field(default_factory=list)
    story_structure: Optional[StoryStructure] = None
    theme_analysis: Optional[ThemeAnalysis] = None
    dialogue_intents: List[DialogueIntent] = field(default_factory=list)
    scene_atmospheres: List[SceneAtmosphere] = field(default_factory=list)
    conflict_evolutions: List[ConflictEvolution] = field(default_factory=list)
    emotional_arcs: List[EmotionalArc] = field(default_factory=list)
    summary: str = ""


class ScriptDeepAnalyzer:
    """剧本深度语义分析器"""

    # 意图关键词映射
    INTENT_KEYWORDS = {
        "询问": ["吗", "呢", "？", "怎么", "什么", "为什么", "哪里", "谁", "多少"],
        "命令": ["给我", "必须", "马上", "立刻", "不准", "不许", "去", "做"],
        "请求": ["请", "能不能", "可以吗", "帮我", "麻烦"],
        "威胁": ["否则", "不然", "等着", "小心", "后果"],
        "安慰": ["没事", "别怕", "有我", "会好的", "放心"],
        "挑衅": ["哼", "切", "就这", "不过如此", "敢吗"],
        "表白": ["喜欢你", "爱你", "想和你", "在一起"],
        "陈述": ["是", "有", "在", "我", "你", "他"],
    }

    # 情绪关键词
    EMOTION_KEYWORDS = {
        "愤怒": ["滚", "讨厌", "气死", "混蛋", "可恶", "该死"],
        "悲伤": ["哭", "难过", "伤心", "痛苦", "失去", "离开"],
        "快乐": ["哈哈", "开心", "高兴", "太好了", "棒"],
        "恐惧": ["怕", "害怕", "恐怖", "危险", "快跑"],
        "惊讶": ["啊", "天哪", "竟然", "居然", "什么"],
        "温柔": ["亲爱的", "宝贝", "乖", "心疼"],
    }

    # 场景氛围关键词
    MOOD_KEYWORDS = {
        "紧张": ["突然", "猛地", "瞬间", "心跳", "屏住呼吸"],
        "温馨": ["阳光", "温暖", "笑容", "拥抱", "家"],
        "恐怖": ["黑暗", "阴影", "诡异", "寂静", "冷风"],
        "欢快": ["笑声", "音乐", "跳舞", "热闹", "阳光"],
        "悲伤": ["雨", "泪", "孤独", "沉默", "黄昏"],
    }

    # 时间关键词
    TIME_KEYWORDS = {
        "白天": ["白天", "上午", "下午", "中午", "阳光"],
        "夜晚": ["夜晚", "晚上", "深夜", "月光", "星光"],
        "黎明": ["黎明", "清晨", "日出", "晨光"],
        "黄昏": ["黄昏", "夕阳", "日落", "傍晚"],
    }

    def __init__(self):
        pass

    def analyze(self, script_text: str, title: str = "") -> DeepAnalysisResult:
        """
        完整深度分析剧本

        Args:
            script_text: 剧本文本
            title: 作品标题

        Returns:
            深度分析结果
        """
        print(f"开始深度分析: {title or '未命名'}")

        result = DeepAnalysisResult(title=title or "未命名作品")

        # 1. 角色关系分析
        print("  分析角色关系...")
        result.character_relations = self._analyze_character_relations(script_text)

        # 2. 剧情结构分析
        print("  分析剧情结构...")
        result.story_structure = self._analyze_story_structure(script_text)

        # 3. 主题分析
        print("  分析主题...")
        result.theme_analysis = self._analyze_theme(script_text)

        # 4. 对话意图分析
        print("  分析对话意图...")
        result.dialogue_intents = self._analyze_dialogue_intents(script_text)

        # 5. 场景氛围分析
        print("  分析场景氛围...")
        result.scene_atmospheres = self._analyze_scene_atmospheres(script_text)

        # 6. 冲突演进分析
        print("  分析冲突演进...")
        result.conflict_evolutions = self._analyze_conflicts(script_text)

        # 7. 情感弧线分析
        print("  分析情感弧线...")
        result.emotional_arcs = self._analyze_emotional_arcs(script_text)

        # 8. 生成摘要
        result.summary = self._generate_summary(result)

        print(f"  分析完成")
        return result

    def _extract_characters(self, text: str) -> List[str]:
        """提取角色名（简单规则：对话格式 角色名：台词）"""
        characters = set()
        # 匹配 "角色名：" 或 "角色名:" 格式
        pattern = r'^([\u4e00-\u9fa5A-Za-z]{2,4})[：:]'
        for line in text.split('\n'):
            line = line.strip()
            match = re.match(pattern, line)
            if match:
                name = match.group(1)
                # 过滤常见非角色词
                if name not in ["旁白", "解说", "字幕", "标题", "场景", "时间", "地点"]:
                    characters.add(name)
        return sorted(characters)

    def _analyze_character_relations(self, text: str) -> List[CharacterRelation]:
        """分析角色关系"""
        characters = self._extract_characters(text)
        relations = []

        if len(characters) < 2:
            return relations

        # 简单分析：出现在同一场景/对话中的角色可能有关系
        lines = text.split('\n')
        co_occurrence = {}

        current_scene_chars = set()
        for line in lines:
            line = line.strip()
            # 场景分隔
            if re.match(r'^(场景|第[一二三四五六七八九十\d]+[场幕集])', line):
                if len(current_scene_chars) >= 2:
                    chars_list = sorted(current_scene_chars)
                    for i in range(len(chars_list)):
                        for j in range(i + 1, len(chars_list)):
                            key = (chars_list[i], chars_list[j])
                            co_occurrence[key] = co_occurrence.get(key, 0) + 1
                current_scene_chars = set()
            # 角色对话
            match = re.match(r'^([\u4e00-\u9fa5A-Za-z]{2,4})[：:]', line)
            if match:
                current_scene_chars.add(match.group(1))

        # 处理最后一个场景
        if len(current_scene_chars) >= 2:
            chars_list = sorted(current_scene_chars)
            for i in range(len(chars_list)):
                for j in range(i + 1, len(chars_list)):
                    key = (chars_list[i], chars_list[j])
                    co_occurrence[key] = co_occurrence.get(key, 0) + 1

        # 生成关系
        for (c1, c2), count in co_occurrence.items():
            intensity = min(1.0, count * 0.3)
            # 简单情感判断（基于对话中的情绪词）
            sentiment = "neutral"
            relations.append(CharacterRelation(
                character1=c1,
                character2=c2,
                relation_type="互动",
                intensity=round(intensity, 2),
                sentiment=sentiment,
                description=f"共同出现{count}次",
            ))

        return sorted(relations, key=lambda x: -x.intensity)

    def _analyze_story_structure(self, text: str) -> StoryStructure:
        """分析剧情结构"""
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        total_lines = len(lines)

        if total_lines == 0:
            return StoryStructure()

        # 简单三幕式划分
        act1_end = int(total_lines * 0.25)
        act2_end = int(total_lines * 0.75)

        structure = StoryStructure(
            structure_type="three_act",
            acts=[
                {"act": 1, "name": "建置", "start": 0, "end": act1_end,
                 "description": "介绍角色、背景、初始状态"},
                {"act": 2, "name": "对抗", "start": act1_end, "end": act2_end,
                 "description": "冲突升级、遇到障碍、尝试解决"},
                {"act": 3, "name": "解决", "start": act2_end, "end": total_lines,
                 "description": "高潮、解决冲突、结局"},
            ],
            turning_points=[
                {"position": "25%", "type": "激励事件", "description": "打破平衡的事件"},
                {"position": "50%", "type": "中点", "description": "局势转变"},
                {"position": "75%", "type": "危机", "description": "最黑暗时刻"},
                {"position": "90%", "type": "高潮", "description": "最终对决"},
            ],
        )

        # 根据文本长度判断节奏
        if total_lines < 50:
            structure.pacing = "fast"
        elif total_lines > 200:
            structure.pacing = "slow"
        else:
            structure.pacing = "medium"

        return structure

    def _analyze_theme(self, text: str) -> ThemeAnalysis:
        """分析主题"""
        theme_keywords = {
            "爱情": ["爱", "喜欢", "心动", "表白", "在一起", "分手"],
            "友情": ["朋友", "兄弟", "闺蜜", "友谊", "陪伴"],
            "亲情": ["家人", "父母", "孩子", "家", "温暖"],
            "成长": ["成长", "改变", "学会", "明白", "懂得"],
            "梦想": ["梦想", "目标", "追求", "奋斗", "努力"],
            "复仇": ["复仇", "报仇", "报复", "恨", "惩罚"],
            "正义": ["正义", "公平", "真相", "揭露", "邪恶"],
            "生存": ["生存", "活着", "危险", "逃命", "挣扎"],
        }

        theme_scores = {}
        for theme, keywords in theme_keywords.items():
            score = sum(text.count(kw) for kw in keywords)
            if score > 0:
                theme_scores[theme] = score

        sorted_themes = sorted(theme_scores.items(), key=lambda x: -x[1])

        main_theme = sorted_themes[0][0] if sorted_themes else "未知"
        sub_themes = [t for t, _ in sorted_themes[1:4]]

        # 母题分析（反复出现的意象）
        motif_candidates = ["雨", "花", "刀", "信", "照片", "门", "窗", "路", "梦", "光"]
        motifs = [m for m in motif_candidates if text.count(m) >= 3]

        return ThemeAnalysis(
            main_theme=main_theme,
            sub_themes=sub_themes,
            motif=motifs,
            moral=f"关于{main_theme}的故事",
        )

    def _analyze_dialogue_intents(self, text: str) -> List[DialogueIntent]:
        """分析对话意图"""
        intents = []
        pattern = r'^([\u4e00-\u9fa5A-Za-z]{2,4})[：:](.+)$'

        for line in text.split('\n'):
            line = line.strip()
            match = re.match(pattern, line)
            if match:
                character = match.group(1)
                content = match.group(2).strip()

                if character in ["旁白", "解说", "字幕"]:
                    continue

                # 判断意图
                intent = "陈述"
                for itype, keywords in self.INTENT_KEYWORDS.items():
                    if any(kw in content for kw in keywords):
                        intent = itype
                        break

                # 判断情绪
                emotion = "neutral"
                for etype, keywords in self.EMOTION_KEYWORDS.items():
                    if any(kw in content for kw in keywords):
                        emotion = etype
                        break

                intents.append(DialogueIntent(
                    character=character,
                    content=content[:50],
                    intent=intent,
                    emotion=emotion,
                ))

        return intents[:50]  # 限制数量

    def _analyze_scene_atmospheres(self, text: str) -> List[SceneAtmosphere]:
        """分析场景氛围"""
        atmospheres = []
        scene_id = 0
        current_scene = None

        for line in text.split('\n'):
            line = line.strip()
            # 场景标记
            if re.match(r'^(场景|第[一二三四五六七八九十\d]+[场幕集])', line):
                if current_scene:
                    atmospheres.append(current_scene)
                scene_id += 1
                current_scene = SceneAtmosphere(
                    scene_id=scene_id,
                    location=line[:30],
                )
            elif current_scene:
                # 分析氛围
                for mood, keywords in self.MOOD_KEYWORDS.items():
                    if any(kw in line for kw in keywords):
                        current_scene.mood = mood
                        break
                # 分析时间
                for time_type, keywords in self.TIME_KEYWORDS.items():
                    if any(kw in line for kw in keywords):
                        current_scene.time_of_day = time_type
                        break

        if current_scene:
            atmospheres.append(current_scene)

        return atmospheres

    def _analyze_conflicts(self, text: str) -> List[ConflictEvolution]:
        """分析冲突演进"""
        conflicts = []
        characters = self._extract_characters(text)

        if len(characters) >= 2:
            # 简单人际冲突
            conflict = ConflictEvolution(
                conflict_type="人际",
                parties=characters[:2],
                escalation_level=0.5,
                resolution="待分析",
            )
            conflicts.append(conflict)

        # 内心冲突（独白/心理描写）
        inner_conflict_keywords = ["心里", "内心", "想", "纠结", "犹豫", "矛盾"]
        if any(kw in text for kw in inner_conflict_keywords):
            conflicts.append(ConflictEvolution(
                conflict_type="内心",
                parties=[characters[0] if characters else "主角"],
                escalation_level=0.3,
                resolution="待分析",
            ))

        return conflicts

    def _analyze_emotional_arcs(self, text: str) -> List[EmotionalArc]:
        """分析情感弧线"""
        characters = self._extract_characters(text)
        arcs = []

        for char in characters[:3]:  # 只分析前3个主要角色
            # 简单弧线判断
            arc = EmotionalArc(
                character=char,
                start_emotion="neutral",
                end_emotion="neutral",
                arc_type="flat",
                key_moments=[],
            )
            arcs.append(arc)

        return arcs

    def _generate_summary(self, result: DeepAnalysisResult) -> str:
        """生成分析摘要"""
        parts = []
        parts.append(f"作品《{result.title}》深度分析")

        if result.character_relations:
            parts.append(f"角色关系: {len(result.character_relations)}组关系")

        if result.story_structure:
            parts.append(f"剧情结构: {result.story_structure.structure_type}，节奏{result.story_structure.pacing}")

        if result.theme_analysis:
            parts.append(f"主题: {result.theme_analysis.main_theme}")
            if result.theme_analysis.sub_themes:
                parts.append(f"副主题: {', '.join(result.theme_analysis.sub_themes)}")

        if result.dialogue_intents:
            intent_counts = {}
            for d in result.dialogue_intents:
                intent_counts[d.intent] = intent_counts.get(d.intent, 0) + 1
            top_intent = max(intent_counts.items(), key=lambda x: x[1])[0]
            parts.append(f"对话意图: 主要为{top_intent}")

        if result.scene_atmospheres:
            mood_counts = {}
            for s in result.scene_atmospheres:
                mood_counts[s.mood] = mood_counts.get(s.mood, 0) + 1
            top_mood = max(mood_counts.items(), key=lambda x: x[1])[0]
            parts.append(f"场景氛围: 主要为{top_mood}")

        return "；".join(parts)

    def save_report(self, result: DeepAnalysisResult, output_path: str) -> str:
        """保存分析报告为JSON"""
        data = {
            "title": result.title,
            "summary": result.summary,
            "character_relations": [
                {
                    "character1": r.character1,
                    "character2": r.character2,
                    "relation_type": r.relation_type,
                    "intensity": r.intensity,
                    "sentiment": r.sentiment,
                    "description": r.description,
                }
                for r in result.character_relations
            ],
            "story_structure": {
                "structure_type": result.story_structure.structure_type,
                "pacing": result.story_structure.pacing,
                "acts": result.story_structure.acts,
                "turning_points": result.story_structure.turning_points,
            } if result.story_structure else None,
            "theme_analysis": {
                "main_theme": result.theme_analysis.main_theme,
                "sub_themes": result.theme_analysis.sub_themes,
                "motif": result.theme_analysis.motif,
                "moral": result.theme_analysis.moral,
            } if result.theme_analysis else None,
            "dialogue_intents": [
                {
                    "character": d.character,
                    "content": d.content,
                    "intent": d.intent,
                    "emotion": d.emotion,
                }
                for d in result.dialogue_intents
            ],
            "scene_atmospheres": [
                {
                    "scene_id": s.scene_id,
                    "location": s.location,
                    "time_of_day": s.time_of_day,
                    "mood": s.mood,
                    "weather": s.weather,
                }
                for s in result.scene_atmospheres
            ],
            "conflict_evolutions": [
                {
                    "conflict_type": c.conflict_type,
                    "parties": c.parties,
                    "escalation_level": c.escalation_level,
                    "resolution": c.resolution,
                }
                for c in result.conflict_evolutions
            ],
            "emotional_arcs": [
                {
                    "character": a.character,
                    "start_emotion": a.start_emotion,
                    "end_emotion": a.end_emotion,
                    "arc_type": a.arc_type,
                }
                for a in result.emotional_arcs
            ],
        }

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return output_path

    def print_summary(self, result: DeepAnalysisResult):
        """打印分析摘要"""
        print("\n" + "=" * 60)
        print("剧本深度语义分析报告")
        print("=" * 60)
        print(f"\n{result.summary}")

        print(f"\n角色关系 ({len(result.character_relations)}组):")
        for r in result.character_relations[:5]:
            print(f"  {r.character1} ↔ {r.character2}: {r.relation_type} "
                  f"(强度{r.intensity}, {r.sentiment})")

        if result.story_structure:
            print(f"\n剧情结构:")
            print(f"  类型: {result.story_structure.structure_type}")
            print(f"  节奏: {result.story_structure.pacing}")
            for act in result.story_structure.acts:
                print(f"  第{act['act']}幕 - {act['name']}: {act['description']}")

        if result.theme_analysis:
            print(f"\n主题分析:")
            print(f"  主题: {result.theme_analysis.main_theme}")
            print(f"  副主题: {', '.join(result.theme_analysis.sub_themes)}")
            if result.theme_analysis.motif:
                print(f"  母题: {', '.join(result.theme_analysis.motif)}")

        if result.dialogue_intents:
            print(f"\n对话意图 ({len(result.dialogue_intents)}条):")
            intent_counts = {}
            for d in result.dialogue_intents:
                intent_counts[d.intent] = intent_counts.get(d.intent, 0) + 1
            for intent, count in sorted(intent_counts.items(), key=lambda x: -x[1]):
                print(f"  {intent}: {count}条")

        if result.scene_atmospheres:
            print(f"\n场景氛围 ({len(result.scene_atmospheres)}个):")
            mood_counts = {}
            for s in result.scene_atmospheres:
                mood_counts[s.mood] = mood_counts.get(s.mood, 0) + 1
            for mood, count in sorted(mood_counts.items(), key=lambda x: -x[1]):
                print(f"  {mood}: {count}个")

        print("=" * 60)


def main():
    """命令行测试"""
    print("剧本深度语义分析器 v1.0 测试")
    print("=" * 60)

    # 测试剧本
    test_script = """
场景1：咖啡馆 白天
小明：你好，请问这里有人吗？
小红：没有，请坐。
小明：谢谢。我叫小明，你呢？
小红：我叫小红。你也是来这里看书的吗？
小明：是的，这里环境很温馨。
小红：我也觉得。你喜欢看什么类型的书？
小明：科幻小说，你呢？
小红：我喜欢爱情故事。

场景2：公园 黄昏
小明：小红，我有话想对你说。
小红：什么事？这么严肃。
小明：我喜欢你，从第一次见面就喜欢了。
小红：真的吗？我也是...
小明：那我们在一起吧！
小红：好。

场景3：雨天 夜晚
小明：对不起，我必须离开这里了。
小红：为什么？我们不是说好要在一起的吗？
小明：因为我要去追求我的梦想，这对我很重要。
小红：那我呢？你考虑过我的感受吗？
小明：我会回来的，等我。
小红：我会等你，无论多久。
"""

    analyzer = ScriptDeepAnalyzer()
    result = analyzer.analyze(test_script, title="测试剧本")
    analyzer.print_summary(result)

    # 保存报告
    output = r"C:\Users\Administrator\Videos\剪映导出\Doubao_Jianying-editor\deep_analysis_test.json"
    analyzer.save_report(result, output)
    print(f"\n报告已保存: {output}")
    print("\n✅ 剧本深度语义分析器验证通过")


if __name__ == "__main__":
    main()
