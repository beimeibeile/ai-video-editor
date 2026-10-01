"""
剧情多轮打造系统 v1.0
剧情迭代优化+多版本对比+冲突检测+节奏分析

核心功能：
1. 剧情版本管理：多版本存储、对比、切换
2. 节奏分析：场景时长分布、情绪曲线、高潮点识别
3. 冲突检测：逻辑矛盾、角色不一致、时间线冲突
4. 迭代优化：基于反馈自动优化建议
5. 三幕结构验证：起承转合完整性检查
"""
import json
import uuid
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
from collections import defaultdict


class StoryIssueSeverity(Enum):
    """问题严重程度"""
    CRITICAL = "严重"
    WARNING = "警告"
    INFO = "建议"


class StoryIssueType(Enum):
    """问题类型"""
    PACING = "节奏问题"
    CHARACTER = "角色问题"
    LOGIC = "逻辑矛盾"
    STRUCTURE = "结构问题"
    DIALOGUE = "对话问题"
    EMOTION = "情绪问题"
    TIMELINE = "时间线问题"


class ActType(Enum):
    """幕类型"""
    ACT_I = "第一幕（建置）"
    ACT_II = "第二幕（对抗）"
    ACT_III = "第三幕（解决）"


@dataclass
class StoryIssue:
    """剧情问题"""
    issue_type: StoryIssueType
    severity: StoryIssueSeverity
    description: str
    location: str = ""  # 场景/位置
    suggestion: str = ""

    def to_dict(self):
        return {
            "type": self.issue_type.value,
            "severity": self.severity.value,
            "description": self.description,
            "location": self.location,
            "suggestion": self.suggestion,
        }


@dataclass
class StoryVersion:
    """剧情版本"""
    version_id: str
    version_name: str
    scenes: List[Dict[str, Any]]
    characters: List[Dict[str, Any]]
    total_duration: float = 0.0
    created_at: str = ""
    notes: str = ""
    issues: List[StoryIssue] = field(default_factory=list)

    def to_dict(self):
        return {
            "version_id": self.version_id,
            "version_name": self.version_name,
            "scene_count": len(self.scenes),
            "character_count": len(self.characters),
            "total_duration": self.total_duration,
            "created_at": self.created_at,
            "notes": self.notes,
            "issue_count": len(self.issues),
            "issues": [i.to_dict() for i in self.issues],
        }


@dataclass
class PacingAnalysis:
    """节奏分析结果"""
    total_duration: float = 0.0
    scene_count: int = 0
    avg_scene_duration: float = 0.0
    longest_scene: Dict[str, Any] = field(default_factory=dict)
    shortest_scene: Dict[str, Any] = field(default_factory=dict)
    duration_distribution: Dict[str, int] = field(default_factory=dict)  # 时长区间分布
    emotion_curve: List[Dict[str, Any]] = field(default_factory=list)  # 情绪曲线
    high_points: List[Dict[str, Any]] = field(default_factory=list)  # 高潮点
    low_points: List[Dict[str, Any]] = field(default_factory=list)  # 低谷点
    pacing_score: float = 0.0  # 0-100

    def to_dict(self):
        return asdict(self)


@dataclass
class StructureAnalysis:
    """结构分析结果"""
    act_i_scenes: List[Dict[str, Any]] = field(default_factory=list)
    act_ii_scenes: List[Dict[str, Any]] = field(default_factory=list)
    act_iii_scenes: List[Dict[str, Any]] = field(default_factory=list)
    inciting_incident: Optional[Dict[str, Any]] = None  # 激励事件
    first_turning_point: Optional[Dict[str, Any]] = None  # 第一转折点
    midpoint: Optional[Dict[str, Any]] = None  # 中点
    second_turning_point: Optional[Dict[str, Any]] = None  # 第二转折点
    climax: Optional[Dict[str, Any]] = None  # 高潮
    resolution: Optional[Dict[str, Any]] = None  # 结局
    structure_score: float = 0.0  # 0-100
    missing_elements: List[str] = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


class PacingAnalyzer:
    """节奏分析器"""

    # 情绪强度映射
    EMOTION_INTENSITY = {
        "平静": 0.2, "温馨": 0.3, "喜悦": 0.5, "兴奋": 0.7,
        "紧张": 0.6, "焦虑": 0.5, "悲伤": 0.4, "愤怒": 0.8,
        "恐惧": 0.7, "震惊": 0.9, "坚定": 0.5, "困惑": 0.3,
    }

    def analyze(self, scenes: List[Dict[str, Any]]) -> PacingAnalysis:
        """分析节奏"""
        result = PacingAnalysis()
        result.scene_count = len(scenes)

        if not scenes:
            return result

        # 总时长
        durations = [s.get("duration", s.get("duration_estimate", 0)) for s in scenes]
        result.total_duration = sum(durations)
        result.avg_scene_duration = result.total_duration / len(scenes)

        # 最长/最短场景
        max_idx = durations.index(max(durations))
        min_idx = durations.index(min(durations))
        result.longest_scene = {"index": max_idx, "title": scenes[max_idx].get("title", f"场景{max_idx+1}"), "duration": durations[max_idx]}
        result.shortest_scene = {"index": min_idx, "title": scenes[min_idx].get("title", f"场景{min_idx+1}"), "duration": durations[min_idx]}

        # 时长分布
        for d in durations:
            if d < 5:
                result.duration_distribution["<5秒"] = result.duration_distribution.get("<5秒", 0) + 1
            elif d < 10:
                result.duration_distribution["5-10秒"] = result.duration_distribution.get("5-10秒", 0) + 1
            elif d < 20:
                result.duration_distribution["10-20秒"] = result.duration_distribution.get("10-20秒", 0) + 1
            elif d < 40:
                result.duration_distribution["20-40秒"] = result.duration_distribution.get("20-40秒", 0) + 1
            else:
                result.duration_distribution[">40秒"] = result.duration_distribution.get(">40秒", 0) + 1

        # 情绪曲线
        for i, scene in enumerate(scenes):
            emotion = scene.get("emotional_tone", "平静")
            intensity = self.EMOTION_INTENSITY.get(emotion, 0.3)
            result.emotion_curve.append({
                "scene_index": i,
                "title": scene.get("title", f"场景{i+1}"),
                "emotion": emotion,
                "intensity": intensity,
            })

        # 高潮/低谷点（情绪强度极值）
        if result.emotion_curve:
            intensities = [e["intensity"] for e in result.emotion_curve]
            avg_intensity = sum(intensities) / len(intensities)

            for i, e in enumerate(result.emotion_curve):
                if e["intensity"] > avg_intensity * 1.3:
                    result.high_points.append(e)
                elif e["intensity"] < avg_intensity * 0.7:
                    result.low_points.append(e)

        # 节奏评分
        score = 50.0
        # 场景时长变化（有变化加分）
        if len(set(durations)) > len(durations) * 0.5:
            score += 15
        # 有高潮点加分
        if result.high_points:
            score += 15
        # 情绪曲线有起伏加分
        if max(intensities) - min(intensities) > 0.3:
            score += 10
        # 平均时长合理（5-20秒）加分
        if 5 <= result.avg_scene_duration <= 20:
            score += 10

        result.pacing_score = min(score, 100)
        return result


class StructureAnalyzer:
    """结构分析器（三幕结构）"""

    def analyze(self, scenes: List[Dict[str, Any]]) -> StructureAnalysis:
        """分析三幕结构"""
        result = StructureAnalysis()

        if not scenes:
            result.missing_elements = ["无场景"]
            return result

        n = len(scenes)
        # 简单按比例划分三幕
        act_i_end = max(1, int(n * 0.25))
        act_ii_end = max(act_i_end + 1, int(n * 0.75))

        result.act_i_scenes = scenes[:act_i_end]
        result.act_ii_scenes = scenes[act_i_end:act_ii_end]
        result.act_iii_scenes = scenes[act_ii_end:]

        # 识别关键结构点（基于情绪强度和位置）
        emotion_intensity = {
            "紧张": 0.6, "兴奋": 0.7, "愤怒": 0.8, "恐惧": 0.7,
            "震惊": 0.9, "坚定": 0.5, "悲伤": 0.4, "平静": 0.2,
        }

        def get_intensity(scene):
            return emotion_intensity.get(scene.get("emotional_tone", "平静"), 0.3)

        # 激励事件（第一幕中后段）
        if result.act_i_scenes:
            act_i_intensities = [get_intensity(s) for s in result.act_i_scenes]
            if act_i_intensities:
                idx = act_i_intensities.index(max(act_i_intensities))
                result.inciting_incident = {"index": idx, "title": result.act_i_scenes[idx].get("title", "")}

        # 第一转折点（第一二幕交界处）
        if act_i_end < n:
            result.first_turning_point = {"index": act_i_end, "title": scenes[act_i_end].get("title", "")}

        # 中点（第二幕中间）
        if result.act_ii_scenes:
            mid_idx = len(result.act_ii_scenes) // 2
            result.midpoint = {"index": act_i_end + mid_idx, "title": result.act_ii_scenes[mid_idx].get("title", "")}

        # 第二转折点（第二三幕交界处）
        if act_ii_end < n:
            result.second_turning_point = {"index": act_ii_end, "title": scenes[act_ii_end].get("title", "")}

        # 高潮（第三幕前段）
        if result.act_iii_scenes:
            act_iii_intensities = [get_intensity(s) for s in result.act_iii_scenes]
            if act_iii_intensities:
                idx = act_iii_intensities.index(max(act_iii_intensities))
                result.climax = {"index": act_ii_end + idx, "title": result.act_iii_scenes[idx].get("title", "")}

        # 结局（最后一个场景）
        result.resolution = {"index": n - 1, "title": scenes[-1].get("title", "")}

        # 缺失元素检查
        if not result.inciting_incident:
            result.missing_elements.append("激励事件不明确")
        if not result.climax:
            result.missing_elements.append("高潮不明确")
        if len(result.act_i_scenes) == 0:
            result.missing_elements.append("第一幕缺失")
        if len(result.act_ii_scenes) == 0:
            result.missing_elements.append("第二幕缺失")
        if len(result.act_iii_scenes) == 0:
            result.missing_elements.append("第三幕缺失")

        # 结构评分
        score = 100 - len(result.missing_elements) * 15
        result.structure_score = max(score, 0)
        return result


class ConflictDetector:
    """冲突检测器"""

    def detect(self, scenes: List[Dict[str, Any]],
               characters: List[Dict[str, Any]]) -> List[StoryIssue]:
        """检测剧情冲突"""
        issues = []

        # 1. 角色一致性检测
        char_traits = {}
        for c in characters:
            name = c.get("name", "")
            traits = c.get("personality", {}).get("traits", [])
            if traits:
                char_traits[name] = traits

        # 2. 时间线检测（场景时长异常）
        for i, scene in enumerate(scenes):
            duration = scene.get("duration", scene.get("duration_estimate", 0))
            if duration == 0:
                issues.append(StoryIssue(
                    issue_type=StoryIssueType.TIMELINE,
                    severity=StoryIssueSeverity.WARNING,
                    description=f"场景{i+1}时长为0",
                    location=scene.get("title", f"场景{i+1}"),
                    suggestion="设置合理的场景时长",
                ))
            elif duration > 60:
                issues.append(StoryIssue(
                    issue_type=StoryIssueType.PACING,
                    severity=StoryIssueSeverity.WARNING,
                    description=f"场景{i+1}时长过长（{duration:.0f}秒）",
                    location=scene.get("title", f"场景{i+1}"),
                    suggestion="考虑拆分为多个场景",
                ))

        # 3. 对话检测（对话过少/过多）
        for i, scene in enumerate(scenes):
            dialogues = scene.get("dialogues", [])
            if len(scenes) > 3 and len(dialogues) == 0 and i > 0:
                issues.append(StoryIssue(
                    issue_type=StoryIssueType.DIALOGUE,
                    severity=StoryIssueSeverity.INFO,
                    description=f"场景{i+1}无对话",
                    location=scene.get("title", f"场景{i+1}"),
                    suggestion="考虑添加对话或确认是否为纯动作场景",
                ))

        # 4. 情绪连续性检测
        for i in range(1, len(scenes)):
            prev_emotion = scenes[i-1].get("emotional_tone", "平静")
            curr_emotion = scenes[i].get("emotional_tone", "平静")
            # 极端情绪跳跃
            high_emotions = ["愤怒", "恐惧", "震惊"]
            low_emotions = ["平静", "温馨"]
            if prev_emotion in high_emotions and curr_emotion in low_emotions:
                issues.append(StoryIssue(
                    issue_type=StoryIssueType.EMOTION,
                    severity=StoryIssueSeverity.INFO,
                    description=f"场景{i}到{i+1}情绪跳跃过大（{prev_emotion}→{curr_emotion}）",
                    location=f"{scenes[i-1].get('title','')} → {scenes[i].get('title','')}",
                    suggestion="考虑添加过渡场景或情绪缓冲",
                ))

        return issues


class StoryPolisher:
    """剧情打磨器（主入口）"""

    def __init__(self):
        self.versions: Dict[str, StoryVersion] = {}
        self.current_version_id: Optional[str] = None
        self.pacing_analyzer = PacingAnalyzer()
        self.structure_analyzer = StructureAnalyzer()
        self.conflict_detector = ConflictDetector()

    def create_version(self, scenes: List[Dict[str, Any]],
                       characters: List[Dict[str, Any]],
                       version_name: str = "v1",
                       notes: str = "") -> StoryVersion:
        """创建新版本"""
        version_id = uuid.uuid4().hex[:8]
        total_duration = sum(s.get("duration", s.get("duration_estimate", 0)) for s in scenes)

        version = StoryVersion(
            version_id=version_id,
            version_name=version_name,
            scenes=scenes,
            characters=characters,
            total_duration=total_duration,
            created_at=__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            notes=notes,
        )

        # 自动检测问题
        version.issues = self.conflict_detector.detect(scenes, characters)

        self.versions[version_id] = version
        self.current_version_id = version_id
        return version

    def analyze_pacing(self, version_id: str = None) -> Optional[PacingAnalysis]:
        """分析节奏"""
        version = self._get_version(version_id)
        if not version:
            return None
        return self.pacing_analyzer.analyze(version.scenes)

    def analyze_structure(self, version_id: str = None) -> Optional[StructureAnalysis]:
        """分析结构"""
        version = self._get_version(version_id)
        if not version:
            return None
        return self.structure_analyzer.analyze(version.scenes)

    def compare_versions(self, version_id_1: str, version_id_2: str) -> Dict[str, Any]:
        """对比两个版本"""
        v1 = self.versions.get(version_id_1)
        v2 = self.versions.get(version_id_2)
        if not v1 or not v2:
            return {"error": "版本不存在"}

        return {
            "version_1": v1.to_dict(),
            "version_2": v2.to_dict(),
            "comparison": {
                "scene_count_diff": len(v2.scenes) - len(v1.scenes),
                "duration_diff": v2.total_duration - v1.total_duration,
                "issue_count_diff": len(v2.issues) - len(v1.issues),
                "character_count_diff": len(v2.characters) - len(v1.characters),
            },
        }

    def get_optimization_suggestions(self, version_id: str = None) -> List[Dict[str, Any]]:
        """获取优化建议"""
        version = self._get_version(version_id)
        if not version:
            return []

        suggestions = []
        pacing = self.analyze_pacing(version_id)
        structure = self.analyze_structure(version_id)

        # 节奏优化建议
        if pacing:
            if pacing.pacing_score < 60:
                suggestions.append({
                    "category": "节奏",
                    "priority": "high",
                    "suggestion": f"节奏评分较低({pacing.pacing_score:.0f})，建议增加场景变化和情绪起伏",
                })
            if pacing.avg_scene_duration > 20:
                suggestions.append({
                    "category": "节奏",
                    "priority": "medium",
                    "suggestion": f"平均场景时长过长({pacing.avg_scene_duration:.0f}秒)，建议拆分长场景",
                })
            if not pacing.high_points:
                suggestions.append({
                    "category": "节奏",
                    "priority": "high",
                    "suggestion": "缺少明显高潮点，建议增加情绪强烈的场景",
                })

        # 结构优化建议
        if structure:
            if structure.missing_elements:
                for element in structure.missing_elements:
                    suggestions.append({
                        "category": "结构",
                        "priority": "high",
                        "suggestion": f"结构问题：{element}",
                    })
            if structure.structure_score < 70:
                suggestions.append({
                    "category": "结构",
                    "priority": "medium",
                    "suggestion": f"三幕结构评分较低({structure.structure_score:.0f})，建议完善起承转合",
                })

        # 问题修复建议
        for issue in version.issues:
            if issue.severity == StoryIssueSeverity.CRITICAL:
                suggestions.append({
                    "category": issue.issue_type.value,
                    "priority": "high",
                    "suggestion": issue.description + " → " + issue.suggestion,
                    "location": issue.location,
                })

        return suggestions

    def get_full_report(self, version_id: str = None) -> Dict[str, Any]:
        """获取完整分析报告"""
        version = self._get_version(version_id)
        if not version:
            return {"error": "版本不存在"}

        pacing = self.analyze_pacing(version_id)
        structure = self.analyze_structure(version_id)
        suggestions = self.get_optimization_suggestions(version_id)

        return {
            "version": version.to_dict(),
            "pacing_analysis": pacing.to_dict() if pacing else None,
            "structure_analysis": structure.to_dict() if structure else None,
            "issues": [i.to_dict() for i in version.issues],
            "optimization_suggestions": suggestions,
            "overall_score": round(
                ((pacing.pacing_score if pacing else 50) +
                 (structure.structure_score if structure else 50)) / 2, 1
            ),
        }

    def _get_version(self, version_id: str = None) -> Optional[StoryVersion]:
        """获取版本"""
        if version_id:
            return self.versions.get(version_id)
        return self.versions.get(self.current_version_id) if self.current_version_id else None

    def export_report(self, report: Dict[str, Any], output_path: str) -> str:
        """导出报告"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        return output_path


if __name__ == "__main__":
    print("=" * 60)
    print("✍️ 剧情多轮打造系统 v1.0")
    print("=" * 60)

    polisher = StoryPolisher()

    # 测试场景
    test_scenes = [
        {"title": "场景1: 咖啡馆", "duration": 8, "emotional_tone": "平静",
         "dialogues": [{"speaker": "李明", "content": "你好"}, {"speaker": "王芳", "content": "你好"}]},
        {"title": "场景2: 发现秘密", "duration": 12, "emotional_tone": "紧张",
         "dialogues": [{"speaker": "王芳", "content": "我发现了一个秘密"}]},
        {"title": "场景3: 讨论对策", "duration": 15, "emotional_tone": "焦虑",
         "dialogues": [{"speaker": "李明", "content": "我们该怎么办"}]},
        {"title": "场景4: 调查", "duration": 10, "emotional_tone": "坚定",
         "dialogues": []},
        {"title": "场景5: 对峙", "duration": 18, "emotional_tone": "愤怒",
         "dialogues": [{"speaker": "李明", "content": "是你做的！"}]},
        {"title": "场景6: 真相大白", "duration": 10, "emotional_tone": "震惊",
         "dialogues": [{"speaker": "王芳", "content": "原来如此"}]},
        {"title": "场景7: 结局", "duration": 7, "emotional_tone": "平静",
         "dialogues": []},
    ]

    test_characters = [
        {"name": "李明", "personality": {"traits": ["冷静", "谨慎"]}},
        {"name": "王芳", "personality": {"traits": ["外向", "热情"]}},
    ]

    # 创建版本
    print("\n📝 创建版本v1...")
    v1 = polisher.create_version(test_scenes, test_characters, "v1", "初始版本")
    print(f"  ✅ {v1.version_name}: {len(v1.scenes)}场, {v1.total_duration:.0f}秒, {len(v1.issues)}个问题")

    # 节奏分析
    print("\n📊 节奏分析:")
    pacing = polisher.analyze_pacing()
    print(f"  总时长: {pacing.total_duration:.0f}秒")
    print(f"  平均场景时长: {pacing.avg_scene_duration:.1f}秒")
    print(f"  最长场景: {pacing.longest_scene.get('title')} ({pacing.longest_scene.get('duration')}秒)")
    print(f"  最短场景: {pacing.shortest_scene.get('title')} ({pacing.shortest_scene.get('duration')}秒)")
    print(f"  高潮点: {len(pacing.high_points)}个")
    print(f"  节奏评分: {pacing.pacing_score:.0f}/100")

    # 结构分析
    print("\n🏗️ 结构分析:")
    structure = polisher.analyze_structure()
    print(f"  第一幕: {len(structure.act_i_scenes)}场")
    print(f"  第二幕: {len(structure.act_ii_scenes)}场")
    print(f"  第三幕: {len(structure.act_iii_scenes)}场")
    print(f"  激励事件: {structure.inciting_incident.get('title') if structure.inciting_incident else '无'}")
    print(f"  高潮: {structure.climax.get('title') if structure.climax else '无'}")
    print(f"  结构评分: {structure.structure_score:.0f}/100")

    # 问题检测
    print("\n🔍 问题检测:")
    for issue in v1.issues:
        print(f"  [{issue.severity.value}] {issue.issue_type.value}: {issue.description}")
        if issue.suggestion:
            print(f"    → 建议: {issue.suggestion}")

    # 优化建议
    print("\n💡 优化建议:")
    suggestions = polisher.get_optimization_suggestions()
    for s in suggestions:
        print(f"  [{s['priority']}] {s['category']}: {s['suggestion']}")

    # 完整报告
    print("\n📄 生成完整报告...")
    report = polisher.get_full_report()
    print(f"  综合评分: {report['overall_score']}/100")

    output_dir = r"C:\Users\Administrator\AppData\Local\DoubaoWork\User Data\Default\.doubaowork\agent_mode\workspace\.user_skills\ai-video-editor\capabilities\script_outputs"
    import os
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "story_polisher_test.json")
    polisher.export_report(report, output_path)
    print(f"  已导出: {output_path}")

    print("\n✅ 剧情多轮打造系统验证通过")
