#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P3-4 自动配乐系统 - BGM标签库管理
扫描本地BGM素材，建立标签库（情绪/节奏/风格/时长/版权）
"""
import os
import json
import subprocess
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import logging
logger = logging.getLogger(__name__)


FFPROBE = r"D:\Ai\ffmpeg-master-latest-win64-gpl\bin\ffprobe.exe"

# 默认BGM搜索目录
DEFAULT_BGM_DIRS = [
    r"D:\DobaoWork_Project\Ai_Video_Editor\material\bgm",
    r"D:\DobaoWork_Project\Ai_Video_Editor\material\audio",
]

# 情绪→BGM关键词映射（用于自动打标签）
EMOTION_KEYWORDS = {
    "happy": ["happy", "joy", "upbeat", "cheerful", "开心", "快乐", "欢快", "愉悦", "轻松"],
    "sad": ["sad", "melancholy", "emotional", "悲伤", "伤感", "忧郁", "抒情", "感人"],
    "energetic": ["energetic", "powerful", "epic", "intense", "激情", "热血", "震撼", "力量", "燃"],
    "calm": ["calm", "peaceful", "relaxing", "ambient", "平静", "舒缓", "放松", "治愈", "安静"],
    "romantic": ["romantic", "love", "sweet", "浪漫", "甜蜜", "爱情", "温馨"],
    "tense": ["tense", "suspense", "thriller", "紧张", "悬疑", "惊悚", "压迫"],
    "funny": ["funny", "comedy", "humor", "搞笑", "幽默", "滑稽", "俏皮"],
    "inspiring": ["inspiring", "motivational", "corporate", "激励", "励志", "正能量", "大气"],
}

# 风格→关键词映射
STYLE_KEYWORDS = {
    "cinematic": ["cinematic", "film", "movie", "电影", "影视", "大片"],
    "pop": ["pop", "流行", "时尚", "潮流"],
    "electronic": ["electronic", "edm", "synth", "电子", "电音", "合成器"],
    "acoustic": ["acoustic", "guitar", "piano", "原声", "吉他", "钢琴", "不插电"],
    "corporate": ["corporate", "business", "presentation", "商务", "企业", "演示"],
    "vlog": ["vlog", "lifestyle", "travel", "生活", "旅行", "日常"],
    "chinese": ["chinese", "guzheng", "erhu", "中国风", "古风", "古筝", "二胡", "民族"],
    "rock": ["rock", "metal", "punk", "摇滚", "金属", "朋克"],
}


@dataclass
class BGMTrack:
    """BGM曲目元数据"""
    file_path: str
    file_name: str
    duration: float  # 秒
    sample_rate: int
    channels: int
    bitrate: int
    emotions: List[str]  # 情绪标签
    styles: List[str]  # 风格标签
    tempo: str  # slow/medium/fast
    copyright: str  # 版权状态
    tags: List[str]  # 自定义标签
    bpm: Optional[float] = None  # BPM（如果可检测）

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class BGMLibrary:
    """BGM标签库"""

    def __init__(self, library_path: str = None):
        self.library_path = library_path or os.path.join(
            r"D:\DobaoWork_Project\Ai_Video_Editor", "knowledge", "bgm_library.json"
        )
        self.tracks: Dict[str, BGMTrack] = {}
        self._load()

    def _load(self):
        """加载标签库"""
        if os.path.exists(self.library_path):
            try:
                with open(self.library_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for path, track_data in data.get("tracks", {}).items():
                    self.tracks[path] = BGMTrack(**track_data)
            except Exception as e:
                logger.info(f"[WARN] 加载BGM库失败: {e}")

    def save(self):
        """保存标签库"""
        os.makedirs(os.path.dirname(self.library_path), exist_ok=True)
        data = {
            "version": "1.0",
            "total_tracks": len(self.tracks),
            "tracks": {k: v.to_dict() for k, v in self.tracks.items()}
        }
        with open(self.library_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"[OK] BGM库已保存: {len(self.tracks)}首 -> {self.library_path}")

    def scan_directory(self, directory: str, extensions: List[str] = None) -> int:
        """扫描目录中的音频文件并添加到库"""
        if extensions is None:
            extensions = ['.mp3', '.wav', '.m4a', '.flac', '.ogg', '.aac']

        count = 0
        if not os.path.isdir(directory):
            logger.info(f"[SKIP] 目录不存在: {directory}")
            return 0

        for root, dirs, files in os.walk(directory):
            for fname in files:
                ext = os.path.splitext(fname)[1].lower()
                if ext in extensions:
                    fpath = os.path.join(root, fname)
                    if fpath not in self.tracks:
                        track = self._probe_track(fpath)
                        if track:
                            self.tracks[fpath] = track
                            count += 1
        logger.info(f"[SCAN] {directory}: 新增{count}首")
        return count

    def _probe_track(self, file_path: str) -> Optional[BGMTrack]:
        """用ffprobe探测音频文件元数据"""
        try:
            result = subprocess.run(
                [FFPROBE, "-v", "quiet", "-print_format", "json",
                 "-show_format", "-show_streams", file_path],
                capture_output=True, text=True, timeout=10
            )
            info = json.loads(result.stdout)
            fmt = info.get("format", {})
            streams = info.get("streams", [])
            audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), {})

            duration = float(fmt.get("duration", 0))
            sample_rate = int(audio_stream.get("sample_rate", 44100))
            channels = int(audio_stream.get("channels", 2))
            bitrate = int(fmt.get("bit_rate", 0))

            # 基于文件名自动打标签
            fname = os.path.basename(file_path).lower()
            emotions = self._match_keywords(fname, EMOTION_KEYWORDS)
            styles = self._match_keywords(fname, STYLE_KEYWORDS)

            # 基于时长判断节奏
            if duration < 60:
                tempo = "short"
            elif duration < 180:
                tempo = "medium"
            else:
                tempo = "long"

            return BGMTrack(
                file_path=file_path,
                file_name=os.path.basename(file_path),
                duration=duration,
                sample_rate=sample_rate,
                channels=channels,
                bitrate=bitrate,
                emotions=emotions or ["neutral"],
                styles=styles or ["general"],
                tempo=tempo,
                copyright="unknown",
                tags=[],
            )
        except Exception as e:
            logger.info(f"[WARN] 探测失败 {file_path}: {e}")
            return None

    def _match_keywords(self, text: str, keyword_map: Dict[str, List[str]]) -> List[str]:
        """基于关键词匹配标签"""
        matched = []
        for tag, keywords in keyword_map.items():
            for kw in keywords:
                if kw.lower() in text:
                    matched.append(tag)
                    break
        return matched

    def search(self, emotion: str = None, style: str = None,
               min_duration: float = 0, max_duration: float = 9999,
               limit: int = 10) -> List[BGMTrack]:
        """按条件搜索BGM"""
        results = []
        for track in self.tracks.values():
            if emotion and emotion not in track.emotions:
                continue
            if style and style not in track.styles:
                continue
            if track.duration < min_duration or track.duration > max_duration:
                continue
            results.append(track)
            if len(results) >= limit:
                break
        return results

    def get_stats(self) -> Dict[str, Any]:
        """获取库统计信息"""
        emotion_count = {}
        style_count = {}
        for track in self.tracks.values():
            for e in track.emotions:
                emotion_count[e] = emotion_count.get(e, 0) + 1
            for s in track.styles:
                style_count[s] = style_count.get(s, 0) + 1
        return {
            "total": len(self.tracks),
            "emotions": emotion_count,
            "styles": style_count,
            "avg_duration": sum(t.duration for t in self.tracks.values()) / max(len(self.tracks), 1),
        }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="BGM标签库管理")
    parser.add_argument("action", choices=["scan", "list", "stats", "search"],
                        help="操作: scan扫描/list列出/stats统计/search搜索")
    parser.add_argument("--dir", help="扫描目录（scan时使用）")
    parser.add_argument("--emotion", help="情绪过滤（search时使用）")
    parser.add_argument("--style", help="风格过滤（search时使用）")
    args = parser.parse_args()

    lib = BGMLibrary()

    if args.action == "scan":
        dirs = [args.dir] if args.dir else DEFAULT_BGM_DIRS
        total = 0
        for d in dirs:
            total += lib.scan_directory(d)
        lib.save()
        logger.info(f"\n扫描完成: 共{total}首新增, 库总计{len(lib.tracks)}首")

    elif args.action == "list":
        for path, track in lib.tracks.items():
            logger.info(f"  [{track.emotions}] {track.file_name} ({track.duration:.1f}s)")

    elif args.action == "stats":
        stats = lib.get_stats()
        logger.info(f"总计: {stats['total']}首")
        logger.info(f"平均时长: {stats['avg_duration']:.1f}秒")
        logger.info(f"情绪分布: {stats['emotions']}")
        logger.info(f"风格分布: {stats['styles']}")

    elif args.action == "search":
        results = lib.search(emotion=args.emotion, style=args.style)
        logger.info(f"找到{len(results)}首:")
        for track in results:
            logger.info(f"  {track.file_name} ({track.duration:.1f}s) emotions={track.emotions} styles={track.styles}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
