# cap_search — 网络搜索能力模块

## 概述

基于 AnySearch API 的统一搜索能力，支持通用网页搜索、批量并行搜索、页面全文提取。

## 依赖

- **环境**：AnySearch API Key（在 `.env` 中配置 `ANYSEARCH_API_KEY`）
- **Python**：requests 库

## API

```python
from capabilities.cap_search import search, extract, get_client

# 通用搜索
results = search("剪映视频剪辑技巧", max_results=5)
# results: [{"title": ..., "url": ..., "snippet": ..., "content": ...}, ...]

# 页面提取（Markdown格式）
content = extract("https://example.com/article")

# 批量搜索
client = get_client()
results = client.batch_search([
    {"query": "抖音爆款文案", "max_results": 3},
    {"query": "BGM推荐", "max_results": 3},
])
```

## 降级策略

当 AnySearch 不可用时（未配置API Key或网络不通）：
- 搜索功能返回空结果
- 主流程跳过网络搜索环节，使用内置知识和用户提供的信息
- 不影响其他能力模块正常运行

## 配置

在项目根目录 `.env` 文件中配置：
```
ANYSEARCH_API_KEY=as_sk_xxxxxxxxxxxxxxxx
ANYSEARCH_API_ENDPOINT=https://api.anysearch.com
```

## 适用场景

- 视频制作：搜索热点话题、文案素材、BGM推荐
- 仿制模板：搜索原视频相关信息、同类爆款分析
- 素材准备：搜索参考图、风格趋势、配色方案
- 知识沉淀：搜索剪辑技巧、特效教程
