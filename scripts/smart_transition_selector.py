"""
智能转场选择引擎（Smart Transition Selector）
根据场景情绪、节奏、内容类型自动匹配合适的转场效果和时长

设计原则：
1. 只使用免费转场（is_vip=False）
2. 避免连续使用相同转场
3. 根据情绪/节奏/场景智能匹配
4. 转场时长自适应（快节奏短，慢节奏长）
"""

import logging
import random
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)


# ============ 转场分类库（仅免费转场） ============
# 按视觉风格和情绪适配分类

TRANSITION_LIBRARY = {
    # 基础柔和类 — 适合日常、温馨、平静场景
    "soft": {
        "transitions": ["叠化", "模糊", "泛光", "渐变擦除", "色彩溶解", "叠加", "圆形遮罩"],
        "default_duration": 0.8,
        "emotions": ["平静", "温馨", "浪漫", "回忆", "治愈", "柔和"],
        "description": "柔和过渡，不打断观看节奏",
    },
    # 动感快切类 — 适合快节奏、活力、运动场景
    "dynamic": {
        "transitions": ["闪白", "闪黑", "白光快闪", "快门", "频闪", "向右擦除", "向左擦除", "向上擦除", "向下擦除"],
        "default_duration": 0.3,
        "emotions": ["激动", "紧张", "活力", "运动", "快节奏", "燃"],
        "description": "快速切换，增强节奏感",
    },
    # 滑动位移类 — 适合场景转换、旅行、Vlog
    "slide": {
        "transitions": ["左移", "右移", "上移", "下移", "滑动", "横向拉幕", "竖向拉幕", "向右拉伸", "向左拉伸"],
        "default_duration": 0.6,
        "emotions": ["旅行", "日常", "记录", "轻快", "自然"],
        "description": "方向感滑动，引导视线",
    },
    # 炫酷特效类 — 适合创意、科技、潮流场景
    "cool": {
        "transitions": ["圆形扫描", "放射", "旋转", "立方体", "百叶窗", "窗格", "粒子", "星星", "漩涡", "3D空间"],
        "default_duration": 0.7,
        "emotions": ["炫酷", "科技", "潮流", "创意", "未来感"],
        "description": "视觉冲击力强的特效转场",
    },
    # 复古胶片类 — 适合复古、怀旧、文艺场景
    "retro": {
        "transitions": ["复古放映", "岁月的痕迹", "胶片切闪", "胶片擦除", "胶片融化", "胶片闪光", "水墨", "撕纸"],
        "default_duration": 0.8,
        "emotions": ["复古", "怀旧", "文艺", "老电影", "胶片感"],
        "description": "复古质感，营造年代感",
    },
    # 故障赛博类 — 适合赛博朋克、科技、酷炫场景
    "glitch": {
        "transitions": ["故障", "电视故障_I", "电视故障_II", "雪花故障", "色差顺时针", "色差逆时针", "马赛克"],
        "default_duration": 0.5,
        "emotions": ["赛博朋克", "科技", "故障艺术", "炫酷", "电子"],
        "description": "故障艺术风格，科技感强",
    },
    # 缩放聚焦类 — 适合强调、重点突出、转场聚焦
    "zoom": {
        "transitions": ["推近", "拉远", "圆形遮罩_II", "圆形分割_II", "中心旋转"],
        "default_duration": 0.6,
        "emotions": ["强调", "聚焦", "重点", "震撼", "突出"],
        "description": "缩放聚焦，引导注意力",
    },
    # 翻页书本类 — 适合相册、回忆、故事类
    "book": {
        "transitions": ["翻页", "上下翻页", "翻篇", "回忆下滑", "回忆"],
        "default_duration": 0.9,
        "emotions": ["回忆", "故事", "相册", "日记", "温情"],
        "description": "翻页效果，故事感强",
    },
}

# 情绪→分类映射
EMOTION_TO_CATEGORY = {
    "平静": "soft", "温馨": "soft", "浪漫": "soft", "回忆": "soft", "治愈": "soft", "柔和": "soft",
    "激动": "dynamic", "紧张": "dynamic", "活力": "dynamic", "运动": "dynamic", "快节奏": "dynamic", "燃": "dynamic",
    "旅行": "slide", "日常": "slide", "记录": "slide", "轻快": "slide", "自然": "slide",
    "炫酷": "cool", "科技": "cool", "潮流": "cool", "创意": "cool", "未来感": "cool",
    "复古": "retro", "怀旧": "retro", "文艺": "retro", "老电影": "retro", "胶片感": "retro",
    "赛博朋克": "glitch", "故障艺术": "glitch", "电子": "glitch",
    "强调": "zoom", "聚焦": "zoom", "重点": "zoom", "震撼": "zoom", "突出": "zoom",
    "故事": "book", "相册": "book", "日记": "book", "温情": "book",
}

# 节奏→时长系数
PACE_TO_DURATION_FACTOR = {
    "very_fast": 0.4,   # 极快：0.2-0.3s
    "fast": 0.6,        # 快：0.3-0.5s
    "normal": 1.0,      # 正常：默认时长
    "slow": 1.3,        # 慢：1.2-1.5s
    "very_slow": 1.6,   # 极慢：1.5-2.0s
}


class SmartTransitionSelector:
    """智能转场选择器"""

    def __init__(self):
        self._last_transitions: List[str] = []
        self._max_history = 3  # 避免最近3次重复

    def select(self,
               emotion: str = "平静",
               pace: str = "normal",
               scene_type: str = "general",
               index: int = 0,
               total: int = 1) -> Dict[str, Any]:
        """
        智能选择转场

        Args:
            emotion: 情绪标签（平静/激动/温馨/紧张/炫酷/复古等）
            pace: 节奏（very_fast/fast/normal/slow/very_slow）
            scene_type: 场景类型（general/travel/vlog/cinematic/creative）
            index: 当前转场序号（用于首尾特殊处理）
            total: 总转场数

        Returns:
            {
                "name": 转场名称,
                "duration": 转场时长(秒),
                "category": 分类,
                "reason": 选择理由
            }
        """
        # 1. 确定分类
        category = EMOTION_TO_CATEGORY.get(emotion, "soft")

        # 场景类型微调
        if scene_type == "travel" and category == "soft":
            category = "slide"
        elif scene_type == "cinematic" and category in ["soft", "slide"]:
            category = random.choice(["soft", "zoom", "book"])
        elif scene_type == "creative":
            category = random.choice(["cool", "glitch", "zoom"])

        # 2. 首尾特殊处理
        if index == 0:
            # 第一个转场用柔和的
            category = "soft" if category not in ["dynamic", "glitch"] else category
        elif index == total - 1:
            # 最后一个转场用收尾感强的
            if category in ["dynamic", "glitch"]:
                category = "soft"

        # 3. 选择具体转场（避免重复）
        cat_info = TRANSITION_LIBRARY[category]
        available = [t for t in cat_info["transitions"]
                     if t not in self._last_transitions]
        if not available:
            available = cat_info["transitions"]  # 实在没了就允许重复

        transition_name = random.choice(available)

        # 4. 计算时长
        base_duration = cat_info["default_duration"]
        pace_factor = PACE_TO_DURATION_FACTOR.get(pace, 1.0)
        duration = round(base_duration * pace_factor, 2)

        # 限制范围
        duration = max(0.2, min(2.0, duration))

        # 5. 记录历史
        self._last_transitions.append(transition_name)
        if len(self._last_transitions) > self._max_history:
            self._last_transitions.pop(0)

        return {
            "name": transition_name,
            "duration": duration,
            "category": category,
            "reason": f"情绪={emotion}→分类={category}, 节奏={pace}→时长={duration}s",
        }

    def select_sequence(self,
                        emotions: List[str],
                        pace: str = "normal",
                        scene_type: str = "general") -> List[Dict[str, Any]]:
        """
        为一系列片段选择转场序列

        Args:
            emotions: 每个片段的情绪列表（长度=片段数，转场数=片段数-1）
            pace: 整体节奏
            scene_type: 场景类型

        Returns:
            转场配置列表，每个元素 {name, duration, category, reason}
        """
        self._last_transitions.clear()
        transitions = []
        total = len(emotions) - 1

        for i in range(total):
            # 使用后一个片段的情绪作为转场目标情绪
            target_emotion = emotions[i + 1] if i + 1 < len(emotions) else emotions[-1]
            trans = self.select(
                emotion=target_emotion,
                pace=pace,
                scene_type=scene_type,
                index=i,
                total=total,
            )
            transitions.append(trans)

        return transitions

    def reset(self):
        """重置历史记录"""
        self._last_transitions.clear()


# ============ 便捷函数 ============

_default_selector = None


def get_selector() -> SmartTransitionSelector:
    """获取全局单例"""
    global _default_selector
    if _default_selector is None:
        _default_selector = SmartTransitionSelector()
    return _default_selector


def smart_add_transitions(project, segments: List[Any],
                          emotions: List[str] = None,
                          pace: str = "normal",
                          scene_type: str = "general") -> List[Dict[str, Any]]:
    """
    便捷函数：为剪映工程的片段序列智能添加转场

    Args:
        project: JyProject实例
        segments: 视频片段列表
        emotions: 每个片段的情绪标签（长度应等于segments数）
        pace: 节奏
        scene_type: 场景类型

    Returns:
        应用的转场列表
    """
    if len(segments) < 2:
        return []

    selector = get_selector()
    selector.reset()

    if emotions is None:
        emotions = ["平静"] * len(segments)

    transitions = selector.select_sequence(emotions, pace, scene_type)
    applied = []

    for i, trans in enumerate(transitions):
        if i >= len(segments) - 1:
            break
        try:
            # 转场加在前一个片段上
            project.add_transition_simple(
                trans["name"],
                video_segment=segments[i],
                duration=trans["duration"],
            )
            applied.append(trans)
            logger.info(f"  转场 [{i+1}] {trans['name']} ({trans['duration']}s) - {trans['reason']}")
        except Exception as e:
            logger.warning(f"  转场 [{i+1}] {trans['name']} 失败: {e}")
            # 回退到叠化
            try:
                project.add_transition_simple(
                    "叠化",
                    video_segment=segments[i],
                    duration=0.5,
                )
                applied.append({"name": "叠化", "duration": 0.5, "category": "soft", "reason": "回退默认"})
            except Exception:
                pass

    return applied


def list_categories() -> List[Dict[str, Any]]:
    """列出所有转场分类"""
    return [
        {
            "category": cat,
            "count": len(info["transitions"]),
            "transitions": info["transitions"],
            "default_duration": info["default_duration"],
            "emotions": info["emotions"],
            "description": info["description"],
        }
        for cat, info in TRANSITION_LIBRARY.items()
    ]


if __name__ == "__main__":
    # 测试
    print("=== 智能转场选择引擎测试 ===")
    print()

    print("可用分类:")
    for cat in list_categories():
        print(f"  【{cat['category']}】{cat['count']}种 - {cat['description']}")
    print()

    # 测试序列选择
    selector = SmartTransitionSelector()
    emotions = ["平静", "激动", "紧张", "温馨", "回忆"]
    print(f"测试序列: 情绪={emotions}, 节奏=fast")
    result = selector.select_sequence(emotions, pace="fast", scene_type="vlog")
    for i, r in enumerate(result):
        print(f"  转场{i+1}: {r['name']} ({r['duration']}s) [{r['category']}]")
