"""
AnySearch 灵感搜索集成 v1.0

在剧本改写前/中使用AnySearch搜索：
1. 同类剧本/短剧参考
2. 热门梗/流行语/网络热点
3. 角色设定参考
4. 场景/道具参考
5. film垂直域搜索（电影/剧集参考）

集成到script_rewriter中，作为改写前的灵感获取步骤。
"""

import os
import sys
import json
import re
import subprocess
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict


@dataclass
class SearchResult:
    """单条搜索结果"""
    title: str
    url: str
    snippet: str
    source: str = ""
    relevance: float = 0.0


@dataclass
class InspirationReport:
    """灵感搜索报告"""
    query: str
    similar_scripts: List[SearchResult] = field(default_factory=list)
    trending_topics: List[SearchResult] = field(default_factory=list)
    character_refs: List[SearchResult] = field(default_factory=list)
    scene_refs: List[SearchResult] = field(default_factory=list)
    film_refs: List[SearchResult] = field(default_factory=list)
    raw_results: Dict[str, Any] = field(default_factory=dict)
    search_time: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "query": self.query,
            "similar_scripts": [asdict(r) for r in self.similar_scripts],
            "trending_topics": [asdict(r) for r in self.trending_topics],
            "character_refs": [asdict(r) for r in self.character_refs],
            "scene_refs": [asdict(r) for r in self.scene_refs],
            "film_refs": [asdict(r) for r in self.film_refs],
            "search_time": self.search_time,
        }


class AnySearchInspiration:
    """
    AnySearch灵感搜索器

    使用方式：
        searcher = AnySearchInspiration()
        report = searcher.get_inspiration("程序员加班代码活了", style="suspense")
        print(report.trending_topics)
    """

    def __init__(self, cli_path: str = None, python_path: str = None):
        """
        初始化

        Args:
            cli_path: anysearch_cli.py路径（None则自动探测）
            python_path: Python路径（None则用默认python）
        """
        if cli_path is None:
            # 自动探测
            candidates = [
                r"C:\Users\Administrator\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills\anysearch-skill\scripts\anysearch_cli.py",
                r"C:\Users\Administrator\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills\anysearch\scripts\anysearch_cli.py",
            ]
            for p in candidates:
                if os.path.exists(p):
                    cli_path = p
                    break

        self.cli_path = cli_path
        self.python_path = python_path or "python"
        self.available = cli_path is not None and os.path.exists(cli_path)

        if self.available:
            print(f"  🔍 AnySearch可用: {os.path.basename(cli_path)}")
        else:
            print(f"  ⚠️  AnySearch不可用，灵感搜索将跳过")

    def _run_search(self, query: str, max_results: int = 5, domain: str = None) -> List[SearchResult]:
        """
        执行单次搜索

        Args:
            query: 搜索关键词
            max_results: 最大结果数
            domain: 垂直域（None则通用搜索）

        Returns:
            搜索结果列表
        """
        if not self.available:
            return []

        try:
            cmd = [self.python_path, self.cli_path, "search", query, "--max_results", str(max_results)]
            if domain:
                cmd.extend(["--domain", domain])

            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                timeout=30,
                encoding="utf-8",
                errors="replace",
            )

            output = result.stdout.strip()
            if not output:
                return []

            return self._parse_search_output(output)

        except subprocess.TimeoutExpired:
            print(f"  ⚠️  搜索超时: {query}")
            return []
        except Exception as e:
            print(f"  ⚠️  搜索异常: {e}")
            return []

    def _parse_search_output(self, output: str) -> List[SearchResult]:
        """解析搜索输出（支持Markdown和JSON格式）"""
        results = []

        # 尝试JSON解析
        try:
            data = json.loads(output)
            if isinstance(data, dict):
                items = data.get("results", data.get("items", []))
            elif isinstance(data, list):
                items = data
            else:
                items = []

            for item in items:
                if isinstance(item, dict):
                    results.append(SearchResult(
                        title=item.get("title", ""),
                        url=item.get("url", item.get("link", "")),
                        snippet=item.get("snippet", item.get("description", "")),
                        source=item.get("source", ""),
                    ))
            if results:
                return results
        except (json.JSONDecodeError, ValueError):
            pass

        # Markdown格式解析（AnySearch CLI默认输出）
        # 格式: ### 1. 标题\n- **URL**: ...\n- 摘要
        lines = output.split('\n')
        current = None
        for line in lines:
            line = line.strip()
            # 结果标题行: ### 1. 标题
            if line.startswith('###'):
                if current:
                    results.append(current)
                # 提取标题（去掉序号前缀）
                title = line.lstrip('#').strip()
                # 去掉 "1. " 前缀
                import re
                title = re.sub(r'^\d+\.\s*', '', title)
                current = SearchResult(title=title, url="", snippet="")
            # URL行: - **URL**: https://...
            elif current and '**URL**' in line:
                url_match = re.search(r'https?://[^\s]+', line)
                if url_match:
                    current.url = url_match.group(0)
            # 摘要行（非空、非标题、非URL行）
            elif current and line and not line.startswith('#') and not line.startswith('##'):
                if not line.startswith('- **URL**'):
                    # 去掉前缀 "- "
                    snippet = line.lstrip('- ').strip()
                    if snippet and not snippet.startswith('**'):
                        if current.snippet:
                            current.snippet += " " + snippet
                        else:
                            current.snippet = snippet

        if current:
            results.append(current)

        return results[:5]

    def search_similar_scripts(self, theme: str, style: str = "") -> List[SearchResult]:
        """搜索同类剧本/短剧参考"""
        query = f"{theme} 短剧 剧本 剧情"
        if style:
            query += f" {style}"
        return self._run_search(query, max_results=3)

    def search_trending(self, theme: str = "") -> List[SearchResult]:
        """搜索热门梗/流行语/网络热点"""
        query = f"{theme} 热门梗 流行语 网络热点 2026" if theme else "2026 网络热梗 流行语 短视频热点"
        return self._run_search(query, max_results=3)

    def search_character_ref(self, character_desc: str) -> List[SearchResult]:
        """搜索角色设定参考"""
        query = f"{character_desc} 角色设定 人物形象 短剧"
        return self._run_search(query, max_results=3)

    def search_scene_ref(self, scene_desc: str) -> List[SearchResult]:
        """搜索场景/道具参考"""
        query = f"{scene_desc} 场景设计 道具 短剧拍摄"
        return self._run_search(query, max_results=3)

    def search_film_ref(self, theme: str) -> List[SearchResult]:
        """搜索电影/剧集参考（film垂直域）"""
        query = f"{theme} 电影 剧集 类似题材"
        return self._run_search(query, max_results=3, domain="film")

    def get_inspiration(
        self,
        theme: str,
        style: str = "",
        character_desc: str = "",
        scene_desc: str = "",
        include_trending: bool = True,
        include_film: bool = True,
    ) -> InspirationReport:
        """
        获取完整灵感报告

        Args:
            theme: 主题/创意
            style: 风格
            character_desc: 角色描述
            scene_desc: 场景描述
            include_trending: 是否搜索热门梗
            include_film: 是否搜索电影参考

        Returns:
            InspirationReport
        """
        import time
        start = time.time()

        report = InspirationReport(query=theme)

        print(f"\n{'='*60}")
        print(f"🔍 AnySearch灵感搜索: {theme}")
        print(f"{'='*60}")

        # 同类剧本
        print(f"\n[1/5] 搜索同类剧本参考...")
        report.similar_scripts = self.search_similar_scripts(theme, style)
        print(f"  找到 {len(report.similar_scripts)} 条")

        # 热门梗
        if include_trending:
            print(f"[2/5] 搜索热门梗/流行语...")
            report.trending_topics = self.search_trending(theme)
            print(f"  找到 {len(report.trending_topics)} 条")

        # 角色参考
        if character_desc:
            print(f"[3/5] 搜索角色设定参考...")
            report.character_refs = self.search_character_ref(character_desc)
            print(f"  找到 {len(report.character_refs)} 条")

        # 场景参考
        if scene_desc:
            print(f"[4/5] 搜索场景/道具参考...")
            report.scene_refs = self.search_scene_ref(scene_desc)
            print(f"  找到 {len(report.scene_refs)} 条")

        # 电影参考
        if include_film:
            print(f"[5/5] 搜索电影/剧集参考...")
            report.film_refs = self.search_film_ref(theme)
            print(f"  找到 {len(report.film_refs)} 条")

        report.search_time = time.time() - start

        total = (len(report.similar_scripts) + len(report.trending_topics) +
                 len(report.character_refs) + len(report.scene_refs) +
                 len(report.film_refs))
        print(f"\n✅ 灵感搜索完成: 共{total}条参考, 耗时{report.search_time:.1f}s")
        print(f"{'='*60}\n")

        return report

    def get_inspiration_summary(self, report: InspirationReport) -> str:
        """生成灵感摘要文本（可注入到改写提示词中）"""
        lines = [f"【灵感参考】主题: {report.query}"]

        if report.similar_scripts:
            lines.append("\n同类剧本参考:")
            for r in report.similar_scripts[:2]:
                lines.append(f"  - {r.title}: {r.snippet[:80]}")

        if report.trending_topics:
            lines.append("\n热门梗/流行语:")
            for r in report.trending_topics[:2]:
                lines.append(f"  - {r.title}: {r.snippet[:80]}")

        if report.film_refs:
            lines.append("\n电影/剧集参考:")
            for r in report.film_refs[:2]:
                lines.append(f"  - {r.title}: {r.snippet[:80]}")

        return "\n".join(lines)


if __name__ == "__main__":
    # 测试
    print("="*60)
    print("AnySearch灵感搜索测试")
    print("="*60)

    searcher = AnySearchInspiration()

    if searcher.available:
        report = searcher.get_inspiration(
            theme="程序员加班代码活了",
            style="悬疑",
            character_desc="程序员 深夜 加班",
            scene_desc="办公室 深夜 电脑",
        )

        print("\n灵感摘要:")
        print(searcher.get_inspiration_summary(report))
    else:
        print("AnySearch不可用，跳过测试")
