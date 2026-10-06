"""
原视频逆向分析引擎 v1.0
分析原视频的镜头结构、运镜类型、画面特征、情绪曲线

用于二创编排时理解原视频的结构和节奏。

使用方式：
    from video_reverse_analyzer import VideoReverseAnalyzer
    analyzer = VideoReverseAnalyzer()
    result = analyzer.analyze("video.mp4")
    print(result["shot_boundaries"])  # 镜头切换点
    print(result["scene_features"])   # 场景特征
"""
import os
import subprocess
import json
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class ShotBoundary:
    """镜头切换点"""
    time: float  # 切换时间（秒）
    type: str  # hard/soft
    confidence: float  # 0.0-1.0


@dataclass
class SceneFeature:
    """场景特征"""
    start_time: float
    end_time: float
    duration: float
    avg_brightness: float  # 平均亮度 0-255
    avg_saturation: float  # 平均饱和度 0-1
    motion_level: float  # 运动程度 0-1
    dominant_color: str  # 主色调
    complexity: str  # low/medium/high


@dataclass
class VideoAnalysisResult:
    """视频分析结果"""
    filepath: str
    duration: float
    fps: float
    width: int
    height: int
    shot_count: int
    shot_boundaries: List[ShotBoundary] = field(default_factory=list)
    scene_features: List[SceneFeature] = field(default_factory=list)
    emotion_curve: List[Dict] = field(default_factory=list)
    camera_moves: List[str] = field(default_factory=list)
    estimated_effects: List[str] = field(default_factory=list)
    overall_complexity: str = "medium"
    bgm_segments: int = 0


class VideoReverseAnalyzer:
    """原视频逆向分析引擎"""

    def __init__(self, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe"):
        self.ffmpeg = ffmpeg_path
        self.ffprobe = ffprobe_path

    def analyze(self, video_path: str, sample_interval: float = 1.0) -> VideoAnalysisResult:
        """
        分析视频

        Args:
            video_path: 视频文件路径
            sample_interval: 采样间隔（秒）

        Returns:
            VideoAnalysisResult 分析结果
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"视频文件不存在: {video_path}")

        # 获取视频基本信息
        info = self._get_video_info(video_path)
        duration = info.get("duration", 0)
        fps = info.get("fps", 30)
        width = info.get("width", 1920)
        height = info.get("height", 1080)

        # 检测镜头切换点
        shot_boundaries = self._detect_shot_boundaries(video_path, duration)

        # 提取场景特征
        scene_features = self._extract_scene_features(
            video_path, duration, shot_boundaries, sample_interval
        )

        # 分析情绪曲线
        emotion_curve = self._analyze_emotion_curve(scene_features, duration)

        # 识别运镜类型
        camera_moves = self._identify_camera_moves(scene_features)

        # 估计特效类型
        effects = self._estimate_effects(scene_features, shot_boundaries)

        # 整体复杂度
        complexity = self._calc_overall_complexity(
            shot_boundaries, scene_features, duration
        )

        return VideoAnalysisResult(
            filepath=video_path,
            duration=duration,
            fps=fps,
            width=width,
            height=height,
            shot_count=len(shot_boundaries) + 1,
            shot_boundaries=shot_boundaries,
            scene_features=scene_features,
            emotion_curve=emotion_curve,
            camera_moves=camera_moves,
            estimated_effects=effects,
            overall_complexity=complexity,
        )

    def _get_video_info(self, video_path: str) -> Dict:
        """获取视频基本信息"""
        try:
            cmd = [
                self.ffprobe, "-v", "quiet",
                "-print_format", "json",
                "-show_format", "-show_streams",
                video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            data = json.loads(result.stdout)

            video_stream = next(
                (s for s in data.get("streams", []) if s.get("codec_type") == "video"),
                {}
            )

            # 解析帧率
            fps_str = video_stream.get("r_frame_rate", "30/1")
            if "/" in fps_str:
                num, den = fps_str.split("/")
                fps = float(num) / float(den) if float(den) != 0 else 30
            else:
                fps = float(fps_str)

            return {
                "duration": float(data.get("format", {}).get("duration", 0)),
                "fps": fps,
                "width": int(video_stream.get("width", 1920)),
                "height": int(video_stream.get("height", 1080)),
            }
        except Exception as e:
            print(f"⚠️ 获取视频信息失败: {e}")
            return {"duration": 0, "fps": 30, "width": 1920, "height": 1080}

    def _detect_shot_boundaries(
        self, video_path: str, duration: float
    ) -> List[ShotBoundary]:
        """检测镜头切换点（使用ffmpeg场景检测）"""
        boundaries = []

        try:
            # 使用ffmpeg的select滤镜检测场景变化
            cmd = [
                self.ffmpeg, "-i", video_path,
                "-filter:v", "select='gt(scene,0.3)',showinfo",
                "-f", "null", "-"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

            # 解析showinfo输出中的时间戳
            for line in result.stderr.split("\n"):
                if "showinfo" in line and "pts_time:" in line:
                    match = re.search(r"pts_time:([\d.]+)", line)
                    if match:
                        time = float(match.group(1))
                        # 提取场景变化分数
                        score_match = re.search(r"scene:([\d.]+)", line)
                        score = float(score_match.group(1)) if score_match else 0.5

                        boundary_type = "hard" if score > 0.6 else "soft"
                        boundaries.append(ShotBoundary(
                            time=time,
                            type=boundary_type,
                            confidence=min(score, 1.0),
                        ))

            # 如果没有检测到切换点，根据时长估算
            if not boundaries and duration > 0:
                avg_shot_duration = 3.0  # 假设平均3秒一个镜头
                num_shots = max(1, int(duration / avg_shot_duration))
                for i in range(1, num_shots):
                    boundaries.append(ShotBoundary(
                        time=i * avg_shot_duration,
                        type="estimated",
                        confidence=0.3,
                    ))

        except Exception as e:
            print(f"⚠️ 镜头切换检测失败: {e}")
            # 降级：按固定间隔估算
            if duration > 0:
                avg_shot_duration = 3.0
                num_shots = max(1, int(duration / avg_shot_duration))
                for i in range(1, num_shots):
                    boundaries.append(ShotBoundary(
                        time=i * avg_shot_duration,
                        type="estimated",
                        confidence=0.3,
                    ))

        return boundaries

    def _extract_scene_features(
        self,
        video_path: str,
        duration: float,
        boundaries: List[ShotBoundary],
        sample_interval: float,
    ) -> List[SceneFeature]:
        """提取场景特征（基于帧采样）"""
        features = []

        # 构建镜头时间段
        segments = []
        prev_time = 0.0
        for b in boundaries:
            segments.append((prev_time, b.time))
            prev_time = b.time
        if prev_time < duration:
            segments.append((prev_time, duration))

        # 对每个镜头段提取特征
        for start, end in segments:
            seg_duration = end - start
            if seg_duration <= 0:
                continue

            # 采样中间帧
            sample_time = start + seg_duration / 2

            try:
                # 使用ffmpeg提取帧并获取统计信息
                cmd = [
                    self.ffmpeg, "-ss", str(sample_time),
                    "-i", video_path,
                    "-vframes", "1",
                    "-f", "rawvideo", "-pix_fmt", "rgb24",
                    "-"
                ]
                result = subprocess.run(cmd, capture_output=True, timeout=30)

                if result.returncode == 0 and len(result.stdout) > 0:
                    # 解析RGB数据计算亮度和饱和度
                    frame_data = result.stdout
                    brightness, saturation = self._calc_frame_stats(frame_data)
                else:
                    brightness, saturation = 128, 0.5

            except Exception:
                brightness, saturation = 128, 0.5

            # 估算运动程度（基于镜头时长和切换频率）
            motion_level = min(1.0, 0.3 + (1.0 / max(seg_duration, 0.5)) * 0.5)

            # 主色调（基于亮度估算）
            if brightness < 60:
                dominant_color = "dark"
            elif brightness < 120:
                dominant_color = "medium"
            elif brightness < 180:
                dominant_color = "bright"
            else:
                dominant_color = "high_key"

            # 复杂度
            if seg_duration < 1.5:
                complexity = "high"
            elif seg_duration < 3:
                complexity = "medium"
            else:
                complexity = "low"

            features.append(SceneFeature(
                start_time=round(start, 2),
                end_time=round(end, 2),
                duration=round(seg_duration, 2),
                avg_brightness=round(brightness, 1),
                avg_saturation=round(saturation, 2),
                motion_level=round(motion_level, 2),
                dominant_color=dominant_color,
                complexity=complexity,
            ))

        return features

    def _calc_frame_stats(self, raw_data: bytes) -> Tuple[float, float]:
        """计算帧的亮度和饱和度（简化版）"""
        try:
            # 采样部分像素
            step = max(1, len(raw_data) // 1000)
            total_brightness = 0
            total_saturation = 0
            count = 0

            for i in range(0, min(len(raw_data) - 3, 10000), step * 3):
                r = raw_data[i]
                g = raw_data[i + 1]
                b = raw_data[i + 2]

                # 亮度（ITU-R BT.601）
                brightness = 0.299 * r + 0.587 * g + 0.114 * b
                total_brightness += brightness

                # 饱和度（简化：max-min）
                max_val = max(r, g, b)
                min_val = min(r, g, b)
                saturation = (max_val - min_val) / max(max_val, 1)
                total_saturation += saturation

                count += 1

            if count > 0:
                return total_brightness / count, total_saturation / count
        except Exception:
            pass

        return 128, 0.5

    def _analyze_emotion_curve(
        self, features: List[SceneFeature], duration: float
    ) -> List[Dict]:
        """分析情绪曲线（基于画面特征）"""
        if not features:
            return []

        curve = []
        num_samples = min(10, len(features))
        step = len(features) / num_samples

        for i in range(num_samples):
            idx = int(i * step)
            if idx >= len(features):
                idx = len(features) - 1

            f = features[idx]

            # 根据亮度和运动程度推断情绪
            if f.motion_level > 0.7 and f.avg_brightness > 150:
                emotion = "激烈"
                intensity = 0.8
            elif f.motion_level > 0.5:
                emotion = "紧张"
                intensity = 0.6
            elif f.avg_brightness < 80:
                emotion = "沉重"
                intensity = 0.5
            elif f.avg_saturation > 0.6:
                emotion = "活泼"
                intensity = 0.6
            else:
                emotion = "平静"
                intensity = 0.3

            curve.append({
                "position": round(f.start_time / max(duration, 1), 2),
                "time": f.start_time,
                "emotion": emotion,
                "intensity": intensity,
                "brightness": f.avg_brightness,
                "motion": f.motion_level,
            })

        return curve

    def _identify_camera_moves(self, features: List[SceneFeature]) -> List[str]:
        """识别运镜类型（基于运动程度估算）"""
        moves = set()

        for f in features:
            if f.motion_level > 0.7:
                moves.add("快速运镜")
            elif f.motion_level > 0.4:
                moves.add("中等运镜")
            else:
                moves.add("固定/缓慢")

            if f.complexity == "high":
                moves.add("快速剪辑")

        return sorted(list(moves))

    def _estimate_effects(
        self, features: List[SceneFeature], boundaries: List[ShotBoundary]
    ) -> List[str]:
        """估计特效类型"""
        effects = []

        # 检查快速切换（可能有闪白/转场特效）
        hard_cuts = sum(1 for b in boundaries if b.type == "hard")
        if hard_cuts > len(boundaries) * 0.5:
            effects.append("快速转场")

        # 检查高亮度场景（可能有闪白）
        high_brightness = sum(1 for f in features if f.avg_brightness > 200)
        if high_brightness > len(features) * 0.2:
            effects.append("闪白/高光")

        # 检查低饱和度（可能有调色）
        low_sat = sum(1 for f in features if f.avg_saturation < 0.3)
        if low_sat > len(features) * 0.3:
            effects.append("低饱和调色")

        # 检查高运动（可能有动态模糊）
        high_motion = sum(1 for f in features if f.motion_level > 0.7)
        if high_motion > len(features) * 0.3:
            effects.append("动态模糊/手持感")

        if not effects:
            effects.append("基础剪辑")

        return effects

    def _calc_overall_complexity(
        self,
        boundaries: List[ShotBoundary],
        features: List[SceneFeature],
        duration: float,
    ) -> str:
        """计算整体复杂度"""
        if duration == 0:
            return "medium"

        shot_density = len(boundaries) / duration  # 每秒镜头数
        avg_shot_duration = duration / max(len(boundaries) + 1, 1)

        if shot_density > 0.5 or avg_shot_duration < 2:
            return "high"
        elif shot_density > 0.2 or avg_shot_duration < 4:
            return "medium"
        else:
            return "low"

    def print_summary(self, result: VideoAnalysisResult):
        """打印分析摘要"""
        print("=" * 60)
        print("原视频逆向分析报告")
        print("=" * 60)
        print(f"\n文件: {os.path.basename(result.filepath)}")
        print(f"时长: {result.duration:.1f}秒")
        print(f"分辨率: {result.width}x{result.height}")
        print(f"帧率: {result.fps:.1f}fps")
        print(f"镜头数: {result.shot_count}")
        print(f"整体复杂度: {result.overall_complexity}")

        print(f"\n镜头切换点 ({len(result.shot_boundaries)}):")
        for b in result.shot_boundaries[:10]:
            print(f"  [{b.time:6.2f}s] {b.type:6s} 置信度{b.confidence:.0%}")
        if len(result.shot_boundaries) > 10:
            print(f"  ... 还有{len(result.shot_boundaries) - 10}个")

        print(f"\n场景特征 ({len(result.scene_features)}):")
        for f in result.scene_features[:8]:
            print(f"  [{f.start_time:6.2f}-{f.end_time:6.2f}] "
                  f"亮度{f.avg_brightness:5.1f} 饱和{f.avg_saturation:.2f} "
                  f"运动{f.motion_level:.2f} {f.complexity}")
        if len(result.scene_features) > 8:
            print(f"  ... 还有{len(result.scene_features) - 8}个")

        print(f"\n情绪曲线:")
        for e in result.emotion_curve:
            bar = "█" * int(e["intensity"] * 20)
            print(f"  [{e['position']:.0%}] {e['emotion']:4s} {bar} ({e['intensity']:.1f})")

        print(f"\n运镜类型: {', '.join(result.camera_moves)}")
        print(f"估计特效: {', '.join(result.estimated_effects)}")
        print("=" * 60)


def main():
    """命令行测试"""
    import sys

    analyzer = VideoReverseAnalyzer()

    if len(sys.argv) > 1:
        video_path = sys.argv[1]
    else:
        # 使用测试视频
        test_dir = r"C:\Users\Administrator\Videos\剪映导出\Doubao_Jianying-editor\抖音短视频去水印拉取"
        test_videos = [
            os.path.join(test_dir, f)
            for f in os.listdir(test_dir)
            if f.endswith(".mp4")
        ] if os.path.exists(test_dir) else []

        if test_videos:
            video_path = test_videos[0]
        else:
            print("未找到测试视频，请指定视频路径")
            print("用法: python video_reverse_analyzer.py <video_path>")
            return

    print(f"分析视频: {video_path}")
    result = analyzer.analyze(video_path)
    analyzer.print_summary(result)


if __name__ == "__main__":
    main()
