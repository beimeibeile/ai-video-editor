"""
cap_video_analyzer — 视频分析模块
视频信息提取、场景检测、关键帧提取、缩略图生成

依赖：ffmpeg/ffprobe
"""
import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Optional, List, Dict


def _find_ffprobe() -> Optional[str]:
    """查找ffprobe可执行文件"""
    candidates = [
        "ffprobe",
        r"C:\ffmpeg\bin\ffprobe.exe",
        r"C:\Program Files\ffmpeg\bin\ffprobe.exe",
    ]
    for c in candidates:
        try:
            result = subprocess.run([c, "-version"], capture_output=True, timeout=5)
            if result.returncode == 0:
                return c
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return None


def _find_ffmpeg() -> Optional[str]:
    """查找ffmpeg可执行文件"""
    candidates = [
        "ffmpeg",
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
    ]
    for c in candidates:
        try:
            result = subprocess.run([c, "-version"], capture_output=True, timeout=5)
            if result.returncode == 0:
                return c
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return None


FFPROBE = _find_ffprobe()
FFMPEG = _find_ffmpeg()


def get_video_info(video_path: str) -> Dict:
    """
    获取视频基本信息

    Returns:
        {duration, width, height, fps, bitrate, codec, has_audio, audio_codec}
    """
    if not FFPROBE:
        return {"error": "ffprobe not found"}

    if not os.path.exists(video_path):
        return {"error": f"file not found: {video_path}"}

    try:
        cmd = [
            FFPROBE, "-v", "quiet", "-print_format", "json",
            "-show_format", "-show_streams", video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        data = json.loads(result.stdout)

        video_stream = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), None)
        audio_stream = next((s for s in data.get("streams", []) if s.get("codec_type") == "audio"), None)

        info = {
            "duration": float(data.get("format", {}).get("duration", 0)),
            "bitrate": int(data.get("format", {}).get("bit_rate", 0)),
            "size": int(data.get("format", {}).get("size", 0)),
        }

        if video_stream:
            info["width"] = int(video_stream.get("width", 0))
            info["height"] = int(video_stream.get("height", 0))
            info["codec"] = video_stream.get("codec_name", "")
            # 解析帧率
            r_frame_rate = video_stream.get("r_frame_rate", "0/1")
            num, den = map(int, r_frame_rate.split("/"))
            info["fps"] = round(num / den, 2) if den > 0 else 0

        if audio_stream:
            info["has_audio"] = True
            info["audio_codec"] = audio_stream.get("codec_name", "")
            info["audio_channels"] = audio_stream.get("channels", 0)
        else:
            info["has_audio"] = False

        return info
    except Exception as e:
        return {"error": str(e)}


def detect_scenes(video_path: str, threshold: float = 0.3) -> List[float]:
    """
    场景检测（基于帧差异）

    Args:
        video_path: 视频路径
        threshold: 场景切换阈值（0.1-1.0，越小越敏感）

    Returns:
        场景切换时间点列表（秒）
    """
    if not FFMPEG:
        return []

    try:
        cmd = [
            FFMPEG, "-i", video_path,
            "-filter:v", f"select='gt(scene,{threshold})',showinfo",
            "-f", "null", "-"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        scenes = []
        for line in result.stderr.split("\n"):
            if "showinfo" in line and "pts_time:" in line:
                try:
                    time_str = line.split("pts_time:")[1].split()[0]
                    scenes.append(round(float(time_str), 2))
                except (IndexError, ValueError):
                    continue

        return sorted(set(scenes))
    except Exception:
        return []


def extract_keyframes(video_path: str, output_dir: str,
                      num_frames: int = 5) -> List[str]:
    """
    提取关键帧（均匀采样）

    Args:
        video_path: 视频路径
        output_dir: 输出目录
        num_frames: 提取帧数

    Returns:
        提取的帧文件路径列表
    """
    if not FFMPEG:
        return []

    os.makedirs(output_dir, exist_ok=True)

    info = get_video_info(video_path)
    duration = info.get("duration", 0)
    if duration <= 0:
        return []

    frames = []
    interval = duration / (num_frames + 1)

    for i in range(1, num_frames + 1):
        timestamp = interval * i
        output_path = os.path.join(output_dir, f"keyframe_{i:03d}.jpg")

        try:
            cmd = [
                FFMPEG, "-y", "-ss", str(timestamp),
                "-i", video_path,
                "-vframes", "1", "-q:v", "2",
                output_path
            ]
            subprocess.run(cmd, capture_output=True, timeout=30)
            if os.path.exists(output_path):
                frames.append(output_path)
        except Exception:
            continue

    return frames


def generate_thumbnail(video_path: str, output_path: str,
                       timestamp: float = 1.0,
                       width: int = 320) -> Optional[str]:
    """
    生成视频缩略图

    Args:
        video_path: 视频路径
        output_path: 输出路径
        timestamp: 截图时间点（秒）
        width: 缩略图宽度

    Returns:
        缩略图路径，失败返回None
    """
    if not FFMPEG:
        return None

    try:
        cmd = [
            FFMPEG, "-y", "-ss", str(timestamp),
            "-i", video_path,
            "-vframes", "1", "-q:v", "3",
            "-vf", f"scale={width}:-1",
            output_path
        ]
        subprocess.run(cmd, capture_output=True, timeout=30)
        return output_path if os.path.exists(output_path) else None
    except Exception:
        return None


def analyze_video(video_path: str, output_dir: str = None) -> Dict:
    """
    完整视频分析（信息+场景+关键帧）

    Args:
        video_path: 视频路径
        output_dir: 输出目录（关键帧/缩略图）

    Returns:
        分析结果字典
    """
    result = {
        "path": video_path,
        "info": get_video_info(video_path),
        "scenes": [],
        "keyframes": [],
        "thumbnail": None,
    }

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        result["scenes"] = detect_scenes(video_path)
        result["keyframes"] = extract_keyframes(video_path, output_dir)
        result["thumbnail"] = generate_thumbnail(
            video_path, os.path.join(output_dir, "thumbnail.jpg")
        )

    return result


def is_available() -> bool:
    """检查ffmpeg/ffprobe是否可用"""
    return FFMPEG is not None and FFPROBE is not None
