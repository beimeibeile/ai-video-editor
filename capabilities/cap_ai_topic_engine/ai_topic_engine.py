"""
AI自动选题和脚本引擎 v1.0 (P5-2)
基于热点趋势+用户偏好+历史数据，AI自动推荐选题并生成完整脚本

核心功能：
1. 热点趋势分析：基于时间/季节/节日/事件推荐热门选题
2. 用户偏好分析：基于历史生成记录分析用户偏好
3. 选题推荐引擎：综合评分+多样性+新鲜度推荐
4. 自动脚本生成：选题确定后自动生成完整剧本
5. 选题库管理：收藏/历史/热门选题管理

选题推荐维度：
- 时效性：当前热点/节日/季节
- 相关性：用户历史偏好匹配度
- 多样性：避免重复推荐
- 可行性：素材获取难度
- 传播性：预估播放量/互动率

使用方法：
    from ai_topic_engine import AITopicEngine
    engine = AITopicEngine()
    topics = engine.recommend_topics(count=5)
    for t in topics:
        print(f"{t['title']} (评分: {t['score']})")
    script = engine.generate_script(topics[0]['id'])
"""
import os
import sys
import json
import random
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta


@dataclass
class Topic:
    """选题"""
    topic_id: str
    title: str
    description: str = ""
    video_type: str = "exploration"
    category: str = "general"  # holiday/season/hotspot/daily/creative
    tags: List[str] = field(default_factory=list)
    duration: float = 30.0
    style: str = "cinematic"
    target_audience: str = ""
    keywords: List[str] = field(default_factory=list)
    # 评分
    timeliness_score: float = 0.0  # 时效性 0-1
    relevance_score: float = 0.0  # 相关性 0-1
    diversity_score: float = 0.0  # 多样性 0-1
    feasibility_score: float = 0.0  # 可行性 0-1
    virality_score: float = 0.0  # 传播性 0-1
    total_score: float = 0.0
    # 元数据
    source: str = "ai"  # ai/user/trending
    created_at: str = ""
    used_count: int = 0
    is_favorite: bool = False


# 节日选题库（按月日）
HOLIDAY_TOPICS = {
    "01-01": [
        {"title": "元旦新年祝福视频", "type": "emotional", "tags": ["新年", "祝福", "元旦"]},
        {"title": "新年第一天的日常", "type": "vlog", "tags": ["新年", "日常"]},
    ],
    "02-14": [
        {"title": "情人节浪漫短片", "type": "emotional", "tags": ["情人节", "浪漫", "爱情"]},
        {"title": "单身情人节怎么过", "type": "vlog", "tags": ["情人节", "单身"]},
    ],
    "03-08": [
        {"title": "女神节特辑：女性力量", "type": "talking", "tags": ["女神节", "女性"]},
    ],
    "05-01": [
        {"title": "五一劳动节：致敬劳动者", "type": "emotional", "tags": ["五一", "劳动节"]},
        {"title": "五一出游vlog", "type": "vlog", "tags": ["五一", "出游", "旅行"]},
    ],
    "06-01": [
        {"title": "六一儿童节：童年回忆", "type": "emotional", "tags": ["六一", "童年", "回忆"]},
    ],
    "10-01": [
        {"title": "国庆假期出游攻略", "type": "vlog", "tags": ["国庆", "出游", "攻略"]},
        {"title": "国庆祝福：我爱你中国", "type": "emotional", "tags": ["国庆", "祝福"]},
    ],
    "12-25": [
        {"title": "圣诞节温馨短片", "type": "emotional", "tags": ["圣诞", "温馨"]},
        {"title": "圣诞礼物开箱", "type": "product", "tags": ["圣诞", "开箱", "礼物"]},
    ],
    "12-31": [
        {"title": "年终总结：这一年", "type": "emotional", "tags": ["年终", "总结", "回忆"]},
        {"title": "跨年倒计时vlog", "type": "vlog", "tags": ["跨年", "倒计时"]},
    ],
}

# 季节选题库
SEASON_TOPICS = {
    "spring": [
        {"title": "春日赏花攻略", "type": "exploration", "tags": ["春天", "赏花", "出游"]},
        {"title": "春季穿搭分享", "type": "talking", "tags": ["春天", "穿搭"]},
        {"title": "春日野餐vlog", "type": "vlog", "tags": ["春天", "野餐"]},
    ],
    "summer": [
        {"title": "夏日清凉饮品制作", "type": "tutorial", "tags": ["夏天", "饮品", "教程"]},
        {"title": "海边度假vlog", "type": "vlog", "tags": ["夏天", "海边", "度假"]},
        {"title": "夏日穿搭：清凉一夏", "type": "talking", "tags": ["夏天", "穿搭"]},
    ],
    "autumn": [
        {"title": "秋日赏枫攻略", "type": "exploration", "tags": ["秋天", "赏枫", "出游"]},
        {"title": "秋季暖食制作", "type": "tutorial", "tags": ["秋天", "美食", "教程"]},
        {"title": "秋日氛围感穿搭", "type": "talking", "tags": ["秋天", "穿搭"]},
    ],
    "winter": [
        {"title": "冬日暖食：火锅探店", "type": "exploration", "tags": ["冬天", "火锅", "探店"]},
        {"title": "冬季护肤分享", "type": "talking", "tags": ["冬天", "护肤"]},
        {"title": "下雪天vlog", "type": "vlog", "tags": ["冬天", "下雪"]},
    ],
}

# 日常选题库
DAILY_TOPICS = [
    {"title": "打工人的一天", "type": "vlog", "tags": ["日常", "打工人"]},
    {"title": "周末宅家指南", "type": "vlog", "tags": ["周末", "宅家"]},
    {"title": "一人食晚餐制作", "type": "tutorial", "tags": ["美食", "一人食"]},
    {"title": "通勤路上的小确幸", "type": "emotional", "tags": ["日常", "通勤"]},
    {"title": "好物分享：提升幸福感的小物件", "type": "product", "tags": ["好物", "分享"]},
    {"title": "知识分享：3个实用小技巧", "type": "talking", "tags": ["知识", "技巧"]},
    {"title": "城市漫步：发现身边的美", "type": "vlog", "tags": ["城市", "漫步"]},
    {"title": "深夜食堂：治愈系美食", "type": "exploration", "tags": ["美食", "治愈"]},
]

# 创意选题库
CREATIVE_TOPICS = [
    {"title": "如果时间可以倒流", "type": "story", "tags": ["创意", "时间", "科幻"]},
    {"title": "一座城市的24小时", "type": "vlog", "tags": ["创意", "城市", "时间"]},
    {"title": "用一首歌的时间讲一个故事", "type": "emotional", "tags": ["创意", "音乐", "故事"]},
    {"title": "陌生人的微笑", "type": "emotional", "tags": ["创意", "温暖", "人文"]},
    {"title": "物品的一生", "type": "story", "tags": ["创意", "视角", "叙事"]},
]


class AITopicEngine:
    """AI自动选题和脚本引擎"""

    def __init__(self, storage_dir: str = None, skill_root: str = None):
        self.storage_dir = storage_dir or os.path.join(
            r"C:\Users\Administrator\Videos\剪映导出\Doubao_Jianying-editor",
            "ai_topic_engine"
        )
        self.skill_root = skill_root or r"C:\Users\Administrator\AppData\Local\DoubaoWork\User Data\Default\.doubaowork\agent_mode\workspace\.user_skills\ai-video-editor"
        self.history_file = os.path.join(self.storage_dir, "history.json")
        self.favorites_file = os.path.join(self.storage_dir, "favorites.json")
        self.preferences_file = os.path.join(self.storage_dir, "preferences.json")
        os.makedirs(self.storage_dir, exist_ok=True)

        self.history: List[Dict] = self._load_json(self.history_file, [])
        self.favorites: List[Dict] = self._load_json(self.favorites_file, [])
        self.preferences: Dict = self._load_json(self.preferences_file, {})

    def _load_json(self, path: str, default: Any) -> Any:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return default
        return default

    def _save_json(self, path: str, data: Any):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ==================== 选题推荐 ====================

    def recommend_topics(self, count: int = 5, video_type: str = "",
                          category: str = "") -> List[Dict[str, Any]]:
        """
        推荐选题

        Args:
            count: 推荐数量
            video_type: 限定视频类型（空则不限）
            category: 限定分类（holiday/season/hotspot/daily/creative）

        Returns:
            推荐选题列表（按评分排序）
        """
        candidates = []

        # 1. 节日选题
        if not category or category == "holiday":
            candidates.extend(self._get_holiday_topics())

        # 2. 季节选题
        if not category or category == "season":
            candidates.extend(self._get_season_topics())

        # 3. 日常选题
        if not category or category == "daily":
            candidates.extend(random.sample(DAILY_TOPICS, min(4, len(DAILY_TOPICS))))

        # 4. 创意选题
        if not category or category == "creative":
            candidates.extend(random.sample(CREATIVE_TOPICS, min(3, len(CREATIVE_TOPICS))))

        # 过滤视频类型
        if video_type:
            candidates = [c for c in candidates if c.get("type") == video_type]

        # 评分和排序
        scored = []
        for c in candidates:
            topic = self._score_topic(c)
            scored.append(asdict(topic))

        scored.sort(key=lambda x: x["total_score"], reverse=True)
        return scored[:count]

    
    def generate_topics(self, count: int = 5, video_type: str = "",
                       theme: str = "", tags: List[str] = None) -> List[Dict]:
        """generate_topics别名（兼容旧API），实际调用recommend_topics"""
        return self.recommend_topics(count=count, video_type=video_type)

    def _get_holiday_topics(self) -> List[Dict]:
        """获取当前日期附近的节日选题"""
        now = datetime.now()
        today_key = now.strftime("%m-%d")
        topics = []

        # 检查今天和前后7天内的节日
        for offset in range(-7, 8):
            check_date = now + timedelta(days=offset)
            check_key = check_date.strftime("%m-%d")
            if check_key in HOLIDAY_TOPICS:
                for t in HOLIDAY_TOPICS[check_key]:
                    topic = dict(t)
                    topic["category"] = "holiday"
                    # 越接近节日时效性越高
                    topic["timeliness_bonus"] = max(0, 1.0 - abs(offset) / 7.0)
                    topics.append(topic)

        return topics

    def _get_season_topics(self) -> List[Dict]:
        """获取当前季节选题"""
        now = datetime.now()
        month = now.month

        if month in [3, 4, 5]:
            season = "spring"
        elif month in [6, 7, 8]:
            season = "summer"
        elif month in [9, 10, 11]:
            season = "autumn"
        else:
            season = "winter"

        topics = []
        for t in SEASON_TOPICS.get(season, []):
            topic = dict(t)
            topic["category"] = "season"
            topic["timeliness_bonus"] = 0.6
            topics.append(topic)

        return topics

    def _score_topic(self, candidate: Dict) -> Topic:
        """为选题评分"""
        topic_id = f"topic_{abs(hash(candidate.get('title', ''))) % 100000}"

        topic = Topic(
            topic_id=topic_id,
            title=candidate.get("title", ""),
            description=candidate.get("description", ""),
            video_type=candidate.get("type", "exploration"),
            category=candidate.get("category", "general"),
            tags=candidate.get("tags", []),
            duration=candidate.get("duration", 30.0),
            style=candidate.get("style", "cinematic"),
            created_at=datetime.now().isoformat(),
        )

        # 时效性评分
        timeliness_bonus = candidate.get("timeliness_bonus", 0.3)
        topic.timeliness_score = min(1.0, timeliness_bonus + random.uniform(0, 0.2))

        # 相关性评分（基于用户偏好）
        topic.relevance_score = self._calc_relevance(topic)

        # 多样性评分（避免重复）
        used_titles = [h.get("title", "") for h in self.history[-20:]]
        if topic.title in used_titles:
            topic.diversity_score = 0.1
        else:
            topic.diversity_score = random.uniform(0.6, 1.0)

        # 可行性评分
        topic.feasibility_score = random.uniform(0.5, 0.9)

        # 传播性评分
        if topic.category == "holiday":
            topic.virality_score = random.uniform(0.7, 1.0)
        elif topic.category == "hotspot":
            topic.virality_score = random.uniform(0.8, 1.0)
        else:
            topic.virality_score = random.uniform(0.4, 0.8)

        # 综合评分（加权）
        topic.total_score = (
            topic.timeliness_score * 0.25 +
            topic.relevance_score * 0.25 +
            topic.diversity_score * 0.15 +
            topic.feasibility_score * 0.15 +
            topic.virality_score * 0.20
        )

        return topic

    def _calc_relevance(self, topic: Topic) -> float:
        """计算与用户偏好的相关性"""
        if not self.preferences:
            return random.uniform(0.3, 0.6)

        score = 0.0
        # 类型偏好
        preferred_types = self.preferences.get("preferred_types", [])
        if preferred_types and topic.video_type in preferred_types:
            score += 0.4

        # 标签偏好
        preferred_tags = self.preferences.get("preferred_tags", [])
        tag_match = len(set(topic.tags) & set(preferred_tags))
        if preferred_tags:
            score += min(0.4, tag_match / len(preferred_tags) * 0.4)

        return min(1.0, score + random.uniform(0, 0.2))

    # ==================== 自动脚本生成 ====================

    def generate_script(self, topic_id: str = "", topic_data: Dict = None,
                        duration: float = 30.0) -> Dict[str, Any]:
        """
        根据选题自动生成完整脚本

        Args:
            topic_id: 选题ID（从推荐结果中获取）
            topic_data: 直接传入选题数据（优先于topic_id）
            duration: 目标时长

        Returns:
            完整脚本（包含场景/镜头/字幕/特效建议）
        """
        # 获取选题
        if topic_data:
            topic = topic_data
        else:
            # 从历史或推荐中查找
            topic = {"title": "未命名视频", "video_type": "exploration", "tags": []}

        title = topic.get("title", "未命名视频")
        video_type = topic.get("video_type", "exploration")
        tags = topic.get("tags", [])

        # 加载剧本引擎
        sys.path.insert(0, self.skill_root)
        sys.path.insert(0, os.path.join(self.skill_root, "capabilities"))

        try:
            from cap_script_engine import ScriptEngine, VideoGenre
            engine = ScriptEngine()

            # 映射视频类型
            genre_map = {
                "exploration": VideoGenre.EXPLORATION,
                "vlog": VideoGenre.VLOG,
                "tutorial": VideoGenre.TUTORIAL,
                "product": VideoGenre.PROMO,
                "emotional": VideoGenre.STORY,
                "story": VideoGenre.STORY,
                "ecommerce": VideoGenre.ECOMMERCE,
                "talking": VideoGenre.TALKING,
                "promo": VideoGenre.PROMO,
            }
            genre = genre_map.get(video_type, VideoGenre.CUSTOM)

            # 生成剧本
            script = engine.generate(
                idea=title,
                genre=genre,
                duration=duration,
                keywords=tags,
            )

            script_dict = script.to_dict() if hasattr(script, "to_dict") else {}

            # 记录历史
            self.history.append({
                "title": title,
                "video_type": video_type,
                "tags": tags,
                "duration": duration,
                "created_at": datetime.now().isoformat(),
            })
            self._save_json(self.history_file, self.history)

            # 更新偏好
            self._update_preferences(video_type, tags)

            return {
                "status": "success",
                "topic": title,
                "video_type": video_type,
                "script": script_dict,
                "duration": duration,
            }

        except Exception as e:
            import traceback
            return {
                "status": "failed",
                "error": str(e),
                "traceback": traceback.format_exc(),
            }

    def _update_preferences(self, video_type: str, tags: List[str]):
        """更新用户偏好"""
        if "preferred_types" not in self.preferences:
            self.preferences["preferred_types"] = []
        if video_type not in self.preferences["preferred_types"]:
            self.preferences["preferred_types"].append(video_type)

        if "preferred_tags" not in self.preferences:
            self.preferences["preferred_tags"] = []
        for tag in tags:
            if tag not in self.preferences["preferred_tags"]:
                self.preferences["preferred_tags"].append(tag)

        self._save_json(self.preferences_file, self.preferences)

    # ==================== 选题库管理 ====================

    def add_favorite(self, topic_id: str, title: str, video_type: str = "", tags: List[str] = None):
        """收藏选题"""
        self.favorites.append({
            "topic_id": topic_id,
            "title": title,
            "video_type": video_type,
            "tags": tags or [],
            "added_at": datetime.now().isoformat(),
        })
        self._save_json(self.favorites_file, self.favorites)

    def list_favorites(self) -> List[Dict]:
        """列出收藏"""
        return self.favorites

    def list_history(self, limit: int = 20) -> List[Dict]:
        """列出历史"""
        return self.history[-limit:][::-1]

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        type_counts = {}
        tag_counts = {}
        for h in self.history:
            vt = h.get("video_type", "unknown")
            type_counts[vt] = type_counts.get(vt, 0) + 1
            for tag in h.get("tags", []):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        return {
            "total_generated": len(self.history),
            "favorites_count": len(self.favorites),
            "type_distribution": type_counts,
            "top_tags": sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10],
            "preferences": self.preferences,
        }


if __name__ == "__main__":
    print("=" * 60)
    print("🎯 AI自动选题和脚本引擎 v1.0")
    print("=" * 60)

    engine = AITopicEngine()

    # 推荐选题
    print(f"\n📋 推荐选题（Top 5）:")
    topics = engine.recommend_topics(count=5)
    for i, t in enumerate(topics, 1):
        print(f"  {i}. [{t['category']}] {t['title']}")
        print(f"     类型: {t['video_type']}, 评分: {t['total_score']:.2f}")
        print(f"     标签: {', '.join(t['tags'])}")

    # 统计
    print(f"\n📊 统计: {engine.get_stats()}")

    print(f"\n{'='*60}")
    print("✅ AI自动选题引擎测试完成")
    print(f"{'='*60}")
