"""
自然语言指令引擎 v1.0 (P5-1)
用户用自然语言描述需求，系统自动解析意图、提取参数、生成视频

核心功能：
1. NLU意图解析：从自然语言中提取视频类型/主题/时长/风格/特效等参数
2. 参数自动映射：将提取的参数映射到pipeline输入
3. 一键生成：调用ScriptDrivenPipeline全链路生成
4. 意图确认：生成前展示解析结果，用户可确认或修改

支持的自然语言指令示例：
- "做一个30秒的探店美食视频，主题是淮南牛肉汤"
- "帮我生成一个vlog，记录今天的日常，时长45秒"
- "做一个产品测评视频，测评最新的相机，风格要专业"
- "生成一个情感故事短片，关于友情，1分钟"
- "做一个口播知识视频，讲AI视频剪辑，30秒"

使用方法：
    from natural_language import NaturalLanguageEngine
    nle = NaturalLanguageEngine()
    result = nle.parse("做一个30秒的探店美食视频，主题是淮南牛肉汤")
    print(result)  # 展示解析结果
    nle.generate(result)  # 一键生成
"""
import os
import sys
import re
import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class ParsedCommand:
    """解析后的指令"""
    original_text: str
    intent: str = "generate_video"  # generate_video/explain/help
    video_type: str = "exploration"  # exploration/vlog/tutorial/product/emotional/story/ecommerce/talking/promo
    topic: str = ""
    duration: float = 30.0
    style: str = "cinematic"  # cinematic/warm/cool/vintage/noir/minimal
    aspect_ratio: str = "9:16"
    hook_effect: str = "wipe"  # wipe/bg_slide/layout/subtitle_bar/character_card/date_badge
    target_audience: str = ""
    keywords: List[str] = field(default_factory=list)
    confidence: float = 0.0
    missing_params: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


# 视频类型关键词映射
VIDEO_TYPE_KEYWORDS = {
    "exploration": ["探店", "美食", "餐饮", "打卡", "测评店", "吃喝玩乐", "美食探店"],
    "vlog": ["vlog", "日常", "记录", "生活", "日记", "随拍", "日常记录"],
    "tutorial": ["教程", "教学", "演示", "怎么做", "如何", "步骤", "操作指南"],
    "product": ["产品", "测评", "评测", "开箱", "体验", "好物", "推荐产品"],
    "emotional": ["情感", "情绪", "治愈", "感动", "温情", "走心", "情感故事"],
    "story": ["故事", "剧情", "短片", "微电影", "叙事", "情节", "故事短片"],
    "ecommerce": ["电商", "带货", "直播", "商品", "卖货", "促销", "电商带货"],
    "talking": ["口播", "知识", "科普", "讲解", "说", "讲", "知识分享"],
    "promo": ["宣传", "推广", "广告", "品牌", "企业", "公司", "宣传片"],
}

# 风格关键词映射
STYLE_KEYWORDS = {
    "cinematic": ["电影", "电影感", "大片", "专业", "高级", "质感"],
    "warm": ["温暖", "温馨", "暖色", "治愈", "柔和"],
    "cool": ["冷色", "科技", "未来", "赛博", "酷炫"],
    "vintage": ["复古", "怀旧", "胶片", "老电影", "港风"],
    "noir": ["黑色", "悬疑", "暗黑", "神秘", "压抑"],
    "minimal": ["简约", "极简", "干净", "简洁", "性冷淡"],
    "upbeat": ["轻快", "活泼", "欢快", "轻松", "动感", "活力", "明快", "俏皮", "元气", "热血", "燃", "happy", "upbeat", "lively"],
}

# 特效关键词映射
HOOK_EFFECT_KEYWORDS = {
    "wipe": ["擦除", "擦开", "划像", "过渡"],
    "bg_slide": ["背景滑动", "滑入", "背景移动"],
    "layout": ["排版", "文字排版", "布局"],
    "subtitle_bar": ["字幕条", "标题条", "标签", "胶囊"],
    "character_card": ["角色卡", "人物卡", "角色介绍", "人物介绍"],
    "date_badge": ["日期", "时间戳", "时间标签"],
}

# 时长解析模式
DURATION_PATTERNS = [
    (r'(\d+(?:\.\d+)?)\s*(?:秒|s|S)', 1.0),
    (r'(\d+(?:\.\d+)?)\s*(?:分钟|分|min|m)', 60.0),
    (r'(\d+)\s*秒', 1.0),
]

# 主题提取模式
TOPIC_PATTERNS = [
    r'(?:主题|题目|标题|内容|关于|讲的是|介绍)\s*[是：:为]?\s*["「『]?([^，。！？,.;!?\n]+)',
    r'(?:做|生成|制作|拍)\s*(?:一个|一个|条|支)\s*[^，。]*?[，,]\s*(?:主题|内容|关于)?\s*([^，。！？\n]+)',
]


class NaturalLanguageEngine:
    """自然语言指令引擎"""

    def __init__(self, skill_root: str = None):
        self.skill_root = skill_root or r"C:\Users\Administrator\AppData\Local\DoubaoWork\User Data\Default\.doubaowork\agent_mode\workspace\.user_skills\ai-video-editor"
        self.pipeline = None

    def _load_pipeline(self):
        """懒加载pipeline"""
        if self.pipeline is None:
            sys.path.insert(0, self.skill_root)
            sys.path.insert(0, os.path.join(self.skill_root, "capabilities"))
            from cap_e2e_pipeline.pipeline_script_driver import ScriptDrivenPipeline
            self.pipeline = ScriptDrivenPipeline()
        return self.pipeline

    # ==================== 意图解析 ====================

    def parse(self, text: str) -> Dict[str, Any]:
        """
        解析自然语言指令

        Args:
            text: 用户输入的自然语言

        Returns:
            ParsedCommand 解析结果
        """
        text = text.strip()
        cmd = ParsedCommand(original_text=text)

        # 0. 口语关键词标准化（将用户口语转为系统标准关键词）
        try:
            from cap_keyword_normalizer import KeywordNormalizer
            normalizer = KeywordNormalizer(skill_root=self.skill_root)
            norm_result = normalizer.normalize(text)
            # 使用标准化后的文本进行后续解析
            parse_text = norm_result.normalized_text
            # 合并提取的标准关键词
            std_keywords = []
            for cat, kws in norm_result.extracted_keywords.items():
                std_keywords.extend(kws)
            cmd.keywords = list(set(std_keywords))
            cmd.confidence += norm_result.confidence * 0.1
        except Exception:
            parse_text = text

        # 1. 检测意图
        if any(w in parse_text for w in ["帮助", "怎么用", "使用方法", "help", "Help"]):
            cmd.intent = "help"
            cmd.confidence = 0.9
            return asdict(cmd)

        if any(w in parse_text for w in ["解释", "说明", "什么是", "介绍一下"]):
            cmd.intent = "explain"
            cmd.confidence = 0.8
            return asdict(cmd)

        cmd.intent = "generate_video"

        # 2. 提取视频类型
        video_type, type_confidence = self._extract_video_type(parse_text)
        cmd.video_type = video_type
        cmd.confidence += type_confidence * 0.3

        # 3. 提取时长
        duration, duration_found = self._extract_duration(parse_text)
        if duration_found:
            cmd.duration = duration
            cmd.confidence += 0.15

        # 4. 提取风格
        style, style_found = self._extract_style(parse_text)
        if style_found:
            cmd.style = style
            cmd.confidence += 0.1

        # 5. 提取特效
        hook_effect, effect_found = self._extract_hook_effect(parse_text)
        if effect_found:
            cmd.hook_effect = hook_effect
            cmd.confidence += 0.1

        # 6. 提取主题
        topic = self._extract_topic(parse_text, cmd.video_type)
        cmd.topic = topic
        if topic:
            cmd.confidence += 0.25

        # 7. 提取关键词（合并标准化提取的和文本提取的）
        text_keywords = self._extract_keywords(parse_text)
        all_keywords = list(set(cmd.keywords + text_keywords))
        cmd.keywords = all_keywords[:8]

        # 8. 检查缺失参数
        if not cmd.topic:
            cmd.missing_params.append("topic（主题）")
            cmd.suggestions.append("请补充视频主题，例如：主题是淮南牛肉汤")

        # 9. 归一化置信度
        cmd.confidence = min(1.0, cmd.confidence)

        return asdict(cmd)

    def _extract_video_type(self, text: str) -> Tuple[str, float]:
        """提取视频类型"""
        text_lower = text.lower()
        best_type = "exploration"
        best_score = 0

        for vtype, keywords in VIDEO_TYPE_KEYWORDS.items():
            score = 0
            for kw in keywords:
                if kw in text or kw.lower() in text_lower:
                    score += 1
            if score > best_score:
                best_score = score
                best_type = vtype

        if best_score > 0:
            return best_type, min(1.0, best_score * 0.5)
        return "exploration", 0.0

    def _extract_duration(self, text: str) -> Tuple[float, bool]:
        """提取时长"""
        for pattern, multiplier in DURATION_PATTERNS:
            match = re.search(pattern, text)
            if match:
                try:
                    value = float(match.group(1))
                    duration = value * multiplier
                    # 合理范围检查
                    if 3 <= duration <= 600:
                        return duration, True
                except ValueError:
                    pass
        return 30.0, False

    def _extract_style(self, text: str) -> Tuple[str, bool]:
        """提取风格"""
        for style, keywords in STYLE_KEYWORDS.items():
            for kw in keywords:
                if kw in text:
                    return style, True
        return "cinematic", False

    def _extract_hook_effect(self, text: str) -> Tuple[str, bool]:
        """提取开场特效"""
        for effect, keywords in HOOK_EFFECT_KEYWORDS.items():
            for kw in keywords:
                if kw in text:
                    return effect, True
        return "wipe", False

    def _extract_topic(self, text: str, video_type: str) -> str:
        """提取主题（改进版：过滤结构描述性内容）"""
        # 结构描述过滤词（这些词开头的内容不是主题）
        structural_prefixes = ["要有", "包含", "包括", "需要", "个", "片段", "镜头", "场景", "结尾", "开场", "标题", "字幕", "配乐", "特效", "转场"]

        def _is_structural(t: str) -> bool:
            """判断是否是结构描述而非主题"""
            if not t:
                return True
            # 包含数字+量词+片段/镜头等结构词
            if re.search(r'\d+\s*[个条段帧]\s*(旅行|片段|镜头|场景|内容)', t):
                return True
            # 以结构词开头
            for prefix in structural_prefixes:
                if t.startswith(prefix):
                    return True
            # 纯标点或太短
            if len(t) <= 1:
                return True
            return False

        # 尝试模式匹配
        for pattern in TOPIC_PATTERNS:
            match = re.search(pattern, text)
            if match:
                topic = match.group(1).strip()
                topic = re.sub(r'[，。！？,.;!?]$', '', topic)
                # 过滤结构描述
                if not _is_structural(topic) and len(topic) > 1 and len(topic) < 50:
                    return topic

        # 从类型关键词后提取（改进：只取第一个逗号前的内容，且过滤结构词）
        type_keywords = VIDEO_TYPE_KEYWORDS.get(video_type, [])
        for kw in type_keywords:
            if kw in text:
                idx = text.find(kw)
                after = text[idx + len(kw):].strip()
                after = re.sub(r'^[的，,：:是为关于]+', '', after)
                # 只取第一个逗号/句号前的内容
                after = re.split(r'[，。！？,.;!?]', after)[0].strip()
                if not _is_structural(after) and len(after) > 1 and len(after) < 50:
                    return after

        # 兜底：从节日/地点/主题名词中提取
        fallback_topics = ["国庆", "春节", "中秋", "端午", "元旦", "圣诞", "情人节", "母亲节", "父亲节",
                           "旅行", "旅游", "美食", "探店", "产品", "测评", "日常", "教程", "情感",
                           "故事", "口播", "知识", "好物", "推荐", "风景", "人物", "城市", "校园",
                           "职场", "宠物", "健身", "婚礼", "生日", "毕业", "年会"]
        for ft in fallback_topics:
            if ft in text:
                return ft

        return ""

    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词（改进版）"""
        keywords = []

        # 1. 提取引号中的内容
        quotes = re.findall(r'["「『]([^"」』]+)["」』]', text)
        keywords.extend(quotes)

        # 2. 提取视频类型关键词
        for vtype, kws in VIDEO_TYPE_KEYWORDS.items():
            for kw in kws:
                if kw in text and kw not in keywords:
                    keywords.append(kw)

        # 3. 提取风格关键词
        for style, kws in STYLE_KEYWORDS.items():
            for kw in kws:
                if kw in text and kw not in keywords:
                    keywords.append(kw)

        # 4. 提取数字+量词（如"30秒"、"3个"）
        quantities = re.findall(r'\d+\s*[秒分钟个条支段帧]', text)
        keywords.extend(quantities)

        # 5. 提取常见名词（节日、地点、主题词）
        common_nouns = ["国庆", "春节", "中秋", "端午", "旅行", "旅游", "美食", "探店", "产品", "测评",
                        "日常", "vlog", "教程", "情感", "故事", "口播", "知识", "好物", "推荐",
                        "风景", "人物", "城市", "农村", "校园", "职场", "宠物", "宝宝", "健身"]
        for noun in common_nouns:
            if noun in text and noun not in keywords:
                keywords.append(noun)

        return list(set(keywords))[:8]

    # ==================== 指令确认 ====================

    def format_parsed(self, cmd: ParsedCommand) -> str:
        """格式化解析结果，用于展示给用户确认"""
        lines = [
            "=" * 50,
            "📋 指令解析结果",
            "=" * 50,
            f"原始指令: {cmd.original_text}",
            f"意图: {cmd.intent}",
            f"视频类型: {cmd.video_type}",
            f"主题: {cmd.topic or '（未指定）'}",
            f"时长: {cmd.duration}秒",
            f"风格: {cmd.style}",
            f"开场特效: {cmd.hook_effect}",
            f"画幅: {cmd.aspect_ratio}",
            f"置信度: {cmd.confidence:.0%}",
        ]

        if cmd.keywords:
            lines.append(f"关键词: {', '.join(cmd.keywords)}")

        if cmd.missing_params:
            lines.append("")
            lines.append("⚠️ 缺失参数:")
            for p in cmd.missing_params:
                lines.append(f"  - {p}")

        if cmd.suggestions:
            lines.append("")
            lines.append("💡 建议:")
            for s in cmd.suggestions:
                lines.append(f"  - {s}")

        lines.append("=" * 50)
        return "\n".join(lines)

    # ==================== 一键生成 ====================

    def generate(self, cmd: Dict[str, Any], project_name: str = None,
                 auto_confirm: bool = False) -> Dict[str, Any]:
        """
        根据解析结果一键生成视频

        Args:
            cmd: 解析后的指令
            project_name: 工程名（默认自动生成）
            auto_confirm: 是否自动确认（跳过确认步骤）

        Returns:
            生成结果
        """
        if isinstance(cmd, dict):
            cmd = ParsedCommand(**cmd)
        if cmd.intent == "help":
            return {
                "status": "help",
                "message": self._get_help_text(),
            }

        if cmd.intent == "explain":
            return {
                "status": "explain",
                "message": f"已解析指令：{cmd.original_text}\n{self.format_parsed(cmd)}",
            }

        # 检查缺失参数
        if cmd.missing_params and not auto_confirm:
            return {
                "status": "need_confirm",
                "message": "存在缺失参数，请补充后重试",
                "missing": cmd.missing_params,
                "suggestions": cmd.suggestions,
                "parsed": asdict(cmd),
            }

        # 自动生成工程名
        if not project_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            topic_safe = re.sub(r'[^\w\u4e00-\u9fff]', '_', cmd.topic[:10]) or "video"
            project_name = f"NL_{topic_safe}_{timestamp}"

        # 加载pipeline并生成
        pipeline = self._load_pipeline()

        try:
            result = pipeline.run(
                topic=cmd.topic or "未命名视频",
                video_type=cmd.video_type,
                duration=cmd.duration,
                project_name=project_name,
                hook_effect=cmd.hook_effect,
            )

            return {
                "status": "success",
                "project_name": project_name,
                "draft_path": result.get("draft_path", ""),
                "duration": result.get("total_duration", cmd.duration),
                "segments": result.get("segment_count", 0),
                "parsed": asdict(cmd),
            }

        except Exception as e:
            import traceback
            return {
                "status": "failed",
                "error": str(e),
                "traceback": traceback.format_exc(),
                "parsed": asdict(cmd),
            }

    def parse_and_generate(self, text: str, project_name: str = None,
                            auto_confirm: bool = False) -> Dict[str, Any]:
        """
        解析并生成（一键式）

        Args:
            text: 自然语言指令
            project_name: 工程名
            auto_confirm: 是否自动确认

        Returns:
            生成结果
        """
        cmd = self.parse(text)
        return self.generate(cmd, project_name=project_name, auto_confirm=auto_confirm)

    def _get_help_text(self) -> str:
        """获取帮助文本"""
        return """
🤖 AI视频编辑器 - 自然语言指令帮助

支持的指令格式：
  "做一个30秒的探店美食视频，主题是淮南牛肉汤"
  "帮我生成一个vlog，记录今天的日常，时长45秒"
  "做一个产品测评视频，测评最新的相机"
  "生成一个情感故事短片，关于友情，1分钟"
  "做一个口播知识视频，讲AI视频剪辑"

视频类型：探店美食 / Vlog日常 / 教程演示 / 产品测评 / 情感故事 / 电商带货 / 口播知识 / 宣传片

时长支持：秒(s) / 分钟(min)，例如：30秒 / 1分钟 / 90s

风格：电影感 / 温暖 / 科技 / 复古 / 简约
"""


if __name__ == "__main__":
    print("=" * 60)
    print("🗣️ 自然语言指令引擎 v1.0")
    print("=" * 60)

    nle = NaturalLanguageEngine()

    # 测试用例
    test_cases = [
        "做一个30秒的探店美食视频，主题是淮南牛肉汤",
        "帮我生成一个vlog，记录今天的日常，时长45秒",
        "做一个产品测评视频，测评最新的相机，风格要专业",
        "生成一个情感故事短片，关于友情，1分钟",
        "做一个口播知识视频，讲AI视频剪辑，30秒",
    ]

    for i, text in enumerate(test_cases, 1):
        print(f"\n{'─'*60}")
        print(f"测试 {i}: {text}")
        print(f"{'─'*60}")
        cmd = nle.parse(text)
        print(nle.format_parsed(cmd))

    print(f"\n{'='*60}")
    print("✅ 自然语言指令引擎测试完成")
    print(f"{'='*60}")
