"""
剧本深度语义分析引擎 v1.0
识别剧本中的冲突点、转折点、高潮点，分析情绪曲线，自动分配镜头强度

用于script_parser和instruction_translator的深度语义增强。

使用方式：
    from script_deep_analyzer import ScriptDeepAnalyzer
    analyzer = ScriptDeepAnalyzer()
    result = analyzer.analyze(script_text)
    print(result["conflict_points"])  # 冲突点
    print(result["turning_points"])   # 转折点
    print(result["climax_points"])    # 高潮点
    print(result["emotion_curve"])    # 情绪曲线
"""
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class StoryPoint:
    """故事节点"""
    type: str  # conflict/turning/climax/setup/resolution
    position: float  # 0.0-1.0 相对位置
    description: str
    intensity: float  # 0.0-1.0
    sentence_index: int = -1


@dataclass
class EmotionPoint:
    """情绪节点"""
    position: float  # 0.0-1.0
    emotion: str
    intensity: float  # 0.0-1.0


class ScriptDeepAnalyzer:
    """剧本深度语义分析引擎"""

    def __init__(self):
        # 冲突关键词
        self.conflict_keywords = {
            "打": 0.8, "骂": 0.7, "吵": 0.6, "争": 0.5, "斗": 0.7,
            "拒绝": 0.6, "反对": 0.7, "阻止": 0.6, "威胁": 0.8, "攻击": 0.9,
            "摔": 0.7, "砸": 0.8, "推": 0.6, "踢": 0.7, "扇": 0.8,
            "怒": 0.7, "气": 0.5, "恨": 0.8, "仇": 0.9, "怨": 0.6,
            "误会": 0.5, "矛盾": 0.6, "冲突": 0.7, "对抗": 0.8,
        }
        # 转折关键词
        self.turning_keywords = {
            "突然": 0.7, "忽然": 0.7, "没想到": 0.8, "谁知": 0.7, "不料": 0.7,
            "结果": 0.5, "最后": 0.4, "终于": 0.5, "于是": 0.3, "因此": 0.3,
            "但是": 0.5, "然而": 0.5, "可是": 0.4, "却": 0.4, "反倒": 0.5,
            "发现": 0.6, "得知": 0.6, "明白": 0.5, "知道": 0.4,
            "转身": 0.5, "离开": 0.4, "回来": 0.5, "出现": 0.6,
        }
        # 高潮关键词
        self.climax_keywords = {
            "爆发": 0.9, "崩溃": 0.9, "绝望": 0.9, "狂喜": 0.9, "震惊": 0.8,
            "真相": 0.8, "大白": 0.7, "揭晓": 0.8, "揭秘": 0.8,
            "决战": 0.9, "对决": 0.9, "终局": 0.8, "结局": 0.7,
            "最": 0.6, "极": 0.6, "彻底": 0.7, "完全": 0.5,
        }
        # 情绪关键词映射
        self.emotion_keywords = {
            "开心": ["开心", "高兴", "快乐", "喜悦", "兴奋", "激动", "笑", "乐"],
            "悲伤": ["悲伤", "难过", "伤心", "哭", "泪", "痛苦", "绝望"],
            "愤怒": ["愤怒", "生气", "怒", "气", "火", "咆哮", "怒吼"],
            "紧张": ["紧张", "害怕", "恐惧", "慌", "忐忑", "不安", "担心"],
            "惊喜": ["惊喜", "意外", "没想到", "震惊", "哇", "天哪"],
            "平静": ["平静", "安静", "沉默", "淡定", "从容", "冷静"],
            "委屈": ["委屈", "可怜", "冤枉", "心酸", "难受"],
            "得意": ["得意", "骄傲", "自豪", "炫耀", "嚣张"],
        }

    def analyze(self, script_text: str) -> Dict:
        """
        深度分析剧本

        Args:
            script_text: 剧本文本

        Returns:
            分析结果字典
        """
        # 分句
        sentences = self._split_sentences(script_text)
        if not sentences:
            return self._empty_result()

        # 分析每个句子
        sentence_analysis = []
        for i, sent in enumerate(sentences):
            analysis = self._analyze_sentence(sent, i, len(sentences))
            sentence_analysis.append(analysis)

        # 识别故事节点
        conflict_points = self._identify_points(sentence_analysis, "conflict")
        turning_points = self._identify_points(sentence_analysis, "turning")
        climax_points = self._identify_points(sentence_analysis, "climax")

        # 情绪曲线
        emotion_curve = self._build_emotion_curve(sentence_analysis)

        # 故事结构
        structure = self._analyze_structure(sentence_analysis, conflict_points, turning_points, climax_points)

        # 镜头强度分配
        camera_intensity = self._assign_camera_intensity(sentence_analysis, structure)

        return {
            "total_sentences": len(sentences),
            "conflict_points": conflict_points,
            "turning_points": turning_points,
            "climax_points": climax_points,
            "emotion_curve": emotion_curve,
            "structure": structure,
            "camera_intensity": camera_intensity,
            "sentence_analysis": sentence_analysis,
        }

    def _split_sentences(self, text: str) -> List[str]:
        """分句"""
        # 按标点符号分句
        sentences = re.split(r'[。！？!?\n]+', text)
        return [s.strip() for s in sentences if s.strip()]

    def _analyze_sentence(self, sentence: str, index: int, total: int) -> Dict:
        """分析单个句子"""
        position = index / max(total - 1, 1)

        # 冲突分数
        conflict_score = self._calc_keyword_score(sentence, self.conflict_keywords)
        # 转折分数
        turning_score = self._calc_keyword_score(sentence, self.turning_keywords)
        # 高潮分数
        climax_score = self._calc_keyword_score(sentence, self.climax_keywords)

        # 情绪识别
        emotion, emotion_intensity = self._detect_emotion(sentence)

        return {
            "index": index,
            "position": position,
            "text": sentence,
            "conflict_score": conflict_score,
            "turning_score": turning_score,
            "climax_score": climax_score,
            "emotion": emotion,
            "emotion_intensity": emotion_intensity,
        }

    def _calc_keyword_score(self, text: str, keywords: Dict[str, float]) -> float:
        """计算关键词分数"""
        score = 0.0
        for keyword, weight in keywords.items():
            if keyword in text:
                score = max(score, weight)
        return min(score, 1.0)

    def _detect_emotion(self, text: str) -> Tuple[str, float]:
        """检测情绪"""
        best_emotion = "平静"
        best_score = 0.0
        for emotion, keywords in self.emotion_keywords.items():
            for kw in keywords:
                if kw in text:
                    score = 0.5 + 0.1 * text.count(kw)
                    if score > best_score:
                        best_score = score
                        best_emotion = emotion
        return best_emotion, min(best_score, 1.0)

    def _identify_points(self, sentence_analysis: List[Dict], point_type: str) -> List[StoryPoint]:
        """识别故事节点"""
        score_key = f"{point_type}_score"
        points = []
        threshold = 0.5

        for sa in sentence_analysis:
            score = sa.get(score_key, 0)
            if score >= threshold:
                points.append(StoryPoint(
                    type=point_type,
                    position=sa["position"],
                    description=sa["text"][:50],
                    intensity=score,
                    sentence_index=sa["index"],
                ))

        # 按强度排序，取前3个
        points.sort(key=lambda x: x.intensity, reverse=True)
        return points[:3]

    def _build_emotion_curve(self, sentence_analysis: List[Dict]) -> List[EmotionPoint]:
        """构建情绪曲线（采样10个点）"""
        if not sentence_analysis:
            return []

        num_samples = min(10, len(sentence_analysis))
        curve = []
        step = len(sentence_analysis) / num_samples

        for i in range(num_samples):
            idx = int(i * step)
            if idx < len(sentence_analysis):
                sa = sentence_analysis[idx]
                curve.append(EmotionPoint(
                    position=sa["position"],
                    emotion=sa["emotion"],
                    intensity=sa["emotion_intensity"],
                ))

        return curve

    def _analyze_structure(
        self,
        sentence_analysis: List[Dict],
        conflict_points: List[StoryPoint],
        turning_points: List[StoryPoint],
        climax_points: List[StoryPoint],
    ) -> Dict:
        """分析故事结构"""
        total = len(sentence_analysis)
        if total == 0:
            return {"type": "unknown", "phases": {}}

        # 三幕结构分析
        setup_end = int(total * 0.25)
        confrontation_end = int(total * 0.75)

        setup_conflict = sum(sa["conflict_score"] for sa in sentence_analysis[:setup_end])
        confrontation_conflict = sum(sa["conflict_score"] for sa in sentence_analysis[setup_end:confrontation_end])
        resolution_conflict = sum(sa["conflict_score"] for sa in sentence_analysis[confrontation_end:])

        # 确定主要高潮位置
        main_climax = climax_points[0].position if climax_points else 0.7

        return {
            "type": "three_act" if total > 5 else "simple",
            "setup": {
                "range": [0, setup_end],
                "conflict_level": round(setup_conflict / max(setup_end, 1), 2),
            },
            "confrontation": {
                "range": [setup_end, confrontation_end],
                "conflict_level": round(confrontation_conflict / max(confrontation_end - setup_end, 1), 2),
            },
            "resolution": {
                "range": [confrontation_end, total],
                "conflict_level": round(resolution_conflict / max(total - confrontation_end, 1), 2),
            },
            "main_climax_position": round(main_climax, 2),
            "conflict_count": len(conflict_points),
            "turning_count": len(turning_points),
            "climax_count": len(climax_points),
        }

    def _assign_camera_intensity(self, sentence_analysis: List[Dict], structure: Dict) -> List[Dict]:
        """分配镜头强度"""
        result = []
        for sa in sentence_analysis:
            # 基础强度
            intensity = 0.3  # 默认低强度

            # 冲突提升强度
            intensity += sa["conflict_score"] * 0.4
            # 转折提升强度
            intensity += sa["turning_score"] * 0.2
            # 高潮提升强度
            intensity += sa["climax_score"] * 0.3
            # 情绪强度
            intensity += sa["emotion_intensity"] * 0.2

            # 高潮附近额外提升
            climax_pos = structure.get("main_climax_position", 0.7)
            distance_to_climax = abs(sa["position"] - climax_pos)
            if distance_to_climax < 0.15:
                intensity += 0.2

            intensity = min(intensity, 1.0)

            # 映射到运镜强度
            if intensity < 0.4:
                camera_level = "low"
                camera_moves = ["固定", "缓慢平移", "缓慢推近"]
            elif intensity < 0.7:
                camera_level = "medium"
                camera_moves = ["推近", "轻微晃动", "平移"]
            else:
                camera_level = "high"
                camera_moves = ["快速推近", "剧烈晃动", "手持感", "快速变焦"]

            result.append({
                "index": sa["index"],
                "position": sa["position"],
                "intensity": round(intensity, 2),
                "camera_level": camera_level,
                "recommended_moves": camera_moves,
                "emotion": sa["emotion"],
            })

        return result

    def print_summary(self, result: Dict):
        """打印分析摘要"""
        print("=" * 60)
        print("剧本深度语义分析报告")
        print("=" * 60)
        print(f"\n总句子数: {result['total_sentences']}")

        print(f"\n冲突点 ({len(result['conflict_points'])}):")
        for p in result["conflict_points"]:
            print(f"  [{p.position:.0%}] 强度{p.intensity:.1f}: {p.description}")

        print(f"\n转折点 ({len(result['turning_points'])}):")
        for p in result["turning_points"]:
            print(f"  [{p.position:.0%}] 强度{p.intensity:.1f}: {p.description}")

        print(f"\n高潮点 ({len(result['climax_points'])}):")
        for p in result["climax_points"]:
            print(f"  [{p.position:.0%}] 强度{p.intensity:.1f}: {p.description}")

        print(f"\n故事结构: {result['structure']['type']}")
        print(f"  建置段冲突: {result['structure']['setup']['conflict_level']}")
        print(f"  对抗段冲突: {result['structure']['confrontation']['conflict_level']}")
        print(f"  解决段冲突: {result['structure']['resolution']['conflict_level']}")
        print(f"  主高潮位置: {result['structure']['main_climax_position']:.0%}")

        print(f"\n情绪曲线:")
        for ep in result["emotion_curve"]:
            bar = "█" * int(ep.intensity * 20)
            print(f"  [{ep.position:.0%}] {ep.emotion:4s} {bar} ({ep.intensity:.1f})")

        print("=" * 60)

    def _empty_result(self) -> Dict:
        """空结果"""
        return {
            "total_sentences": 0,
            "conflict_points": [],
            "turning_points": [],
            "climax_points": [],
            "emotion_curve": [],
            "structure": {"type": "empty"},
            "camera_intensity": [],
            "sentence_analysis": [],
        }


def main():
    """命令行测试"""
    analyzer = ScriptDeepAnalyzer()

    # 测试剧本（豆包被打）
    test_script = """
    豆包开心地在抖音主页展示自己的作品。
    突然，一个神秘人出现，开始攻击豆包。
    豆包愤怒地反抗，但被打得节节败退。
    混乱中，作品卡片被打碎了。
    最后，豆包满身伤痕地爬回头像框，委屈地看着观众。
    """

    print("测试剧本:")
    print(test_script)
    print()

    result = analyzer.analyze(test_script)
    analyzer.print_summary(result)


if __name__ == "__main__":
    main()
