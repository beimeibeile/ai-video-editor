"""
cap_search — 网络搜索能力模块
基于AnySearch API，支持通用搜索、批量搜索、页面提取
依赖：anysearch环境（API Key配置）
"""
from .search_client import AnySearchClient, get_client, search, extract

__all__ = ["AnySearchClient", "get_client", "search", "extract"]
