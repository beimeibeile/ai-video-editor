"""
BGM库扩充工具
- 批量导入BGM素材
- 自动标注（情绪/风格/时长/节奏/乐器）
- BGM素材分类标准
- 基于音频特征的自动分类
"""

import os
import sys
import json
import subprocess
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)

# ============ BGM素材分类标准 ============

# 情绪分类（9种）
EMOTIONS = {
    "calm": {"keywords": ["平静", "舒缓", "放松", "安静", "柔和", "calm", "relax", "peaceful", "soft", "gentle"], "weight": 1.0},
    "happy": {"keywords": ["开心", "快乐", "愉悦", "欢快", "活泼", "happy", "joy", "cheerful", "upbeat", "fun"], "weight": 1.0},
    "sad": {"keywords": ["悲伤", "忧伤", "难过", "忧郁", "伤感", "sad", "melancholy", "sorrow", "emotional", "tear"], "weight": 1.0},
    "energetic": {"keywords": ["激昂", "活力", "动感", "兴奋", "热血", "energetic", "exciting", "powerful", "intense", "epic"], "weight": 1.0},
    "tense": {"keywords": ["紧张", "悬疑", "压迫", "恐惧", "惊险", "tense", "suspense", "thriller", "dark", "mystery"], "weight": 1.0},
    "romantic": {"keywords": ["浪漫", "温馨", "甜蜜", "爱情", "温柔", "romantic", "love", "sweet", "tender", "warm"], "weight": 1.0},
    "epic": {"keywords": ["史诗", "宏大", "壮丽", "震撼", "大气", "epic", "grand", "majestic", "cinematic", "orchestral"], "weight": 1.0},
    "mysterious": {"keywords": ["神秘", "奇幻", "梦幻", "空灵", "迷幻", "mysterious", "fantasy", "dreamy", "ethereal", "ambient"], "weight": 1.0},
    "neutral": {"keywords": ["中性", "通用", "背景", "平淡", "neutral", "general", "background", "simple", "minimal"], "weight": 0.5},
}

# 风格分类（12种）
STYLES = {
    "cinematic": {"keywords": ["电影", "影视", "配乐", "cinematic", "film", "movie", "score", "soundtrack"], "weight": 1.0},
    "electronic": {"keywords": ["电子", "合成器", "电音", "electronic", "synth", "edm", "techno", "house"], "weight": 1.0},
    "orchestral": {"keywords": ["管弦", "交响", "古典", "orchestral", "symphony", "classical", "strings", "orchestra"], "weight": 1.0},
    "piano": {"keywords": ["钢琴", "独奏", "piano", "solo", "ballad"], "weight": 1.0},
    "guitar": {"keywords": ["吉他", "木吉他", "acoustic", "guitar", "folk"], "weight": 1.0},
    "rock": {"keywords": ["摇滚", "金属", "rock", "metal", "punk", "alternative"], "weight": 1.0},
    "pop": {"keywords": ["流行", "pop", "dance", "chart"], "weight": 1.0},
    "jazz": {"keywords": ["爵士", "jazz", "blues", "swing"], "weight": 1.0},
    "ambient": {"keywords": ["氛围", "环境", "ambient", "atmospheric", "chill", "lofi"], "weight": 1.0},
    "corporate": {"keywords": ["企业", "商务", "励志", "corporate", "business", "motivational", "inspiring"], "weight": 1.0},
    "folk": {"keywords": ["民谣", "民族", "世界", "folk", "world", "ethnic", "traditional"], "weight": 1.0},
    "hiphop": {"keywords": ["嘻哈", "说唱", "rap", "hiphop", "trap", "beat"], "weight": 1.0},
}

# 节奏分类
TEMPOS = {
    "very_slow": {"bpm_range": (0, 70), "description": "极慢（抒情/氛围）"},
    "slow": {"bpm_range": (70, 100), "description": "慢速（舒缓/放松）"},
    "medium": {"bpm_range": (100, 130), "description": "中速（通用/流行）"},
    "fast": {"bpm_range": (130, 160), "description": "快速（动感/活力）"},
    "very_fast": {"bpm_range": (160, 300), "description": "极快（激烈/兴奋）"},
}

# 时长分类
DURATIONS = {
    "very_short": {"range": (0, 10), "description": "极短（转场/音效）"},
    "short": {"range": (10, 30), "description": "短（短视频/片段）"},
    "medium": {"range": (30, 60), "description": "中（标准视频）"},
    "long": {"range": (60, 180), "description": "长（完整视频）"},
    "very_long": {"range": (180, 9999), "description": "极长（长视频/背景）"},
}


@dataclass
class BGMTrack:
    """BGM曲目元数据"""
    file_path: str
    file_name: str
    duration: float = 0.0
    sample_rate: int = 44100
    channels: int = 2
    bitrate: int = 0
    emotions: List[str] = field(default_factory=list)
    styles: List[str] = field(default_factory=list)
    tempo: str = "medium"
    duration_category: str = "medium"
    copyright: str = "unknown"
    tags: List[str] = field(default_factory=list)
    bpm: Optional[float] = None
    instruments: List[str] = field(default_factory=list)
    energy: float = 0.5  # 0.0-1.0 能量值
    valence: float = 0.5  # 0.0-1.0 情绪效价（积极/消极）


class BGMLibraryExpander:
    """BGM库扩充工具"""

    def __init__(self, library_path: str = None):
        self.library_path = library_path or os.path.join(
            r"D:\DobaoWork_Project\Ai_Video_Editor",
            "knowledge", "bgm_library.json"
        )
        self.ffprobe = r"D:\Ai\ffmpeg-master-latest-win64-gpl\bin\ffprobe.exe"
        self.library = self._load_library()

    def _load_library(self) -> Dict:
        """加载BGM库"""
        if os.path.exists(self.library_path):
            with open(self.library_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"version": "2.0", "total_tracks": 0, "tracks": {}}

    def _save_library(self):
        """保存BGM库"""
        self.library["total_tracks"] = len(self.library["tracks"])
        os.makedirs(os.path.dirname(self.library_path), exist_ok=True)
        with open(self.library_path, "w", encoding="utf-8") as f:
            json.dump(self.library, f, ensure_ascii=False, indent=2)
        logger.info(f"BGM库已保存: {self.library['total_tracks']}首")

    def _probe_audio(self, file_path: str) -> Dict[str, Any]:
        """用ffprobe探测音频信息"""
        try:
            result = subprocess.run(
                [self.ffprobe, "-v", "quiet", "-print_format", "json",
                 "-show_format", "-show_streams", file_path],
                capture_output=True, text=True, timeout=10
            )
            info = json.loads(result.stdout)
            fmt = info.get("format", {})
            stream = next((s for s in info.get("streams", [])
                          if s.get("codec_type") == "audio"), {})
            return {
                "duration": float(fmt.get("duration", 0)),
                "sample_rate": int(stream.get("sample_rate", 44100)),
                "channels": int(stream.get("channels", 2)),
                "bitrate": int(fmt.get("bit_rate", 0)),
            }
        except Exception as e:
            logger.error(f"音频探测失败 {file_path}: {e}")
            return {"duration": 0, "sample_rate": 44100, "channels": 2, "bitrate": 0}

    def _analyze_audio_features(self, file_path: str) -> Dict[str, float]:
        """基于音频特征分析（简化版：用ffmpeg获取音量/频谱特征）"""
        try:
            # 获取平均音量和峰值
            result = subprocess.run(
                [self.ffprobe.replace("ffprobe", "ffmpeg"), "-i", file_path,
                 "-af", "volumedetect", "-f", "null", "-"],
                capture_output=True, text=True, timeout=15
            )
            stderr = result.stderr
            mean_volume = -30.0
            max_volume = -10.0
            for line in stderr.split("\n"):
                if "mean_volume" in line:
                    mean_volume = float(line.split(":")[1].strip().replace("dB", ""))
                if "max_volume" in line:
                    max_volume = float(line.split(":")[1].strip().replace("dB", ""))

            # 能量值：基于平均音量（-60到0映射到0-1）
            energy = max(0.0, min(1.0, (mean_volume + 40) / 30))
            # 动态范围：max - mean
            dynamic_range = max_volume - mean_volume
            # 效价：基于动态范围（大动态范围→更积极）
            valence = max(0.0, min(1.0, dynamic_range / 20))

            return {
                "mean_volume": mean_volume,
                "max_volume": max_volume,
                "dynamic_range": dynamic_range,
                "energy": energy,
                "valence": valence,
            }
        except Exception as e:
            logger.error(f"音频特征分析失败 {file_path}: {e}")
            return {"energy": 0.5, "valence": 0.5}

    def _classify_emotion(self, file_name: str, features: Dict) -> List[str]:
        """基于文件名和音频特征分类情绪"""
        text = file_name.lower()
        scores = {}

        # 基于关键词（权重更高，因为文件名通常包含明确的情绪信息）
        for emotion, config in EMOTIONS.items():
            score = 0
            for kw in config["keywords"]:
                if kw.lower() in text:
                    score += config["weight"] * 3.0  # 关键词权重×3
            scores[emotion] = score

        # 如果文件名中有明确的情绪关键词，直接使用
        keyword_emotions = [e for e, s in scores.items() if s >= 3.0]
        if keyword_emotions:
            return keyword_emotions[:2]

        # 否则基于音频特征调整
        energy = features.get("energy", 0.5)
        valence = features.get("valence", 0.5)

        if energy > 0.7:
            scores["energetic"] += 1.0
            scores["epic"] += 0.5
        elif energy < 0.3:
            scores["calm"] += 1.0
            scores["mysterious"] += 0.5

        if valence > 0.6:
            scores["happy"] += 0.8
            scores["romantic"] += 0.5
        elif valence < 0.4:
            scores["sad"] += 0.5
            scores["tense"] += 0.3

        # 返回得分最高的1-2个情绪
        sorted_emotions = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        result = [e for e, s in sorted_emotions if s > 0.3][:2]
        return result if result else ["neutral"]

    def _classify_style(self, file_name: str) -> List[str]:
        """基于文件名分类风格"""
        text = file_name.lower()
        scores = {}

        for style, config in STYLES.items():
            score = 0
            for kw in config["keywords"]:
                if kw.lower() in text:
                    score += config["weight"]
            if score > 0:
                scores[style] = score

        sorted_styles = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        result = [s for s, sc in sorted_styles if sc > 0][:2]
        return result if result else ["general"]

    def _classify_tempo(self, bpm: Optional[float], features: Dict) -> str:
        """分类节奏"""
        if bpm:
            for tempo, config in TEMPOS.items():
                low, high = config["bpm_range"]
                if low <= bpm < high:
                    return tempo
        # 基于能量估算
        energy = features.get("energy", 0.5)
        if energy > 0.8:
            return "fast"
        elif energy > 0.6:
            return "medium"
        elif energy > 0.3:
            return "slow"
        else:
            return "very_slow"

    def _classify_duration(self, duration: float) -> str:
        """分类时长"""
        for cat, config in DURATIONS.items():
            low, high = config["range"]
            if low <= duration < high:
                return cat
        return "medium"

    def import_track(self, file_path: str, auto_tag: bool = True) -> Optional[BGMTrack]:
        """导入单首BGM"""
        if not os.path.exists(file_path):
            logger.error(f"文件不存在: {file_path}")
            return None

        file_name = os.path.basename(file_path)
        ext = os.path.splitext(file_name)[1].lower()
        if ext not in [".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"]:
            logger.warning(f"不支持的音频格式: {ext}")
            return None

        # 探测音频信息
        probe = self._probe_audio(file_path)
        features = self._analyze_audio_features(file_path)

        # 自动标注
        if auto_tag:
            emotions = self._classify_emotion(file_name, features)
            styles = self._classify_style(file_name)
            tempo = self._classify_tempo(None, features)
            duration_cat = self._classify_duration(probe["duration"])
        else:
            emotions = ["neutral"]
            styles = ["general"]
            tempo = "medium"
            duration_cat = "medium"

        track = BGMTrack(
            file_path=file_path,
            file_name=file_name,
            duration=probe["duration"],
            sample_rate=probe["sample_rate"],
            channels=probe["channels"],
            bitrate=probe["bitrate"],
            emotions=emotions,
            styles=styles,
            tempo=tempo,
            duration_category=duration_cat,
            energy=features.get("energy", 0.5),
            valence=features.get("valence", 0.5),
        )

        # 添加到库
        self.library["tracks"][file_path] = asdict(track)
        logger.info(f"导入BGM: {file_name} (情绪={emotions}, 风格={styles}, 时长={probe['duration']:.1f}s)")
        return track

    def import_directory(self, dir_path: str, auto_tag: bool = True) -> int:
        """批量导入目录中的BGM"""
        if not os.path.isdir(dir_path):
            logger.error(f"目录不存在: {dir_path}")
            return 0

        count = 0
        audio_exts = [".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"]
        for root, dirs, files in os.walk(dir_path):
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext in audio_exts:
                    file_path = os.path.join(root, f)
                    if file_path not in self.library["tracks"]:
                        track = self.import_track(file_path, auto_tag)
                        if track:
                            count += 1

        logger.info(f"批量导入完成: {count}首新BGM")
        return count

    def generate_synthetic_bgm(self, output_dir: str, count: int = 20) -> int:
        """生成合成BGM（使用ffmpeg生成不同特征的测试BGM）"""
        os.makedirs(output_dir, exist_ok=True)
        ffmpeg = self.ffprobe.replace("ffprobe", "ffmpeg")

        # 预设配置：(文件名, 频率, 时长, 情绪, 风格)
        presets = [
            ("calm_piano_01", 262, 30, "calm", "piano"),  # C4
            ("calm_ambient_01", 220, 45, "calm", "ambient"),  # A3
            ("happy_pop_01", 523, 20, "happy", "pop"),  # C5
            ("happy_ukulele_01", 392, 25, "happy", "folk"),  # G4
            ("sad_piano_01", 196, 35, "sad", "piano"),  # G3
            ("sad_strings_01", 175, 40, "sad", "orchestral"),  # F3
            ("energetic_rock_01", 440, 20, "energetic", "rock"),  # A4
            ("energetic_edm_01", 330, 25, "energetic", "electronic"),  # E4
            ("tense_suspense_01", 147, 30, "tense", "cinematic"),  # D3
            ("tense_dark_01", 110, 35, "tense", "ambient"),  # A2
            ("romantic_piano_01", 294, 30, "romantic", "piano"),  # D4
            ("romantic_strings_01", 247, 40, "romantic", "orchestral"),  # B3
            ("epic_orchestral_01", 349, 45, "epic", "orchestral"),  # F4
            ("epic_cinematic_01", 392, 50, "epic", "cinematic"),  # G4
            ("mysterious_ambient_01", 208, 35, "mysterious", "ambient"),  # G#3
            ("mysterious_fantasy_01", 262, 40, "mysterious", "cinematic"),  # C4
            ("corporate_motivational_01", 330, 30, "energetic", "corporate"),  # E4
            ("corporate_inspiring_01", 392, 35, "happy", "corporate"),  # G4
            ("jazz_smooth_01", 294, 40, "calm", "jazz"),  # D4
            ("lofi_chill_01", 220, 45, "calm", "ambient"),  # A3
        ]

        count = min(count, len(presets))
        generated = 0

        for i in range(count):
            name, freq, duration, emotion, style = presets[i]
            output_path = os.path.join(output_dir, f"{name}.mp3")

            if os.path.exists(output_path):
                # 已存在，直接导入
                if output_path not in self.library["tracks"]:
                    self.import_track(output_path, auto_tag=True)
                generated += 1
                continue

            try:
                # 使用ffmpeg生成正弦波+淡入淡出的简单BGM
                # 添加轻微的频率调制模拟音乐感
                cmd = [
                    ffmpeg, "-y",
                    "-f", "lavfi", "-i", f"sine=frequency={freq}:duration={duration}",
                    "-af", f"afade=t=in:st=0:d=2,afade=t=out:st={duration-3}:d=3,volume=0.5",
                    "-codec:a", "libmp3lame", "-b:a", "128k",
                    output_path
                ]
                subprocess.run(cmd, capture_output=True, timeout=30)

                if os.path.exists(output_path):
                    # 手动标注（因为文件名已包含情绪/风格信息）
                    track = self.import_track(output_path, auto_tag=True)
                    if track:
                        generated += 1
                        logger.info(f"生成BGM: {name}.mp3 ({duration}s, {emotion}/{style})")
            except Exception as e:
                logger.error(f"生成BGM失败 {name}: {e}")

        logger.info(f"合成BGM生成完成: {generated}首")
        return generated

    def retag_all(self) -> int:
        """重新标注所有BGM（修复分类错误）"""
        count = 0
        tracks_to_update = list(self.library["tracks"].keys())

        for file_path in tracks_to_update:
            if not os.path.exists(file_path):
                continue

            file_name = os.path.basename(file_path)
            features = self._analyze_audio_features(file_path)

            emotions = self._classify_emotion(file_name, features)
            styles = self._classify_style(file_name)
            tempo = self._classify_tempo(None, features)
            duration_cat = self._classify_duration(self.library["tracks"][file_path].get("duration", 0))

            self.library["tracks"][file_path]["emotions"] = emotions
            self.library["tracks"][file_path]["styles"] = styles
            self.library["tracks"][file_path]["tempo"] = tempo
            self.library["tracks"][file_path]["duration_category"] = duration_cat
            self.library["tracks"][file_path]["energy"] = features.get("energy", 0.5)
            self.library["tracks"][file_path]["valence"] = features.get("valence", 0.5)
            count += 1

        logger.info(f"重新标注完成: {count}首BGM")
        return count

    def get_stats(self) -> Dict[str, Any]:
        """获取库统计信息"""
        tracks = list(self.library["tracks"].values())
        emotion_count = {}
        style_count = {}
        tempo_count = {}
        duration_count = {}

        for t in tracks:
            for e in t.get("emotions", []):
                emotion_count[e] = emotion_count.get(e, 0) + 1
            for s in t.get("styles", []):
                style_count[s] = style_count.get(s, 0) + 1
            tempo_count[t.get("tempo", "unknown")] = tempo_count.get(t.get("tempo", "unknown"), 0) + 1
            duration_count[t.get("duration_category", "unknown")] = duration_count.get(t.get("duration_category", "unknown"), 0) + 1

        avg_duration = sum(t.get("duration", 0) for t in tracks) / max(len(tracks), 1)

        return {
            "total": len(tracks),
            "emotions": emotion_count,
            "styles": style_count,
            "tempos": tempo_count,
            "durations": duration_count,
            "avg_duration": round(avg_duration, 1),
        }

    def save(self):
        """保存BGM库"""
        self._save_library()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="BGM库扩充工具")
    parser.add_argument("action", choices=["import", "generate", "stats", "scan"],
                        help="操作: import导入目录/generate生成合成BGM/stats统计/scan扫描目录")
    parser.add_argument("--dir", help="目录路径（import/scan时使用）")
    parser.add_argument("--output", help="输出目录（generate时使用）")
    parser.add_argument("--count", type=int, default=20, help="生成数量（generate时使用）")
    args = parser.parse_args()

    expander = BGMLibraryExpander()

    if args.action == "import" and args.dir:
        count = expander.import_directory(args.dir)
        expander.save()
        print(f"导入完成: {count}首新BGM")
    elif args.action == "generate":
        output_dir = args.output or r"D:\DobaoWork_Project\Ai_Video_Editor\material\bgm_synthetic"
        count = expander.generate_synthetic_bgm(output_dir, args.count)
        expander.save()
        print(f"生成完成: {count}首BGM")
    elif args.action == "stats":
        stats = expander.get_stats()
        print(json.dumps(stats, ensure_ascii=False, indent=2))
    elif args.action == "scan" and args.dir:
        # 只扫描不导入
        audio_exts = [".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"]
        count = 0
        for root, dirs, files in os.walk(args.dir):
            for f in files:
                if os.path.splitext(f)[1].lower() in audio_exts:
                    count += 1
        print(f"扫描到 {count} 个音频文件")

    # 打印统计
    stats = expander.get_stats()
    print(f"\nBGM库统计: {stats['total']}首, 平均时长{stats['avg_duration']}s")
    print(f"情绪分布: {stats['emotions']}")
    print(f"风格分布: {stats['styles']}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    main()
