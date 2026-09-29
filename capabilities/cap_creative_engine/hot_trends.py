"""
热点搜索器 - 基于AnySearch垂类搜索的热点/流行元素/BGM推荐搜索

升级：全部搜索使用general.general垂类tag + zone=cn + language=zh-CN
新增：分镜结构参考、片头风格、转场趋势、BGM具体推荐提炼
"""

import os
import sys
import re
from typing import List, Dict, Any, Optional

# 尝试导入AnySearch客户端
try:
    from ...capabilities.cap_search.search_client import AnySearchClient
    HAS_ANYSEARCH = True
except ImportError:
    try:
        from capabilities.cap_search.search_client import AnySearchClient
        HAS_ANYSEARCH = True
    except ImportError:
        HAS_ANYSEARCH = False


class HotTrendsSearcher:
    """热点搜索器（垂类搜索增强版）"""

    def __init__(self, api_key: Optional[str] = None):
        self.client = None
        if HAS_ANYSEARCH:
            try:
                self.client = AnySearchClient(api_key=api_key)
            except Exception:
                self.client = None

    @property
    def available(self) -> bool:
        return self.client is not None and self.client.is_available

    def _vertical_search(self, query: str, max_results: int = 5) -> List[Dict]:
        """统一垂类搜索：general.general + 中文优先"""
        if not self.available:
            return []
        try:
            return self.client.search(
                query, max_results=max_results,
                tag="general.general",
                zone="cn", language="zh-CN"
            )
        except Exception:
            return []

    def search_hot_topics(self, theme: str, platform: str = "抖音", max_results: int = 5) -> List[Dict[str, str]]:
        """搜索热门话题（垂类搜索）"""
        query = f"{platform} {theme} 热门话题 爆款 2026"
        results = self._vertical_search(query, max_results)
        return [{"title": r.get("title", ""), "url": r.get("url", ""), "snippet": r.get("snippet", "")} for r in results]

    def search_bgm_recommendations(self, theme: str, max_results: int = 5) -> List[Dict[str, str]]:
        """搜索BGM推荐（垂类搜索）"""
        query = f"{theme} 背景音乐 BGM 推荐 短视频 抖音热门"
        results = self._vertical_search(query, max_results)
        return [{"title": r.get("title", ""), "url": r.get("url", ""), "snippet": r.get("snippet", "")} for r in results]

    def extract_bgm_names(self, theme: str, max_count: int = 5) -> List[Dict[str, str]]:
        """
        从搜索结果中提炼具体BGM名称和风格
        Returns: [{"name": "曲名", "style": "风格", "mood": "情绪"}]
        """
        results = self.search_bgm_recommendations(theme, max_results=5)
        bgms = []
        seen = set()
        for r in results:
            text = (r.get("title", "") + " " + r.get("snippet", "")).strip()
            # 提取《》中的歌曲名
            songs = re.findall(r'[《【]([^》】]{2,30})[》】]', text)
            for song in songs:
                if song not in seen and not re.search(r'http|www|点击|关注', song):
                    seen.add(song)
                    bgms.append({"name": song, "style": theme, "mood": "推荐", "source": r.get("title", "")[:30]})
            if len(bgms) >= max_count:
                break
        # 如果没提取到，用通用推荐
        if not bgms:
            defaults = [
                {"name": "搜索BGM关键词", "style": theme, "mood": "在剪映音乐库搜索以下关键词", "source": "本地推荐"},
            ]
            return defaults
        return bgms[:max_count]

    def search_copywriting(self, theme: str, max_results: int = 5) -> List[Dict[str, str]]:
        """搜索爆款文案参考（垂类搜索）"""
        query = f"{theme} 文案 爆款 钩子 短视频 抖音"
        results = self._vertical_search(query, max_results)
        return [{"title": r.get("title", ""), "url": r.get("url", ""), "snippet": r.get("snippet", "")} for r in results]

    def search_style_trends(self, theme: str, max_results: int = 5) -> List[Dict[str, str]]:
        """搜索风格趋势和配色方案（垂类搜索）"""
        query = f"{theme} 视觉风格 配色 趋势 短视频 2026"
        results = self._vertical_search(query, max_results)
        return [{"title": r.get("title", ""), "url": r.get("url", ""), "snippet": r.get("snippet", "")} for r in results]

    def search_storyboard_structures(self, theme: str, max_results: int = 5) -> List[Dict[str, str]]:
        """搜索分镜结构和叙事节奏参考"""
        query = f"{theme} 短视频 分镜 脚本 结构 叙事 节奏 教程"
        results = self._vertical_search(query, max_results)
        return [{"title": r.get("title", ""), "url": r.get("url", ""), "snippet": r.get("snippet", "")} for r in results]

    def extract_storyboard_tips(self, theme: str, max_count: int = 5) -> List[str]:
        """从分镜搜索结果中提炼可执行的分镜技巧"""
        results = self.search_storyboard_structures(theme, max_results=5)
        tips = []
        seen = set()
        for r in results:
            snippet = r.get("snippet", "")
            if not snippet:
                continue
            # 按标点分割，提取有价值的短句
            sentences = re.split(r'[。！？；\n\r]', snippet)
            for s in sentences:
                s = s.strip()
                if (8 <= len(s) <= 50 and
                    not re.search(r'http|www|点击|关注|点赞|收藏|转发|私信', s) and
                    s not in seen):
                    # 只保留包含分镜/节奏/镜头相关关键词的句子
                    if re.search(r'镜头|分镜|节奏|转场|运镜|特写|全景|中景|近景|开场|结尾|叙事|结构|剪辑', s):
                        seen.add(s)
                        tips.append(s)
                if len(tips) >= max_count:
                    break
            if len(tips) >= max_count:
                break
        return tips[:max_count]

    def search_intro_styles(self, theme: str, max_results: int = 5) -> List[Dict[str, str]]:
        """搜索片头/开场风格趋势"""
        query = f"{theme} 短视频 片头 开场 钩子 设计 趋势 2026"
        results = self._vertical_search(query, max_results)
        return [{"title": r.get("title", ""), "url": r.get("url", ""), "snippet": r.get("snippet", "")} for r in results]

    def extract_intro_tips(self, theme: str, max_count: int = 3) -> List[str]:
        """从片头搜索结果中提炼片头设计技巧"""
        results = self.search_intro_styles(theme, max_results=5)
        tips = []
        seen = set()
        for r in results:
            snippet = r.get("snippet", "")
            if not snippet:
                continue
            sentences = re.split(r'[。！？；\n\r]', snippet)
            for s in sentences:
                s = s.strip()
                if (8 <= len(s) <= 50 and
                    not re.search(r'http|www|点击|关注|点赞', s) and
                    re.search(r'开场|片头|钩子|前3秒|黄金3秒|入魂|吸引|留住', s) and
                    s not in seen):
                    seen.add(s)
                    tips.append(s)
                if len(tips) >= max_count:
                    break
            if len(tips) >= max_count:
                break
        return tips[:max_count]

    def search_transition_trends(self, theme: str = "", max_results: int = 5) -> List[Dict[str, str]]:
        """搜索转场和特效趋势"""
        query = f"短视频 转场 特效 趋势 流行 剪映 2026 {theme}"
        results = self._vertical_search(query, max_results)
        return [{"title": r.get("title", ""), "url": r.get("url", ""), "snippet": r.get("snippet", "")} for r in results]

    def extract_transition_names(self, max_count: int = 5) -> List[str]:
        """从转场搜索结果中提炼流行转场名称"""
        results = self.search_transition_trends(max_results=5)
        names = []
        seen = set()
        for r in results:
            text = r.get("title", "") + " " + r.get("snippet", "")
            # 提取转场名称
            transitions = re.findall(r'[《【「]([^》】」]{2,15})[》】」]', text)
            for t in transitions:
                if t not in seen and not re.search(r'http|点击|关注', t):
                    seen.add(t)
                    names.append(t)
            if len(names) >= max_count:
                break
        # 补充常用转场
        defaults = ["叠化", "闪黑", "缩放", "滑动", "旋转"]
        for d in defaults:
            if d not in seen:
                names.append(d)
                seen.add(d)
            if len(names) >= max_count:
                break
        return names[:max_count]

    def comprehensive_search(self, theme: str) -> Dict[str, List[Dict[str, str]]]:
        """综合搜索：话题+BGM+文案+风格+分镜+片头+转场"""
        return {
            "hot_topics": self.search_hot_topics(theme),
            "bgm_recommendations": self.search_bgm_recommendations(theme),
            "copywriting": self.search_copywriting(theme),
            "style_trends": self.search_style_trends(theme),
            "storyboard_structures": self.search_storyboard_structures(theme),
            "intro_styles": self.search_intro_styles(theme),
            "transition_trends": self.search_transition_trends(theme),
        }

    def creative_research(self, theme: str) -> Dict[str, Any]:
        """
        创意研究：综合搜索并提炼可执行建议
        Returns: {
            "hot_topics": [...],
            "bgm_names": [{"name", "style", "mood"}],
            "copywriting_refs": [...],
            "storyboard_tips": [...],
            "intro_tips": [...],
            "transition_names": [...],
        }
        """
        return {
            "hot_topics": self.search_hot_topics(theme, max_results=3),
            "bgm_names": self.extract_bgm_names(theme, max_count=3),
            "copywriting_refs": self.search_copywriting(theme, max_results=3),
            "storyboard_tips": self.extract_storyboard_tips(theme, max_count=3),
            "intro_tips": self.extract_intro_tips(theme, max_count=2),
            "transition_names": self.extract_transition_names(max_count=3),
        }

    def generate_hook_suggestions(self, theme: str, count: int = 3) -> List[str]:
        """基于搜索结果生成钩子文案建议"""
        # 内置钩子模板
        from .templates import get_template
        template = get_template(theme)
        hooks = template.get("hook_templates", [])

        # 从搜索结果提炼更精准的钩子
        if self.available:
            try:
                copywriting = self.search_copywriting(theme, max_results=3)
                for item in copywriting:
                    snippet = item.get("snippet", "")
                    if snippet and len(snippet) > 10:
                        sentences = [s.strip() for s in re.split(r'[。！？；\n\r]', snippet)
                                     if 5 < len(s.strip()) < 30
                                     and not re.search(r'http|点击|关注|点赞|收藏', s.strip())]
                        if sentences:
                            hooks.append(sentences[0])
            except Exception:
                pass

        return hooks[:count] if hooks else [f"{theme}｜视觉盛宴"]
