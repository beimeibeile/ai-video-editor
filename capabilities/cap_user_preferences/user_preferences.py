"""
用户偏好学习系统 v1.0 (P5-4)
记录用户使用习惯和偏好，自动调整生成参数，越用越懂用户

核心功能：
1. 使用记录：记录每次生成的参数和用户反馈
2. 偏好分析：分析用户常用类型/时长/风格/特效
3. 自动调整：基于历史偏好自动推荐生成参数
4. 反馈学习：用户修改参数后自动学习
5. 偏好画像：生成用户偏好画像报告

学习维度：
- 视频类型偏好：用户最常用的视频类型
- 时长偏好：用户偏好的视频时长
- 风格偏好：用户偏好的视觉风格
- 特效偏好：用户常用的开场特效
- 画幅偏好：用户偏好的画幅比例
- 节奏偏好：用户偏好的剪辑节奏
- 修改模式：用户经常修改哪些参数

使用方法：
    from user_preferences import UserPreferenceLearner
    learner = UserPreferenceLearner()
    learner.record_generation(video_type="exploration", duration=30, style="warm")
    preferences = learner.get_recommendations()
    print(preferences)
"""
import os
import sys
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from collections import Counter


@dataclass
class GenerationRecord:
    """生成记录"""
    record_id: str
    timestamp: str
    video_type: str = "exploration"
    duration: float = 30.0
    style: str = "cinematic"
    hook_effect: str = "wipe"
    aspect_ratio: str = "9:16"
    topic: str = ""
    tags: List[str] = field(default_factory=list)
    # 用户反馈
    user_modified: bool = False
    modified_params: List[str] = field(default_factory=list)
    user_rating: int = 0  # 0=未评分, 1-5星
    regenerated: bool = False
    # 元数据
    success: bool = True
    error: str = ""


@dataclass
class UserProfile:
    """用户偏好画像"""
    total_generations: int = 0
    favorite_type: str = ""
    favorite_duration: float = 30.0
    favorite_style: str = "cinematic"
    favorite_effect: str = "wipe"
    favorite_aspect: str = "9:16"
    type_distribution: Dict[str, int] = field(default_factory=dict)
    style_distribution: Dict[str, int] = field(default_factory=dict)
    effect_distribution: Dict[str, int] = field(default_factory=dict)
    common_modifications: List[str] = field(default_factory=list)
    average_rating: float = 0.0
    learning_level: str = "beginner"  # beginner/intermediate/advanced/expert
    recommendations: Dict[str, Any] = field(default_factory=dict)


class UserPreferenceLearner:
    """用户偏好学习系统"""

    def __init__(self, storage_dir: str = None):
        self.storage_dir = storage_dir or os.path.join(
            r"C:\Users\Administrator\Videos\剪映导出\Doubao_Jianying-editor",
            "user_preferences"
        )
        self.records_file = os.path.join(self.storage_dir, "records.json")
        self.profile_file = os.path.join(self.storage_dir, "profile.json")
        os.makedirs(self.storage_dir, exist_ok=True)

        self.records: List[GenerationRecord] = self._load_records()
        self.profile: UserProfile = self._load_profile()

    def _load_records(self) -> List[GenerationRecord]:
        if os.path.exists(self.records_file):
            try:
                with open(self.records_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return [GenerationRecord(**r) for r in data]
            except Exception:
                return []
        return []

    def _save_records(self):
        with open(self.records_file, "w", encoding="utf-8") as f:
            json.dump([asdict(r) for r in self.records], f, ensure_ascii=False, indent=2)

    def _load_profile(self) -> UserProfile:
        if os.path.exists(self.profile_file):
            try:
                with open(self.profile_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return UserProfile(**data)
            except Exception:
                return UserProfile()
        return UserProfile()

    def _save_profile(self):
        with open(self.profile_file, "w", encoding="utf-8") as f:
            json.dump(asdict(self.profile), f, ensure_ascii=False, indent=2)

    # ==================== 记录生成 ====================

    def record_generation(self, video_type: str = "exploration", duration: float = 30.0,
                          user_modified: bool = False,
                          style: str = "cinematic", hook_effect: str = "wipe",
                          aspect_ratio: str = "9:16", topic: str = "",
                          tags: List[str] = None, success: bool = True,
                          error: str = "") -> str:
        """
        记录一次生成

        Returns:
            record_id 记录ID
        """
        record_id = f"gen_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.records)}"
        record = GenerationRecord(
            record_id=record_id,
            timestamp=datetime.now().isoformat(),
            video_type=video_type,
            duration=duration,
            style=style,
            hook_effect=hook_effect,
            aspect_ratio=aspect_ratio,
            topic=topic,
            tags=tags or [],
            success=success,
            error=error,
        )
        self.records.append(record)
        self._save_records()
        self._update_profile()
        return record_id

    def record_feedback(self, record_id: str, user_modified: bool = False,
                        modified_params: List[str] = None, user_rating: int = 0,
                        regenerated: bool = False):
        """记录用户反馈"""
        for record in self.records:
            if record.record_id == record_id:
                record.user_modified = user_modified
                record.modified_params = modified_params or []
                record.user_rating = user_rating
                record.regenerated = regenerated
                self._save_records()
                self._update_profile()
                return True
        return False

    # ==================== 偏好分析 ====================

    def _update_profile(self):
        """更新用户偏好画像"""
        if not self.records:
            return

        successful = [r for r in self.records if r.success]
        if not successful:
            return

        self.profile.total_generations = len(successful)

        # 类型分布
        type_counts = Counter(r.video_type for r in successful)
        self.profile.type_distribution = dict(type_counts)
        self.profile.favorite_type = type_counts.most_common(1)[0][0] if type_counts else "exploration"

        # 风格分布
        style_counts = Counter(r.style for r in successful)
        self.profile.style_distribution = dict(style_counts)
        self.profile.favorite_style = style_counts.most_common(1)[0][0] if style_counts else "cinematic"

        # 特效分布
        effect_counts = Counter(r.hook_effect for r in successful)
        self.profile.effect_distribution = dict(effect_counts)
        self.profile.favorite_effect = effect_counts.most_common(1)[0][0] if effect_counts else "wipe"

        # 平均时长
        durations = [r.duration for r in successful]
        self.profile.favorite_duration = round(sum(durations) / len(durations), 1) if durations else 30.0

        # 画幅
        aspect_counts = Counter(r.aspect_ratio for r in successful)
        self.profile.favorite_aspect = aspect_counts.most_common(1)[0][0] if aspect_counts else "9:16"

        # 常见修改
        all_modifications = []
        for r in successful:
            all_modifications.extend(r.modified_params)
        mod_counts = Counter(all_modifications)
        self.profile.common_modifications = [m for m, _ in mod_counts.most_common(5)]

        # 平均评分
        ratings = [r.user_rating for r in successful if r.user_rating > 0]
        self.profile.average_rating = round(sum(ratings) / len(ratings), 1) if ratings else 0.0

        # 学习等级
        if self.profile.total_generations < 5:
            self.profile.learning_level = "beginner"
        elif self.profile.total_generations < 20:
            self.profile.learning_level = "intermediate"
        elif self.profile.total_generations < 50:
            self.profile.learning_level = "advanced"
        else:
            self.profile.learning_level = "expert"

        # 生成推荐
        self.profile.recommendations = self._generate_recommendations()

        self._save_profile()

    def _generate_recommendations(self) -> Dict[str, Any]:
        """生成参数推荐"""
        recs = {}

        # 基于历史频率推荐
        if self.profile.type_distribution:
            recs["video_type"] = self.profile.favorite_type
            recs["video_type_confidence"] = (
                self.profile.type_distribution.get(self.profile.favorite_type, 0) /
                max(1, self.profile.total_generations)
            )

        recs["duration"] = self.profile.favorite_duration
        recs["style"] = self.profile.favorite_style
        recs["hook_effect"] = self.profile.favorite_effect
        recs["aspect_ratio"] = self.profile.favorite_aspect

        # 基于常见修改的智能调整
        if "duration" in self.profile.common_modifications:
            recs["duration_note"] = "用户经常修改时长，建议提供更多时长选项"
        if "style" in self.profile.common_modifications:
            recs["style_note"] = "用户经常修改风格，建议增加风格预览"

        return recs

    # ==================== 获取推荐 ====================

    def get_recommendations(self) -> Dict[str, Any]:
        """获取当前推荐参数"""
        return self.profile.recommendations or self._generate_recommendations()

    def get_profile(self) -> Dict[str, Any]:
        """获取用户偏好画像"""
        return asdict(self.profile)

    def get_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """获取历史记录"""
        return [asdict(r) for r in self.records[-limit:][::-1]]

    # ==================== 智能参数应用 ====================

    def apply_preferences(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        将用户偏好应用到生成参数中
        （只填充用户未指定的参数）

        Args:
            params: 用户指定的参数

        Returns:
            补充完整后的参数
        """
        recs = self.get_recommendations()
        result = dict(params)

        # 只填充未指定的参数
        for key in ["video_type", "duration", "style", "hook_effect", "aspect_ratio"]:
            if key not in result or result[key] is None:
                if key in recs:
                    result[key] = recs[key]

        return result

    # ==================== 统计 ====================

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        # 最近7天活跃度
        now = datetime.now()
        week_ago = now - timedelta(days=7)
        recent = [r for r in self.records
                  if datetime.fromisoformat(r.timestamp) > week_ago]

        # 成功率
        success_count = sum(1 for r in self.records if r.success)
        success_rate = success_count / max(1, len(self.records))

        # 修改率
        modified_count = sum(1 for r in self.records if r.user_modified)
        modification_rate = modified_count / max(1, len(self.records))

        return {
            "total_generations": len(self.records),
            "recent_7days": len(recent),
            "success_rate": round(success_rate, 2),
            "modification_rate": round(modification_rate, 2),
            "average_rating": self.profile.average_rating,
            "learning_level": self.profile.learning_level,
            "favorite_type": self.profile.favorite_type,
            "favorite_duration": self.profile.favorite_duration,
            "favorite_style": self.profile.favorite_style,
        }


if __name__ == "__main__":
    print("=" * 60)
    print("🧠 用户偏好学习系统 v1.0")
    print("=" * 60)

    learner = UserPreferenceLearner()

    # 模拟一些生成记录
    for i in range(10):
        vtype = "exploration" if i < 6 else "vlog"
        duration = 30 if i < 8 else 45
        style = "warm" if i < 7 else "cinematic"
        learner.record_generation(
            video_type=vtype,
            duration=duration,
            style=style,
            topic=f"测试视频{i}",
        )

    # 记录一些反馈
    records = learner.get_history(limit=3)
    for r in records[:2]:
        learner.record_feedback(r["record_id"], user_modified=True, modified_params=["duration"], user_rating=4)

    # 显示画像
    profile = learner.get_profile()
    print(f"\n👤 用户偏好画像:")
    print(f"  总生成数: {profile['total_generations']}")
    print(f"  学习等级: {profile['learning_level']}")
    print(f"  最爱类型: {profile['favorite_type']}")
    print(f"  最爱时长: {profile['favorite_duration']}秒")
    print(f"  最爱风格: {profile['favorite_style']}")
    print(f"  最爱特效: {profile['favorite_effect']}")
    print(f"  平均评分: {profile['average_rating']}")

    # 显示推荐
    recs = learner.get_recommendations()
    print(f"\n💡 推荐参数:")
    for k, v in recs.items():
        print(f"  {k}: {v}")

    # 统计
    stats = learner.get_stats()
    print(f"\n📊 统计:")
    print(f"  成功率: {stats['success_rate']:.0%}")
    print(f"  修改率: {stats['modification_rate']:.0%}")
    print(f"  近7天活跃: {stats['recent_7days']}次")

    print(f"\n{'='*60}")
    print("✅ 用户偏好学习系统测试完成")
    print(f"{'='*60}")
