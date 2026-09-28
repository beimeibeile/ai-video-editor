"""
热点搜索器 - 基于AnySearch的热点/流行元素/BGM推荐搜索

功能：
- 搜索抖音/小红书热门话题
- 搜索流行BGM和音效
- 搜索爆款文案参考
- 搜索风格趋势和配色方案
"""

import os
import sys
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
    """热点搜索器"""

    def __init__(self, api_key: Optional[str] = None):
        self.client = None
        if HAS_ANYSEARCH:
            try:
                self.client = AnySearchClient(api_key=api_key)
            except Exception:
                self.client = None

    @property
    def available(self) -> bool:
        return self.client is not None

    def search_hot_topics(self, theme: str, platform: str = "抖音", max_results: int = 5) -> List[Dict[str, str]]:
        """搜索热门话题"""
        if not self.available:
            return []
        try:
            query = f"{platform} {theme} 热门话题 爆款 2026"
            results = self.client.search(query, max_results=max_results)
            return [{"title": r.get("title", ""), "url": r.get("url", ""), "snippet": r.get("snippet", "")} for r in results]
        except Exception:
            return []

    def search_bgm_recommendations(self, theme: str, max_results: int = 5) -> List[Dict[str, str]]:
        """搜索BGM推荐"""
        if not self.available:
            return []
        try:
            query = f"{theme} 背景音乐 BGM 推荐 短视频"
            results = self.client.search(query, max_results=max_results)
            return [{"title": r.get("title", ""), "url": r.get("url", ""), "snippet": r.get("snippet", "")} for r in results]
        except Exception:
            return []

    def search_copywriting(self, theme: str, max_results: int = 5) -> List[Dict[str, str]]:
        """搜索爆款文案参考"""
        if not self.available:
            return []
        try:
            query = f"{theme} 文案 爆款 钩子 短视频"
            results = self.client.search(query, max_results=max_results)
            return [{"title": r.get("title", ""), "url": r.get("url", ""), "snippet": r.get("snippet", "")} for r in results]
        except Exception:
            return []

    def search_style_trends(self, theme: str, max_results: int = 5) -> List[Dict[str, str]]:
        """搜索风格趋势和配色方案"""
        if not self.available:
            return []
        try:
            query = f"{theme} 视觉风格 配色 趋势 2026"
            results = self.client.search(query, max_results=max_results)
            return [{"title": r.get("title", ""), "url": r.get("url", ""), "snippet": r.get("snippet", "")} for r in results]
        except Exception:
            return []

    def comprehensive_search(self, theme: str) -> Dict[str, List[Dict[str, str]]]:
        """综合搜索：话题+BGM+文案+风格"""
        return {
            "hot_topics": self.search_hot_topics(theme),
            "bgm_recommendations": self.search_bgm_recommendations(theme),
            "copywriting": self.search_copywriting(theme),
            "style_trends": self.search_style_trends(theme),
        }

    def generate_hook_suggestions(self, theme: str, count: int = 3) -> List[str]:
        """基于搜索结果生成钩子文案建议"""
        # 内置钩子模板（不依赖搜索也能工作）
        from .templates import get_template
        template = get_template(theme)
        hooks = template.get("hook_templates", [])

        # 如果有搜索结果，可以基于搜索结果生成更精准的钩子
        if self.available:
            try:
                copywriting = self.search_copywriting(theme, max_results=3)
                for item in copywriting:
                    snippet = item.get("snippet", "")
                    if snippet and len(snippet) > 10:
                        # 从搜索结果中提取短句作为钩子参考
                        sentences = [s.strip() for s in snippet.replace("。", "。|").split("|") if len(s.strip()) > 5 and len(s.strip()) < 30]
                        if sentences:
                            hooks.append(sentences[0])
            except Exception:
                pass

        return hooks[:count] if hooks else [f"{theme}｜视觉盛宴"]
