"""
剧本改写记忆与自学习引擎 v1.0

核心功能：
1. 改写经验库：记录每次改写的输入→输出→质量门评分→用户反馈
2. 角色记忆库：积累角色设定，跨项目复用
3. 风格模板库：不同风格的改写参数模板
4. 用户偏好学习：从反馈中学习用户喜欢的节奏/时长/风格
5. 质量趋势分析：历史改写的质量评分趋势
6. 相似案例检索：查找相似的历史改写供参考

存储：JSON文件（rewrite_memory.json），自动保存
"""

import logging
logger = logging.getLogger(__name__)


import os
import json
import time
import hashlib
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class RewriteRecord:
    """单次改写记录"""
    record_id: str
    timestamp: str
    mode: str                    # creative/adapt
    input_text: str              # 原始输入
    input_hash: str              # 输入哈希（用于相似检索）
    constraints: Dict[str, Any]  # 改写约束
    output_summary: Dict[str, Any]  # 输出摘要（场景数/角色数/节拍数）
    quality_score: float         # 质量门评分（0-10）
    quality_gates: List[Dict]    # 质量门详情
    user_feedback: Optional[str] = None  # 用户反馈（good/bad/neutral）
    user_rating: Optional[int] = None    # 用户评分（1-5）
    notes: str = ""              # 备注


@dataclass
class CharacterMemory:
    """角色记忆"""
    name: str
    role: str = "supporting"
    voice_style: Optional[str] = None
    description: Optional[str] = None
    appearance_hint: Optional[str] = None
    use_count: int = 0
    last_used: str = ""
    tags: List[str] = field(default_factory=list)


@dataclass
class StyleTemplate:
    """风格模板"""
    name: str
    style: str
    duration: float
    platform: str
    tone: str
    genre: str
    hook_required: bool = True
    max_scenes: int = 10
    use_count: int = 0
    success_rate: float = 0.0
    avg_quality_score: float = 0.0


@dataclass
class UserPreferences:
    """用户偏好（从反馈中学习）"""
    preferred_styles: Dict[str, int] = field(default_factory=dict)  # 风格→使用次数
    preferred_durations: List[float] = field(default_factory=list)  # 偏好时长
    preferred_platforms: Dict[str, int] = field(default_factory=dict)
    avg_rating: float = 0.0
    total_rewrites: int = 0
    quality_trend: List[float] = field(default_factory=list)  # 最近N次质量评分
    successful_strategies: List[str] = field(default_factory=list)
    failed_strategies: List[str] = field(default_factory=list)


class RewriteMemory:
    """
    剧本改写记忆与自学习引擎

    使用方式：
        memory = RewriteMemory(memory_path="rewrite_memory.json")
        memory.record_rewrite(record)
        similar = memory.find_similar(input_text, top_k=3)
        prefs = memory.get_preferences()
    """

    def __init__(self, memory_path: str = None):
        if memory_path is None:
            memory_path = os.path.join(
                r"D:\DobaoWork_Project\Ai_Video_Editor", "rewrite_memory.json"
            )
        self.memory_path = memory_path
        self.records: List[RewriteRecord] = []
        self.characters: Dict[str, CharacterMemory] = {}
        self.style_templates: Dict[str, StyleTemplate] = {}
        self.preferences = UserPreferences()
        self._load()

    def _load(self):
        """从JSON加载记忆"""
        if os.path.exists(self.memory_path):
            try:
                with open(self.memory_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                self.records = [RewriteRecord(**r) for r in data.get("records", [])]
                self.characters = {
                    name: CharacterMemory(**c)
                    for name, c in data.get("characters", {}).items()
                }
                self.style_templates = {
                    name: StyleTemplate(**s)
                    for name, s in data.get("style_templates", {}).items()
                }
                prefs_data = data.get("preferences", {})
                self.preferences = UserPreferences(**prefs_data)
                logger.info(f"  📚 记忆加载: {len(self.records)}条记录, {len(self.characters)}个角色, {len(self.style_templates)}个模板")
            except Exception as e:
                logger.error(f"  ⚠️  记忆加载失败: {e}，使用空记忆")
                self.records = []
                self.characters = {}
                self.style_templates = {}
                self.preferences = UserPreferences()
        else:
            logger.info(f"  📚 新建记忆库: {self.memory_path}")

    def _save(self):
        """保存到JSON"""
        os.makedirs(os.path.dirname(self.memory_path) or ".", exist_ok=True)
        data = {
            "records": [asdict(r) for r in self.records],
            "characters": {name: asdict(c) for name, c in self.characters.items()},
            "style_templates": {name: asdict(s) for name, s in self.style_templates.items()},
            "preferences": asdict(self.preferences),
            "last_updated": datetime.now().isoformat(),
            "version": "1.0",
        }
        with open(self.memory_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _hash_text(self, text: str) -> str:
        """计算文本哈希"""
        return hashlib.md5(text.encode("utf-8")).hexdigest()[:12]

    def _text_similarity(self, text1: str, text2: str) -> float:
        """简单文本相似度（基于字符集合的Jaccard相似度）"""
        set1 = set(text1)
        set2 = set(text2)
        if not set1 or not set2:
            return 0.0
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0.0

    # ============================================================
    # 记录改写
    # ============================================================

    def record_rewrite(
        self,
        mode: str,
        input_text: str,
        constraints: Dict[str, Any],
        output_summary: Dict[str, Any],
        quality_score: float,
        quality_gates: List[Dict],
        user_feedback: str = None,
        user_rating: int = None,
        notes: str = "",
    ) -> RewriteRecord:
        """
        记录一次改写

        Args:
            mode: 模式（creative/adapt）
            input_text: 原始输入
            constraints: 改写约束
            output_summary: 输出摘要
            quality_score: 质量门评分
            quality_gates: 质量门详情
            user_feedback: 用户反馈
            user_rating: 用户评分（1-5）
            notes: 备注

        Returns:
            RewriteRecord
        """
        record = RewriteRecord(
            record_id=f"rw_{int(time.time())}_{self._hash_text(input_text)[:6]}",
            timestamp=datetime.now().isoformat(),
            mode=mode,
            input_text=input_text[:500],  # 限制长度
            input_hash=self._hash_text(input_text),
            constraints=constraints,
            output_summary=output_summary,
            quality_score=quality_score,
            quality_gates=quality_gates,
            user_feedback=user_feedback,
            user_rating=user_rating,
            notes=notes,
        )

        self.records.append(record)

        # 更新用户偏好
        self._update_preferences(record)

        # 更新角色记忆
        self._update_characters(output_summary)

        # 更新风格模板
        self._update_style_template(constraints, quality_score, user_rating)

        self._save()
        return record

    def _update_preferences(self, record: RewriteRecord):
        """从记录中更新用户偏好"""
        prefs = self.preferences
        prefs.total_rewrites += 1

        # 风格偏好
        style = record.constraints.get("style", "unknown")
        prefs.preferred_styles[style] = prefs.preferred_styles.get(style, 0) + 1

        # 时长偏好
        duration = record.constraints.get("duration", 30)
        prefs.preferred_durations.append(duration)
        if len(prefs.preferred_durations) > 50:
            prefs.preferred_durations = prefs.preferred_durations[-50:]

        # 平台偏好
        platform = record.constraints.get("platform", "unknown")
        prefs.preferred_platforms[platform] = prefs.preferred_platforms.get(platform, 0) + 1

        # 质量趋势
        prefs.quality_trend.append(record.quality_score)
        if len(prefs.quality_trend) > 50:
            prefs.quality_trend = prefs.quality_trend[-50:]

        # 用户评分
        if record.user_rating:
            ratings = [r.user_rating for r in self.records if r.user_rating]
            prefs.avg_rating = sum(ratings) / len(ratings) if ratings else 0.0

        # 成功/失败策略
        if record.user_feedback == "good" or (record.user_rating and record.user_rating >= 4):
            strategy = f"{record.mode}_{style}"
            if strategy not in prefs.successful_strategies:
                prefs.successful_strategies.append(strategy)
        elif record.user_feedback == "bad" or (record.user_rating and record.user_rating <= 2):
            strategy = f"{record.mode}_{style}"
            if strategy not in prefs.failed_strategies:
                prefs.failed_strategies.append(strategy)

    def _update_characters(self, output_summary: Dict[str, Any]):
        """从输出中更新角色记忆"""
        characters = output_summary.get("characters", [])
        for char in characters:
            name = char.get("name", "") if isinstance(char, dict) else str(char)
            if not name:
                continue
            if name in self.characters:
                self.characters[name].use_count += 1
                self.characters[name].last_used = datetime.now().isoformat()
            else:
                self.characters[name] = CharacterMemory(
                    name=name,
                    role=char.get("role", "supporting") if isinstance(char, dict) else "supporting",
                    description=char.get("description", "") if isinstance(char, dict) else "",
                    use_count=1,
                    last_used=datetime.now().isoformat(),
                )

    def _update_style_template(self, constraints: Dict, quality_score: float, user_rating: int = None):
        """更新风格模板统计"""
        style = constraints.get("style", "default")
        if style not in self.style_templates:
            self.style_templates[style] = StyleTemplate(
                name=style,
                style=style,
                duration=constraints.get("duration", 30),
                platform=constraints.get("platform", "douyin"),
                tone=constraints.get("tone", "neutral"),
                genre=constraints.get("genre", "vlog"),
            )

        template = self.style_templates[style]
        template.use_count += 1

        # 更新平均质量分
        old_total = template.avg_quality_score * (template.use_count - 1)
        template.avg_quality_score = (old_total + quality_score) / template.use_count

        # 更新成功率（用户评分>=4视为成功）
        if user_rating:
            successes = sum(1 for r in self.records
                          if r.constraints.get("style") == style and r.user_rating and r.user_rating >= 4)
            total_rated = sum(1 for r in self.records
                            if r.constraints.get("style") == style and r.user_rating)
            template.success_rate = successes / total_rated if total_rated > 0 else 0.0

    # ============================================================
    # 检索与查询
    # ============================================================

    def find_similar(self, input_text: str, top_k: int = 3, min_similarity: float = 0.3) -> List[RewriteRecord]:
        """
        查找相似的历史改写

        Args:
            input_text: 输入文本
            top_k: 返回最相似的K条
            min_similarity: 最小相似度阈值

        Returns:
            相似记录列表（按相似度降序）
        """
        scored = []
        for record in self.records:
            sim = self._text_similarity(input_text, record.input_text)
            if sim >= min_similarity:
                scored.append((sim, record))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in scored[:top_k]]

    def get_preferences(self) -> UserPreferences:
        """获取用户偏好"""
        return self.preferences

    def get_quality_trend(self) -> Dict[str, Any]:
        """获取质量趋势分析"""
        trend = self.preferences.quality_trend
        if not trend:
            return {"trend": "no_data", "avg": 0, "recent_avg": 0, "improving": False}

        avg = sum(trend) / len(trend)
        recent = trend[-10:] if len(trend) >= 10 else trend
        recent_avg = sum(recent) / len(recent)
        older = trend[:-10] if len(trend) > 10 else trend[:len(trend)//2]
        older_avg = sum(older) / len(older) if older else avg

        return {
            "trend": "improving" if recent_avg > older_avg else "declining" if recent_avg < older_avg else "stable",
            "avg": round(avg, 2),
            "recent_avg": round(recent_avg, 2),
            "older_avg": round(older_avg, 2),
            "improving": recent_avg > older_avg,
            "total_records": len(self.records),
        }

    def get_character_suggestions(self, context: str = "") -> List[CharacterMemory]:
        """
        获取角色建议（基于使用频率和上下文）

        Args:
            context: 上下文文本（用于匹配角色标签）

        Returns:
            推荐角色列表
        """
        chars = list(self.characters.values())
        chars.sort(key=lambda c: c.use_count, reverse=True)
        return chars[:10]

    def get_style_suggestions(self) -> List[StyleTemplate]:
        """获取风格建议（基于成功率和使用频率）"""
        templates = list(self.style_templates.values())
        templates.sort(key=lambda t: (t.success_rate, t.use_count), reverse=True)
        return templates[:5]

    def get_rewrite_suggestion(self, input_text: str, mode: str = "creative") -> Dict[str, Any]:
        """
        基于记忆给出改写建议

        Args:
            input_text: 输入文本
            mode: 模式

        Returns:
            建议字典
        """
        suggestion = {
            "similar_cases": [],
            "recommended_style": None,
            "recommended_duration": None,
            "quality_target": 7.0,
            "warnings": [],
            "tips": [],
        }

        # 相似案例
        similar = self.find_similar(input_text, top_k=3)
        suggestion["similar_cases"] = [
            {
                "id": r.record_id,
                "mode": r.mode,
                "quality_score": r.quality_score,
                "summary": r.output_summary,
                "feedback": r.user_feedback,
            }
            for r in similar
        ]

        # 推荐风格
        styles = self.get_style_suggestions()
        if styles:
            suggestion["recommended_style"] = styles[0].style
            suggestion["recommended_duration"] = styles[0].duration

        # 质量目标
        trend = self.get_quality_trend()
        suggestion["quality_target"] = max(7.0, trend.get("recent_avg", 7.0))

        # 警告
        if similar:
            avg_sim_quality = sum(r.quality_score for r in similar) / len(similar)
            if avg_sim_quality < 5.0:
                suggestion["warnings"].append(f"相似案例平均质量分较低({avg_sim_quality:.1f})，建议增加细节描述")

        # 提示
        prefs = self.get_preferences()
        if prefs.total_rewrites > 0:
            most_used_style = max(prefs.preferred_styles, key=prefs.preferred_styles.get) if prefs.preferred_styles else None
            if most_used_style:
                suggestion["tips"].append(f"你最常用的风格是「{most_used_style}」")
            if prefs.avg_rating > 0:
                suggestion["tips"].append(f"历史平均评分: {prefs.avg_rating:.1f}/5")

        return suggestion

    # ============================================================
    # 用户反馈
    # ============================================================

    def record_feedback(self, record_id: str, feedback: str, rating: int = None, notes: str = ""):
        """
        记录用户反馈

        Args:
            record_id: 记录ID
            feedback: 反馈（good/bad/neutral）
            rating: 评分（1-5）
            notes: 备注
        """
        for record in self.records:
            if record.record_id == record_id:
                record.user_feedback = feedback
                record.user_rating = rating
                record.notes = notes
                self._update_preferences(record)
                self._save()
                return True
        return False

    # ============================================================
    # 统计与报告
    # ============================================================

    def get_stats(self) -> Dict[str, Any]:
        """获取记忆库统计"""
        return {
            "total_records": len(self.records),
            "creative_count": sum(1 for r in self.records if r.mode == "creative"),
            "adapt_count": sum(1 for r in self.records if r.mode == "adapt"),
            "total_characters": len(self.characters),
            "total_templates": len(self.style_templates),
            "avg_quality": round(sum(r.quality_score for r in self.records) / len(self.records), 2) if self.records else 0,
            "quality_trend": self.get_quality_trend(),
            "top_styles": sorted(self.preferences.preferred_styles.items(), key=lambda x: x[1], reverse=True)[:5],
            "feedback_distribution": {
                "good": sum(1 for r in self.records if r.user_feedback == "good"),
                "bad": sum(1 for r in self.records if r.user_feedback == "bad"),
                "neutral": sum(1 for r in self.records if r.user_feedback == "neutral"),
                "no_feedback": sum(1 for r in self.records if not r.user_feedback),
            },
        }

    def print_report(self):
        """打印记忆库报告"""
        stats = self.get_stats()
        logger.info(f"\n{'='*60}")
        logger.info(f"改写记忆库报告")
        logger.info(f"{'='*60}")
        logger.info(f"  总记录: {stats['total_records']} (创意{stats['creative_count']} / 改编{stats['adapt_count']})")
        logger.info(f"  角色库: {stats['total_characters']}个")
        logger.info(f"  风格模板: {stats['total_templates']}个")
        logger.info(f"  平均质量: {stats['avg_quality']}/10")
        logger.info(f"  质量趋势: {stats['quality_trend']['trend']} (近期{stats['quality_trend']['recent_avg']} vs 早期{stats['quality_trend']['older_avg']})")
        logger.info(f"  反馈分布: {stats['feedback_distribution']}")
        if stats['top_styles']:
            logger.info(f"  常用风格: {', '.join(f'{s}({c}次)' for s, c in stats['top_styles'])}")
        logger.info(f"{'='*60}\n")


if __name__ == "__main__":
    # 测试
    logger.info("="*60)
    logger.info("改写记忆与自学习引擎测试")
    logger.info("="*60)

    memory = RewriteMemory(memory_path=r"D:\DobaoWork_Project\Ai_Video_Editor\director_engine_test\test_rewrite_memory.json")

    # 记录几次改写
    logger.info("\n记录3次改写...")
    r1 = memory.record_rewrite(
        mode="creative",
        input_text="一个程序员深夜加班，代码自己活了过来",
        constraints={"style": "suspense", "duration": 15, "platform": "douyin"},
        output_summary={"scenes": 5, "characters": ["小张"], "beats": 8},
        quality_score=7.0,
        quality_gates=[{"gate_id": "Q01", "passed": False}],
    )
    logger.info(f"  记录1: {r1.record_id}, 质量{r1.quality_score}")

    r2 = memory.record_rewrite(
        mode="adapt",
        input_text="改编一个办公室喜剧剧本",
        constraints={"style": "funny", "duration": 20, "platform": "douyin"},
        output_summary={"scenes": 3, "characters": ["小明", "小红"], "beats": 6},
        quality_score=8.5,
        quality_gates=[],
        user_feedback="good",
        user_rating=5,
    )
    logger.info(f"  记录2: {r2.record_id}, 质量{r2.quality_score}, 反馈{r2.user_feedback}")

    r3 = memory.record_rewrite(
        mode="creative",
        input_text="程序员加班的故事",
        constraints={"style": "suspense", "duration": 15, "platform": "douyin"},
        output_summary={"scenes": 4, "characters": ["小张"], "beats": 7},
        quality_score=6.0,
        quality_gates=[],
        user_feedback="bad",
        user_rating=2,
    )
    logger.info(f"  记录3: {r3.record_id}, 质量{r3.quality_score}, 反馈{r3.user_feedback}")

    # 相似检索
    logger.info("\n相似检索（输入：程序员深夜加班）...")
    similar = memory.find_similar("程序员深夜加班", top_k=2)
    for s in similar:
        logger.info(f"  相似: {s.record_id} (质量{s.quality_score})")

    # 改写建议
    logger.info("\n改写建议...")
    suggestion = memory.get_rewrite_suggestion("程序员深夜加班", mode="creative")
    logger.info(f"  推荐风格: {suggestion['recommended_style']}")
    logger.info(f"  质量目标: {suggestion['quality_target']}")
    logger.info(f"  相似案例: {len(suggestion['similar_cases'])}个")
    logger.info(f"  提示: {suggestion['tips']}")

    # 报告
    memory.print_report()

    # 清理测试文件
    import os
    test_path = r"D:\DobaoWork_Project\Ai_Video_Editor\director_engine_test\test_rewrite_memory.json"
    if os.path.exists(test_path):
        os.remove(test_path)
        logger.info("测试文件已清理")
