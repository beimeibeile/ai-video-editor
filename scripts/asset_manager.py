#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
素材资产管理系统
扫描素材目录，提取元数据，建立索引，提供搜索和筛选
"""
import os
import json
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)

FFPROBE = r"D:\Ai\ffmpeg-master-latest-win64-gpl\bin\ffprobe.exe"
MATERIAL_ROOT = r"D:\DobaoWork_Project\Ai_Video_Editor\material"
INDEX_FILE = os.path.join(MATERIAL_ROOT, "asset_index.json")

# 支持的文件类型
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tiff"}
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv"}
AUDIO_EXTS = {".mp3", ".wav", ".ogg", ".m4a", ".flac", ".aac"}
TEMPLATE_EXTS = {".draft", ".json", ".template"}


@dataclass
class Asset:
    """素材元数据"""
    id: str
    file_path: str
    file_name: str
    asset_type: str  # image/video/audio/template
    size_bytes: int
    created_at: float
    modified_at: float
    duration: float = 0  # 视频/音频时长
    width: int = 0
    height: int = 0
    fps: float = 0
    codec: str = ""
    tags: List[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class AssetManager:
    """素材管理器"""

    def __init__(self, root: str = None):
        self.root = root or MATERIAL_ROOT
        self.assets: Dict[str, Asset] = {}
        self._load_index()

    def _load_index(self):
        """加载索引"""
        if os.path.exists(INDEX_FILE):
            try:
                with open(INDEX_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for item in data.get("assets", []):
                    asset = Asset(**item)
                    self.assets[asset.id] = asset
                logger.info(f"加载素材索引: {len(self.assets)}个")
            except Exception as e:
                logger.error(f"加载索引失败: {e}")
                self.assets = {}

    def _save_index(self):
        """保存索引"""
        data = {
            "version": "1.0",
            "updated": time.time(),
            "total": len(self.assets),
            "assets": [asdict(a) for a in self.assets.values()]
        }
        os.makedirs(os.path.dirname(INDEX_FILE), exist_ok=True)
        with open(INDEX_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _get_asset_type(self, ext: str) -> Optional[str]:
        ext = ext.lower()
        if ext in IMAGE_EXTS:
            return "image"
        if ext in VIDEO_EXTS:
            return "video"
        if ext in AUDIO_EXTS:
            return "audio"
        if ext in TEMPLATE_EXTS:
            return "template"
        return None

    def _probe_media(self, file_path: str) -> Dict[str, Any]:
        """用ffprobe探测媒体文件信息"""
        result = {"duration": 0, "width": 0, "height": 0, "fps": 0, "codec": ""}
        if not os.path.exists(FFPROBE):
            return result
        try:
            import subprocess
            cmd = [FFPROBE, "-v", "quiet", "-print_format", "json",
                   "-show_format", "-show_streams", file_path]
            out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, timeout=10)
            data = json.loads(out)
            fmt = data.get("format", {})
            result["duration"] = float(fmt.get("duration", 0))
            for stream in data.get("streams", []):
                if stream.get("codec_type") == "video":
                    result["width"] = int(stream.get("width", 0))
                    result["height"] = int(stream.get("height", 0))
                    result["codec"] = stream.get("codec_name", "")
                    fps_str = stream.get("r_frame_rate", "0/1")
                    if "/" in fps_str:
                        num, den = fps_str.split("/")
                        if float(den) > 0:
                            result["fps"] = float(num) / float(den)
                    break
                elif stream.get("codec_type") == "audio":
                    result["codec"] = stream.get("codec_name", "")
        except Exception as e:
            logger.debug(f"探测失败 {file_path}: {e}")
        return result

    def scan(self, force: bool = False) -> int:
        """
        扫描素材目录，更新索引
        Args:
            force: 是否强制重新扫描（忽略缓存）
        Returns:
            新增/更新的素材数量
        """
        count = 0
        for dirpath, dirnames, filenames in os.walk(self.root):
            # 跳过隐藏目录和git目录
            dirnames[:] = [d for d in dirnames if not d.startswith('.') and d != '.git']
            for filename in filenames:
                ext = os.path.splitext(filename)[1].lower()
                asset_type = self._get_asset_type(ext)
                if not asset_type:
                    continue
                file_path = os.path.join(dirpath, filename)
                try:
                    stat = os.stat(file_path)
                except OSError:
                    continue

                asset_id = self._make_id(file_path)

                # 检查是否需要更新
                if not force and asset_id in self.assets:
                    existing = self.assets[asset_id]
                    if existing.modified_at == stat.st_mtime and existing.size_bytes == stat.st_size:
                        continue

                # 探测媒体信息
                media_info = {}
                if asset_type in ("video", "audio"):
                    media_info = self._probe_media(file_path)

                # 从路径提取标签
                tags = self._extract_tags(file_path)

                asset = Asset(
                    id=asset_id,
                    file_path=file_path,
                    file_name=filename,
                    asset_type=asset_type,
                    size_bytes=stat.st_size,
                    created_at=stat.st_ctime,
                    modified_at=stat.st_mtime,
                    duration=media_info.get("duration", 0),
                    width=media_info.get("width", 0),
                    height=media_info.get("height", 0),
                    fps=media_info.get("fps", 0),
                    codec=media_info.get("codec", ""),
                    tags=tags,
                )
                self.assets[asset_id] = asset
                count += 1

        # 清理已删除的文件
        to_remove = [aid for aid, a in self.assets.items() if not os.path.exists(a.file_path)]
        for aid in to_remove:
            del self.assets[aid]

        self._save_index()
        logger.info(f"扫描完成: 新增/更新{count}个, 清理{len(to_remove)}个, 总计{len(self.assets)}个")
        return count

    def _make_id(self, file_path: str) -> str:
        """生成素材ID"""
        import hashlib
        return hashlib.md5(file_path.encode('utf-8')).hexdigest()[:12]

    def _extract_tags(self, file_path: str) -> List[str]:
        """从文件路径提取标签"""
        tags = []
        rel = os.path.relpath(file_path, self.root)
        parts = rel.replace("\\", "/").split("/")
        for part in parts[:-1]:  # 目录名作为标签
            if part and part not in tags:
                tags.append(part.lower())
        # 文件名关键词
        name = os.path.splitext(os.path.basename(file_path))[0].lower()
        keywords = ["bgm", "template", "draft", "export", "test", "sample",
                    "happy", "sad", "cinematic", "vlog", "cover", "logo"]
        for kw in keywords:
            if kw in name and kw not in tags:
                tags.append(kw)
        return tags

    def search(self, asset_type: str = None, keyword: str = None,
               tags: List[str] = None, min_duration: float = None,
               max_duration: float = None, limit: int = 50) -> List[Dict[str, Any]]:
        """
        搜索素材
        Args:
            asset_type: 类型过滤 (image/video/audio/template)
            keyword: 文件名关键词
            tags: 标签过滤
            min_duration: 最小时长
            max_duration: 最大时长
            limit: 返回数量
        Returns:
            匹配的素材列表
        """
        results = []
        for asset in self.assets.values():
            if asset_type and asset.asset_type != asset_type:
                continue
            if keyword and keyword.lower() not in asset.file_name.lower():
                continue
            if tags:
                if not any(t in asset.tags for t in tags):
                    continue
            if min_duration and asset.duration < min_duration:
                continue
            if max_duration and asset.duration > max_duration:
                continue
            results.append(asdict(asset))

        results.sort(key=lambda x: x["modified_at"], reverse=True)
        return results[:limit]

    def get_stats(self) -> Dict[str, Any]:
        """获取素材统计"""
        stats = {"total": len(self.assets), "by_type": {}, "total_size": 0}
        for asset in self.assets.values():
            t = asset.asset_type
            stats["by_type"][t] = stats["by_type"].get(t, 0) + 1
            stats["total_size"] += asset.size_bytes
        return stats


# 全局单例
_manager: Optional[AssetManager] = None


def get_manager() -> AssetManager:
    global _manager
    if _manager is None:
        _manager = AssetManager()
    return _manager


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    mgr = AssetManager()
    print("扫描素材目录...")
    count = mgr.scan(force=True)
    print(f"新增/更新: {count}")
    print(f"\n统计: {json.dumps(mgr.get_stats(), ensure_ascii=False, indent=2)}")
    print(f"\n最近素材:")
    for a in mgr.search(limit=5):
        print(f"  [{a['asset_type']}] {a['file_name']} ({a['size_bytes']//1024}KB)")
