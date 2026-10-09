# -*- coding: utf-8 -*-
"""
多音轨混音优化器 v1.0
Multi-Track Audio Mixer

核心能力：
1. 多音轨管理（人声/BGM/环境音/音效）
2. 音量平衡（各轨相对音量）
3. 闪避（Ducking）- 人声出现时BGM自动降低
4. 淡入淡出（各轨平滑过渡）
5. 音量标准化（loudnorm -16 LUFS）
6. 动态范围压缩（避免音量突变）
7. 频率均衡（人声频段与BGM避让）

基于ffmpeg音频滤镜实现：
- amix: 多轨混合
- sidechaincompress: 闪避压缩
- volume: 音量调节
- afade: 淡入淡出
- loudnorm: 响度标准化
- acompressor: 动态压缩
- highpass/lowpass: 频率滤波
"""
import os
import sys
import json
import subprocess
import tempfile
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
import logging
logger = logging.getLogger(__name__)


# ==================== 数据结构 ====================

@dataclass
class AudioTrack:
    """单条音轨"""
    name: str                    # 轨道名（voice/bgm/ambience/sfx）
    path: str                    # 音频文件路径
    track_type: str = "bgm"      # 类型：voice/bgm/ambience/sfx
    volume: float = 1.0          # 基础音量 0-2（1.0=原始音量）
    start_time: float = 0.0      # 起始时间（秒）
    duration: float = None       # 持续时间（秒，None=全长）
    fade_in: float = 0.0         # 淡入时长（秒）
    fade_out: float = 0.0        # 淡出时长（秒）
    ducking: bool = False        # 是否受人声闪避控制
    highpass: float = 0          # 高通滤波频率（Hz，0=不启用）
    lowpass: float = 0           # 低通滤波频率（Hz，0=不启用）
    compressor: bool = False     # 是否启用动态压缩

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "path": self.path,
            "type": self.track_type,
            "volume": self.volume,
            "start": self.start_time,
            "duration": self.duration,
            "fade_in": self.fade_in,
            "fade_out": self.fade_out,
            "ducking": self.ducking,
            "highpass": self.highpass,
            "lowpass": self.lowpass,
            "compressor": self.compressor,
        }


@dataclass
class MixConfig:
    """混音配置"""
    output_path: str                    # 输出路径
    sample_rate: int = 44100            # 采样率
    channels: int = 2                   # 声道数
    target_lufs: float = -16.0          # 目标响度（LUFS，短视频标准-16）
    ducking_threshold: float = -30.0    # 闪避阈值（dB）
    ducking_ratio: float = 4.0          # 闪避压缩比
    ducking_attack: float = 0.01        # 闪避启动时间（秒）
    ducking_release: float = 0.25       # 闪避释放时间（秒）
    ducking_reduction: float = -12.0    # 闪避最大衰减（dB）
    master_compressor: bool = True      # 母带压缩
    normalize: bool = True              # 响度标准化
    tracks: List[AudioTrack] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "output": self.output_path,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "target_lufs": self.target_lufs,
            "ducking": {
                "threshold": self.ducking_threshold,
                "ratio": self.ducking_ratio,
                "attack": self.ducking_attack,
                "release": self.ducking_release,
                "reduction": self.ducking_reduction,
            },
            "master_compressor": self.master_compressor,
            "normalize": self.normalize,
            "tracks": [t.to_dict() for t in self.tracks],
        }


# ==================== 预设配置 ====================

# 短视频常见混音预设
PRESETS = {
    "vlog": {
        "description": "Vlog/口播：人声清晰，BGM轻量衬托",
        "voice_volume": 1.2,
        "bgm_volume": 0.35,
        "ambience_volume": 0.2,
        "sfx_volume": 0.8,
        "ducking": True,
        "bgm_highpass": 200,
        "target_lufs": -16.0,
    },
    "music_video": {
        "description": "音乐/MV：BGM主导，人声点缀",
        "voice_volume": 0.8,
        "bgm_volume": 1.0,
        "ambience_volume": 0.15,
        "sfx_volume": 0.6,
        "ducking": False,
        "bgm_highpass": 0,
        "target_lufs": -14.0,
    },
    "drama": {
        "description": "剧情/影视：对白为主，氛围音衬托，音效强调",
        "voice_volume": 1.3,
        "bgm_volume": 0.4,
        "ambience_volume": 0.3,
        "sfx_volume": 0.9,
        "ducking": True,
        "bgm_highpass": 150,
        "target_lufs": -18.0,
    },
    "comedy": {
        "description": "搞笑/短剧：节奏明快，音效突出",
        "voice_volume": 1.2,
        "bgm_volume": 0.45,
        "ambience_volume": 0.15,
        "sfx_volume": 1.0,
        "ducking": True,
        "bgm_highpass": 200,
        "target_lufs": -15.0,
    },
    "cinematic": {
        "description": "电影级：宽动态范围，氛围感强",
        "voice_volume": 1.1,
        "bgm_volume": 0.5,
        "ambience_volume": 0.4,
        "sfx_volume": 0.85,
        "ducking": True,
        "bgm_highpass": 100,
        "target_lufs": -20.0,
    },
    "album_template": {
        "description": "相册模板：BGM主导，无旁白，音效点缀",
        "voice_volume": 0.0,
        "bgm_volume": 0.9,
        "ambience_volume": 0.2,
        "sfx_volume": 0.7,
        "ducking": False,
        "bgm_highpass": 0,
        "target_lufs": -16.0,
    },
}


# ==================== 混音器 ====================

class MultiTrackMixer:
    """多音轨混音器"""

    def __init__(self, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe"):
        self.ffmpeg = ffmpeg_path
        self.ffprobe = ffprobe_path

    def get_duration(self, audio_path: str) -> float:
        """获取音频时长"""
        cmd = [
            self.ffprobe, "-v", "quiet", "-print_format", "json",
            "-show_format", audio_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        data = json.loads(result.stdout)
        return float(data["format"]["duration"])

    def build_filter_graph(self, config: MixConfig) -> Tuple[str, List[str]]:
        """
        构建ffmpeg滤镜图

        Returns:
            (filter_complex, output_labels)
        """
        filters = []
        input_labels = []

        # 为每条音轨构建处理链
        voice_track = None
        ducking_tracks = []

        for i, track in enumerate(config.tracks):
            label = f"[{i}:a]"
            chain = []

            # 1. 延迟（起始时间）
            if track.start_time > 0:
                chain.append(f"adelay={int(track.start_time*1000)}|{int(track.start_time*1000)}")

            # 2. 高通滤波
            if track.highpass > 0:
                chain.append(f"highpass=f={track.highpass}")

            # 3. 低通滤波
            if track.lowpass > 0:
                chain.append(f"lowpass=f={track.lowpass}")

            # 4. 音量调节
            if track.volume != 1.0:
                chain.append(f"volume={track.volume}")

            # 5. 动态压缩
            if track.compressor:
                chain.append("acompressor=threshold=-20dB:ratio=3:attack=5:release=50")

            # 6. 淡入淡出（afade一次只能做一个方向，需要串联）
            if track.fade_in > 0:
                chain.append(f"afade=t=in:st=0:d={track.fade_in}")
            if track.fade_out > 0:
                dur = track.duration or self.get_duration(track.path)
                fade_start = max(0, dur - track.fade_out)
                chain.append(f"afade=t=out:st={fade_start}:d={track.fade_out}")

            # 构建链（注意：标签名不能以a/v/s/d/t开头，会被ffmpeg解析为流选择器）
            if chain:
                out_label = f"[p{i}]"
                filters.append(f"{label}{','.join(chain)}{out_label}")
                input_labels.append(out_label)
            else:
                input_labels.append(label)

            # 记录人声轨和闪避轨
            if track.track_type == "voice":
                voice_track = i
            if track.ducking:
                ducking_tracks.append(i)

        # 闪避处理（人声控制BGM等轨道）
        # 注意1：ffmpeg滤镜标签只能用一次，人声需要asplit分成两份
        # 注意2：sidechaincompress输出时长=侧链信号时长，需要apad延长侧链
        if voice_track is not None and ducking_tracks:
            voice_label = input_labels[voice_track]
            # 复制人声轨：一份用于侧链（apad延长），一份用于混合
            voice_sc_label = f"[vsc{voice_track}]"
            voice_mix_label = f"[vmix{voice_track}]"
            filters.append(f"{voice_label}asplit=2{voice_sc_label}{voice_mix_label}")
            input_labels[voice_track] = voice_mix_label

            # 侧链信号apad延长（确保覆盖整个BGM时长）
            voice_sc_padded = f"[vscp{voice_track}]"
            filters.append(f"{voice_sc_label}apad{voice_sc_padded}")

            for di in ducking_tracks:
                if di == voice_track:
                    continue
                bgm_label = input_labels[di]
                ducked_label = f"[dk{di}]"
                # sidechaincompress: 人声作为侧链信号，压缩BGM
                filters.append(
                    f"{bgm_label}{voice_sc_padded}sidechaincompress="
                    f"threshold={config.ducking_threshold}dB:"
                    f"ratio={config.ducking_ratio}:"
                    f"attack={config.ducking_attack*1000}:"
                    f"release={config.ducking_release*1000}"
                    f"{ducked_label}"
                )
                input_labels[di] = ducked_label

        # 混合所有轨道
        mix_inputs = "".join(input_labels)
        mix_label = "[mixed]"
        filters.append(
            f"{mix_inputs}amix=inputs={len(config.tracks)}:"
            f"duration=longest:dropout_transition=0{mix_label}"
        )

        # 母带处理
        master_chain = []

        # 母带压缩
        if config.master_compressor:
            master_chain.append(
                "acompressor=threshold=-18dB:ratio=2.5:attack=10:release=100:makeup=2dB"
            )

        # 响度标准化
        if config.normalize:
            master_chain.append(
                f"loudnorm=I={config.target_lufs}:TP=-1.5:LRA=11"
            )

        if master_chain:
            final_label = "[out]"
            filters.append(f"{mix_label}{','.join(master_chain)}{final_label}")
            final = final_label
        else:
            final = mix_label

        return ";".join(filters), final

    def mix(self, config: MixConfig) -> Dict:
        """
        执行混音

        Args:
            config: 混音配置

        Returns:
            {success, output_path, duration, command, error}
        """
        # 验证输入文件
        for track in config.tracks:
            if not os.path.exists(track.path):
                return {"success": False, "error": f"文件不存在: {track.path}"}

        # 构建输入参数
        input_args = []
        for track in config.tracks:
            input_args.extend(["-i", track.path])

        # 构建滤镜图
        filter_complex, final_label = self.build_filter_graph(config)

        # 构建输出命令
        cmd = [
            self.ffmpeg, "-y",
            *input_args,
            "-filter_complex", filter_complex,
            "-map", final_label,
            "-ar", str(config.sample_rate),
            "-ac", str(config.channels),
            "-c:a", "aac",
            "-b:a", "192k",
            config.output_path,
        ]

        # 执行
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=300
            )
            if result.returncode != 0:
                return {
                    "success": False,
                    "error": result.stderr[-500:],
                    "command": " ".join(cmd),
                }

            # 获取输出时长
            duration = self.get_duration(config.output_path)

            return {
                "success": True,
                "output_path": config.output_path,
                "duration": round(duration, 2),
                "command": " ".join(cmd),
                "track_count": len(config.tracks),
            }
        except Exception as e:
            return {"success": False, "error": str(e), "command": " ".join(cmd)}

    def mix_from_preset(self, tracks: List[AudioTrack], preset_name: str,
                        output_path: str) -> Dict:
        """
        使用预设混音

        Args:
            tracks: 音轨列表
            preset_name: 预设名（见PRESETS）
            output_path: 输出路径

        Returns:
            混音结果
        """
        preset = PRESETS.get(preset_name)
        if not preset:
            return {"success": False, "error": f"未知预设: {preset_name}"}

        # 应用预设到各轨
        for track in tracks:
            if track.track_type == "voice":
                track.volume = preset["voice_volume"]
                track.compressor = True
            elif track.track_type == "bgm":
                track.volume = preset["bgm_volume"]
                track.ducking = preset["ducking"]
                track.highpass = preset["bgm_highpass"]
            elif track.track_type == "ambience":
                track.volume = preset["ambience_volume"]
            elif track.track_type == "sfx":
                track.volume = preset["sfx_volume"]

        config = MixConfig(
            output_path=output_path,
            target_lufs=preset["target_lufs"],
            tracks=tracks,
        )

        return self.mix(config)

    def analyze_loudness(self, audio_path: str) -> Dict:
        """
        分析音频响度

        Returns:
            {integrated_lufs, true_peak, lra, threshold}
        """
        cmd = [
            self.ffmpeg, "-i", audio_path,
            "-af", "loudnorm=print_format=json",
            "-f", "null", "-"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        # 从stderr中提取JSON
        stderr = result.stderr
        json_start = stderr.rfind("{")
        json_end = stderr.rfind("}") + 1

        if json_start >= 0 and json_end > json_start:
            try:
                data = json.loads(stderr[json_start:json_end])
                return {
                    "integrated_lufs": float(data.get("input_i", 0)),
                    "true_peak": float(data.get("input_tp", 0)),
                    "lra": float(data.get("input_lra", 0)),
                    "threshold": float(data.get("input_thresh", 0)),
                    "target_offset": float(data.get("target_offset", 0)),
                }
            except (json.JSONDecodeError, ValueError):
                pass

        return {"error": "无法解析响度数据"}


# ==================== 剪映工程音量优化 ====================

class JianyingAudioOptimizer:
    """
    剪映工程音频优化器

    直接修改剪映draft_info.json中的音频片段音量，实现：
    - 各轨音量平衡
    - 人声/BGM/音效分层音量
    - 淡入淡出
    """

    def __init__(self, draft_path: str):
        self.draft_path = draft_path
        self.info_path = os.path.join(draft_path, "draft_info.json")
        self.content_path = os.path.join(draft_path, "draft_content.json")

    def load(self) -> Dict:
        """加载工程"""
        with open(self.info_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)
        return self.data

    def save(self):
        """保存工程"""
        with open(self.info_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def get_audio_tracks(self) -> List[Dict]:
        """获取所有音频轨道"""
        audio_tracks = []
        for track in self.data.get("tracks", []):
            if "audio" in track.get("name", "").lower() or track.get("type") == "audio":
                audio_tracks.append(track)
        return audio_tracks

    def set_track_volume(self, track_name: str, volume: float) -> int:
        """
        设置指定轨道所有片段的音量

        Args:
            track_name: 轨道名（如"BGM"、"AudioTrack"）
            volume: 音量（1.0=原始，0.5=减半，2.0=翻倍）

        Returns:
            修改的片段数量
        """
        count = 0
        for track in self.data.get("tracks", []):
            if track_name.lower() in track.get("name", "").lower():
                for seg in track.get("segments", []):
                    seg["volume"] = volume
                    count += 1
        return count

    def set_volume_by_type(self, voice_vol: float = 1.2, bgm_vol: float = 0.4,
                           sfx_vol: float = 0.8) -> Dict:
        """
        按类型设置音量（根据轨道名判断）

        Returns:
            {voice_count, bgm_count, sfx_count, other_count}
        """
        counts = {"voice": 0, "bgm": 0, "sfx": 0, "other": 0}

        for track in self.data.get("tracks", []):
            name = track.get("name", "").lower()
            if any(kw in name for kw in ["voice", "narration", "tts", "配音", "人声", "旁白"]):
                vol = voice_vol
                key = "voice"
            elif any(kw in name for kw in ["bgm", "music", "音乐", "配乐"]):
                vol = bgm_vol
                key = "bgm"
            elif any(kw in name for kw in ["sfx", "effect", "音效", "sound"]):
                vol = sfx_vol
                key = "sfx"
            else:
                vol = 1.0
                key = "other"

            for seg in track.get("segments", []):
                seg["volume"] = vol
                counts[key] += 1

        return counts

    def add_fade_to_track(self, track_name: str, fade_in: float = 0.3,
                          fade_out: float = 0.5) -> int:
        """
        为轨道片段添加淡入淡出

        Args:
            track_name: 轨道名
            fade_in: 淡入时长（秒）
            fade_out: 淡出时长（秒）

        Returns:
            修改的片段数量
        """
        count = 0
        for track in self.data.get("tracks", []):
            if track_name.lower() in track.get("name", "").lower():
                for seg in track.get("segments", []):
                    duration = seg.get("target_timerange", {}).get("duration", 0) / 1e6
                    if duration <= 0:
                        continue

                    fade = {
                        "fade_in": int(min(fade_in, duration * 0.3) * 1e6),
                        "fade_out": int(min(fade_out, duration * 0.3) * 1e6),
                    }
                    seg["fade"] = fade
                    count += 1
        return count

    def optimize(self, preset: str = "vlog") -> Dict:
        """
        一键优化剪映工程音频

        Args:
            preset: 预设名

        Returns:
            优化结果
        """
        p = PRESETS.get(preset, PRESETS["vlog"])

        result = {
            "preset": preset,
            "volume_changes": self.set_volume_by_type(
                voice_vol=p["voice_volume"],
                bgm_vol=p["bgm_volume"],
                sfx_vol=p["sfx_volume"],
            ),
            "fade_added": 0,
        }

        # 为BGM添加淡入淡出
        for track in self.data.get("tracks", []):
            name = track.get("name", "").lower()
            if any(kw in name for kw in ["bgm", "music", "音乐"]):
                result["fade_added"] += self.add_fade_to_track(
                    track.get("name", ""), fade_in=0.5, fade_out=1.0
                )

        self.save()
        return result


# ==================== CLI入口 ====================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    import argparse

    parser = argparse.ArgumentParser(description="多音轨混音优化器")
    subparsers = parser.add_subparsers(dest="command")

    # 混音命令
    mix_parser = subparsers.add_parser("mix", help="多音轨混音")
    mix_parser.add_argument("--voice", help="人声音频路径")
    mix_parser.add_argument("--bgm", help="BGM音频路径")
    mix_parser.add_argument("--ambience", help="环境音路径")
    mix_parser.add_argument("--sfx", nargs="*", help="音效路径（可多个）")
    mix_parser.add_argument("--preset", default="vlog", choices=list(PRESETS.keys()))
    mix_parser.add_argument("--output", required=True, help="输出路径")
    mix_parser.add_argument("--ffmpeg", default="ffmpeg")

    # 响度分析
    loud_parser = subparsers.add_parser("loudness", help="分析音频响度")
    loud_parser.add_argument("--input", required=True)
    loud_parser.add_argument("--ffmpeg", default="ffmpeg")

    # 列出预设
    subparsers.add_parser("presets", help="列出所有预设")

    args = parser.parse_args()

    if args.command == "presets":
        logger.info("可用预设：")
        for name, p in PRESETS.items():
            logger.info(f"  {name:15s} - {p['description']}")

    elif args.command == "loudness":
        mixer = MultiTrackMixer(ffmpeg_path=args.ffmpeg)
        result = mixer.analyze_loudness(args.input)
        logger.info(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.command == "mix":
        tracks = []
        if args.voice:
            tracks.append(AudioTrack(name="voice", path=args.voice, track_type="voice",
                                      fade_in=0.1, fade_out=0.2, compressor=True))
        if args.bgm:
            tracks.append(AudioTrack(name="bgm", path=args.bgm, track_type="bgm",
                                      fade_in=0.5, fade_out=1.0))
        if args.ambience:
            tracks.append(AudioTrack(name="ambience", path=args.ambience, track_type="ambience",
                                      fade_in=0.3, fade_out=0.5))
        if args.sfx:
            for i, sfx_path in enumerate(args.sfx):
                tracks.append(AudioTrack(name=f"sfx_{i}", path=sfx_path, track_type="sfx"))

        if not tracks:
            logger.info("错误：至少需要一条音轨")
            sys.exit(1)

        mixer = MultiTrackMixer(ffmpeg_path=args.ffmpeg)
        result = mixer.mix_from_preset(tracks, args.preset, args.output)

        if result["success"]:
            logger.info(f"✅ 混音完成: {result['output_path']}")
            logger.info(f"   时长: {result['duration']}秒")
            logger.info(f"   音轨数: {result['track_count']}")
        else:
            logger.info(f"❌ 混音失败: {result.get('error', '未知错误')}")
            sys.exit(1)
