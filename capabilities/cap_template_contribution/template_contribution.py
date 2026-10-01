"""
社区模板贡献模块
用户模板上传与审核机制，模板评分、分类、搜索，社区贡献者体系
"""

import os
import json
import time
import hashlib
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum


class TemplateStatus(Enum):
    """模板状态"""
    PENDING = "pending"        # 待审核
    APPROVED = "approved"      # 已通过
    REJECTED = "rejected"      # 已拒绝
    DRAFT = "draft"            # 草稿
    REMOVED = "removed"        # 已下架


class ReviewResult(Enum):
    """审核结果"""
    PASS = "pass"
    FAIL = "fail"
    NEEDS_REVISION = "needs_revision"


@dataclass
class Template:
    """模板"""
    id: str
    name: str
    author: str
    author_id: str
    description: str = ""
    category: str = "general"
    tags: List[str] = field(default_factory=list)
    version: str = "1.0.0"
    status: TemplateStatus = TemplateStatus.DRAFT
    rating: float = 0.0
    rating_count: int = 0
    download_count: int = 0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    file_path: str = ""
    file_size: int = 0
    file_hash: str = ""
    preview_image: str = ""
    duration: float = 0.0
    shot_count: int = 0
    config: Dict[str, Any] = field(default_factory=dict)
    review_notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d


@dataclass
class Contributor:
    """贡献者"""
    id: str
    name: str
    avatar: str = ""
    bio: str = ""
    template_count: int = 0
    total_downloads: int = 0
    total_rating: float = 0.0
    level: int = 1
    badges: List[str] = field(default_factory=list)
    joined_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Review:
    """审核记录"""
    id: str
    template_id: str
    reviewer: str
    result: ReviewResult
    comments: str = ""
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["result"] = self.result.value
        return d


class TemplateContributionSystem:
    """社区模板贡献系统"""

    def __init__(self, data_dir: str = None):
        self.data_dir = data_dir or os.path.join(
            os.path.expanduser("~"), ".ai_video_editor", "community"
        )
        os.makedirs(self.data_dir, exist_ok=True)
        self.templates_file = os.path.join(self.data_dir, "templates.json")
        self.contributors_file = os.path.join(self.data_dir, "contributors.json")
        self.reviews_file = os.path.join(self.data_dir, "reviews.json")
        self.ratings_file = os.path.join(self.data_dir, "ratings.json")

        self.templates = self._load(self.templates_file, {})
        self.contributors = self._load(self.contributors_file, {})
        self.reviews = self._load(self.reviews_file, {})
        self.ratings = self._load(self.ratings_file, {})  # template_id -> {user_id -> rating}

    def _load(self, path: str, default: Any) -> Any:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return default

    def _save(self, path: str, data: Any) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _save_all(self) -> None:
        self._save(self.templates_file, self.templates)
        self._save(self.contributors_file, self.contributors)
        self._save(self.reviews_file, self.reviews)
        self._save(self.ratings_file, self.ratings)

    def _generate_id(self) -> str:
        return hashlib.md5(f"{time.time()}{os.urandom(8)}".encode()).hexdigest()[:12]

    # ==================== 贡献者管理 ====================

    def register_contributor(self, name: str, avatar: str = "",
                              bio: str = "") -> Contributor:
        """注册贡献者"""
        cid = self._generate_id()
        contributor = Contributor(id=cid, name=name, avatar=avatar, bio=bio)
        self.contributors[cid] = contributor.to_dict()
        self._save(self.contributors_file, self.contributors)
        return contributor

    def get_contributor(self, cid: str) -> Optional[Dict[str, Any]]:
        """获取贡献者信息"""
        return self.contributors.get(cid)

    def update_contributor_level(self, cid: str) -> None:
        """更新贡献者等级（基于模板数和下载量）"""
        c = self.contributors.get(cid)
        if not c:
            return
        score = c["template_count"] * 10 + c["total_downloads"]
        if score >= 1000:
            c["level"] = 5
        elif score >= 500:
            c["level"] = 4
        elif score >= 200:
            c["level"] = 3
        elif score >= 50:
            c["level"] = 2
        else:
            c["level"] = 1
        self._save(self.contributors_file, self.contributors)

    # ==================== 模板上传 ====================

    def upload_template(self, name: str, author_id: str, file_path: str,
                        description: str = "", category: str = "general",
                        tags: List[str] = None, duration: float = 0.0,
                        shot_count: int = 0, preview_image: str = "") -> Template:
        """
        上传模板（状态为待审核）

        Args:
            name: 模板名称
            author_id: 作者ID
            file_path: 模板文件路径
            description: 描述
            category: 分类
            tags: 标签
            duration: 时长
            shot_count: 镜头数
            preview_image: 预览图路径

        Returns:
            Template对象
        """
        author = self.contributors.get(author_id)
        if not author:
            raise ValueError(f"贡献者不存在: {author_id}")

        tid = self._generate_id()
        file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0

        # 计算文件哈希
        file_hash = ""
        if os.path.exists(file_path):
            with open(file_path, "rb") as f:
                file_hash = hashlib.md5(f.read()).hexdigest()

        template = Template(
            id=tid,
            name=name,
            author=author["name"],
            author_id=author_id,
            description=description,
            category=category,
            tags=tags or [],
            status=TemplateStatus.PENDING,
            file_path=file_path,
            file_size=file_size,
            file_hash=file_hash,
            preview_image=preview_image,
            duration=duration,
            shot_count=shot_count,
        )

        self.templates[tid] = template.to_dict()
        self._save(self.templates_file, self.templates)
        return template

    # ==================== 模板审核 ====================

    def review_template(self, template_id: str, reviewer: str,
                        result: ReviewResult, comments: str = "") -> Optional[Review]:
        """审核模板"""
        t = self.templates.get(template_id)
        if not t:
            return None

        rid = self._generate_id()
        review = Review(
            id=rid,
            template_id=template_id,
            reviewer=reviewer,
            result=result,
            comments=comments,
        )

        self.reviews[rid] = review.to_dict()

        # 更新模板状态
        if result == ReviewResult.PASS:
            t["status"] = TemplateStatus.APPROVED.value
            # 更新贡献者模板数
            c = self.contributors.get(t["author_id"])
            if c:
                c["template_count"] += 1
                self.update_contributor_level(t["author_id"])
        elif result == ReviewResult.FAIL:
            t["status"] = TemplateStatus.REJECTED.value
        elif result == ReviewResult.NEEDS_REVISION:
            t["status"] = TemplateStatus.DRAFT.value

        t["review_notes"] = comments
        t["updated_at"] = time.time()

        self._save_all()
        return review

    def get_pending_templates(self) -> List[Dict[str, Any]]:
        """获取待审核模板列表"""
        return [t for t in self.templates.values()
                if t["status"] == TemplateStatus.PENDING.value]

    # ==================== 模板评分 ====================

    def rate_template(self, template_id: str, user_id: str,
                      rating: float) -> bool:
        """
        评分模板（1-5星）

        Args:
            template_id: 模板ID
            user_id: 用户ID
            rating: 评分（1-5）

        Returns:
            是否成功
        """
        t = self.templates.get(template_id)
        if not t or t["status"] != TemplateStatus.APPROVED.value:
            return False

        rating = max(1.0, min(5.0, rating))

        if template_id not in self.ratings:
            self.ratings[template_id] = {}

        is_new = user_id not in self.ratings[template_id]
        self.ratings[template_id][user_id] = rating

        # 重新计算平均评分
        ratings = list(self.ratings[template_id].values())
        t["rating"] = sum(ratings) / len(ratings)
        t["rating_count"] = len(ratings)

        self._save_all()
        return True

    # ==================== 模板下载 ====================

    def download_template(self, template_id: str) -> Optional[str]:
        """下载模板（返回文件路径）"""
        t = self.templates.get(template_id)
        if not t or t["status"] != TemplateStatus.APPROVED.value:
            return None

        t["download_count"] += 1

        # 更新贡献者下载量
        c = self.contributors.get(t["author_id"])
        if c:
            c["total_downloads"] += 1
            self.update_contributor_level(t["author_id"])

        self._save_all()
        return t["file_path"]

    # ==================== 模板搜索 ====================

    def search_templates(self, keyword: str = "", category: str = "",
                         min_rating: float = 0.0, sort_by: str = "rating",
                         limit: int = 20) -> List[Dict[str, Any]]:
        """
        搜索模板

        Args:
            keyword: 关键词（匹配名称、描述、标签）
            category: 分类筛选
            min_rating: 最低评分
            sort_by: 排序方式（rating/downloads/newest）
            limit: 返回数量

        Returns:
            模板列表
        """
        results = []
        for t in self.templates.values():
            if t["status"] != TemplateStatus.APPROVED.value:
                continue
            if category and t["category"] != category:
                continue
            if t["rating"] < min_rating:
                continue
            if keyword:
                kw = keyword.lower()
                if (kw not in t["name"].lower() and
                        kw not in t["description"].lower() and
                        not any(kw in tag.lower() for tag in t["tags"])):
                    continue
            results.append(t)

        # 排序
        if sort_by == "rating":
            results.sort(key=lambda x: x["rating"], reverse=True)
        elif sort_by == "downloads":
            results.sort(key=lambda x: x["download_count"], reverse=True)
        elif sort_by == "newest":
            results.sort(key=lambda x: x["created_at"], reverse=True)

        return results[:limit]

    # ==================== 分类管理 ====================

    def get_categories(self) -> List[Dict[str, Any]]:
        """获取所有分类及模板数量"""
        categories = {}
        for t in self.templates.values():
            if t["status"] == TemplateStatus.APPROVED.value:
                cat = t["category"]
                if cat not in categories:
                    categories[cat] = {"name": cat, "count": 0}
                categories[cat]["count"] += 1
        return list(categories.values())

    # ==================== 统计 ====================

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        approved = [t for t in self.templates.values()
                    if t["status"] == TemplateStatus.APPROVED.value]
        pending = [t for t in self.templates.values()
                   if t["status"] == TemplateStatus.PENDING.value]
        total_downloads = sum(t["download_count"] for t in approved)
        avg_rating = (sum(t["rating"] for t in approved) / len(approved)
                      if approved else 0.0)

        return {
            "total_templates": len(self.templates),
            "approved": len(approved),
            "pending": len(pending),
            "total_downloads": total_downloads,
            "avg_rating": round(avg_rating, 2),
            "total_contributors": len(self.contributors),
            "categories": self.get_categories(),
        }
