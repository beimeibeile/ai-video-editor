"""
社区模板市场 v1.0 (P4-4)
模板上传/下载/评分+版本管理+搜索分类

核心功能：
1. 模板管理：上传/下载/删除/更新模板
2. 评分系统：用户评分+评论
3. 版本管理：模板版本追踪和回滚
4. 搜索分类：按标签/类型/热度/时间搜索
5. 本地库：本地模板库管理和同步

模板格式：
- JSON格式，包含模板元数据+场景结构+风格参数
- 与cap_template_system兼容

使用方法：
    from template_market import TemplateMarket
    market = TemplateMarket()
    market.upload_template(template_data, author="user1")
    templates = market.search_templates(keyword="探店")
    market.rate_template(template_id, rating=5)
"""
import os
import sys
import json
import hashlib
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class Template:
    """模板"""
    template_id: str
    name: str
    description: str = ""
    author: str = ""
    version: str = "1.0.0"
    category: str = "general"  # exploration/vlog/tutorial/product/emotional/story/ecommerce/talking/general
    tags: List[str] = field(default_factory=list)
    scene_structure: List[Dict[str, Any]] = field(default_factory=list)
    style_params: Dict[str, Any] = field(default_factory=dict)
    duration: float = 30.0
    aspect_ratio: str = "9:16"
    created_at: str = ""
    updated_at: str = ""
    download_count: int = 0
    rating_sum: float = 0.0
    rating_count: int = 0
    rating: float = 0.0
    comments: List[Dict[str, Any]] = field(default_factory=list)
    is_official: bool = False
    is_published: bool = True


@dataclass
class TemplateVersion:
    """模板版本"""
    version: str
    changelog: str = ""
    created_at: str = ""
    template_data: Dict[str, Any] = field(default_factory=dict)


class TemplateMarket:
    """社区模板市场"""

    CATEGORIES = [
        "exploration",  # 探店美食
        "vlog",  # 日常Vlog
        "tutorial",  # 教程演示
        "product",  # 产品测评
        "emotional",  # 剧情情感
        "story",  # 故事叙事
        "ecommerce",  # 电商带货
        "talking",  # 口播知识
        "general",  # 通用
    ]

    def __init__(self, storage_dir: str = None):
        self.storage_dir = storage_dir or os.path.join(
            r"C:\Users\Administrator\Videos\剪映导出\Doubao_Jianying-editor",
            "template_market"
        )
        self.templates_file = os.path.join(self.storage_dir, "templates.json")
        self.versions_dir = os.path.join(self.storage_dir, "versions")
        os.makedirs(self.storage_dir, exist_ok=True)
        os.makedirs(self.versions_dir, exist_ok=True)
        self.templates: Dict[str, Template] = {}
        self._load()

    def _load(self):
        """加载模板库"""
        if os.path.exists(self.templates_file):
            try:
                with open(self.templates_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for tid, tdata in data.items():
                    self.templates[tid] = Template(**tdata)
            except Exception as e:
                print(f"⚠️ 模板库加载失败: {e}")

    def _save(self):
        """保存模板库"""
        data = {tid: asdict(t) for tid, t in self.templates.items()}
        with open(self.templates_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _generate_id(self, name: str, author: str) -> str:
        """生成模板ID"""
        raw = f"{name}_{author}_{datetime.now().isoformat()}"
        return hashlib.md5(raw.encode()).hexdigest()[:12]

    # ==================== 模板上传/下载 ====================

    def upload_template(self, name: str, description: str = "",
                        author: str = "anonymous", category: str = "general",
                        tags: List[str] = None, scene_structure: List[Dict] = None,
                        style_params: Dict = None, duration: float = 30.0,
                        aspect_ratio: str = "9:16", version: str = "1.0.0",
                        is_official: bool = False) -> str:
        """上传模板"""
        template_id = self._generate_id(name, author)
        now = datetime.now().isoformat()

        template = Template(
            template_id=template_id,
            name=name,
            description=description,
            author=author,
            version=version,
            category=category if category in self.CATEGORIES else "general",
            tags=tags or [],
            scene_structure=scene_structure or [],
            style_params=style_params or {},
            duration=duration,
            aspect_ratio=aspect_ratio,
            created_at=now,
            updated_at=now,
            is_official=is_official,
        )

        self.templates[template_id] = template
        self._save_version(template)
        self._save()
        print(f"✅ 模板已上传: {name} (ID: {template_id}, v{version})")
        return template_id

    def download_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """下载模板"""
        if template_id not in self.templates:
            print(f"❌ 模板不存在: {template_id}")
            return None

        template = self.templates[template_id]
        template.download_count += 1
        self._save()

        return {
            "template_id": template.template_id,
            "name": template.name,
            "description": template.description,
            "author": template.author,
            "version": template.version,
            "category": template.category,
            "tags": template.tags,
            "scene_structure": template.scene_structure,
            "style_params": template.style_params,
            "duration": template.duration,
            "aspect_ratio": template.aspect_ratio,
        }

    def delete_template(self, template_id: str, author: str = None) -> bool:
        """删除模板"""
        if template_id not in self.templates:
            return False

        template = self.templates[template_id]
        if author and template.author != author and not template.is_official:
            print(f"❌ 无权限删除模板: {template_id}")
            return False

        del self.templates[template_id]
        self._save()
        print(f"🗑️ 模板已删除: {template_id}")
        return True

    # ==================== 模板更新/版本管理 ====================

    def update_template(self, template_id: str, name: str = None,
                        description: str = None, tags: List[str] = None,
                        scene_structure: List[Dict] = None, style_params: Dict = None,
                        version: str = None, changelog: str = "") -> bool:
        """更新模板"""
        if template_id not in self.templates:
            return False

        template = self.templates[template_id]

        if name:
            template.name = name
        if description:
            template.description = description
        if tags is not None:
            template.tags = tags
        if scene_structure is not None:
            template.scene_structure = scene_structure
        if style_params is not None:
            template.style_params = style_params
        if version:
            template.version = version

        template.updated_at = datetime.now().isoformat()
        self._save_version(template, changelog)
        self._save()
        print(f"✅ 模板已更新: {template.name} (v{template.version})")
        return True

    def _save_version(self, template: Template, changelog: str = ""):
        """保存模板版本"""
        version_file = os.path.join(self.versions_dir, f"{template.template_id}.json")
        versions = []
        if os.path.exists(version_file):
            try:
                with open(version_file, "r", encoding="utf-8") as f:
                    versions = json.load(f)
            except Exception:
                pass

        versions.append({
            "version": template.version,
            "changelog": changelog,
            "created_at": template.updated_at,
            "template_data": asdict(template),
        })

        with open(version_file, "w", encoding="utf-8") as f:
            json.dump(versions, f, ensure_ascii=False, indent=2)

    def get_versions(self, template_id: str) -> List[Dict[str, Any]]:
        """获取模板版本历史"""
        version_file = os.path.join(self.versions_dir, f"{template_id}.json")
        if os.path.exists(version_file):
            with open(version_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def rollback_version(self, template_id: str, version: str) -> bool:
        """回滚到指定版本"""
        versions = self.get_versions(template_id)
        for v in versions:
            if v["version"] == version:
                template_data = v["template_data"]
                self.templates[template_id] = Template(**template_data)
                self.templates[template_id].updated_at = datetime.now().isoformat()
                self._save()
                print(f"⏪ 模板已回滚到 v{version}")
                return True
        return False

    # ==================== 评分/评论 ====================

    def rate_template(self, template_id: str, rating: float, user: str = "anonymous") -> bool:
        """评分模板（1-5星）"""
        if template_id not in self.templates:
            return False

        if rating < 1 or rating > 5:
            print(f"❌ 评分必须在1-5之间")
            return False

        template = self.templates[template_id]
        template.rating_sum += rating
        template.rating_count += 1
        template.rating = round(template.rating_sum / template.rating_count, 1)
        self._save()
        print(f"⭐ 模板评分: {template.name} = {template.rating} ({template.rating_count}人评分)")
        return True

    def add_comment(self, template_id: str, comment: str, user: str = "anonymous") -> bool:
        """添加评论"""
        if template_id not in self.templates:
            return False

        template = self.templates[template_id]
        template.comments.append({
            "user": user,
            "comment": comment,
            "created_at": datetime.now().isoformat(),
        })
        self._save()
        return True

    # ==================== 搜索/分类 ====================

    def search_templates(self, keyword: str = "", category: str = "",
                         tag: str = "", sort_by: str = "rating",
                         limit: int = 20) -> List[Dict[str, Any]]:
        """搜索模板"""
        results = []

        for template in self.templates.values():
            if not template.is_published:
                continue

            # 关键词搜索（名称/描述/标签）
            if keyword:
                keyword_lower = keyword.lower()
                if (keyword_lower not in template.name.lower() and
                        keyword_lower not in template.description.lower() and
                        not any(keyword_lower in t.lower() for t in template.tags)):
                    continue

            # 分类筛选
            if category and template.category != category:
                continue

            # 标签筛选
            if tag and tag not in template.tags:
                continue

            results.append(asdict(template))

        # 排序
        if sort_by == "rating":
            results.sort(key=lambda x: x["rating"], reverse=True)
        elif sort_by == "downloads":
            results.sort(key=lambda x: x["download_count"], reverse=True)
        elif sort_by == "newest":
            results.sort(key=lambda x: x["created_at"], reverse=True)
        elif sort_by == "name":
            results.sort(key=lambda x: x["name"])

        return results[:limit]

    def list_categories(self) -> List[Dict[str, Any]]:
        """列出分类及模板数量"""
        categories = []
        for cat in self.CATEGORIES:
            count = sum(1 for t in self.templates.values() if t.category == cat and t.is_published)
            categories.append({"category": cat, "count": count})
        return categories

    def list_trending(self, limit: int = 10) -> List[Dict[str, Any]]:
        """列出热门模板"""
        return self.search_templates(sort_by="downloads", limit=limit)

    def list_newest(self, limit: int = 10) -> List[Dict[str, Any]]:
        """列出最新模板"""
        return self.search_templates(sort_by="newest", limit=limit)

    def list_top_rated(self, limit: int = 10) -> List[Dict[str, Any]]:
        """列出评分最高模板"""
        return self.search_templates(sort_by="rating", limit=limit)

    # ==================== 统计 ====================

    def get_stats(self) -> Dict[str, Any]:
        """获取模板市场统计"""
        total = len(self.templates)
        published = sum(1 for t in self.templates.values() if t.is_published)
        official = sum(1 for t in self.templates.values() if t.is_official)
        total_downloads = sum(t.download_count for t in self.templates.values())
        total_ratings = sum(t.rating_count for t in self.templates.values())
        avg_rating = sum(t.rating for t in self.templates.values()) / max(1, total)

        return {
            "total_templates": total,
            "published_templates": published,
            "official_templates": official,
            "total_downloads": total_downloads,
            "total_ratings": total_ratings,
            "average_rating": round(avg_rating, 1),
            "categories": self.list_categories(),
            "timestamp": datetime.now().isoformat(),
        }


if __name__ == "__main__":
    print("=" * 60)
    print("🏪 社区模板市场 v1.0")
    print("=" * 60)

    market = TemplateMarket()

    # 上传测试模板
    tid = market.upload_template(
        name="探店美食模板",
        description="适合探店美食类短视频，包含开场钩子+菜品展示+总结号召",
        author="official",
        category="exploration",
        tags=["探店", "美食", "餐饮"],
        duration=30,
        is_official=True,
    )

    # 评分
    market.rate_template(tid, 5)
    market.rate_template(tid, 4)

    # 搜索
    print(f"\n搜索结果:")
    for t in market.search_templates(keyword="探店"):
        print(f"  {t['name']} (评分: {t['rating']}, 下载: {t['download_count']})")

    print(f"\n统计: {market.get_stats()}")
