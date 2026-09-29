"""
素材库逻辑索引系统
像人脑记忆一样，秒级检索合适素材

功能：
- 扫描素材库目录，自动分类（图片/视频/音频/贴纸/字幕条/特效）
- 提取元数据（分辨率/时长/帧率/编码/文件大小/颜色）
- 自动标签（基于文件名+路径+元数据）
- JSON持久化索引，增量更新
- 多维度检索（类型/标签/分辨率/时长/比例/颜色）
- 语义相似度检索（基于标签的模糊匹配）
"""
import os
import sys
import json
import hashlib
from datetime import datetime
from typing import List, Dict, Optional, Any, Tuple

# ffmpeg/ffprobe路径
FFPROBE = r"D:\Ai\ffmpeg-master-latest-win64-gpl\bin\ffprobe.exe"
FFMPEG = r"D:\Ai\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe"

# 支持的文件类型
IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif', '.tiff'}
VIDEO_EXTS = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv'}
AUDIO_EXTS = {'.mp3', '.wav', '.aac', '.ogg', '.flac', '.m4a', '.wma'}
SUBTITLE_EXTS = {'.srt', '.ass', '.vtt', '.ssa'}

# 路径关键词→标签映射
PATH_KEYWORD_TAGS = {
    # 场景
    "城市": ["城市", "都市", "街景", "建筑"],
    "自然": ["自然", "风景", "山", "海", "森林", "天空", "日落", "日出"],
    "人物": ["人物", "人像", "美女", "帅哥", "模特", "face", "portrait"],
    "动物": ["动物", "猫", "狗", "鸟", "宠物", "animal"],
    "美食": ["美食", "食物", "菜", "饮品", "food", "cooking"],
    # 风格
    "赛博朋克": ["赛博", "cyberpunk", "霓虹", "未来"],
    "国风": ["国风", "中式", "古风", "旗袍", "汉服", "chinese"],
    "日系": ["日系", "japan", "动漫", "anime"],
    "复古": ["复古", "vintage", "怀旧", "胶片"],
    "极简": ["极简", "minimal", "简约", "干净"],
    # 用途
    "背景": ["背景", "background", "bg", "wallpaper", "壁纸"],
    "封面": ["封面", "cover", "thumbnail"],
    "片头": ["片头", "intro", "opening"],
    "片尾": ["片尾", "outro", "ending"],
    "转场": ["转场", "transition", "过渡"],
    "特效": ["特效", "effect", "vfx", "粒子", "光效"],
    "贴纸": ["贴纸", "sticker", "emoji", "表情"],
    "字幕条": ["字幕条", "subtitle_bar", "text_bar", "标题栏"],
    "占位": ["占位", "placeholder", "测试", "test"],
    # 比例
    "竖屏": ["竖屏", "9:16", "portrait", "vertical"],
    "横屏": ["横屏", "16:9", "landscape", "horizontal"],
    "方形": ["方形", "1:1", "square"],
    # 情绪
    "治愈": ["治愈", "温暖", "温馨", "healing", "warm"],
    "震撼": ["震撼", "史诗", "epic", "震撼", "cinematic"],
    "搞笑": ["搞笑", "趣味", "funny", "meme"],
    "悬疑": ["悬疑", "惊悚", "thriller", "dark"],
}


class AssetIndex:
    """素材库逻辑索引"""

    def __init__(self, library_root: str, index_path: str = None):
        """
        Args:
            library_root: 素材库根目录
            index_path: 索引文件保存路径（默认在library_root下）
        """
        self.library_root = os.path.abspath(library_root)
        if index_path is None:
            index_path = os.path.join(self.library_root, ".asset_index.json")
        self.index_path = index_path
        self.assets: Dict[str, Dict] = {}  # id -> asset_info
        self._load()

    def _file_id(self, filepath: str) -> str:
        """生成文件唯一ID（基于路径+大小+修改时间）"""
        stat = os.stat(filepath)
        raw = f"{filepath}_{stat.st_size}_{stat.st_mtime}"
        return hashlib.md5(raw.encode()).hexdigest()[:12]

    def _classify(self, filepath: str) -> str:
        """根据扩展名分类"""
        ext = os.path.splitext(filepath)[1].lower()
        if ext in IMAGE_EXTS:
            return "image"
        elif ext in VIDEO_EXTS:
            return "video"
        elif ext in AUDIO_EXTS:
            return "audio"
        elif ext in SUBTITLE_EXTS:
            return "subtitle"
        else:
            return "other"

    def _extract_tags(self, filepath: str, asset_type: str) -> List[str]:
        """基于路径和文件名自动提取标签"""
        tags = set()
        tags.add(asset_type)

        # 文件名和路径（小写）
        full_path = filepath.lower().replace("\\", "/")
        filename = os.path.basename(filepath).lower()

        # 路径关键词匹配
        for tag, keywords in PATH_KEYWORD_TAGS.items():
            for kw in keywords:
                if kw.lower() in full_path:
                    tags.add(tag)
                    break

        # 文件名中的数字（可能是序号）
        import re
        if re.search(r'\d{2,}', filename):
            tags.add("序列")

        return sorted(tags)

    def _get_image_info(self, filepath: str) -> Dict:
        """获取图片元数据"""
        try:
            from PIL import Image
            with Image.open(filepath) as img:
                w, h = img.size
                mode = img.mode
            ratio = f"{w}:{h}"
            # 简化比例
            from math import gcd
            g = gcd(w, h)
            simple_ratio = f"{w//g}:{h//g}"
            return {
                "width": w, "height": h,
                "ratio": simple_ratio,
                "mode": mode,
                "orientation": "portrait" if h > w else ("landscape" if w > h else "square"),
            }
        except Exception:
            return {}

    def _get_video_info(self, filepath: str) -> Dict:
        """获取视频元数据（用ffprobe）"""
        try:
            import subprocess
            cmd = [FFPROBE, "-v", "quiet", "-print_format", "json",
                   "-show_format", "-show_streams", filepath]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            info = json.loads(result.stdout)

            video_stream = next((s for s in info.get("streams", [])
                                 if s.get("codec_type") == "video"), {})
            audio_stream = next((s for s in info.get("streams", [])
                                 if s.get("codec_type") == "audio"), None)

            w = int(video_stream.get("width", 0))
            h = int(video_stream.get("height", 0))
            duration = float(info.get("format", {}).get("duration", 0))
            fps_str = video_stream.get("r_frame_rate", "0/1")
            try:
                num, den = fps_str.split("/")
                fps = round(float(num) / float(den), 2) if float(den) > 0 else 0
            except Exception:
                fps = 0

            from math import gcd
            g = gcd(w, h) if w and h else 1
            simple_ratio = f"{w//g}:{h//g}" if w and h else "unknown"

            return {
                "width": w, "height": h,
                "ratio": simple_ratio,
                "duration_sec": round(duration, 2),
                "fps": fps,
                "codec": video_stream.get("codec_name", ""),
                "has_audio": audio_stream is not None,
                "orientation": "portrait" if h > w else ("landscape" if w > h else "square"),
            }
        except Exception:
            return {}

    def _get_audio_info(self, filepath: str) -> Dict:
        """获取音频元数据"""
        try:
            import subprocess
            cmd = [FFPROBE, "-v", "quiet", "-print_format", "json",
                   "-show_format", filepath]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            info = json.loads(result.stdout)
            fmt = info.get("format", {})
            return {
                "duration_sec": round(float(fmt.get("duration", 0)), 2),
                "bit_rate": int(fmt.get("bit_rate", 0)),
                "format": fmt.get("format_name", ""),
            }
        except Exception:
            return {}

    def scan(self, force: bool = False) -> int:
        """
        扫描素材库，建立/更新索引

        Args:
            force: 是否强制全量重新扫描（否则增量更新）

        Returns:
            新增/更新的素材数量
        """
        updated = 0
        existing_ids = set()

        for root, dirs, files in os.walk(self.library_root):
            # 跳过隐藏目录和索引文件
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for filename in files:
                if filename.startswith('.'):
                    continue
                filepath = os.path.join(root, filename)
                ext = os.path.splitext(filename)[1].lower()
                if ext not in IMAGE_EXTS | VIDEO_EXTS | AUDIO_EXTS | SUBTITLE_EXTS:
                    continue

                asset_id = self._file_id(filepath)
                existing_ids.add(asset_id)

                # 增量更新：如果已存在且未变化则跳过
                if not force and asset_id in self.assets:
                    continue

                asset_type = self._classify(filepath)
                stat = os.stat(filepath)

                asset = {
                    "id": asset_id,
                    "path": filepath,
                    "filename": filename,
                    "type": asset_type,
                    "size_bytes": stat.st_size,
                    "size_mb": round(stat.st_size / 1024 / 1024, 2),
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "tags": self._extract_tags(filepath, asset_type),
                }

                # 提取类型特定元数据
                if asset_type == "image":
                    asset.update(self._get_image_info(filepath))
                elif asset_type == "video":
                    asset.update(self._get_video_info(filepath))
                elif asset_type == "audio":
                    asset.update(self._get_audio_info(filepath))

                self.assets[asset_id] = asset
                updated += 1

        # 清理已删除的文件
        removed = [aid for aid in self.assets if aid not in existing_ids]
        for aid in removed:
            del self.assets[aid]

        self._save()
        return updated

    def search(self, asset_type: str = None, tags: List[str] = None,
               min_duration: float = None, max_duration: float = None,
               orientation: str = None, ratio: str = None,
               keyword: str = None, limit: int = 20) -> List[Dict]:
        """
        多维度检索素材

        Args:
            asset_type: 类型过滤 (image/video/audio/subtitle)
            tags: 标签过滤（匹配任意一个即可）
            min_duration/max_duration: 时长过滤（视频/音频）
            orientation: 方向过滤 (portrait/landscape/square)
            ratio: 比例过滤 (如 "9:16")
            keyword: 关键词模糊匹配（文件名/标签）
            limit: 返回数量上限

        Returns:
            匹配的素材列表（按相关度排序）
        """
        results = []

        for asset in self.assets.values():
            score = 0

            # 类型过滤
            if asset_type and asset["type"] != asset_type:
                continue

            # 标签过滤
            if tags:
                asset_tags = set(asset.get("tags", []))
                matched = set(tags) & asset_tags
                if not matched:
                    continue
                score += len(matched) * 10

            # 时长过滤
            dur = asset.get("duration_sec", 0)
            if min_duration and dur < min_duration:
                continue
            if max_duration and dur > max_duration:
                continue

            # 方向过滤
            if orientation and asset.get("orientation") != orientation:
                continue

            # 比例过滤
            if ratio and asset.get("ratio") != ratio:
                continue

            # 关键词模糊匹配
            if keyword:
                kw = keyword.lower()
                if kw in asset["filename"].lower():
                    score += 5
                if any(kw in t.lower() for t in asset.get("tags", [])):
                    score += 3

            asset["_score"] = score
            results.append(asset)

        # 按相关度排序
        results.sort(key=lambda x: x["_score"], reverse=True)
        return results[:limit]

    def get_best(self, asset_type: str = None, context: str = "",
                 style: str = "", limit: int = 5) -> List[Dict]:
        """
        智能推荐：根据上下文和风格自动匹配最合适的素材

        Args:
            asset_type: 素材类型
            context: 上下文描述（如"赛博朋克城市夜景"）
            style: 风格（如"cinematic"）
            limit: 返回数量

        Returns:
            推荐素材列表
        """
        # 从上下文提取关键词作为标签
        context_tags = []
        for tag, keywords in PATH_KEYWORD_TAGS.items():
            for kw in keywords:
                if kw.lower() in context.lower():
                    context_tags.append(tag)
                    break

        # 风格映射到标签
        style_tag_map = {
            "cinematic": ["震撼", "电影"],
            "vlog": ["治愈", "日常"],
            "tutorial": ["极简"],
            "thriller": ["悬疑"],
            "emotional": ["治愈"],
        }
        if style in style_tag_map:
            context_tags.extend(style_tag_map[style])

        if not context_tags:
            # 无匹配标签时返回最新的素材
            all_assets = list(self.assets.values())
            all_assets.sort(key=lambda x: x.get("modified", ""), reverse=True)
            if asset_type:
                all_assets = [a for a in all_assets if a["type"] == asset_type]
            return all_assets[:limit]

        return self.search(asset_type=asset_type, tags=context_tags, limit=limit)

    def stats(self) -> Dict:
        """获取素材库统计信息"""
        type_counts = {}
        tag_counts = {}
        total_size = 0

        for asset in self.assets.values():
            t = asset["type"]
            type_counts[t] = type_counts.get(t, 0) + 1
            total_size += asset.get("size_bytes", 0)
            for tag in asset.get("tags", []):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        # 标签TOP10
        top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]

        return {
            "total": len(self.assets),
            "by_type": type_counts,
            "total_size_mb": round(total_size / 1024 / 1024, 1),
            "top_tags": top_tags,
            "library_root": self.library_root,
        }

    def _save(self):
        """保存索引到文件"""
        data = {
            "version": "1.0",
            "created": datetime.now().isoformat(),
            "library_root": self.library_root,
            "assets": self.assets,
        }
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
        with open(self.index_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _load(self):
        """从文件加载索引"""
        if os.path.exists(self.index_path):
            try:
                with open(self.index_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.assets = data.get("assets", {})
            except Exception:
                self.assets = {}

    def add_custom_tags(self, asset_id: str, tags: List[str]):
        """为素材添加自定义标签"""
        if asset_id in self.assets:
            existing = set(self.assets[asset_id].get("tags", []))
            existing.update(tags)
            self.assets[asset_id]["tags"] = sorted(existing)
            self._save()

    def get_asset(self, asset_id: str) -> Optional[Dict]:
        """根据ID获取素材信息"""
        return self.assets.get(asset_id)


# ==================== 便捷函数 ====================

def build_index(library_root: str, force: bool = False) -> AssetIndex:
    """构建/更新素材库索引"""
    idx = AssetIndex(library_root)
    count = idx.scan(force=force)
    stats = idx.stats()
    print(f"✅ 索引完成: {count} 个素材新增/更新")
    print(f"   总计: {stats['total']} 个素材, {stats['total_size_mb']}MB")
    print(f"   分类: {stats['by_type']}")
    print(f"   TOP标签: {stats['top_tags'][:5]}")
    return idx


def search_assets(library_root: str, **kwargs) -> List[Dict]:
    """快速检索素材"""
    idx = AssetIndex(library_root)
    return idx.search(**kwargs)


if __name__ == "__main__":
    # 测试：扫描默认素材库
    default_lib = r"C:\Users\Administrator\Videos\剪映导出\Doubao_Jianying-editor\material"
    if os.path.exists(default_lib):
        idx = build_index(default_lib, force=True)
        print("\n检索测试:")
        results = idx.search(asset_type="image", tags=["占位"], limit=5)
        for r in results:
            print(f"  [{r['type']}] {r['filename']} ({r.get('ratio','?')}) tags={r['tags']}")
    else:
        print(f"素材库不存在: {default_lib}")
