#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P3-1 视频内容理解引擎
场景切换检测 + 节奏分析 + 色彩分析 + 情绪推断 + 特效识别框架
输出结构化JSON供P3-2/P3-3决策使用
"""
import os
import json
import subprocess
import tempfile
import math
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass, asdict, field
import logging
logger = logging.getLogger(__name__)


FFMPEG = r"D:\Ai\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe"
FFPROBE = r"D:\Ai\ffmpeg-master-latest-win64-gpl\bin\ffprobe.exe"


@dataclass
class SceneSegment:
    """场景片段"""
    index: int
    start: float
    end: float
    duration: float
    avg_brightness: float = 0  # 0-255
    avg_contrast: float = 0  # 0-128
    dominant_color: str = "#000000"
    color_temperature: str = "neutral"  # warm/cool/neutral
    motion_level: float = 0  # 0-1
    scene_type: str = "unknown"  # indoor/outdoor/portrait/product/landscape/other
    emotion: str = "neutral"  # happy/sad/energetic/calm/tense/...
    emotion_confidence: float = 0.0


@dataclass
class VideoAnalysisResult:
    """视频分析结果"""
    file_path: str
    duration: float
    width: int
    height: int
    fps: float
    total_scenes: int
    scenes: List[SceneSegment] = field(default_factory=list)
    overall_pace: str = "medium"  # slow/medium/fast
    overall_emotion: str = "neutral"
    avg_brightness: float = 0
    avg_contrast: float = 0
    scene_change_frequency: float = 0  # 次/分钟
    detected_effects: List[Dict[str, Any]] = field(default_factory=list)


class VideoAnalyzer:
    """视频分析器"""

    def __init__(self, sample_interval: float = 1.0,
                 scene_threshold: float = 0.3):
        """
        Args:
            sample_interval: 帧采样间隔（秒）
            scene_threshold: 场景切换阈值（0-1，越大越不敏感）
        """
        self.sample_interval = sample_interval
        self.scene_threshold = scene_threshold

    def analyze(self, video_path: str) -> VideoAnalysisResult:
        """完整分析视频"""
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"视频文件不存在: {video_path}")

        # 1. 获取视频元数据
        meta = self._probe_video(video_path)
        result = VideoAnalysisResult(
            file_path=video_path,
            duration=meta["duration"],
            width=meta["width"],
            height=meta["height"],
            fps=meta["fps"],
            total_scenes=0,
        )

        # 2. 采样帧并分析
        frames = self._sample_and_analyze_frames(video_path, meta["duration"])

        # 3. 场景切换检测
        scenes = self._detect_scenes(frames, meta["duration"])
        result.scenes = scenes
        result.total_scenes = len(scenes)

        # 4. 整体统计
        if scenes:
            result.avg_brightness = sum(s.avg_brightness for s in scenes) / len(scenes)
            result.avg_contrast = sum(s.avg_contrast for s in scenes) / len(scenes)
            result.scene_change_frequency = (len(scenes) - 1) / max(meta["duration"] / 60, 0.1)

            # 整体节奏判断
            if result.scene_change_frequency < 6:
                result.overall_pace = "slow"
            elif result.scene_change_frequency < 15:
                result.overall_pace = "medium"
            else:
                result.overall_pace = "fast"

            # 整体情绪（取出现最多的）
            emotion_count = {}
            for s in scenes:
                emotion_count[s.emotion] = emotion_count.get(s.emotion, 0) + 1
            result.overall_emotion = max(emotion_count, key=emotion_count.get)

        # 5. 特效识别（基础框架）
        result.detected_effects = self._detect_effects(frames, scenes)

        return result

    def _probe_video(self, video_path: str) -> Dict[str, Any]:
        """获取视频元数据"""
        result = subprocess.run(
            [FFPROBE, "-v", "quiet", "-print_format", "json",
             "-show_format", "-show_streams", video_path],
            capture_output=True, text=True, timeout=15
        )
        info = json.loads(result.stdout)
        fmt = info.get("format", {})
        streams = info.get("streams", [])
        video_stream = next((s for s in streams if s.get("codec_type") == "video"), {})

        # 解析帧率
        fps_str = video_stream.get("r_frame_rate", "30/1")
        try:
            num, den = fps_str.split("/")
            fps = float(num) / float(den)
        except Exception:
            fps = 30.0

        return {
            "duration": float(fmt.get("duration", 0)),
            "width": int(video_stream.get("width", 1920)),
            "height": int(video_stream.get("height", 1080)),
            "fps": fps,
            "bitrate": int(fmt.get("bit_rate", 0)),
        }

    def _sample_and_analyze_frames(self, video_path: str,
                                     duration: float) -> List[Dict[str, Any]]:
        """采样帧并分析每帧的色彩/亮度"""
        frames = []
        num_samples = int(duration / self.sample_interval) + 1

        with tempfile.TemporaryDirectory() as tmpdir:
            # 用ffmpeg采样帧
            output_pattern = os.path.join(tmpdir, "frame_%04d.png")
            cmd = [
                FFMPEG, "-y", "-i", video_path,
                "-vf", f"fps={1/self.sample_interval},scale=160:90",
                "-q:v", "5",
                output_pattern
            ]
            subprocess.run(cmd, capture_output=True, timeout=60)

            # 分析每帧
            for i in range(num_samples):
                frame_path = os.path.join(tmpdir, f"frame_{i+1:04d}.png")
                if os.path.exists(frame_path):
                    frame_data = self._analyze_frame(frame_path)
                    frame_data["timestamp"] = i * self.sample_interval
                    frames.append(frame_data)

        return frames

    def _analyze_frame(self, frame_path: str) -> Dict[str, Any]:
        """分析单帧的色彩/亮度/对比度"""
        try:
            from PIL import Image
            img = Image.open(frame_path).convert("RGB")
            pixels = list(img.getdata())
            n = len(pixels)

            # 亮度
            brightness = sum(0.299 * r + 0.587 * g + 0.114 * b for r, g, b in pixels) / n

            # 对比度（标准差）
            mean_brightness = brightness
            variance = sum((0.299 * r + 0.587 * g + 0.114 * b - mean_brightness) ** 2
                          for r, g, b in pixels) / n
            contrast = math.sqrt(variance)

            # 主色调（量化到16色）
            color_buckets = {}
            for r, g, b in pixels:
                key = (r // 64, g // 64, b // 64)
                color_buckets[key] = color_buckets.get(key, 0) + 1
            dominant = max(color_buckets, key=color_buckets.get)
            dominant_color = f"#{dominant[0]*64:02x}{dominant[1]*64:02x}{dominant[2]*64:02x}"

            # 色温判断
            avg_r = sum(r for r, g, b in pixels) / n
            avg_b = sum(b for r, g, b in pixels) / n
            if avg_r > avg_b * 1.1:
                color_temp = "warm"
            elif avg_b > avg_r * 1.1:
                color_temp = "cool"
            else:
                color_temp = "neutral"

            return {
                "brightness": brightness,
                "contrast": contrast,
                "dominant_color": dominant_color,
                "color_temperature": color_temp,
                "avg_r": avg_r,
                "avg_b": avg_b,
            }
        except Exception as e:
            return {
                "brightness": 128,
                "contrast": 50,
                "dominant_color": "#000000",
                "color_temperature": "neutral",
                "avg_r": 128,
                "avg_b": 128,
                "error": str(e),
            }

    def _detect_scenes(self, frames: List[Dict[str, Any]],
                        duration: float) -> List[SceneSegment]:
        """基于帧间差异检测场景切换"""
        if not frames:
            return []

        scenes = []
        scene_start = 0.0
        scene_frames = [frames[0]]

        for i in range(1, len(frames)):
            prev = frames[i - 1]
            curr = frames[i]

            # 计算帧间差异（亮度+色彩）
            brightness_diff = abs(curr["brightness"] - prev["brightness"]) / 255
            color_diff = abs(curr["avg_r"] - prev["avg_r"]) + abs(curr["avg_b"] - prev["avg_b"])
            color_diff_norm = color_diff / 510
            total_diff = brightness_diff * 0.6 + color_diff_norm * 0.4

            if total_diff > self.scene_threshold:
                # 场景切换
                scene_end = curr["timestamp"]
                scene = self._build_scene(len(scenes), scene_start, scene_end, scene_frames)
                scenes.append(scene)
                scene_start = scene_end
                scene_frames = [curr]
            else:
                scene_frames.append(curr)

        # 最后一个场景
        if scene_frames:
            scene = self._build_scene(len(scenes), scene_start, duration, scene_frames)
            scenes.append(scene)

        return scenes

    def _build_scene(self, index: int, start: float, end: float,
                      frames: List[Dict[str, Any]]) -> SceneSegment:
        """构建场景片段对象"""
        duration = end - start
        avg_brightness = sum(f["brightness"] for f in frames) / len(frames)
        avg_contrast = sum(f["contrast"] for f in frames) / len(frames)

        # 主色调（取出现最多的）
        color_count = {}
        for f in frames:
            c = f["dominant_color"]
            color_count[c] = color_count.get(c, 0) + 1
        dominant_color = max(color_count, key=color_count.get)

        # 色温
        temp_count = {}
        for f in frames:
            t = f["color_temperature"]
            temp_count[t] = temp_count.get(t, 0) + 1
        color_temp = max(temp_count, key=temp_count.get)

        # 运动水平（基于帧间亮度波动）
        if len(frames) > 1:
            brightness_changes = [abs(frames[i]["brightness"] - frames[i-1]["brightness"])
                                  for i in range(1, len(frames))]
            motion_level = min(1.0, sum(brightness_changes) / len(brightness_changes) / 50)
        else:
            motion_level = 0

        # 场景类型推断（基于亮度+对比度+色温）
        scene_type = self._infer_scene_type(avg_brightness, avg_contrast, color_temp)

        # 情绪推断
        emotion, confidence = self._infer_emotion(
            avg_brightness, avg_contrast, color_temp, motion_level, duration
        )

        return SceneSegment(
            index=index,
            start=start,
            end=end,
            duration=duration,
            avg_brightness=avg_brightness,
            avg_contrast=avg_contrast,
            dominant_color=dominant_color,
            color_temperature=color_temp,
            motion_level=motion_level,
            scene_type=scene_type,
            emotion=emotion,
            emotion_confidence=confidence,
        )

    def _infer_scene_type(self, brightness: float, contrast: float,
                           color_temp: str) -> str:
        """推断场景类型"""
        if brightness < 60:
            return "indoor_dark"
        elif brightness > 200 and contrast < 40:
            return "overexterior"
        elif color_temp == "warm" and brightness > 150:
            return "outdoor_sunny"
        elif color_temp == "cool" and brightness < 100:
            return "indoor"
        elif contrast > 80:
            return "high_contrast"
        else:
            return "general"

    def _infer_emotion(self, brightness: float, contrast: float,
                       color_temp: str, motion: float,
                       duration: float) -> Tuple[str, float]:
        """
        推断情绪（基于色彩+节奏启发式规则）

        Returns:
            (emotion, confidence)
        """
        scores = {
            "happy": 0, "sad": 0, "energetic": 0,
            "calm": 0, "tense": 0, "romantic": 0,
        }

        # 亮度影响
        if brightness > 180:
            scores["happy"] += 2
            scores["energetic"] += 1
        elif brightness < 80:
            scores["sad"] += 2
            scores["tense"] += 1
        else:
            scores["calm"] += 1

        # 对比度影响
        if contrast > 80:
            scores["energetic"] += 1
            scores["tense"] += 1
        elif contrast < 40:
            scores["calm"] += 2
            scores["romantic"] += 1

        # 色温影响
        if color_temp == "warm":
            scores["happy"] += 1
            scores["romantic"] += 1
        elif color_temp == "cool":
            scores["sad"] += 1
            scores["calm"] += 1

        # 运动影响
        if motion > 0.5:
            scores["energetic"] += 2
            scores["tense"] += 1
        elif motion < 0.2:
            scores["calm"] += 1
            scores["sad"] += 1

        # 时长影响（短镜头=快节奏）
        if duration < 2:
            scores["energetic"] += 1
        elif duration > 8:
            scores["calm"] += 1

        # 选择最高分
        best_emotion = max(scores, key=scores.get)
        total_score = sum(scores.values())
        confidence = scores[best_emotion] / max(total_score, 1)

        return best_emotion, round(confidence, 2)

    def _detect_effects(self, frames: List[Dict[str, Any]],
                         scenes: List[SceneSegment]) -> List[Dict[str, Any]]:
        """
        特效识别（基础框架）
        基于帧特征突变检测常见特效
        """
        effects = []

        if len(frames) < 3:
            return effects

        # 检测闪光特效（亮度瞬间峰值）
        for i in range(1, len(frames) - 1):
            prev_b = frames[i - 1]["brightness"]
            curr_b = frames[i]["brightness"]
            next_b = frames[i + 1]["brightness"]

            if curr_b > 200 and curr_b > prev_b * 1.5 and curr_b > next_b * 1.2:
                effects.append({
                    "type": "flash",
                    "timestamp": frames[i]["timestamp"],
                    "confidence": 0.7,
                    "description": "检测到亮度峰值，可能为闪光特效",
                })

        # 检测黑白特效（饱和度为0，即R=G=B）
        for i, frame in enumerate(frames):
            if abs(frame.get("avg_r", 128) - frame.get("avg_b", 128)) < 10:
                effects.append({
                    "type": "black_white",
                    "timestamp": frame["timestamp"],
                    "confidence": 0.6,
                    "description": "检测到低饱和度，可能为黑白滤镜",
                })
                break  # 只报告一次

        # 检测高对比度特效
        high_contrast_scenes = [s for s in scenes if s.avg_contrast > 100]
        if high_contrast_scenes:
            effects.append({
                "type": "high_contrast",
                "scenes": [s.index for s in high_contrast_scenes],
                "confidence": 0.5,
                "description": f"{len(high_contrast_scenes)}个场景对比度异常高，可能使用了对比度特效",
            })

        return effects

    def export_json(self, result: VideoAnalysisResult, output_path: str):
        """导出分析结果为JSON"""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        data = {
            "file_path": result.file_path,
            "duration": result.duration,
            "width": result.width,
            "height": result.height,
            "fps": result.fps,
            "total_scenes": result.total_scenes,
            "overall_pace": result.overall_pace,
            "overall_emotion": result.overall_emotion,
            "avg_brightness": round(result.avg_brightness, 2),
            "avg_contrast": round(result.avg_contrast, 2),
            "scene_change_frequency": round(result.scene_change_frequency, 2),
            "scenes": [asdict(s) for s in result.scenes],
            "detected_effects": result.detected_effects,
        }
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return output_path


def main():
    import argparse
    parser = argparse.ArgumentParser(description="视频内容理解引擎")
    parser.add_argument("video", help="视频文件路径")
    parser.add_argument("-o", "--output", help="输出JSON路径（可选）")
    parser.add_argument("--interval", type=float, default=1.0, help="采样间隔（秒）")
    parser.add_argument("--threshold", type=float, default=0.3, help="场景切换阈值")
    args = parser.parse_args()

    analyzer = VideoAnalyzer(sample_interval=args.interval, scene_threshold=args.threshold)
    result = analyzer.analyze(args.video)

    logger.info(f"=== 视频分析结果 ===")
    logger.info(f"文件: {result.file_path}")
    logger.info(f"时长: {result.duration:.1f}秒 | 分辨率: {result.width}x{result.height} | {result.fps}fps")
    logger.info(f"场景数: {result.total_scenes} | 节奏: {result.overall_pace} | 整体情绪: {result.overall_emotion}")
    logger.info(f"平均亮度: {result.avg_brightness:.1f} | 平均对比度: {result.avg_contrast:.1f}")
    logger.info(f"场景切换频率: {result.scene_change_frequency:.1f}次/分钟")
    logger.info(f"\n=== 场景详情 ===")
    for s in result.scenes:
        logger.info(f"  场景{s.index}: {s.start:.1f}-{s.end:.1f}s ({s.duration:.1f}s) "
              f"类型={s.scene_type} 情绪={s.emotion}({s.emotion_confidence}) "
              f"亮度={s.avg_brightness:.0f} 运动={s.motion_level:.2f}")

    if result.detected_effects:
        logger.info(f"\n=== 检测到的特效 ===")
        for e in result.detected_effects:
            logger.info(f"  {e['type']}: {e['description']} (置信度={e.get('confidence', 0)})")

    if args.output:
        path = analyzer.export_json(result, args.output)
        logger.info(f"\n分析结果已保存: {path}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
