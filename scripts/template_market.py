"""
模板市场模块（Template Market）
阶段三任务10：社区模板市场

功能：
1. 模板库管理（本地JSON存储）
2. 模板分类与标签（风格/场景/时长/难度）
3. 模板搜索与推荐
4. 模板上传/下载（本地文件管理）
5. 模板评分与评论
6. 使用统计与热门排行
7. 模板版本管理
"""

import os
import json
import time
import shutil
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime


# ============ 模板分类定义 ============
TEMPLATE_CATEGORIES = {
    "style": ["电影感", "日系清新", "复古胶片", "赛博朋克", "国潮", "极简", "ins风", "暗黑", "暖色调", "冷色调"],
    "scene": ["探店", "Vlog", "教程", "产品展示", "剧情", "口播", "带货", "宣传", "婚礼", "旅行", "美食", "宠物"],
    "duration": ["15秒内", "15-30秒", "30-60秒", "1-3分钟", "3分钟以上"],
    "difficulty": ["入门", "简单", "中等", "进阶", "专业"],
    "aspect_ratio": ["9:16竖屏", "16:9横屏", "1:1方形", "4:5竖版"],
}


@dataclass
class Template:
    """模板数据结构"""
    template_id: str
    name: str
    description: str = ""
    author: str = "system"
    category: str = ""  # 主分类
    tags: List[str] = field(default_factory=list)
    style: str = ""
    scene: str = ""
    duration: str = ""
    difficulty: str = "简单"
    aspect_ratio: str = "9:16竖屏"
    version: str = "1.0.0"
    file_path: str = ""  # 模板文件路径（剪映工程/JSON配置）
    thumbnail: str = ""  # 缩略图路径
    rating: float = 0.0  # 平均评分 0-5
    rating_count: int = 0
    download_count: int = 0
    use_count: int = 0
    comments: List[Dict] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    is_official: bool = False
    is_featured: bool = False  # 精选推荐


class TemplateMarket:
    """模板市场管理器"""

    def __init__(self, data_dir: str = None):
        """
        初始化模板市场

        Args:
            data_dir: 数据存储目录
        """
        if data_dir is None:
            data_dir = os.path.join(
                os.path.expanduser("~"), "Videos", "剪映导出",
                "ai-video-editor", "template_market"
            )
        self.data_dir = data_dir
        self.templates_dir = os.path.join(data_dir, "templates")
        self.db_path = os.path.join(data_dir, "templates.json")
        os.makedirs(self.templates_dir, exist_ok=True)
        self._templates: Dict[str, Template] = {}
        self._load_db()

    def _load_db(self):
        """加载模板数据库"""
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for tid, tdata in data.items():
                    self._templates[tid] = Template(**tdata)
            except Exception as e:
                print(f"[TemplateMarket] 加载数据库失败: {e}")
                self._templates = {}
        else:
            self._init_default_templates()

    def _save_db(self):
        """保存模板数据库"""
        data = {tid: asdict(t) for tid, t in self._templates.items()}
        with open(self.db_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _init_default_templates(self):
        """初始化默认模板"""
        defaults = [
            {
                "name": "探店美食-经典结构",
                "description": "Hook开场→环境展示→美食特写→价格地址→CTA引导，适合餐饮探店",
                "category": "探店",
                "tags": ["探店", "美食", "经典结构", "hook"],
                "style": "暖色调",
                "scene": "探店",
                "duration": "30-60秒",
                "difficulty": "简单",
                "aspect_ratio": "9:16竖屏",
                "is_official": True,
                "is_featured": True,
            },
            {
                "name": "口播知识-三段式",
                "description": "痛点引入→知识讲解→总结升华，适合知识分享类口播",
                "category": "口播",
                "tags": ["口播", "知识", "三段式", "干货"],
                "style": "极简",
                "scene": "口播",
                "duration": "30-60秒",
                "difficulty": "简单",
                "aspect_ratio": "9:16竖屏",
                "is_official": True,
                "is_featured": True,
            },
            {
                "name": "Vlog日常-快节奏",
                "description": "多场景快切+动感BGM+文字标注，适合日常Vlog记录",
                "category": "Vlog",
                "tags": ["Vlog", "日常", "快节奏", "多场景"],
                "style": "ins风",
                "scene": "Vlog",
                "duration": "1-3分钟",
                "difficulty": "中等",
                "aspect_ratio": "9:16竖屏",
                "is_official": True,
            },
            {
                "name": "产品展示-高级感",
                "description": "产品特写→功能展示→使用场景→购买引导，适合电商产品展示",
                "category": "产品展示",
                "tags": ["产品", "电商", "高级感", "展示"],
                "style": "极简",
                "scene": "产品展示",
                "duration": "15-30秒",
                "difficulty": "中等",
                "aspect_ratio": "9:16竖屏",
                "is_official": True,
                "is_featured": True,
            },
            {
                "name": "剧情情感-反转结构",
                "description": "铺垫→冲突→反转→升华，适合情感类剧情短片",
                "category": "剧情",
                "tags": ["剧情", "情感", "反转", "故事"],
                "style": "电影感",
                "scene": "剧情",
                "duration": "1-3分钟",
                "difficulty": "进阶",
                "aspect_ratio": "9:16竖屏",
                "is_official": True,
            },
            {
                "name": "教程演示-步骤清晰",
                "description": "问题引入→分步演示→要点总结，适合教程类视频",
                "category": "教程",
                "tags": ["教程", "演示", "步骤", "干货"],
                "style": "极简",
                "scene": "教程",
                "duration": "1-3分钟",
                "difficulty": "简单",
                "aspect_ratio": "9:16竖屏",
                "is_official": True,
            },
            {
                "name": "带货转化-痛点驱动",
                "description": "痛点放大→产品解决方案→用户见证→限时优惠，适合带货视频",
                "category": "带货",
                "tags": ["带货", "转化", "痛点", "电商"],
                "style": "暖色调",
                "scene": "带货",
                "duration": "30-60秒",
                "difficulty": "中等",
                "aspect_ratio": "9:16竖屏",
                "is_official": True,
            },
            {
                "name": "旅行记录-电影感",
                "description": "地标空镜→人文特写→美食体验→情感升华，适合旅行Vlog",
                "category": "旅行",
                "tags": ["旅行", "电影感", "Vlog", "记录"],
                "style": "电影感",
                "scene": "旅行",
                "duration": "1-3分钟",
                "difficulty": "中等",
                "aspect_ratio": "16:9横屏",
                "is_official": True,
                "is_featured": True,
            },
        ]

        for tdata in defaults:
            tid = f"tpl_{int(time.time() * 1000)}_{len(self._templates)}"
            template = Template(template_id=tid, **tdata)
            self._templates[tid] = template
        self._save_db()

    def add_template(self, name: str, description: str = "",
                     category: str = "", tags: List[str] = None,
                     file_path: str = "", author: str = "user",
                     **kwargs) -> Template:
        """
        添加新模板

        Args:
            name: 模板名称
            description: 模板描述
            category: 主分类
            tags: 标签列表
            file_path: 模板文件路径
            author: 作者
            **kwargs: 其他字段

        Returns:
            创建的模板对象
        """
        tid = f"tpl_{int(time.time() * 1000)}_{len(self._templates)}"
        template = Template(
            template_id=tid,
            name=name,
            description=description,
            category=category,
            tags=tags or [],
            file_path=file_path,
            author=author,
            **kwargs
        )
        self._templates[tid] = template
        self._save_db()
        return template

    def get_template(self, template_id: str) -> Optional[Template]:
        """获取模板详情"""
        return self._templates.get(template_id)

    def update_template(self, template_id: str, **kwargs) -> Optional[Template]:
        """更新模板信息"""
        template = self._templates.get(template_id)
        if not template:
            return None
        for key, value in kwargs.items():
            if hasattr(template, key):
                setattr(template, key, value)
        template.updated_at = time.time()
        self._save_db()
        return template

    def delete_template(self, template_id: str) -> bool:
        """删除模板"""
        if template_id in self._templates:
            template = self._templates[template_id]
            # 删除模板文件
            if template.file_path and os.path.exists(template.file_path):
                try:
                    os.remove(template.file_path)
                except Exception:
                    pass
            del self._templates[template_id]
            self._save_db()
            return True
        return False

    def search_templates(self, keyword: str = "", category: str = "",
                         style: str = "", scene: str = "",
                         difficulty: str = "", aspect_ratio: str = "",
                         tags: List[str] = None,
                         sort_by: str = "rating",
                         limit: int = 20, offset: int = 0) -> List[Template]:
        """
        搜索模板

        Args:
            keyword: 关键词（搜索名称/描述/标签）
            category: 主分类过滤
            style: 风格过滤
            scene: 场景过滤
            difficulty: 难度过滤
            aspect_ratio: 画幅过滤
            tags: 标签过滤（任意匹配）
            sort_by: 排序方式（rating/download/use/created/name）
            limit: 返回数量
            offset: 偏移量

        Returns:
            匹配的模板列表
        """
        results = list(self._templates.values())

        # 关键词搜索
        if keyword:
            keyword_lower = keyword.lower()
            results = [
                t for t in results
                if keyword_lower in t.name.lower()
                or keyword_lower in t.description.lower()
                or any(keyword_lower in tag.lower() for tag in t.tags)
            ]

        # 分类过滤
        if category:
            results = [t for t in results if t.category == category]
        if style:
            results = [t for t in results if t.style == style]
        if scene:
            results = [t for t in results if t.scene == scene]
        if difficulty:
            results = [t for t in results if t.difficulty == difficulty]
        if aspect_ratio:
            results = [t for t in results if t.aspect_ratio == aspect_ratio]
        if tags:
            results = [t for t in results if any(tag in t.tags for tag in tags)]

        # 排序
        sort_keys = {
            "rating": lambda t: t.rating,
            "download": lambda t: t.download_count,
            "use": lambda t: t.use_count,
            "created": lambda t: t.created_at,
            "name": lambda t: t.name,
        }
        sort_func = sort_keys.get(sort_by, sort_keys["rating"])
        results.sort(key=sort_func, reverse=True)

        return results[offset:offset + limit]

    def rate_template(self, template_id: str, rating: float,
                      comment: str = "", user: str = "anonymous") -> bool:
        """
        评分模板

        Args:
            template_id: 模板ID
            rating: 评分 1-5
            comment: 评论内容
            user: 用户名

        Returns:
            是否成功
        """
        template = self._templates.get(template_id)
        if not template:
            return False

        rating = max(1.0, min(5.0, rating))

        # 更新平均评分
        total_rating = template.rating * template.rating_count
        template.rating_count += 1
        template.rating = round((total_rating + rating) / template.rating_count, 2)

        # 添加评论
        if comment:
            template.comments.append({
                "user": user,
                "rating": rating,
                "comment": comment,
                "created_at": time.time(),
            })

        self._save_db()
        return True

    def increment_download(self, template_id: str) -> bool:
        """增加下载计数"""
        template = self._templates.get(template_id)
        if template:
            template.download_count += 1
            self._save_db()
            return True
        return False

    def increment_use(self, template_id: str) -> bool:
        """增加使用计数"""
        template = self._templates.get(template_id)
        if template:
            template.use_count += 1
            self._save_db()
            return True
        return False

    def get_featured(self, limit: int = 6) -> List[Template]:
        """获取精选推荐模板"""
        featured = [t for t in self._templates.values() if t.is_featured]
        featured.sort(key=lambda t: t.rating, reverse=True)
        return featured[:limit]

    def get_hot(self, limit: int = 10) -> List[Template]:
        """获取热门模板（按使用+下载综合排序）"""
        templates = list(self._templates.values())
        templates.sort(
            key=lambda t: t.use_count * 2 + t.download_count,
            reverse=True
        )
        return templates[:limit]

    def get_newest(self, limit: int = 10) -> List[Template]:
        """获取最新模板"""
        templates = list(self._templates.values())
        templates.sort(key=lambda t: t.created_at, reverse=True)
        return templates[:limit]

    def get_categories(self) -> Dict[str, List[str]]:
        """获取所有分类选项"""
        return TEMPLATE_CATEGORIES

    def get_stats(self) -> Dict[str, Any]:
        """获取模板市场统计"""
        templates = list(self._templates.values())
        category_count = {}
        for t in templates:
            cat = t.category or "未分类"
            category_count[cat] = category_count.get(cat, 0) + 1

        return {
            "total": len(templates),
            "official_count": sum(1 for t in templates if t.is_official),
            "featured_count": sum(1 for t in templates if t.is_featured),
            "total_downloads": sum(t.download_count for t in templates),
            "total_uses": sum(t.use_count for t in templates),
            "avg_rating": round(sum(t.rating for t in templates) / max(len(templates), 1), 2),
            "categories": category_count,
        }

    def list_all(self) -> List[Template]:
        """列出所有模板"""
        return list(self._templates.values())


# 全局单例
_market = None

def get_market(data_dir: str = None) -> TemplateMarket:
    """获取模板市场单例"""
    global _market
    if _market is None:
        _market = TemplateMarket(data_dir)
    return _market


if __name__ == "__main__":
    market = TemplateMarket()
    print("=== 模板市场统计 ===")
    stats = market.get_stats()
    for k, v in stats.items():
        print(f"  {k}: {v}")

    print("\n=== 精选模板 ===")
    for t in market.get_featured():
        print(f"  [{t.category}] {t.name} (评分:{t.rating})")

    print("\n=== 搜索测试: '探店' ===")
    results = market.search_templates(keyword="探店")
    for t in results:
        print(f"  {t.name} - {t.description[:30]}...")
