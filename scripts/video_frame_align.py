"""
视频帧对齐工具
将视频裁剪到精确帧边界，解决质量门E006帧对齐失败问题

使用方法:
    from video_frame_align import align_video_to_frames, get_video_duration
    aligned = align_video_to_frames("input.mp4", "output.mp4", fps=30)
"""

import logging
logger = logging.getLogger(__name__)


import os
import subprocess
import json
from typing import Optional

FFMPEG_PATH = r"D:\Ai\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe"
FFPROBE_PATH = r"D:\Ai\ffmpeg-master-latest-win64-gpl\bin\ffprobe.exe"


def get_video_info(video_path: str) -> dict:
    """获取视频元信息（时长、帧率、分辨率）"""
    if not os.path.exists(video_path):
        return {}
    try:
        result = subprocess.run(
            [FFPROBE_PATH, "-v", "quiet", "-print_format", "json",
             "-show_format", "-show_streams", video_path],
            capture_output=True, text=True, timeout=30
        )
        data = json.loads(result.stdout)
        stream = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), {})
        duration = float(data.get("format", {}).get("duration", 0))
        fps_str = stream.get("r_frame_rate", "30/1")
        if "/" in fps_str:
            num, den = fps_str.split("/")
            fps = float(num) / float(den) if float(den) != 0 else 30.0
        else:
            fps = float(fps_str)
        return {
            "duration": duration,
            "fps": fps,
            "width": stream.get("width", 0),
            "height": stream.get("height", 0),
            "codec": stream.get("codec_name", ""),
        }
    except Exception as e:
        logger.error(f"获取视频信息失败: {e}")
        return {}


def align_video_to_frames(
    video_path: str,
    output_path: str,
    target_duration: float = None,
    fps: int = 30,
) -> Optional[str]:
    """
    将视频对齐到精确帧边界

    Args:
        video_path: 输入视频路径
        output_path: 输出视频路径
        target_duration: 目标时长（秒），None则自动取整到最近帧
        fps: 目标帧率

    Returns:
        输出路径或None
    """
    if not os.path.exists(video_path):
        logger.info(f"视频不存在: {video_path}")
        return None

    info = get_video_info(video_path)
    if not info:
        return None

    src_duration = info["duration"]
    frame_dur = 1.0 / fps

    if target_duration:
        # 裁剪到目标时长（向下取整到帧边界）
        target_frames = int(target_duration / frame_dur)
        aligned_duration = target_frames * frame_dur
    else:
        # 自动取整到最近帧（向下取整，避免黑帧）
        target_frames = int(src_duration / frame_dur)
        aligned_duration = target_frames * frame_dur

    # 如果已经对齐，直接复制
    if abs(src_duration - aligned_duration) < 0.001:
        import shutil
        shutil.copy2(video_path, output_path)
        return output_path

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    try:
        cmd = [
            FFMPEG_PATH, "-y",
            "-i", video_path,
            "-t", f"{aligned_duration:.6f}",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            "-r", str(fps),
            output_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            new_info = get_video_info(output_path)
            logger.info(f"  对齐: {src_duration:.3f}s -> {new_info.get('duration', 0):.3f}s ({target_frames}帧@{fps}fps)")
            return output_path
        else:
            logger.error(f"  对齐失败: {result.stderr[-200:] if result.stderr else 'unknown'}")
            return None
    except Exception as e:
        logger.info(f"  对齐异常: {e}")
        return None


def batch_align_videos(
    video_paths: list,
    output_dir: str,
    target_durations: list = None,
    fps: int = 30,
) -> list:
    """
    批量对齐视频

    Args:
        video_paths: 输入视频路径列表
        output_dir: 输出目录
        target_durations: 每个视频的目标时长（None则自动取整）
        fps: 帧率

    Returns:
        对齐后的视频路径列表
    """
    os.makedirs(output_dir, exist_ok=True)
    results = []
    for i, vpath in enumerate(video_paths):
        if not os.path.exists(vpath):
            results.append(None)
            continue
        basename = os.path.splitext(os.path.basename(vpath))[0]
        out_path = os.path.join(output_dir, f"{basename}_aligned.mp4")
        target = target_durations[i] if target_durations and i < len(target_durations) else None
        aligned = align_video_to_frames(vpath, out_path, target_duration=target, fps=fps)
        results.append(aligned)
    return results


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        video = sys.argv[1]
        info = get_video_info(video)
        logger.info(f"视频: {video}")
        logger.info(f"  时长: {info.get('duration', 0):.3f}s")
        logger.info(f"  帧率: {info.get('fps', 0):.1f}fps")
        logger.info(f"  分辨率: {info.get('width', 0)}x{info.get('height', 0)}")
        if info:
            frame_dur = 1.0 / 30
            frames = int(info["duration"] / frame_dur)
            logger.info(f"  30fps帧数: {frames} (对齐后时长: {frames * frame_dur:.3f}s)")
    else:
        logger.info("用法: python video_frame_align.py <video_path>")
