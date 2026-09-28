"""
AnySearch 搜索客户端
统一封装网页搜索、批量搜索、页面提取
API Key从config读取，不硬编码
"""
import requests
from typing import List, Dict, Optional
import sys, os
# 确保skill根目录在path中
_skill_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _skill_root not in sys.path:
    sys.path.insert(0, _skill_root)
from core.config import config


class AnySearchClient:
    """AnySearch API客户端"""

    def __init__(self, api_key: str = None, endpoint: str = None):
        self.api_key = api_key or config.anysearch_api_key
        self.endpoint = endpoint or config.anysearch_endpoint
        self.session = requests.Session()
        if self.api_key:
            self.session.headers.update({
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            })

    @property
    def is_available(self) -> bool:
        return bool(self.api_key)

    def search(self, query: str, max_results: int = 5, timeout: int = 30) -> List[Dict]:
        """
        通用网页搜索

        Args:
            query: 搜索关键词
            max_results: 最大结果数
            timeout: 超时秒数

        Returns:
            结果列表，每项包含title, url, snippet, content
        """
        if not self.is_available:
            return []

        try:
            r = self.session.post(
                f"{self.endpoint}/v1/search",
                json={"query": query, "max_results": max_results},
                timeout=timeout
            )
            data = r.json()
            if data.get("code") == 0:
                return data.get("data", {}).get("results", [])
        except Exception as e:
            print(f"⚠️  AnySearch搜索失败: {e}")
        return []

    def batch_search(self, queries: List[Dict], timeout: int = 60) -> Dict[str, List[Dict]]:
        """
        批量并行搜索

        Args:
            queries: [{"query": "关键词", "max_results": 5}, ...]

        Returns:
            {query: results} 字典
        """
        if not self.is_available:
            return {}

        results = {}
        for q in queries:
            query = q.get("query", "")
            max_results = q.get("max_results", 5)
            results[query] = self.search(query, max_results, timeout)
        return results

    def extract(self, url: str, timeout: int = 30) -> str:
        """
        提取网页全文内容（Markdown格式）

        Args:
            url: 网页URL

        Returns:
            Markdown格式的页面内容
        """
        if not self.is_available:
            return ""

        try:
            r = self.session.post(
                f"{self.endpoint}/v1/extract",
                json={"url": url},
                timeout=timeout
            )
            data = r.json()
            if data.get("code") == 0:
                return data.get("data", {}).get("content", "")
        except Exception as e:
            print(f"⚠️  AnySearch提取失败: {e}")
        return ""

    def search_and_extract(self, query: str, max_results: int = 3, timeout: int = 60) -> List[Dict]:
        """
        搜索并提取前N个结果的全文

        Returns:
            [{"title": ..., "url": ..., "snippet": ..., "content": ...}, ...]
        """
        results = self.search(query, max_results, timeout)
        for r in results:
            if r.get("url"):
                r["full_content"] = self.extract(r["url"], timeout)
        return results


# 全局单例
_client: Optional[AnySearchClient] = None


def get_client() -> AnySearchClient:
    global _client
    if _client is None:
        _client = AnySearchClient()
    return _client


def search(query: str, max_results: int = 5) -> List[Dict]:
    """快捷搜索函数"""
    return get_client().search(query, max_results)


def extract(url: str) -> str:
    """快捷提取函数"""
    return get_client().extract(url)
