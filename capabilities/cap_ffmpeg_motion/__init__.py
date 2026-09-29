"""
cap_ffmpeg_motion - FFmpeg轻量级动效工具集

零GPU消耗，秒级生成，适合批量处理和快速动效
"""
from .ffmpeg_motion import FFmpegMotion, get_ffmpeg_motion

__all__ = ["FFmpegMotion", "get_ffmpeg_motion"]
