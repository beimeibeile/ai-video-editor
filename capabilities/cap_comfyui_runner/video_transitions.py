"""
视频转场效果生成工具
使用ffmpeg xfade滤镜实现视频之间的各种转场效果
支持淡入淡出、滑动、缩放、旋转等多种转场
"""
import os
import subprocess
from typing import List, Optional, Tuple


# 可用的转场效果列表
TRANSITION_EFFECTS = [
    "fade", "fadeblack", "fadewhite", "fadegrays",
    "slideleft", "slideright", "slideup", "slidedown",
    "circleopen", "circleclose", "circlecrop",
    "rectcrop", "distance", "wipeleft", "wiperight", "wipeup", "wipedown",
    "smoothleft", "smoothright", "smoothup", "smoothdown",
    "rectcrop", "circlecrop", "radial", "hblur", "wipetl", "wipetr", "wipebl", "wipebr",
    "zoomin", "zoomout",
]


def concat_with_transition(
    video_paths: List[str],
    output_path: str,
    transition: str = "fade",
    transition_duration: float = 0.5,
    ffmpeg_path: str = r"D:\Ai\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe",
) -> str:
    """
    将多个视频用转场效果拼接在一起

    Args:
        video_paths: 视频路径列表（至少2个）
        output_path: 输出视频路径
        transition: 转场效果名称（见TRANSITION_EFFECTS）
        transition_duration: 转场持续时间（秒）
        ffmpeg_path: ffmpeg路径

    Returns:
        输出视频路径
    """
    if len(video_paths) < 2:
        raise ValueError("至少需要2个视频")

    if transition not in TRANSITION_EFFECTS:
        raise ValueError(f"未知转场效果: {transition}，可用: {TRANSITION_EFFECTS}")

    # 获取每个视频的时长
    from .ffmpeg_utils import get_video_info_simple
    ffprobe_path = ffmpeg_path.replace("ffmpeg", "ffprobe")
    durations = []
    for v in video_paths:
        info = get_video_info_simple(v, ffprobe_path=ffprobe_path)
        durations.append(info.get("duration", 0))

    # 构建xfade滤镜链
    # 第一个视频作为基础，后续视频依次叠加
    filter_parts = []
    current_offset = 0

    for i in range(1, len(video_paths)):
        prev_duration = durations[i - 1]
        # 计算偏移量（前一个视频的结束时间减去转场持续时间）
        offset = current_offset + prev_duration - transition_duration
        current_offset = offset

        if i == 1:
            # 第一次转场：[0:v][1:v]xfade
            filter_parts.append(
                f"[0:v][1:v]xfade=transition={transition}:duration={transition_duration}:offset={offset}[v{i}]"
            )
        else:
            # 后续转场：[v{i-1}][i:v]xfade
            filter_parts.append(
                f"[v{i-1}][{i}:v]xfade=transition={transition}:duration={transition_duration}:offset={offset}[v{i}]"
            )

    # 最后一个输出标签
    last_label = f"[v{len(video_paths)-1}]"

    filter_str = ";".join(filter_parts)

    # 构建ffmpeg命令
    cmd = [ffmpeg_path, "-y"]
    for v in video_paths:
        cmd.extend(["-i", v])

    cmd.extend([
        "-filter_complex", filter_str,
        "-map", last_label,
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "20",
        output_path
    ])

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg失败: {result.stderr[-500:]}")

    return output_path


def add_transition_between(
    video1: str,
    video2: str,
    output_path: str,
    transition: str = "fade",
    transition_duration: float = 0.5,
    ffmpeg_path: str = r"D:\Ai\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe",
) -> str:
    """
    在两个视频之间添加转场效果

    Args:
        video1: 第一个视频路径
        video2: 第二个视频路径
        output_path: 输出视频路径
        transition: 转场效果名称
        transition_duration: 转场持续时间（秒）
        ffmpeg_path: ffmpeg路径

    Returns:
        输出视频路径
    """
    return concat_with_transition(
        [video1, video2], output_path, transition, transition_duration, ffmpeg_path
    )


def list_transitions() -> List[str]:
    """列出所有可用的转场效果"""
    return TRANSITION_EFFECTS.copy()


__all__ = ["concat_with_transition", "add_transition_between", "list_transitions", "TRANSITION_EFFECTS"]


if __name__ == "__main__":
    print("视频转场效果工具已加载")
    print("可用转场效果:")
    for i, effect in enumerate(TRANSITION_EFFECTS):
        print(f"  {i+1}. {effect}")
