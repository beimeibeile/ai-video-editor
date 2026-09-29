"""
通用素材库 (Asset Library)
带逻辑索引的素材管理系统，像人脑记忆一样秒级检索

核心设计：
- 索引文件 index.json：记录所有素材的元数据标签
- 多维标签：type/style/mood/tags/duration/format
- 智能匹配：根据上下文加权评分，返回最佳匹配
- 使用统计：usage_count越高越优先推荐
- 自动扫描：扫描目录自动生成/更新索引
"""
import os
import json
import hashlib
from typing import List, Dict, Optional, Any
from datetime import datetime


class AssetLibrary:
    """通用素材库"""

    # 素材类型
    TYPES = ["sfx", "background", "sticker", "font", "music", "video", "image"]

    # 风格标签（与片头生成器对齐）
    STYLES = ["impact", "cute", "funny", "minimal", "suspense", "epic", "warm", "tech", "cinematic", "retro"]

    # 情绪标签
    MOODS = ["紧张", "欢快", "低沉", "平静", "神秘", "搞笑", "温馨", "震撼", "治愈", "燃", "悲伤", "期待"]

    def __init__(self, library_root: str = None):
        if library_root is None:
            library_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
        self.root = library_root
        self.index_path = os.path.join(self.root, "index.json")
        self.assets: Dict[str, Dict] = {}  # id -> metadata
        self._load_index()

    # ==================== 索引管理 ====================

    def _load_index(self):
        """加载索引文件"""
        if os.path.exists(self.index_path):
            try:
                with open(self.index_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.assets = data.get("assets", {})
            except Exception:
                self.assets = {}
        else:
            self.assets = {}

    def _save_index(self):
        """保存索引文件"""
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
        data = {
            "version": "1.0",
            "updated_at": datetime.now().isoformat(),
            "total": len(self.assets),
            "assets": self.assets,
        }
        with open(self.index_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _generate_id(self, path: str) -> str:
        """根据文件路径生成唯一ID"""
        return hashlib.md5(path.encode('utf-8')).hexdigest()[:12]

    def scan_directory(self, auto_tag: bool = True) -> int:
        """
        扫描素材目录，自动生成/更新索引

        Args:
            auto_tag: 是否根据文件名/路径自动推断标签

        Returns:
            新增/更新的素材数量
        """
        count = 0
        type_dirs = {
            "sfx": "sfx", "background": "backgrounds", "sticker": "stickers",
            "font": "fonts", "music": "music", "video": "video", "image": "image"
        }

        for asset_type, dir_name in type_dirs.items():
            dir_path = os.path.join(self.root, dir_name)
            if not os.path.exists(dir_path):
                continue
            for filename in os.listdir(dir_path):
                filepath = os.path.join(dir_path, filename)
                if not os.path.isfile(filepath):
                    continue
                asset_id = self._generate_id(filepath)
                if asset_id in self.assets:
                    continue  # 已索引

                # 自动推断标签
                tags = []
                style = None
                mood = None
                if auto_tag:
                    name_lower = filename.lower()
                    # 从文件名推断风格
                    for s in self.STYLES:
                        if s in name_lower:
                            style = s
                            break
                    # 从文件名推断情绪
                    for m in self.MOODS:
                        if m in filename:
                            mood = m
                            break
                    # 通用标签
                    if any(k in name_lower for k in ["whoosh", "swosh", "嗖"]):
                        tags.extend(["whoosh", "转场", "运动"])
                    if any(k in name_lower for k in ["ding", "叮", "pop"]):
                        tags.extend(["叮", "提示", "清脆"])
                    if any(k in name_lower for k in ["boom", "爆炸", "冲击"]):
                        tags.extend(["boom", "冲击", "震撼"])
                    if any(k in name_lower for k in ["rain", "雨", "nature"]):
                        tags.extend(["自然", "环境音"])
                    if any(k in name_lower for k in ["loop", "循环", "bg"]):
                        tags.append("循环")

                metadata = {
                    "id": asset_id,
                    "name": filename,
                    "path": os.path.relpath(filepath, self.root),
                    "type": asset_type,
                    "tags": tags,
                    "style": style,
                    "mood": mood,
                    "duration": None,  # 音视频需探测
                    "format": os.path.splitext(filename)[1].lower(),
                    "size_bytes": os.path.getsize(filepath),
                    "description": "",
                    "usage_count": 0,
                    "created_at": datetime.now().isoformat(),
                }
                self.assets[asset_id] = metadata
                count += 1

        self._save_index()
        return count

    # ==================== 素材查询 ====================

    def search(self,
               asset_type: str = None,
               tags: List[str] = None,
               style: str = None,
               mood: str = None,
               duration_range: tuple = None,
               keyword: str = None,
               limit: int = 10) -> List[Dict]:
        """
        多维搜索素材

        Args:
            asset_type: 素材类型 sfx/background/sticker/font/music
            tags: 标签列表（任意匹配）
            style: 风格 impact/cute/funny/minimal/suspense...
            mood: 情绪 紧张/欢快/低沉/平静...
            duration_range: (min_dur, max_dur) 秒
            keyword: 关键词（名称/描述/标签模糊匹配）
            limit: 返回数量

        Returns:
            匹配的素材列表（按使用次数+匹配度排序）
        """
        results = []
        for asset in self.assets.values():
            score = 0.0

            # 类型过滤
            if asset_type and asset["type"] != asset_type:
                continue

            # 风格匹配（精确匹配加分）
            if style:
                if asset.get("style") == style:
                    score += 10
                elif asset.get("style") is None:
                    score += 2  # 无风格标签的不排除

            # 情绪匹配
            if mood:
                if asset.get("mood") == mood:
                    score += 8
                elif asset.get("mood") is None:
                    score += 1

            # 标签匹配（每个匹配标签加分）
            if tags:
                asset_tags = set(asset.get("tags", []))
                match_count = len(set(tags) & asset_tags)
                score += match_count * 5

            # 关键词模糊匹配
            if keyword:
                kw = keyword.lower()
                search_text = (asset["name"] + asset.get("description", "") +
                              " ".join(asset.get("tags", []))).lower()
                if kw in search_text:
                    score += 6

            # 时长过滤
            if duration_range and asset.get("duration"):
                dur = asset["duration"]
                if dur < duration_range[0] or dur > duration_range[1]:
                    continue

            # 使用次数加权（越用越推荐）
            score += asset.get("usage_count", 0) * 0.5

            if score > 0 or (not tags and not style and not mood and not keyword):
                asset_copy = dict(asset)
                asset_copy["_match_score"] = round(score, 2)
                results.append(asset_copy)

        # 按匹配度+使用次数排序
        results.sort(key=lambda x: (x["_match_score"], x.get("usage_count", 0)), reverse=True)
        return results[:limit]

    def get_best_match(self,
                       asset_type: str,
                       context: str = "",
                       style: str = None,
                       mood: str = None,
                       tags: List[str] = None) -> Optional[Dict]:
        """
        智能推荐最佳匹配素材（秒级检索）

        Args:
            asset_type: 素材类型
            context: 上下文描述（如"片头主标题出现"、"转场瞬间"）
            style: 风格
            mood: 情绪
            tags: 标签

        Returns:
            最佳匹配素材的完整元数据，找不到返回None
        """
        # 从上下文推断标签
        inferred_tags = []
        if context:
            ctx_lower = context.lower()
            if any(k in ctx_lower for k in ["出现", "入场", "开场", "标题"]):
                inferred_tags.append("转场")
            if any(k in ctx_lower for k in ["转场", "切换", "过渡"]):
                inferred_tags.append("转场")
            if any(k in ctx_lower for k in ["结尾", "淡出", "结束"]):
                inferred_tags.append("结尾")

        all_tags = list(set((tags or []) + inferred_tags))
        results = self.search(
            asset_type=asset_type,
            tags=all_tags if all_tags else None,
            style=style,
            mood=mood,
            keyword=context if context else None,
            limit=3
        )
        if results:
            best = results[0]
            self._increment_usage(best["id"])
            return best
        return None

    def get_path(self, asset_id: str) -> Optional[str]:
        """获取素材的绝对路径"""
        asset = self.assets.get(asset_id)
        if asset:
            return os.path.join(self.root, asset["path"])
        return None

    # ==================== 素材管理 ====================

    def add_asset(self, filepath: str, asset_type: str,
                  tags: List[str] = None, style: str = None,
                  mood: str = None, description: str = "",
                  duration: float = None) -> str:
        """
        手动添加素材到索引

        Returns:
            素材ID
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"素材不存在: {filepath}")

        # 复制到素材库目录
        type_dir = {
            "sfx": "sfx", "background": "backgrounds", "sticker": "stickers",
            "font": "fonts", "music": "music", "video": "video", "image": "image"
        }.get(asset_type, "misc")
        dest_dir = os.path.join(self.root, type_dir)
        os.makedirs(dest_dir, exist_ok=True)

        import shutil
        filename = os.path.basename(filepath)
        dest_path = os.path.join(dest_dir, filename)
        if filepath != dest_path:
            shutil.copy2(filepath, dest_path)

        asset_id = self._generate_id(dest_path)
        self.assets[asset_id] = {
            "id": asset_id,
            "name": filename,
            "path": os.path.relpath(dest_path, self.root),
            "type": asset_type,
            "tags": tags or [],
            "style": style,
            "mood": mood,
            "duration": duration,
            "format": os.path.splitext(filename)[1].lower(),
            "size_bytes": os.path.getsize(dest_path),
            "description": description,
            "usage_count": 0,
            "created_at": datetime.now().isoformat(),
        }
        self._save_index()
        return asset_id

    def update_asset(self, asset_id: str, **kwargs) -> bool:
        """更新素材元数据"""
        if asset_id not in self.assets:
            return False
        for key, value in kwargs.items():
            if key in self.assets[asset_id]:
                self.assets[asset_id][key] = value
        self._save_index()
        return True

    def remove_asset(self, asset_id: str, delete_file: bool = False) -> bool:
        """移除素材（可选删除文件）"""
        if asset_id not in self.assets:
            return False
        if delete_file:
            filepath = self.get_path(asset_id)
            if filepath and os.path.exists(filepath):
                os.remove(filepath)
        del self.assets[asset_id]
        self._save_index()
        return True

    def _increment_usage(self, asset_id: str):
        """增加使用计数"""
        if asset_id in self.assets:
            self.assets[asset_id]["usage_count"] = self.assets[asset_id].get("usage_count", 0) + 1
            self._save_index()

    # ==================== 统计 ====================

    def stats(self) -> Dict:
        """素材库统计"""
        type_count = {}
        style_count = {}
        mood_count = {}
        total_size = 0
        for asset in self.assets.values():
            t = asset["type"]
            type_count[t] = type_count.get(t, 0) + 1
            if asset.get("style"):
                style_count[asset["style"]] = style_count.get(asset["style"], 0) + 1
            if asset.get("mood"):
                mood_count[asset["mood"]] = mood_count.get(asset["mood"], 0) + 1
            total_size += asset.get("size_bytes", 0)
        return {
            "total": len(self.assets),
            "by_type": type_count,
            "by_style": style_count,
            "by_mood": mood_count,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
        }


# 全局单例
_default_library = None

def get_library() -> AssetLibrary:
    """获取默认素材库实例"""
    global _default_library
    if _default_library is None:
        _default_library = AssetLibrary()
    return _default_library
