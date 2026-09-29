"""
创意引擎 - 理解用户诉求，生成创意方向和分镜脚本（AnySearch垂类搜索深度增强版）

流程：
1. 解析用户诉求（主题、风格、目的、平台）
2. 创意研究（AnySearch垂类搜索：热点/BGM/分镜/片头/转场趋势）
3. 生成创意方向建议（2-3个方向，融入热点趋势）
4. 生成分镜脚本（融入分镜技巧和片头设计）
5. 输出改进建议（融入行业最佳实践）
"""

import os
import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from .templates import get_template, list_themes
from .storyboard import StoryboardGenerator, Storyboard
from .hot_trends import HotTrendsSearcher


@dataclass
class CreativeDirection:
    """创意方向"""
    name: str
    description: str
    theme: str
    hook: str
    rhythm: str
    key_visual: str
    target_audience: str
    emotional_arc: str
    bgm_recommendation: str = ""
    transition_style: str = ""
    intro_style: str = ""
    pros: List[str] = field(default_factory=list)
    cons: List[str] = field(default_factory=list)


@dataclass
class CreativeResearch:
    """创意研究结果（来自AnySearch垂类搜索）"""
    hot_topics: List[Dict] = field(default_factory=list)
    bgm_names: List[Dict] = field(default_factory=list)
    copywriting_refs: List[Dict] = field(default_factory=list)
    storyboard_tips: List[str] = field(default_factory=list)
    intro_tips: List[str] = field(default_factory=list)
    transition_names: List[str] = field(default_factory=list)
    has_search: bool = False


class CreativeEngine:
    """创意引擎（AnySearch垂类搜索深度增强版）"""

    def __init__(self, anysearch_api_key: Optional[str] = None):
        self.trends = HotTrendsSearcher(api_key=anysearch_api_key)

    def analyze_requirement(self, user_input: str) -> Dict[str, Any]:
        """解析用户诉求"""
        theme_keywords = {
            "赛博朋克": ["赛博", "朋克", "未来", "科技", "霓虹", "机械", "cyber"],
            "国风": ["国风", "古风", "中国风", "传统", "东方", "汉服", "古典"],
            "治愈": ["治愈", "温暖", "小确幸", "生活", "日常", "美好"],
            "卡点": ["卡点", "踩点", "节奏", "快剪", "混剪"],
            "电影感": ["电影", "cinematic", "大片", "质感", "光影"],
            "极简": ["极简", "简约", "干净", "留白"],
            "复古": ["复古", "怀旧", "胶片", "年代", "老照片"],
            "城市": ["城市", "都市", "街景", "夜景", "霓虹", "街道"],
            "自然": ["自然", "风景", "山水", "户外", "旅行", "风光"],
        }

        detected_theme = "极简"
        keywords = []
        for theme, kws in theme_keywords.items():
            for kw in kws:
                if kw.lower() in user_input.lower():
                    detected_theme = theme
                    keywords.append(kw)
                    break

        platform = "抖音"
        if "小红书" in user_input:
            platform = "小红书"
        elif "b站" in user_input.lower() or "bilibili" in user_input.lower():
            platform = "B站"
        elif "视频号" in user_input:
            platform = "视频号"

        purpose = "分享"
        if "带货" in user_input or "卖货" in user_input or "推广" in user_input:
            purpose = "带货"
        elif "教程" in user_input or "教学" in user_input:
            purpose = "教程"
        elif "宣传" in user_input or "品牌" in user_input:
            purpose = "品牌宣传"

        return {
            "theme": detected_theme,
            "style": detected_theme,
            "purpose": purpose,
            "platform": platform,
            "duration_hint": "15-30秒" if platform == "抖音" else "30-60秒",
            "keywords": keywords,
            "raw_input": user_input,
        }

    def do_creative_research(self, theme: str) -> CreativeResearch:
        """
        执行创意研究（AnySearch垂类搜索）
        搜索：热点话题、BGM推荐、爆款文案、分镜技巧、片头风格、转场趋势
        """
        research = CreativeResearch()
        if not self.trends.available:
            return research

        try:
            data = self.trends.creative_research(theme)
            research.hot_topics = data.get("hot_topics", [])
            research.bgm_names = data.get("bgm_names", [])
            research.copywriting_refs = data.get("copywriting_refs", [])
            research.storyboard_tips = data.get("storyboard_tips", [])
            research.intro_tips = data.get("intro_tips", [])
            research.transition_names = data.get("transition_names", [])
            research.has_search = True
            print(f"  创意研究: 热点{len(research.hot_topics)} BGM{len(research.bgm_names)} "
                  f"分镜技巧{len(research.storyboard_tips)} 片头技巧{len(research.intro_tips)} "
                  f"转场{len(research.transition_names)}")
        except Exception as e:
            print(f"  创意研究失败: {e}")

        return research

    def generate_directions(self, user_input: str, count: int = 3,
                            research: Optional[CreativeResearch] = None) -> List[CreativeDirection]:
        """
        生成创意方向建议（融入热点趋势）

        Args:
            user_input: 用户诉求
            count: 生成方向数量
            research: 创意研究结果（None则自动执行）
        """
        req = self.analyze_requirement(user_input)
        theme = req["theme"]
        template = get_template(theme)

        # 自动执行创意研究
        if research is None and self.trends.available:
            research = self.do_creative_research(theme)

        # 从研究结果提取推荐
        bgm_hint = ""
        transition_hint = ""
        intro_hint = ""
        if research and research.has_search:
            if research.bgm_names:
                bgm_hint = research.bgm_names[0].get("name", "")
            if research.transition_names:
                transition_hint = research.transition_names[0]
            if research.intro_tips:
                intro_hint = research.intro_tips[0][:20]

        directions = []

        # 方向1：经典模板方向
        d1 = CreativeDirection(
            name=f"{theme}经典版",
            description=f"采用{theme}主题的经典视觉语言，稳扎稳打，适合大多数场景。",
            theme=theme,
            hook=template.get("hook_templates", ["视觉盛宴"])[0],
            rhythm=template.get("rhythm", "舒缓"),
            key_visual=template.get("color_grade", "标准调色"),
            target_audience="泛人群",
            emotional_arc="平稳叙事，首尾呼应",
            bgm_recommendation=bgm_hint or f"{theme}风格纯音乐",
            transition_style=transition_hint or "叠化",
            intro_style=intro_hint or "视觉冲击开场",
            pros=["风格成熟稳定", "受众广泛", "制作风险低"],
            cons=["创新性一般", "可能缺乏记忆点"],
        )
        directions.append(d1)

        # 方向2：快节奏强化版
        d2 = CreativeDirection(
            name=f"{theme}节奏版",
            description=f"强化节奏感和视觉冲击，适合抖音等快消平台，更容易获得高完播率。",
            theme=theme,
            hook=template.get("hook_templates", ["视觉盛宴"])[1] if len(template.get("hook_templates", [])) > 1 else "节奏控｜视觉盛宴",
            rhythm="快切",
            key_visual=f"高对比+{template.get('color_grade', '鲜艳')}",
            target_audience="年轻群体",
            emotional_arc="快节奏推进，高潮迭起",
            bgm_recommendation=bgm_hint or f"{theme}节奏卡点BGM",
            transition_style=transition_hint or "闪黑/缩放",
            intro_style="快切混剪开场",
            pros=["完播率高", "视觉冲击力强", "适合算法推荐"],
            cons=["制作要求高", "可能过于喧闹"],
        )
        directions.append(d2)

        # 方向3：情绪叙事版
        d3 = CreativeDirection(
            name=f"{theme}叙事版",
            description=f"注重情绪铺垫和故事感，用镜头语言讲述一个完整的情绪弧线。",
            theme=theme,
            hook=template.get("hook_templates", ["视觉盛宴"])[2] if len(template.get("hook_templates", [])) > 2 else "光影叙事｜电影质感",
            rhythm="递进",
            key_visual=f"电影级调色+{template.get('color_grade', '柔光')}",
            target_audience="追求品质的用户",
            emotional_arc="从平静到高潮，余韵悠长",
            bgm_recommendation=bgm_hint or f"{theme}氛围纯音乐",
            transition_style="叠化/淡入淡出",
            intro_style=intro_hint or "悬念式开场",
            pros=["高级感强", "有故事性", "容易引发共鸣"],
            cons=["节奏较慢", "对素材质量要求高"],
        )
        directions.append(d3)

        return directions[:count]

    def generate_storyboard(self,
                            user_input: str = "",
                            theme: str = "",
                            num_shots: int = 6,
                            title: str = "",
                            hook: str = "",
                            custom_subtitles: Optional[List[str]] = None,
                            use_hot_trends: bool = True,
                            research: Optional[CreativeResearch] = None,
                            ) -> Storyboard:
        """
        生成分镜脚本（融入分镜技巧和片头设计）

        Args:
            user_input: 用户诉求
            theme: 主题
            num_shots: 镜头数量
            title: 视频标题
            hook: 开篇钩子
            custom_subtitles: 自定义字幕
            use_hot_trends: 是否使用热点搜索
            research: 创意研究结果（None则自动执行）
        """
        # 确定主题
        if not theme and user_input:
            req = self.analyze_requirement(user_input)
            theme = req["theme"]
        elif not theme:
            theme = "极简"

        # 执行创意研究
        if research is None and use_hot_trends and self.trends.available:
            research = self.do_creative_research(theme)

        # 热点搜索增强
        if use_hot_trends and self.trends.available:
            # 1. 生成钩子文案
            if not hook:
                hooks = self.trends.generate_hook_suggestions(theme, count=1)
                if hooks:
                    hook = hooks[0]

            # 2. 搜索爆款文案，提炼网感字幕
            if custom_subtitles is None:
                search_subtitles = self._extract_subtitles_from_search(theme, num_shots)
                if search_subtitles:
                    custom_subtitles = search_subtitles
                    print(f"  创意字幕: 从搜索结果提炼 {len(custom_subtitles)} 个网感字幕")

        # 生成分镜
        generator = StoryboardGenerator(theme=theme)
        storyboard = generator.generate(
            num_shots=num_shots,
            title=title,
            hook=hook,
            custom_subtitles=custom_subtitles,
        )

        # 融入分镜技巧（如果有研究结果）
        if research and research.has_search and research.storyboard_tips:
            extra = "\n\n【搜索参考】分镜技巧:\n"
            for tip in research.storyboard_tips[:3]:
                extra += f"  - {tip}\n"
            storyboard.creative_notes = (storyboard.creative_notes or "") + extra

        # 融入片头技巧
        if research and research.has_search and research.intro_tips:
            extra = "\n【搜索参考】片头设计:\n"
            for tip in research.intro_tips[:2]:
                extra += f"  - {tip}\n"
            storyboard.creative_notes = (storyboard.creative_notes or "") + extra

        # 融入BGM推荐
        if research and research.has_search and research.bgm_names:
            extra = "\n【搜索参考】BGM推荐:\n"
            for bgm in research.bgm_names[:3]:
                extra += f"  - {bgm.get('name', '')}（{bgm.get('style', '')}）\n"
            storyboard.creative_notes = (storyboard.creative_notes or "") + extra

        return storyboard

    def _extract_subtitles_from_search(self, theme: str, count: int) -> List[str]:
        """从AnySearch搜索结果中提炼网感字幕"""
        try:
            results = self.trends.search_copywriting(theme, max_results=5)
            if not results:
                return []

            raw_phrases = []
            for r in results:
                title = r.get("title", "")
                if title:
                    raw_phrases.append(title)
                snippet = r.get("snippet", "")
                if snippet:
                    sentences = re.split(r'[。！？；\n\r]', snippet)
                    raw_phrases.extend(sentences)

            cleaned = []
            seen = set()
            for p in raw_phrases:
                p = p.strip()
                if (4 <= len(p) <= 20 and
                    not re.search(r'http|www|\.com|\.cn|点击|关注|点赞|收藏|转发', p) and
                    p not in seen):
                    seen.add(p)
                    cleaned.append(p)

            if len(cleaned) < count:
                creative_phrases = [
                    f"{theme}｜视觉盛宴",
                    f"{theme}｜帧帧如画",
                    f"{theme}｜光影叙事",
                    f"{theme}｜美好瞬间",
                    f"{theme}｜极致体验",
                    f"{theme}｜沉浸式",
                ]
                for p in creative_phrases:
                    if p not in seen:
                        cleaned.append(p)
                        seen.add(p)
                    if len(cleaned) >= count:
                        break

            return cleaned[:count]
        except Exception as e:
            print(f"  搜索字幕提炼失败: {e}")
            return []

    def get_improvement_suggestions(self, storyboard: Storyboard,
                                    research: Optional[CreativeResearch] = None) -> List[str]:
        """
        基于分镜脚本给出改进建议（融入行业最佳实践）

        Args:
            storyboard: 已生成的分镜脚本
            research: 创意研究结果
        """
        suggestions = []

        # 基础检查
        if storyboard.rhythm == "快切" and storyboard.total_duration > 30:
            suggestions.append("快切节奏建议控制在15-20秒以内，过长容易疲劳。")

        shot_types = [s.shot_type for s in storyboard.shots]
        if len(set(shot_types)) < 3:
            suggestions.append("景别变化较少，建议增加特写/全景的对比，增强视觉层次。")

        camera_moves = [s.camera_move for s in storyboard.shots]
        if len(set(camera_moves)) < 2:
            suggestions.append("运镜方式单一，建议混合使用推拉摇移，避免单调。")

        subtitles = [s.subtitle for s in storyboard.shots if s.subtitle]
        if not subtitles:
            suggestions.append("建议添加字幕，尤其是开篇钩子和关键信息点。")

        transitions = [s.transition_out for s in storyboard.shots if s.transition_out != "none"]
        if len(set(transitions)) == 1 and len(transitions) > 3:
            suggestions.append("转场类型单一，建议在关键节点使用不同转场增强节奏感。")

        # 融入搜索到的行业最佳实践
        if research and research.has_search:
            if research.storyboard_tips:
                suggestions.append("【行业参考】" + research.storyboard_tips[0])
            if research.intro_tips:
                suggestions.append("【片头参考】" + research.intro_tips[0])
            if research.transition_names:
                suggestions.append(f"【流行转场】可尝试: {'、'.join(research.transition_names[:3])}")

        # 通用建议
        suggestions.append("开篇3秒是黄金时间，确保第一个镜头最有冲击力。")
        suggestions.append("结尾建议留有余韵，避免戛然而止。")

        return suggestions

    def full_pipeline(self, user_input: str, num_shots: int = 6,
                      output_dir: str = "", use_research: bool = True) -> Dict[str, Any]:
        """
        完整创意流程：分析→研究→方向→分镜→建议

        Args:
            user_input: 用户诉求
            num_shots: 镜头数量
            output_dir: 输出目录
            use_research: 是否执行AnySearch创意研究
        """
        # 1. 分析诉求
        requirement = self.analyze_requirement(user_input)
        theme = requirement["theme"]

        # 2. 创意研究（AnySearch垂类搜索）
        research = CreativeResearch()
        if use_research and self.trends.available:
            research = self.do_creative_research(theme)

        # 3. 生成创意方向
        directions = self.generate_directions(user_input, count=3, research=research)

        # 4. 使用第一个方向生成分镜
        selected = directions[0]
        storyboard = self.generate_storyboard(
            user_input=user_input,
            theme=selected.theme,
            num_shots=num_shots,
            hook=selected.hook,
            research=research,
        )

        # 5. 改进建议
        suggestions = self.get_improvement_suggestions(storyboard, research=research)

        # 6. 保存文件
        files = {}
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            json_path = os.path.join(output_dir, "storyboard.json")
            md_path = os.path.join(output_dir, "storyboard.md")
            storyboard.save(json_path, fmt="json")
            storyboard.save(md_path, fmt="md")
            files = {"json": json_path, "markdown": md_path}

        return {
            "requirement": requirement,
            "research": research,
            "directions": directions,
            "storyboard": storyboard,
            "suggestions": suggestions,
            "files": files,
        }
