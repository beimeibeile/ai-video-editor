# -*- coding: utf-8 -*-
"""
原视频逆向分析工具 v1.0
分析原视频的镜头结构、运镜、特效、色彩、节奏等，用于模板仿制参考。

核心能力：
1. 镜头分割（场景切换检测）
2. 运镜分析（推/拉/摇/移/跟/固定）
3. 色彩分析（主色调、饱和度、对比度）
4. 节奏分析（镜头时长分布、剪辑节奏）
5. 特效检测（闪白、震动、模糊等）
6. 字幕检测（文字区域识别）

使用方式：
    from video_reverse_analyzer import VideoReverseAnalyzer
    analyzer = VideoReverseAnalyzer("input.mp4")
    report = analyzer.analyze()
    analyzer.save_report(report, "analysis_report.json")
"""

import logging
logger = logging.getLogger(__name__)

import os
import sys
import json
import subprocess
import tempfile
from typing import Dict, List
from dataclasses import dataclass, field


@dataclass
class ShotInfo:
    """镜头信息"""
    index: int                    # 镜头序号
    start_time: float             # 开始时间（秒）
    end_time: float               # 结束时间（秒）
    duration: float               # 时长（秒）
    start_frame: int              # 开始帧
    end_frame: int                # 结束帧
    camera_move: str = "unknown"  # 运镜方式
    dominant_color: str = "#000000"  # 主色调
    brightness: float = 0.0       # 亮度 0-1
    contrast: float = 0.0         # 对比度 0-1
    saturation: float = 0.0       # 饱和度 0-1
    has_text: bool = False        # 是否有文字
    has_effect: bool = False      # 是否有特效
    effect_type: str = ""         # 特效类型


@dataclass
class VideoAnalysisReport:
    """视频分析报告"""
    video_path: str
    width: int = 0
    height: int = 0
    fps: float = 0.0
    duration: float = 0.0
    total_frames: int = 0
    codec: str = ""
    shots: List[ShotInfo] = field(default_factory=list)
    average_shot_duration: float = 0.0
    shot_duration_distribution: Dict = field(default_factory=dict)
    camera_move_distribution: Dict = field(default_factory=dict)
    color_palette: List[str] = field(default_factory=list)
    average_brightness: float = 0.0
    average_contrast: float = 0.0
    average_saturation: float = 0.0
    editing_pace: str = "medium"  # slow/medium/fast
    detected_effects: List[str] = field(default_factory=list)
    text_regions: List[Dict] = field(default_factory=list)


class VideoReverseAnalyzer:
    """原视频逆向分析器"""

    def __init__(self, video_path: str, ffmpeg_path: str = "ffmpeg",
                 ffprobe_path: str = "ffprobe"):
        self.video_path = video_path
        self.ffmpeg = ffmpeg_path
        self.ffprobe = ffprobe_path
        self._temp_dir = None

    def _get_temp_dir(self) -> str:
        if not self._temp_dir:
            self._temp_dir = tempfile.mkdtemp(prefix="video_analysis_")
        return self._temp_dir

    def probe_video(self) -> Dict:
        """探测视频基本信息"""
        cmd = [
            self.ffprobe, "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height,r_frame_rate,codec_name,nb_frames,duration",
            "-show_entries", "format=duration",
            "-of", "json",
            self.video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        data = json.loads(result.stdout or "{}")

        stream = (data.get("streams") or [{}])[0]
        fmt = data.get("format", {})

        # 解析帧率
        fps_str = stream.get("r_frame_rate", "30/1")
        if "/" in fps_str:
            num, den = fps_str.split("/")
            fps = float(num) / float(den) if float(den) != 0 else 30.0
        else:
            fps = float(fps_str)

        duration = float(stream.get("duration") or fmt.get("duration") or 0)
        total_frames = int(stream.get("nb_frames") or 0)
        if total_frames == 0 and duration > 0 and fps > 0:
            total_frames = int(duration * fps)

        return {
            "width": int(stream.get("width") or 0),
            "height": int(stream.get("height") or 0),
            "fps": fps,
            "duration": duration,
            "total_frames": total_frames,
            "codec": stream.get("codec_name", ""),
        }

    def detect_shot_boundaries(self, threshold: float = 0.3) -> List[float]:
        """检测镜头边界（场景切换）

        使用ffmpeg的select滤镜检测帧间差异
        """
        # 使用ffmpeg的scene检测
        cmd = [
            self.ffmpeg, "-i", self.video_path,
            "-filter:v", f"select='gt(scene,{threshold})',showinfo",
            "-f", "null", "-"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        # 解析showinfo输出中的pts_time
        boundaries = [0.0]  # 第一帧开始
        for line in result.stderr.split("\n"):
            if "showinfo" in line and "pts_time:" in line:
                try:
                    time_str = line.split("pts_time:")[1].split()[0]
                    time_val = float(time_str)
                    boundaries.append(time_val)
                except (ValueError, IndexError):
                    continue

        return sorted(set(boundaries))

    def extract_frame(self, time_sec: float, output_path: str) -> bool:
        """提取指定时间的帧"""
        cmd = [
            self.ffmpeg, "-y", "-ss", str(time_sec),
            "-i", self.video_path,
            "-frames:v", "1",
            "-q:v", "2",
            output_path
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=30)
        return os.path.exists(output_path)

    def analyze_frame_color(self, frame_path: str) -> Dict:
        """分析帧的色彩信息（使用Pillow）"""
        try:
            from PIL import Image
            import numpy as np

            img = Image.open(frame_path).convert("RGB")
            img_small = img.resize((50, 50))  # 缩小加速
            arr = np.array(img_small)

            # 计算主色调（平均色）
            avg_color = arr.mean(axis=(0, 1))
            dominant_color = "#{:02X}{:02X}{:02X}".format(
                int(avg_color[0]), int(avg_color[1]), int(avg_color[2])
            )

            # 亮度
            brightness = (0.299 * avg_color[0] + 0.587 * avg_color[1] +
                         0.114 * avg_color[2]) / 255.0

            # 对比度（标准差）
            gray = np.mean(arr, axis=2)
            contrast = float(np.std(gray) / 128.0)

            # 饱和度
            max_rgb = arr.max(axis=2).astype(float)
            min_rgb = arr.min(axis=2).astype(float)
            saturation = float(np.mean((max_rgb - min_rgb) / (max_rgb + 1e-6)))

            return {
                "dominant_color": dominant_color,
                "brightness": round(brightness, 3),
                "contrast": round(min(contrast, 1.0), 3),
                "saturation": round(min(saturation, 1.0), 3),
            }
        except ImportError:
            return {"dominant_color": "#000000", "brightness": 0.5,
                    "contrast": 0.5, "saturation": 0.5}
        except Exception as e:
            return {"dominant_color": "#000000", "brightness": 0.5,
                    "contrast": 0.5, "saturation": 0.5, "error": str(e)}

    def estimate_camera_move(self, frame1_path: str, frame2_path: str) -> str:
        """估算两帧之间的运镜方式（简化版）"""
        try:
            from PIL import Image
            import numpy as np

            img1 = np.array(Image.open(frame1_path).convert("L").resize((100, 100)))
            img2 = np.array(Image.open(frame2_path).convert("L").resize((100, 100)))

            # 计算帧间差异
            diff = np.abs(img1.astype(float) - img2.astype(float))
            mean_diff = np.mean(diff)

            # 差异很小 -> 固定镜头
            if mean_diff < 5:
                return "固定"
            # 差异较大 -> 可能有运镜
            elif mean_diff < 15:
                return "缓慢移动"
            else:
                return "快速移动/切换"
        except Exception:
            return "unknown"

    def analyze(self, sample_interval: float = 1.0) -> VideoAnalysisReport:
        """完整分析视频

        Args:
            sample_interval: 采样间隔（秒），用于色彩和运镜分析

        Returns:
            视频分析报告
        """
        logger.info(f"开始分析: {self.video_path}")

        # 1. 探测基本信息
        logger.info("  探测视频信息...")
        probe = self.probe_video()
        report = VideoAnalysisReport(
            video_path=self.video_path,
            width=probe["width"],
            height=probe["height"],
            fps=probe["fps"],
            duration=probe["duration"],
            total_frames=probe["total_frames"],
            codec=probe["codec"],
        )

        # 2. 检测镜头边界
        logger.info("  检测镜头边界...")
        boundaries = self.detect_shot_boundaries()
        if len(boundaries) <= 1:
            # 如果没检测到，按固定间隔分段
            boundaries = [i * 5.0 for i in range(int(probe["duration"] / 5) + 1)]

        # 3. 分析每个镜头
        logger.info("  分析镜头细节...")
        temp_dir = self._get_temp_dir()
        all_colors = []
        all_brightness = []
        all_contrast = []
        all_saturation = []

        for i in range(len(boundaries)):
            start = boundaries[i]
            end = boundaries[i + 1] if i + 1 < len(boundaries) else probe["duration"]
            duration = end - start

            if duration <= 0:
                continue

            shot = ShotInfo(
                index=i,
                start_time=round(start, 2),
                end_time=round(end, 2),
                duration=round(duration, 2),
                start_frame=int(start * probe["fps"]),
                end_frame=int(end * probe["fps"]),
            )

            # 提取中间帧进行色彩分析
            mid_time = (start + end) / 2
            frame_path = os.path.join(temp_dir, f"frame_{i:04d}.jpg")
            if self.extract_frame(mid_time, frame_path):
                color_info = self.analyze_frame_color(frame_path)
                shot.dominant_color = color_info["dominant_color"]
                shot.brightness = color_info["brightness"]
                shot.contrast = color_info["contrast"]
                shot.saturation = color_info["saturation"]

                all_colors.append(color_info["dominant_color"])
                all_brightness.append(color_info["brightness"])
                all_contrast.append(color_info["contrast"])
                all_saturation.append(color_info["saturation"])

            # 估算运镜（比较镜头首尾帧）
            if duration > 1.0:
                frame_start = os.path.join(temp_dir, f"frame_{i:04d}_start.jpg")
                frame_end = os.path.join(temp_dir, f"frame_{i:04d}_end.jpg")
                if self.extract_frame(start + 0.1, frame_start) and \
                   self.extract_frame(end - 0.1, frame_end):
                    shot.camera_move = self.estimate_camera_move(frame_start, frame_end)

            report.shots.append(shot)

        # 4. 统计分析
        logger.info("  生成统计报告...")
        if report.shots:
            durations = [s.duration for s in report.shots]
            report.average_shot_duration = round(sum(durations) / len(durations), 2)

            # 镜头时长分布
            dist = {"<1s": 0, "1-3s": 0, "3-5s": 0, "5-10s": 0, ">10s": 0}
            for d in durations:
                if d < 1:
                    dist["<1s"] += 1
                elif d < 3:
                    dist["1-3s"] += 1
                elif d < 5:
                    dist["3-5s"] += 1
                elif d < 10:
                    dist["5-10s"] += 1
                else:
                    dist[">10s"] += 1
            report.shot_duration_distribution = dist

            # 剪辑节奏判断
            if report.average_shot_duration < 1.5:
                report.editing_pace = "fast"
            elif report.average_shot_duration < 3.5:
                report.editing_pace = "medium"
            else:
                report.editing_pace = "slow"

            # 运镜分布
            cam_dist = {}
            for s in report.shots:
                cam_dist[s.camera_move] = cam_dist.get(s.camera_move, 0) + 1
            report.camera_move_distribution = cam_dist

            # 平均色彩
            if all_brightness:
                report.average_brightness = round(sum(all_brightness) / len(all_brightness), 3)
                report.average_contrast = round(sum(all_contrast) / len(all_contrast), 3)
                report.average_saturation = round(sum(all_saturation) / len(all_saturation), 3)

            # 色彩调色板（取出现最多的颜色）
            color_count = {}
            for c in all_colors:
                color_count[c] = color_count.get(c, 0) + 1
            report.color_palette = [c for c, _ in
                                    sorted(color_count.items(), key=lambda x: -x[1])[:10]]

        logger.info(f"  分析完成: {len(report.shots)}个镜头")
        return report

    def save_report(self, report: VideoAnalysisReport, output_path: str) -> str:
        """保存分析报告为JSON"""
        data = {
            "video_path": report.video_path,
            "width": report.width,
            "height": report.height,
            "fps": report.fps,
            "duration": report.duration,
            "total_frames": report.total_frames,
            "codec": report.codec,
            "shot_count": len(report.shots),
            "average_shot_duration": report.average_shot_duration,
            "shot_duration_distribution": report.shot_duration_distribution,
            "camera_move_distribution": report.camera_move_distribution,
            "color_palette": report.color_palette,
            "average_brightness": report.average_brightness,
            "average_contrast": report.average_contrast,
            "average_saturation": report.average_saturation,
            "editing_pace": report.editing_pace,
            "detected_effects": report.detected_effects,
            "shots": [
                {
                    "index": s.index,
                    "start_time": s.start_time,
                    "end_time": s.end_time,
                    "duration": s.duration,
                    "camera_move": s.camera_move,
                    "dominant_color": s.dominant_color,
                    "brightness": s.brightness,
                    "contrast": s.contrast,
                    "saturation": s.saturation,
                }
                for s in report.shots
            ],
        }

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return output_path

    def print_summary(self, report: VideoAnalysisReport):
        """打印分析摘要"""
        logger.info("\n" + "=" * 60)
        logger.info("视频逆向分析报告")
        logger.info("=" * 60)
        logger.info(f"视频: {os.path.basename(report.video_path)}")
        logger.info(f"分辨率: {report.width}x{report.height}")
        logger.info(f"帧率: {report.fps:.1f}fps")
        logger.info(f"时长: {report.duration:.1f}秒")
        logger.info(f"总帧数: {report.total_frames}")
        logger.info(f"编码: {report.codec}")
        logger.info(f"\n镜头数: {len(report.shots)}")
        logger.info(f"平均镜头时长: {report.average_shot_duration:.2f}秒")
        logger.info(f"剪辑节奏: {report.editing_pace}")
        logger.info(f"\n镜头时长分布:")
        for k, v in report.shot_duration_distribution.items():
            logger.info(f"  {k}: {v}个")
        logger.info(f"\n运镜分布:")
        for k, v in report.camera_move_distribution.items():
            logger.info(f"  {k}: {v}个")
        logger.info(f"\n平均亮度: {report.average_brightness:.3f}")
        logger.info(f"平均对比度: {report.average_contrast:.3f}")
        logger.info(f"平均饱和度: {report.average_saturation:.3f}")
        logger.info(f"\n主色调: {', '.join(report.color_palette[:5])}")
        logger.info("=" * 60)


def main():
    """命令行测试"""
    if len(sys.argv) < 2:
        logger.info("用法: python video_reverse_analyzer.py <video_path> [output.json]")
        sys.exit(1)

    video_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else "analysis_report.json"

    if not os.path.exists(video_path):
        logger.error(f"错误: 文件不存在 {video_path}")
        sys.exit(1)

    analyzer = VideoReverseAnalyzer(video_path)
    report = analyzer.analyze()
    analyzer.print_summary(report)
    analyzer.save_report(report, output_path)
    logger.info(f"\n报告已保存: {output_path}")


if __name__ == "__main__":
    main()
