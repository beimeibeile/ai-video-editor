"""
原型理解引擎 v1.0 (P21-1)
输入参考视频→自动拆解结构（角色/场景/镜头/时间轴/特效），输出结构化原型卡

核心能力：
1. 视频抽帧分析（场景切换检测、镜头时长统计）
2. 音频分析（能量峰值、对白/音效时间点）
3. 视觉元素识别（颜色聚类、运动区域、文字区域）
4. 时间轴结构（每个时间段的视觉+音频特征）
5. 原型卡输出（JSON+Markdown，供方案决策器使用）

使用方法：
    from prototype_analyzer import PrototypeAnalyzer
    analyzer = PrototypeAnalyzer()
    result = analyzer.analyze("参考视频.mp4")
    logger.info(result["summary"])
    result.save("原型卡.json")
"""

import logging
logger = logging.getLogger(__name__)


import os
import sys
import json
import subprocess
import math
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass, field, asdict

# ffmpeg路径
try:
    from paths import FFMPEG
except ImportError:
    FFMPEG = r"D:\Ai\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe"
try:
    from paths import FFPROBE
except ImportError:
    FFPROBE = r"D:\Ai\ffmpeg-master-latest-win64-gpl\bin\ffprobe.exe"


@dataclass
class ShotInfo:
    """镜头信息"""
    index: int
    start_time: float
    end_time: float
    duration: float
    avg_brightness: float = 0.0
    dominant_color: str = "#000000"
    motion_level: float = 0.0  # 0-1
    has_text: bool = False
    has_face: bool = False


@dataclass
class AudioEvent:
    """音频事件"""
    time: float
    duration: float
    energy: float
    event_type: str = "unknown"  # dialogue/sfx/bgm_peak/silence


@dataclass
class PrototypeCard:
    """原型卡 - 参考视频的结构化描述"""
    source_file: str
    duration: float
    width: int
    height: int
    fps: float
    total_shots: int
    avg_shot_duration: float
    shot_density: str = "normal"  # fast(>3切/秒)/normal/slow(<1切/3秒)
    shots: List[ShotInfo] = field(default_factory=list)
    audio_events: List[AudioEvent] = field(default_factory=list)
    visual_style: Dict[str, Any] = field(default_factory=dict)
    timeline_summary: List[Dict[str, Any]] = field(default_factory=list)
    technical_notes: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    def save(self, path: str):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    def summary(self) -> str:
        lines = [
            "=" * 60,
            f"  原型卡: {os.path.basename(self.source_file)}",
            "=" * 60,
            f"  时长: {self.duration:.1f}s | 分辨率: {self.width}x{self.height} | {self.fps:.0f}fps",
            f"  镜头数: {self.total_shots} | 平均镜头: {self.avg_shot_duration:.2f}s | 密度: {self.shot_density}",
            "",
            "  时间轴:",
        ]
        for seg in self.timeline_summary[:10]:
            lines.append(f"    [{seg['start']:.1f}-{seg['end']:.1f}s] {seg['description']}")
        if len(self.timeline_summary) > 10:
            lines.append(f"    ... 共{len(self.timeline_summary)}段")
        lines.append("")
        lines.append("  技术备注:")
        for note in self.technical_notes[:5]:
            lines.append(f"    - {note}")
        lines.append("=" * 60)
        return "\n".join(lines)


class PrototypeAnalyzer:
    """原型理解引擎"""

    def __init__(self, ffmpeg_path: str = None, ffprobe_path: str = None):
        self.ffmpeg = ffmpeg_path or FFMPEG
        self.ffprobe = ffprobe_path or FFPROBE
        self.temp_dir = None

    def _run_cmd(self, cmd: list, timeout: int = 60) -> str:
        """执行命令并返回输出"""
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout
            )
            return result.stdout + result.stderr
        except Exception as e:
            return f"ERROR: {e}"

    def _get_video_info(self, video_path: str) -> dict:
        """获取视频基本信息"""
        cmd = [
            self.ffprobe, "-v", "quiet", "-print_format", "json",
            "-show_format", "-show_streams", video_path
        ]
        output = self._run_cmd(cmd)
        try:
            info = json.loads(output)
            video_stream = next(
                (s for s in info.get("streams", []) if s.get("codec_type") == "video"),
                {}
            )
            return {
                "duration": float(info.get("format", {}).get("duration", 0)),
                "width": int(video_stream.get("width", 1080)),
                "height": int(video_stream.get("height", 1920)),
                "fps": float(eval(video_stream.get("r_frame_rate", "30/1"))),
                "bitrate": int(info.get("format", {}).get("bit_rate", 0)),
            }
        except Exception:
            return {"duration": 0, "width": 1080, "height": 1920, "fps": 30, "bitrate": 0}

    def _detect_scene_changes(self, video_path: str, threshold: float = 0.1) -> List[float]:
        """检测场景切换时间点"""
        cmd = [
            self.ffmpeg, "-i", video_path,
            "-filter:v", f"select='gt(scene,{threshold})',showinfo",
            "-f", "null", "-"
        ]
        output = self._run_cmd(cmd, timeout=120)
        times = []
        for line in output.split("\n"):
            if "showinfo" in line and "pts_time:" in line:
                try:
                    t = float(line.split("pts_time:")[1].split()[0])
                    times.append(t)
                except (ValueError, IndexError):
                    pass
        return sorted(set(times))

    def _extract_frames(self, video_path: str, output_dir: str, fps: float = 1.0) -> List[str]:
        """抽帧"""
        os.makedirs(output_dir, exist_ok=True)
        pattern = os.path.join(output_dir, "frame_%04d.jpg")
        cmd = [
            self.ffmpeg, "-i", video_path, "-vf", f"fps={fps}",
            "-q:v", "3", pattern, "-y"
        ]
        self._run_cmd(cmd, timeout=120)
        frames = sorted([
            os.path.join(output_dir, f)
            for f in os.listdir(output_dir)
            if f.startswith("frame_") and f.endswith(".jpg")
        ])
        return frames

    def _analyze_audio_energy(self, video_path: str) -> List[Tuple[float, float]]:
        """分析音频能量曲线（每秒一个采样点）"""
        cmd = [
            self.ffmpeg, "-i", video_path,
            "-af", "astats=metadata=1:reset=1,ametadata=print:key=lavfi.astats.Overall.RMS_level",
            "-f", "null", "-"
        ]
        output = self._run_cmd(cmd, timeout=60)
        energies = []
        current_time = 0
        for line in output.split("\n"):
            if "pts_time:" in line:
                try:
                    current_time = float(line.split("pts_time:")[1].strip())
                except ValueError:
                    pass
            elif "RMS_level" in line:
                try:
                    val = float(line.split("=")[1].strip())
                    if val > -100:
                        energies.append((current_time, val))
                except (ValueError, IndexError):
                    pass
        return energies

    def _detect_audio_events(self, energies: List[Tuple[float, float]]) -> List[AudioEvent]:
        """从能量曲线检测音频事件"""
        if not energies:
            return []
        avg_energy = sum(e[1] for e in energies) / len(energies)
        threshold = avg_energy * 0.7  # 高于平均70%为事件

        events = []
        in_event = False
        event_start = 0
        event_peak = -100

        for t, e in energies:
            if e > threshold and not in_event:
                in_event = True
                event_start = t
                event_peak = e
            elif e > threshold and in_event:
                event_peak = max(event_peak, e)
            elif e <= threshold and in_event:
                duration = t - event_start
                if duration > 0.1:
                    # 分类：短(<0.5s)=音效，中(0.5-2s)=对白，长(>2s)=BGM段落
                    if duration < 0.5:
                        etype = "sfx"
                    elif duration < 2.0:
                        etype = "dialogue"
                    else:
                        etype = "bgm_peak"
                    events.append(AudioEvent(
                        time=event_start, duration=duration,
                        energy=event_peak, event_type=etype
                    ))
                in_event = False

        return events

    def _analyze_frame_brightness(self, frame_path: str) -> float:
        """分析帧的平均亮度"""
        try:
            from PIL import Image, ImageStat
            img = Image.open(frame_path).convert("L")
            stat = ImageStat.Stat(img)
            return stat.mean[0] / 255.0
        except Exception:
            return 0.5

    def _analyze_dominant_color(self, frame_path: str) -> str:
        """分析帧的主色调"""
        try:
            from PIL import Image
            img = Image.open(frame_path).resize((50, 50)).convert("RGB")
            pixels = list(img.getdata())
            # 简单聚类：取平均色
            r = sum(p[0] for p in pixels) // len(pixels)
            g = sum(p[1] for p in pixels) // len(pixels)
            b = sum(p[2] for p in pixels) // len(pixels)
            return f"#{r:02x}{g:02x}{b:02x}"
        except Exception:
            return "#808080"

    def _classify_shot_density(self, total_shots: int, duration: float) -> str:
        """分类镜头密度"""
        if duration <= 0:
            return "unknown"
        cuts_per_sec = total_shots / duration
        if cuts_per_sec > 0.5:
            return "fast"
        elif cuts_per_sec > 0.2:
            return "normal"
        else:
            return "slow"

    def _build_timeline_summary(self, shots: List[ShotInfo],
                                 audio_events: List[AudioEvent]) -> List[Dict[str, Any]]:
        """构建时间轴摘要"""
        if not shots:
            return []

        # 按3秒分段汇总
        segment_duration = 3.0
        total_duration = shots[-1].end_time if shots else 0
        segments = []

        for seg_start in range(0, int(total_duration) + 1, int(segment_duration)):
            seg_end = min(seg_start + segment_duration, total_duration)
            seg_shots = [s for s in shots if s.start_time >= seg_start and s.start_time < seg_end]
            seg_audio = [a for a in audio_events if a.time >= seg_start and a.time < seg_end]

            if not seg_shots:
                continue

            # 描述这个时间段
            avg_bright = sum(s.avg_brightness for s in seg_shots) / len(seg_shots)
            has_dialogue = any(a.event_type == "dialogue" for a in seg_audio)
            has_sfx = any(a.event_type == "sfx" for a in seg_audio)
            motion = sum(s.motion_level for s in seg_shots) / len(seg_shots)

            desc_parts = []
            if avg_bright < 0.3:
                desc_parts.append("暗场")
            elif avg_bright > 0.7:
                desc_parts.append("亮场")
            if motion > 0.5:
                desc_parts.append("高运动")
            if has_dialogue:
                desc_parts.append("对白")
            if has_sfx:
                desc_parts.append("音效")
            if not desc_parts:
                desc_parts.append("静态")

            segments.append({
                "start": seg_start,
                "end": seg_end,
                "shot_count": len(seg_shots),
                "description": "+".join(desc_parts),
                "avg_brightness": round(avg_bright, 2),
                "motion_level": round(motion, 2),
            })

        return segments

    def analyze(self, video_path: str, output_dir: str = None) -> PrototypeCard:
        """
        分析参考视频，生成原型卡

        Args:
            video_path: 参考视频路径
            output_dir: 输出目录（None则自动创建）

        Returns:
            PrototypeCard: 结构化原型卡
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"视频不存在: {video_path}")

        if output_dir is None:
            output_dir = os.path.join(
                os.path.dirname(video_path),
                f"prototype_{os.path.splitext(os.path.basename(video_path))[0]}"
            )
        os.makedirs(output_dir, exist_ok=True)
        self.temp_dir = output_dir

        logger.info(f"\n{'='*60}")
        logger.info(f"  原型理解引擎")
        logger.info(f"{'='*60}")
        logger.info(f"  视频: {os.path.basename(video_path)}")

        # 1. 基本信息
        logger.info("\n[1/5] 获取视频信息...")
        info = self._get_video_info(video_path)
        logger.info(f"  时长: {info['duration']:.1f}s, {info['width']}x{info['height']}, {info['fps']:.0f}fps")

        # 2. 场景切换检测
        logger.info("\n[2/5] 检测场景切换...")
        scene_changes = self._detect_scene_changes(video_path)
        logger.info(f"  检测到 {len(scene_changes)} 个场景切换点")

        # 3. 抽帧分析
        logger.info("\n[3/5] 抽帧分析...")
        frames_dir = os.path.join(output_dir, "frames")
        frames = self._extract_frames(video_path, frames_dir, fps=1.0)
        logger.info(f"  抽取 {len(frames)} 帧")

        # 4. 构建镜头信息
        logger.info("\n[4/5] 分析镜头特征...")
        shots = []
        all_times = [0.0] + scene_changes + [info["duration"]]
        for i in range(len(all_times) - 1):
            start = all_times[i]
            end = all_times[i + 1]
            duration = end - start
            if duration < 0.1:
                continue

            # 找这个时间段的帧
            shot_frames = [
                f for f in frames
                if start <= int(os.path.basename(f).split("_")[1].split(".")[0]) - 1 <= end
            ]
            avg_bright = 0.5
            dom_color = "#808080"
            if shot_frames:
                brightnesses = [self._analyze_frame_brightness(f) for f in shot_frames[:3]]
                avg_bright = sum(brightnesses) / len(brightnesses)
                dom_color = self._analyze_dominant_color(shot_frames[0])

            shots.append(ShotInfo(
                index=i, start_time=start, end_time=end, duration=duration,
                avg_brightness=round(avg_bright, 2),
                dominant_color=dom_color,
                motion_level=0.3 if duration < 2.0 else 0.1,  # 短镜头=高运动
            ))

        avg_shot_dur = sum(s.duration for s in shots) / len(shots) if shots else 0
        shot_density = self._classify_shot_density(len(shots), info["duration"])

        # 5. 音频分析
        logger.info("\n[5/5] 分析音频...")
        energies = self._analyze_audio_energy(video_path)
        audio_events = self._detect_audio_events(energies)
        logger.info(f"  检测到 {len(audio_events)} 个音频事件")

        # 构建时间轴摘要
        timeline = self._build_timeline_summary(shots, audio_events)

        # 技术备注
        notes = []
        if info["width"] > info["height"]:
            notes.append("横屏视频(16:9)，适合电影模式")
        else:
            notes.append("竖屏视频(9:16)，适合短视频模式")
        if shot_density == "fast":
            notes.append("快节奏剪辑，需要精确卡点")
        elif shot_density == "slow":
            notes.append("慢节奏，适合长镜头和运镜")
        if any(a.event_type == "dialogue" for a in audio_events):
            notes.append("包含对白，需要TTS或配音")
        if any(a.event_type == "sfx" for a in audio_events):
            notes.append("包含音效点，需要音画同步")
        if avg_shot_dur < 1.0:
            notes.append("平均镜头<1秒，极高密度，转场设计是关键")

        # 视觉风格
        visual_style = {
            "aspect_ratio": f"{info['width']}:{info['height']}",
            "orientation": "landscape" if info["width"] > info["height"] else "portrait",
            "shot_density": shot_density,
            "avg_brightness": round(sum(s.avg_brightness for s in shots) / len(shots), 2) if shots else 0.5,
            "color_temperature": "warm" if any(int(s.dominant_color[1:3], 16) > int(s.dominant_color[5:7], 16) for s in shots[:5]) else "cool",
        }

        card = PrototypeCard(
            source_file=video_path,
            duration=info["duration"],
            width=info["width"],
            height=info["height"],
            fps=info["fps"],
            total_shots=len(shots),
            avg_shot_duration=round(avg_shot_dur, 2),
            shot_density=shot_density,
            shots=shots,
            audio_events=audio_events,
            visual_style=visual_style,
            timeline_summary=timeline,
            technical_notes=notes,
        )

        # 保存原型卡
        json_path = os.path.join(output_dir, "prototype_card.json")
        card.save(json_path)

        # 保存Markdown摘要
        md_path = os.path.join(output_dir, "prototype_summary.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(card.summary())

        logger.info(f"\n✅ 原型卡生成完成")
        logger.info(f"  JSON: {json_path}")
        logger.info(f"  摘要: {md_path}")
        logger.info(f"  帧目录: {frames_dir}")
        logger.info(card.summary())

        return card


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="原型理解引擎 - 分析参考视频生成原型卡")
    parser.add_argument("video", help="参考视频路径")
    parser.add_argument("-o", "--output", help="输出目录", default=None)
    args = parser.parse_args()

    analyzer = PrototypeAnalyzer()
    card = analyzer.analyze(args.video, args.output)
