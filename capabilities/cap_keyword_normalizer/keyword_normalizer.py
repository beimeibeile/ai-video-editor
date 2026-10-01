"""
口语关键词标准化引擎
将用户口语中的非标准表达转换为系统标准关键词，再进入系统流程。

核心机制：
1. 标准关键词词典：系统内统一使用的标准词
2. 口语→标准映射表：用户常见口语表达→标准词（可自学习扩充）
3. 标准化引擎：输入口语文本，输出标准化文本+提取的标准关键词
4. 自学习：记录用户使用的新表达，人工确认后加入映射表
"""

import os
import json
import re
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field, asdict


# ==================== 标准关键词词典 ====================

STANDARD_KEYWORDS = {
    # 视频类型
    "video_type": {
        "vlog": ["vlog", "Vlog", "VLOG", "日常记录", "生活记录", "流水账"],
        "exploration": ["探店", "探店视频", "探索", "探访", "打卡"],
        "tutorial": ["教程", "教学", "演示", "讲解", "怎么做", "如何做"],
        "product": ["产品", "产品展示", "测评", "评测", "开箱", "好物推荐"],
        "story": ["故事", "情感故事", "剧情", "短片", "微电影"],
        "ecommerce": ["带货", "电商", "直播带货", "商品推荐", "种草"],
        "knowledge": ["口播", "知识", "科普", "干货", "分享"],
        "promo": ["宣传", "宣传片", "广告", "品牌", "企业"],
        "travel": ["旅行", "旅游", "旅拍", "出游", "游记"],
        "food": ["美食", "吃播", "做饭", "料理", "烘焙"],
    },
    # 风格
    "style": {
        "cinematic": ["电影感", "电影", "大片", "专业", "高级", "质感", "影院级"],
        "warm": ["温暖", "温馨", "暖色", "治愈", "柔和", "暖色调"],
        "cool": ["冷色", "科技", "未来", "赛博", "酷炫", "冷色调", "科技感"],
        "vintage": ["复古", "怀旧", "胶片", "老电影", "港风", "复古风"],
        "noir": ["黑色", "悬疑", "暗黑", "神秘", "压抑", "暗黑风"],
        "minimal": ["简约", "极简", "干净", "简洁", "性冷淡", "极简风"],
        "upbeat": ["轻快", "活泼", "欢快", "轻松", "动感", "活力", "明快", "俏皮", "元气", "热血", "燃", "happy", "upbeat", "lively", "活泼可爱"],
        "epic": ["史诗", "震撼", "宏大", "磅礴", "大气", "史诗级"],
        "romantic": ["浪漫", "唯美", "梦幻", "甜蜜", "浪漫风"],
        "funny": ["搞笑", "幽默", "逗比", "沙雕", "喜剧", "搞笑风"],
    },
    # 开场特效
    "hook_effect": {
        "wipe": ["擦开", "羽化擦开", "文字擦开", "擦除", "wipe"],
        "mask_flash": ["快闪", "蒙版快闪", "闪白", "闪烁", "快闪特效"],
        "subtitle_bar": ["字幕条", "高光字幕", "字幕条动画", "标题条"],
        "character_card": ["人物卡", "角色卡", "人物介绍卡", "角色介绍"],
        "glow_outline": ["发光", "发光轮廓", "描边发光", "霓虹发光"],
        "text_background": ["背景滑入", "文字背景", "背景条", "色块滑入"],
        "blinds": ["百叶窗", "百叶窗转场", "百叶窗展开"],
        "zoom_in": ["放大", "推近", "放大入场", "zoom"],
    },
    # 转场
    "transition": {
        "fade": ["淡入淡出", "叠化", "溶解", "fade", "淡入", "淡出"],
        "slide_left": ["左滑", "向左滑", "左滑转场"],
        "slide_right": ["右滑", "向右滑", "右滑转场"],
        "zoom_in": ["放大转场", "推镜转场", "放大过渡"],
        "zoom_out": ["缩小转场", "拉镜转场", "缩小过渡"],
        "rotate": ["旋转转场", "旋转过渡"],
        "flip": ["翻转", "翻页", "flip"],
        "glitch": ["故障", "信号故障", " glitch", "花屏"],
    },
    # 运镜
    "camera_move": {
        "zoom_in": ["推", "推镜", "推进", "推近", "放大镜头"],
        "zoom_out": ["拉", "拉镜", "拉远", "拉远镜头", "缩小镜头"],
        "pan_left": ["左摇", "向左摇", "左移", "向左移"],
        "pan_right": ["右摇", "向右摇", "右移", "向右移"],
        "tilt_up": ["上摇", "向上摇", "上移", "向上移"],
        "tilt_down": ["下摇", "向下摇", "下移", "向下移"],
        "rotate_cw": ["顺时针旋转", "右转", "顺时针"],
        "rotate_ccw": ["逆时针旋转", "左转", "逆时针"],
        "pulse": ["呼吸", "呼吸效果", "微缩放"],
        "handheld": ["手持", "手持晃动", "手持感", "晃动"],
        "dolly_zoom": ["滑动变焦", "希区柯克变焦", "dolly zoom"],
        "static": ["固定", "固定镜头", "静止", "不动"],
    },
    # 画幅
    "aspect_ratio": {
        "9:16": ["竖屏", "竖版", "9:16", "抖音", "快手", "手机竖屏", "垂直"],
        "16:9": ["横屏", "横版", "16:9", "宽屏", "电脑", "横向", "B站", "YouTube"],
        "1:1": ["方形", "正方形", "1:1", "方屏", "ins", "Instagram"],
        "4:3": ["4:3", "标准屏", "传统屏"],
        "3:4": ["3:4", "小红书竖屏", "小红书"],
    },
    # 时长单位
    "duration_unit": {
        "second": ["秒", "s", "S", "秒钟"],
        "minute": ["分钟", "min", "MIN", "分", "分半"],
    },
}


# ==================== 标准化结果 ====================

@dataclass
class NormalizedResult:
    """标准化结果"""
    original_text: str
    normalized_text: str
    extracted_keywords: Dict[str, List[str]] = field(default_factory=dict)
    replacements: List[Dict[str, str]] = field(default_factory=list)
    confidence: float = 0.0
    unknown_terms: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ==================== 标准化引擎 ====================

class KeywordNormalizer:
    """口语关键词标准化引擎"""

    def __init__(self, skill_root: str = None):
        self.skill_root = skill_root or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.custom_mappings_path = os.path.join(
            self.skill_root, "cap_keyword_normalizer", "custom_mappings.json"
        )
        self.learned_terms_path = os.path.join(
            self.skill_root, "cap_keyword_normalizer", "learned_terms.json"
        )
        self.custom_mappings = self._load_custom_mappings()
        self.learned_terms = self._load_learned_terms()

    def _load_custom_mappings(self) -> Dict[str, Dict[str, str]]:
        """加载自定义映射（口语→标准词）"""
        if os.path.exists(self.custom_mappings_path):
            try:
                with open(self.custom_mappings_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_custom_mappings(self):
        """保存自定义映射"""
        os.makedirs(os.path.dirname(self.custom_mappings_path), exist_ok=True)
        with open(self.custom_mappings_path, "w", encoding="utf-8") as f:
            json.dump(self.custom_mappings, f, ensure_ascii=False, indent=2)

    def _load_learned_terms(self) -> Dict[str, int]:
        """加载自学习词频统计"""
        if os.path.exists(self.learned_terms_path):
            try:
                with open(self.learned_terms_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_learned_terms(self):
        """保存自学习词频"""
        os.makedirs(os.path.dirname(self.learned_terms_path), exist_ok=True)
        with open(self.learned_terms_path, "w", encoding="utf-8") as f:
            json.dump(self.learned_terms, f, ensure_ascii=False, indent=2)

    def _build_full_mapping(self) -> Dict[str, Tuple[str, str]]:
        """构建完整映射表：口语词→(标准词, 类别)"""
        mapping = {}
        # 1. 标准词典中的同义词
        for category, standards in STANDARD_KEYWORDS.items():
            for standard, synonyms in standards.items():
                for syn in synonyms:
                    mapping[syn] = (standard, category)
        # 2. 自定义映射（优先级更高）
        for category, terms in self.custom_mappings.items():
            for colloquial, standard in terms.items():
                mapping[colloquial] = (standard, category)
        return mapping

    def normalize(self, text: str) -> NormalizedResult:
        """
        将口语文本标准化

        Args:
            text: 用户输入的口语文本

        Returns:
            NormalizedResult 标准化结果
        """
        if not text:
            return NormalizedResult(original_text="", normalized_text="", confidence=0.0)

        full_mapping = self._build_full_mapping()
        normalized_text = text
        extracted = {}
        replacements = []
        matched_terms = set()

        # 按词长度降序排序，优先匹配长词（避免"电影"先匹配导致"电影感"无法匹配）
        sorted_terms = sorted(full_mapping.keys(), key=len, reverse=True)

        # 使用占位符法避免二次替换（如"秒"→"second"后"s"又被替换）
        placeholder_map = {}  # placeholder -> (standard, category, colloquial)
        temp_text = normalized_text

        for colloquial in sorted_terms:
            if colloquial in temp_text and colloquial not in matched_terms:
                standard, category = full_mapping[colloquial]
                placeholder = f"__KWN_{len(placeholder_map)}__"
                placeholder_map[placeholder] = (standard, category, colloquial)
                temp_text = temp_text.replace(colloquial, placeholder)
                matched_terms.add(colloquial)

        # 将占位符替换为标准词
        for placeholder, (standard, category, colloquial) in placeholder_map.items():
            normalized_text = temp_text.replace(placeholder, standard)
            temp_text = normalized_text
            # 记录提取的关键词
            if category not in extracted:
                extracted[category] = []
            if standard not in extracted[category]:
                extracted[category].append(standard)
            replacements.append({
                "from": colloquial,
                "to": standard,
                "category": category
            })

        # 记录未识别的潜在术语（2-4字中文词，供自学习）
        unknown = self._find_unknown_terms(text, matched_terms)

        # 计算置信度
        total_potential = len(re.findall(r'[\u4e00-\u9fff]{2,6}', text))
        confidence = min(1.0, len(replacements) / max(1, total_potential * 0.3)) if replacements else 0.0

        return NormalizedResult(
            original_text=text,
            normalized_text=normalized_text,
            extracted_keywords=extracted,
            replacements=replacements,
            confidence=confidence,
            unknown_terms=unknown
        )

    def _find_unknown_terms(self, text: str, matched: set) -> List[str]:
        """查找未识别的潜在术语（供自学习）"""
        # 提取2-6字中文词
        candidates = re.findall(r'[\u4e00-\u9fff]{2,6}', text)
        unknown = []
        full_mapping = self._build_full_mapping()
        for term in candidates:
            if term not in full_mapping and term not in matched:
                # 过滤常见虚词和数词
                if not re.match(r'^[0-9一二三四五六七八九十百千万]+$', term):
                    if len(term) >= 2 and term not in unknown:
                        unknown.append(term)
        return unknown[:10]

    def learn(self, colloquial: str, standard: str, category: str, min_freq: int = 3) -> bool:
        """
        自学习：记录用户使用的口语表达，达到阈值后加入映射表

        Args:
            colloquial: 口语表达
            standard: 对应的标准词
            category: 类别（video_type/style/hook_effect等）
            min_freq: 达到多少次使用后自动加入映射

        Returns:
            是否新加入映射表
        """
        key = f"{category}:{colloquial}"
        self.learned_terms[key] = self.learned_terms.get(key, 0) + 1
        self._save_learned_terms()

        if self.learned_terms[key] >= min_freq:
            if category not in self.custom_mappings:
                self.custom_mappings[category] = {}
            self.custom_mappings[category][colloquial] = standard
            self._save_custom_mappings()
            return True
        return False

    def add_mapping(self, colloquial: str, standard: str, category: str) -> bool:
        """
        手动添加映射（人工确认后）

        Args:
            colloquial: 口语表达
            standard: 标准词
            category: 类别

        Returns:
            是否添加成功
        """
        if category not in self.custom_mappings:
            self.custom_mappings[category] = {}
        self.custom_mappings[category][colloquial] = standard
        self._save_custom_mappings()
        return True

    def get_standard_keywords(self, category: str = None) -> Dict[str, List[str]]:
        """获取标准关键词词典"""
        if category:
            return {category: STANDARD_KEYWORDS.get(category, {})}
        return STANDARD_KEYWORDS

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        full_mapping = self._build_full_mapping()
        return {
            "standard_categories": len(STANDARD_KEYWORDS),
            "standard_keywords_total": sum(len(v) for v in STANDARD_KEYWORDS.values()),
            "custom_mappings": sum(len(v) for v in self.custom_mappings.values()),
            "learned_terms": len(self.learned_terms),
            "total_mappings": len(full_mapping),
        }


# ==================== 便捷函数 ====================

def normalize_text(text: str, skill_root: str = None) -> NormalizedResult:
    """便捷函数：标准化文本"""
    normalizer = KeywordNormalizer(skill_root)
    return normalizer.normalize(text)


if __name__ == "__main__":
    print("=" * 60)
    print("口语关键词标准化引擎 v1.0")
    print("=" * 60)

    normalizer = KeywordNormalizer()
    stats = normalizer.get_stats()
    print(f"\n词典统计:")
    for k, v in stats.items():
        print(f"  {k}: {v}")

    # 测试
    test_cases = [
        "帮我做一个30秒的国庆旅行vlog，要有开场标题、3个旅行片段、结尾字幕，风格要轻快活泼",
        "做一个探店视频，去吃淮南牛肉汤，电影感一点",
        "整个竖屏的搞笑短视频，15秒就行",
        "用手持晃动的感觉拍一个vlog，暖色调",
    ]

    print(f"\n测试用例:")
    for i, text in enumerate(test_cases, 1):
        result = normalizer.normalize(text)
        print(f"\n【测试{i}】{text[:40]}...")
        print(f"  标准化后: {result.normalized_text[:50]}...")
        print(f"  提取关键词: {result.extracted_keywords}")
        print(f"  替换数: {len(result.replacements)}, 置信度: {result.confidence:.0%}")
        if result.unknown_terms:
            print(f"  未识别术语: {result.unknown_terms[:5]}")
