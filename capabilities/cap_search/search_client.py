"""
AnySearch 搜索客户端
统一封装网页搜索、批量搜索、页面提取
API Key从config读取，不硬编码
支持用量追踪、预警和自动降级（日限额耗尽时is_available返回False）
"""
import requests
import json
import os
import datetime
from typing import List, Dict, Optional
import sys
# 确保skill根目录在path中
_skill_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _skill_root not in sys.path:
    sys.path.insert(0, _skill_root)
from core.config import config


class AnySearchClient:
    """AnySearch API客户端（含用量追踪与预警）"""

    def __init__(self, api_key: str = None, endpoint: str = None):
        self.api_key = api_key or config.anysearch_api_key
        self.endpoint = endpoint or config.anysearch_endpoint
        self.daily_limit = config.anysearch_daily_limit
        self.warning_ratio = config.anysearch_warning_ratio
        self.session = requests.Session()
        if self.api_key:
            self.session.headers.update({
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            })
        # 用量追踪文件
        self._usage_file = os.path.join(_skill_root, ".cache", "anysearch_usage.json")
        self._usage = self._load_usage()

    def _load_usage(self) -> Dict:
        """加载今日用量记录"""
        today = datetime.date.today().isoformat()
        try:
            if os.path.exists(self._usage_file):
                with open(self._usage_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # 日期变化则重置
                if data.get("date") != today:
                    data = {"date": today, "count": 0, "last_warning": ""}
                return data
        except Exception:
            pass
        return {"date": today, "count": 0, "last_warning": ""}

    def _save_usage(self):
        """保存用量记录"""
        try:
            os.makedirs(os.path.dirname(self._usage_file), exist_ok=True)
            with open(self._usage_file, "w", encoding="utf-8") as f:
                json.dump(self._usage, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _increment_usage(self) -> bool:
        """递增用量计数，返回是否允许继续调用"""
        today = datetime.date.today().isoformat()
        if self._usage.get("date") != today:
            self._usage = {"date": today, "count": 0, "last_warning": ""}

        self._usage["count"] = self._usage.get("count", 0) + 1
        count = self._usage["count"]

        # 预警检查（每天只警告一次）
        warning_threshold = int(self.daily_limit * self.warning_ratio)
        if count >= warning_threshold and self._usage.get("last_warning") != today:
            remaining = self.daily_limit - count
            print(f"⚠️  AnySearch用量预警: 今日已调用 {count}/{self.daily_limit} 次，剩余 {remaining} 次")
            self._usage["last_warning"] = today

        # 限额耗尽检查
        if count >= self.daily_limit:
            print(f"🚫 AnySearch今日配额已耗尽 ({count}/{self.daily_limit})，自动降级为本地模板")
            self._save_usage()
            return False

        self._save_usage()
        return True

    @property
    def usage_info(self) -> Dict:
        """查询当前用量信息"""
        today = datetime.date.today().isoformat()
        if self._usage.get("date") != today:
            return {"date": today, "count": 0, "limit": self.daily_limit, "remaining": self.daily_limit}
        count = self._usage.get("count", 0)
        return {
            "date": today,
            "count": count,
            "limit": self.daily_limit,
            "remaining": max(0, self.daily_limit - count),
            "warning_threshold": int(self.daily_limit * self.warning_ratio),
        }

    @property
    def is_available(self) -> bool:
        """API可用且今日配额未耗尽"""
        if not self.api_key:
            return False
        today = datetime.date.today().isoformat()
        if self._usage.get("date") != today:
            return True
        return self._usage.get("count", 0) < self.daily_limit

    def search(self, query: str, max_results: int = 5, timeout: int = 30,
               tag: str = None, zone: str = None, language: str = None,
               params: Dict = None, format: str = "json") -> List[Dict]:
        """
        统一搜索接口（支持垂类搜索）

        Args:
            query: 搜索关键词
            max_results: 最大结果数（1-10，默认5）
            timeout: 超时秒数
            tag: 垂类标签，格式 {domain}.{sub_domain}，如 "code.doc"、"general.general"
                 不传则自动意图路由；传了则强制路由到指定垂类
            zone: 地区，"cn" 或 "intl"
            language: 偏好语言，如 "zh-CN" 或 "en"
            params: 垂类扩展参数，如 {"library": "golang"}、{"ticker": "AAPL"}
            format: 输出格式，"json" 或 "markdown"（markdown时content字段为结构化Markdown）

        Returns:
            结果列表，每项包含title, url, snippet, content
        """
        if not self.is_available:
            return []
        if not self._increment_usage():
            return []

        try:
            payload = {"query": query, "max_results": max_results}
            if tag:
                payload["tag"] = tag
            if zone:
                payload["zone"] = zone
            if language:
                payload["language"] = language
            if params:
                payload["params"] = params
            if format:
                payload["format"] = format
            r = self.session.post(
                f"{self.endpoint}/v1/search",
                json=payload,
                timeout=timeout
            )
            data = r.json()
            if data.get("code") == 0:
                return data.get("data", {}).get("results", [])
            # API返回配额错误
            if "quota" in str(data.get("message", "")).lower() or data.get("code") in (429, 1001):
                print(f"🚫 AnySearch API返回配额错误，标记今日配额耗尽")
                self._usage["count"] = self.daily_limit
                self._save_usage()
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
            if not self.is_available:
                break
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
        if not self._increment_usage():
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
            if r.get("url") and self.is_available:
                r["full_content"] = self.extract(r["url"], timeout)
        return results

    def get_sub_domains(self, domains: List[str] = None, timeout: int = 15) -> Dict:
        """
        查询可用的垂类子域定义（不消耗搜索额度！）

        Args:
            domains: 要查询的domain列表，如 ["code", "finance"]。None则查询常用domain
            timeout: 超时秒数

        Returns:
            {domain: {description, sub_domains: [{sub_domain, description, params}]}}
        """
        if not self.api_key:
            return {}
        if domains is None:
            domains = ["general", "code", "academic", "business", "finance",
                       "tech", "entertainment", "music", "game", "movie"]

        result = {}
        for domain in domains:
            try:
                r = self.session.get(
                    f"{self.endpoint}/v1/sub-domains",
                    params={"domain": domain},
                    timeout=timeout
                )
                if r.status_code == 200:
                    data = r.json()
                    for d in data.get("data", {}).get("domains", []):
                        result[d["domain"]] = {
                            "description": d.get("description", ""),
                            "sub_domains": d.get("sub_domains", [])
                        }
            except Exception:
                pass
        return result

    def vertical_search(self, tag: str, query: str, max_results: int = 5,
                        params: Dict = None, timeout: int = 30,
                        language: str = "zh-CN", zone: str = None) -> List[Dict]:
        """
        垂类搜索快捷方法（强制路由到指定垂类，获得更精准的结果）

        Args:
            tag: 垂类标签，如 "code.doc"、"academic.search"、"general.general"
            query: 搜索关键词
            max_results: 最大结果数
            params: 垂类扩展参数
            timeout: 超时秒数
            language: 偏好语言
            zone: 地区，"cn" 或 "intl"

        Returns:
            结果列表
        """
        return self.search(query, max_results=max_results, timeout=timeout,
                           tag=tag, params=params, language=language, zone=zone)

    # ── 常用垂类快捷方法 ──

    def search_code(self, query: str, library: str = None, lang: str = None,
                    max_results: int = 5) -> List[Dict]:
        """代码/文档搜索（code.doc 或 code.snippet）"""
        params = {}
        if library:
            params["library"] = library
        tag = "code.doc" if library else "code.snippet"
        if lang and tag == "code.snippet":
            params["lang"] = lang
        return self.vertical_search(tag, query, max_results, params=params)

    def search_academic(self, query: str, max_results: int = 5,
                        open_access: bool = False) -> List[Dict]:
        """学术论文搜索（academic.search）"""
        params = {}
        if open_access:
            params["open_access"] = "true"
        return self.vertical_search("academic.search", query, max_results, params=params)

    def search_hot_topics(self, query: str, max_results: int = 5) -> List[Dict]:
        """热点/通用搜索（general.general，中文优先）"""
        return self.vertical_search("general.general", query, max_results,
                                    language="zh-CN", zone="cn")


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


def get_usage_info() -> Dict:
    """查询AnySearch当前用量信息"""
    return get_client().usage_info
