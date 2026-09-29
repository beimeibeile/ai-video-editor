"""
视频字幕烧录工具
使用ffmpeg将字幕文件烧录到视频中
支持SRT/ASS格式，支持字体、大小、颜色等样式配置
"""
import os
import subprocess
from typing import Optional, Tuple


def burn_subtitles(
    video_path: str,
    subtitle_path: str,
    output_path: str = None,
    font_size: int = 24,
    font_color: str = "white",
    outline_color: str = "black",
    outline_width: int = 2,
    position: str = "bottom",  # top / center / bottom
    margin_v: int = 40,
    ffmpeg_path: str = r"D:\Ai\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe",
) -> str:
    """
    将字幕烧录到视频中（硬字幕）

    Args:
        video_path: 输入视频路径
        subtitle_path: 字幕文件路径（.srt / .ass）
        output_path: 输出视频路径（None则自动命名）
        font_size: 字体大小
        font_color: 字体颜色（white/black/yellow/red等，或十六进制）
        outline_color: 描边颜色
        outline_width: 描边宽度
        position: 位置（top/center/bottom）
        margin_v: 垂直边距（像素）
        ffmpeg_path: ffmpeg路径

    Returns:
        输出视频路径
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"视频不存在: {video_path}")
    if not os.path.exists(subtitle_path):
        raise FileNotFoundError(f"字幕文件不存在: {subtitle_path}")

    if output_path is None:
        base, ext = os.path.splitext(video_path)
        output_path = f"{base}_subtitled{ext}"

    # 位置映射
    pos_map = {"top": "0", "center": "50", "bottom": "100"}
    alignment = pos_map.get(position, "100")

    # 构建subtitles滤镜参数
    # 注意：Windows路径需要转义反斜杠和冒号
    sub_path_escaped = subtitle_path.replace("\\", "/").replace(":", "\\:")

    force_style = (
        f"FontSize={font_size},"
        f"PrimaryColour=&H{_color_to_ass(font_color)}&,"
        f"OutlineColour=&H{_color_to_ass(outline_color)}&,"
        f"Outline={outline_width},"
        f"Alignment={alignment},"
        f"MarginV={margin_v}"
    )

    filter_str = f"subtitles='{sub_path_escaped}':force_style='{force_style}'"

    cmd = [
        ffmpeg_path, "-y",
        "-i", video_path,
        "-vf", filter_str,
        "-c:a", "copy",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "20",
        output_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg失败: {result.stderr[-500:]}")

    return output_path


def _color_to_ass(color: str) -> str:
    """将颜色名或十六进制转换为ASS格式（BGR）"""
    color_map = {
        "white": "00FFFFFF", "black": "00000000",
        "red": "000000FF", "green": "0000FF00",
        "blue": "00FF0000", "yellow": "0000FFFF",
        "cyan": "00FFFF00", "magenta": "00FF00FF",
        "orange": "0000A5FF", "pink": "00CBC0FF",
    }
    if color.lower() in color_map:
        return color_map[color.lower()]
    # 十六进制 #RRGGBB -> AABBGGRR
    if color.startswith("#") and len(color) == 7:
        r, g, b = color[1:3], color[3:5], color[5:7]
        return f"00{b}{g}{r}"
    return "00FFFFFF"  # 默认白色


def create_srt(
    subtitles: list,
    output_path: str,
) -> str:
    """
    创建SRT字幕文件

    Args:
        subtitles: 字幕列表，每个元素为 (start_seconds, end_seconds, text)
        output_path: 输出SRT文件路径

    Returns:
        SRT文件路径
    """
    with open(output_path, "w", encoding="utf-8") as f:
        for i, (start, end, text) in enumerate(subtitles, 1):
            f.write(f"{i}\n")
            f.write(f"{_format_srt_time(start)} --> {_format_srt_time(end)}\n")
            f.write(f"{text}\n\n")
    return output_path


def _format_srt_time(seconds: float) -> str:
    """将秒数格式化为SRT时间格式 HH:MM:SS,mmm"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


__all__ = ["burn_subtitles", "create_srt"]


if __name__ == "__main__":
    print("视频字幕烧录工具已加载")
    print("可用函数: burn_subtitles, create_srt")
