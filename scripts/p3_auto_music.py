#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P3-4 自动配乐系统 - 配乐选择器+音频混合器
基于情绪/场景/风格自动选择BGM，处理时长适配、淡入淡出、音量混合
"""
import os
import json
import subprocess
import tempfile
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

from p3_bgm_library import BGMLibrary, BGMTrack


FFMPEG = r"D:\Ai\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe"
FFPROBE = r"D:\Ai\ffmpeg-master-latest-win64-gpl\bin\ffprobe.exe"


@dataclass
class AudioTrackConfig:
    """音频轨道配置"""
    track_type: str  # bgm / narration / sfx
    file_path: str
    start: float  # 开始时间（秒）
    duration: float  # 持续时间（秒）
    volume: float  # 音量 0-1
    fade_in: float = 0  # 淡入时长（秒）
    fade_out: float = 0  # 淡出时长（秒）
    loop: bool = False  # 是否循环


class MusicSelector:
    """BGM选择器"""

    def __init__(self, library: BGMLibrary = None):
        self.library = library or BGMLibrary()

    def select(self, emotion: str = "neutral", style: str = "general",
               target_duration: float = 60.0,
               exclude_paths: List[str] = None) -> Optional[BGMTrack]:
        """
        选择最合适的BGM

        策略：
        1. 优先选择时长≥目标时长的（避免循环）
        2. 其次选择时长接近目标时长50%以上的（可循环）
        3. 情绪+风格匹配优先
        """
        exclude_paths = exclude_paths or []

        # 第一轮：情绪+风格匹配 + 时长足够
        candidates = self.library.search(
            emotion=emotion, style=style,
            min_duration=target_duration * 0.8,
            limit=20
        )
        candidates = [c for c in candidates if c.file_path not in exclude_paths]
        if candidates:
            # 选择时长最接近目标的
            candidates.sort(key=lambda t: abs(t.duration - target_duration))
            return candidates[0]

        # 第二轮：仅情绪匹配
        candidates = self.library.search(
            emotion=emotion,
            min_duration=target_duration * 0.3,
            limit=20
        )
        candidates = [c for c in candidates if c.file_path not in exclude_paths]
        if candidates:
            candidates.sort(key=lambda t: abs(t.duration - target_duration))
            return candidates[0]

        # 第三轮：任意BGM
        candidates = self.library.search(limit=20)
        candidates = [c for c in candidates if c.file_path not in exclude_paths]
        if candidates:
            return candidates[0]

        return None

    def select_for_sequence(self, emotions: List[Dict[str, Any]],
                             style: str = "general") -> List[AudioTrackConfig]:
        """
        为整个视频序列选择BGM

        Args:
            emotions: 情绪时间线 [{start, end, emotion, intensity}]
            style: 整体风格

        Returns:
            音频轨道配置列表
        """
        configs = []
        used_tracks = []

        for seg in emotions:
            seg_duration = seg["end"] - seg["start"]
            emotion = seg.get("emotion", "neutral")

            track = self.select(
                emotion=emotion, style=style,
                target_duration=seg_duration,
                exclude_paths=used_tracks
            )
            if track:
                used_tracks.append(track.file_path)
                needs_loop = track.duration < seg_duration

                configs.append(AudioTrackConfig(
                    track_type="bgm",
                    file_path=track.file_path,
                    start=seg["start"],
                    duration=seg_duration,
                    volume=0.3,  # BGM默认音量30%
                    fade_in=1.0,
                    fade_out=2.0,
                    loop=needs_loop,
                ))

        return configs


class AudioMixer:
    """音频混合器 - 生成ffmpeg混合命令"""

    def __init__(self, output_dir: str = None):
        self.output_dir = output_dir or tempfile.gettempdir()

    def mix(self, configs: List[AudioTrackConfig],
            output_path: str, total_duration: float) -> bool:
        """
        混合多个音频轨道

        Args:
            configs: 音频轨道配置列表
            output_path: 输出文件路径
            total_duration: 总时长（秒）

        Returns:
            是否成功
        """
        if not configs:
            return False

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # 构建ffmpeg命令
        cmd = [FFMPEG, "-y"]

        # 输入文件
        input_indices = []
        for i, config in enumerate(configs):
            cmd.extend(["-i", config.file_path])
            input_indices.append(i)

        # 构建filter_complex
        filters = []
        mix_inputs = []

        for i, config in enumerate(configs):
            label = f"a{i}"
            parts = []

            # 循环处理
            if config.loop:
                parts.append(f"aloop=loop=-1:size=2e9")

            # 裁剪到目标时长
            parts.append(f"atrim=0:{config.duration}")
            parts.append("asetpts=PTS-STARTPTS")

            # 延迟到开始时间
            if config.start > 0:
                parts.append(f"adelay={int(config.start * 1000)}|{int(config.start * 1000)}")

            # 音量
            parts.append(f"volume={config.volume}")

            # 淡入淡出（使用afade音频滤镜，fade是视频滤镜）
            fade_parts = []
            if config.fade_in > 0:
                fade_parts.append(f"afade=t=in:st=0:d={config.fade_in}")
            if config.fade_out > 0:
                fade_start = max(0, config.duration - config.fade_out)
                fade_parts.append(f"afade=t=out:st={fade_start}:d={config.fade_out}")
            parts.extend(fade_parts)

            filter_str = f"[{i}:a]{','.join(parts)}[{label}]"
            filters.append(filter_str)
            mix_inputs.append(f"[{label}]")

        # 混合
        if len(mix_inputs) > 1:
            filters.append(f"{''.join(mix_inputs)}amix=inputs={len(mix_inputs)}:duration=longest[out]")
        else:
            filters.append(f"{mix_inputs[0]}anull[out]")

        # 根据输出文件扩展名选择编码器
        ext = os.path.splitext(output_path)[1].lower()
        if ext == ".mp3":
            audio_codec = "libmp3lame"
            audio_bitrate = "192k"
        elif ext in (".m4a", ".aac"):
            audio_codec = "aac"
            audio_bitrate = "192k"
        elif ext == ".wav":
            audio_codec = "pcm_s16le"
            audio_bitrate = None
        else:
            audio_codec = "aac"
            audio_bitrate = "192k"

        cmd.extend([
            "-filter_complex", ";".join(filters),
            "-map", "[out]",
            "-t", str(total_duration),
            "-c:a", audio_codec,
        ])
        if audio_bitrate:
            cmd.extend(["-b:a", audio_bitrate])
        cmd.append(output_path)

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode == 0 and os.path.exists(output_path):
                return True
            else:
                logger.error(f"[ERROR] ffmpeg混合失败: {result.stderr[-500:]}")
                return False
        except Exception as e:
            logger.error(f"音频混合异常: {e}")
            return False


class AutoMusicSystem:
    """自动配乐系统 - 整合选择器和混合器"""

    def __init__(self, bgm_dir: str = None):
        self.library = BGMLibrary()
        if bgm_dir:
            self.library.scan_directory(bgm_dir)
            self.library.save()
        self.selector = MusicSelector(self.library)
        self.mixer = AudioMixer()

    def generate_music_plan(self, emotions: List[Dict[str, Any]],
                             style: str = "general",
                             narration_timeline: List[Dict[str, Any]] = None,
                             sfx_events: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        生成完整配乐方案

        Args:
            emotions: 情绪时间线 [{start, end, emotion, intensity}]
            style: 整体风格
            narration_timeline: 旁白时间线 [{start, end, file_path}]
            sfx_events: 音效事件 [{start, type, file_path}]

        Returns:
            完整配乐方案
        """
        all_configs = []

        # 1. BGM
        bgm_configs = self.selector.select_for_sequence(emotions, style)
        all_configs.extend(bgm_configs)

        # 2. 旁白
        if narration_timeline:
            for nar in narration_timeline:
                all_configs.append(AudioTrackConfig(
                    track_type="narration",
                    file_path=nar["file_path"],
                    start=nar["start"],
                    duration=nar["end"] - nar["start"],
                    volume=1.0,  # 旁白满音量
                    fade_in=0.1,
                    fade_out=0.1,
                ))

        # 3. 音效
        if sfx_events:
            for sfx in sfx_events:
                all_configs.append(AudioTrackConfig(
                    track_type="sfx",
                    file_path=sfx["file_path"],
                    start=sfx["start"],
                    duration=sfx.get("duration", 2.0),
                    volume=0.7,
                    fade_in=0.05,
                    fade_out=0.2,
                ))

        # 计算总时长
        total_duration = max(
            (c.start + c.duration for c in all_configs),
            default=0
        )

        return {
            "tracks": [c.__dict__ for c in all_configs],
            "total_duration": total_duration,
            "bgm_count": len(bgm_configs),
            "narration_count": len(narration_timeline or []),
            "sfx_count": len(sfx_events or []),
        }

    def render(self, plan: Dict[str, Any], output_path: str) -> bool:
        """渲染混合音频"""
        configs = [AudioTrackConfig(**t) for t in plan["tracks"]]
        return self.mixer.mix(configs, output_path, plan["total_duration"])


def main():
    import argparse
    parser = argparse.ArgumentParser(description="自动配乐系统")
    parser.add_argument("action", choices=["scan", "select", "stats", "test"],
                        help="操作")
    parser.add_argument("--emotion", default="neutral", help="情绪")
    parser.add_argument("--style", default="general", help="风格")
    parser.add_argument("--duration", type=float, default=60, help="目标时长")
    parser.add_argument("--dir", help="BGM目录")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    system = AutoMusicSystem(bgm_dir=args.dir)

    if args.action == "scan":
        logger.info(f"BGM库: {system.library.get_stats()}")

    elif args.action == "select":
        track = system.selector.select(args.emotion, args.style, args.duration)
        if track:
            logger.info(f"选中: {track.file_name}")
            logger.info(f"  时长: {track.duration:.1f}秒")
            logger.info(f"  情绪: {track.emotions}")
            logger.info(f"  风格: {track.styles}")
        else:
            logger.info("未找到合适的BGM")

    elif args.action == "stats":
        logger.info(json.dumps(system.library.get_stats(), ensure_ascii=False, indent=2))

    elif args.action == "test":
        # 测试完整配乐方案
        emotions = [
            {"start": 0, "end": 10, "emotion": "calm", "intensity": 0.5},
            {"start": 10, "end": 25, "emotion": "energetic", "intensity": 0.8},
            {"start": 25, "end": 35, "emotion": "happy", "intensity": 0.7},
        ]
        plan = system.generate_music_plan(emotions, style="vlog")
        logger.info(json.dumps(plan, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
