"""
视频水印工具
使用ffmpeg为视频添加文字/图片水印
支持位置、大小、透明度、时间范围等配置
"""
import os
import subprocess
from typing import Optional, Tuple


def add_text_watermark(
    video_path: str,
    text: str,
    output_path: str = None,
    font_size: int = 36,
    font_color: str = "white",
    position: str = "bottom-right",
    opacity: float = 0.8,
    margin_x: int = 30,
    margin_y: int = 30,
    start_time: float = None,
    end_time: float = None,
    ffmpeg_path: str = r"D:\Ai\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe",
) -> str:
    """
    为视频添加文字水印

    Args:
        video_path: 输入视频路径
        text: 水印文字
        output_path: 输出视频路径（None则自动命名）
        font_size: 字体大小
        font_color: 字体颜色
        position: 位置（top-left/top-right/top-center/bottom-left/bottom-right/bottom-center/center）
        opacity: 不透明度（0-1）
        margin_x: 水平边距
        margin_y: 垂直边距
        start_time: 开始显示时间（秒，None则从开头）
        end_time: 结束显示时间（秒，None则到结尾）
        ffmpeg_path: ffmpeg路径

    Returns:
        输出视频路径
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"视频不存在: {video_path}")

    if output_path is None:
        base, ext = os.path.splitext(video_path)
        output_path = f"{base}_watermarked{ext}"

    # 位置映射
    pos_map = {
        "top-left": f"x={margin_x}:y={margin_y}",
        "top-right": f"x=w-tw-{margin_x}:y={margin_y}",
        "top-center": f"x=(w-tw)/2:y={margin_y}",
        "bottom-left": f"x={margin_x}:y=h-th-{margin_y}",
        "bottom-right": f"x=w-tw-{margin_x}:y=h-th-{margin_y}",
        "bottom-center": f"x=(w-tw)/2:y=h-th-{margin_y}",
        "center": "x=(w-tw)/2:y=(h-th)/2",
    }
    pos = pos_map.get(position, pos_map["bottom-right"])

    # 构建drawtext滤镜
    drawtext = (
        f"drawtext=text='{text}':"
        f"fontsize={font_size}:"
        f"fontcolor={font_color}@{opacity}:"
        f"{pos}"
    )

    # 时间范围
    if start_time is not None or end_time is not None:
        enable_parts = []
        if start_time is not None:
            enable_parts.append(f"gte(t,{start_time})")
        if end_time is not None:
            enable_parts.append(f"lte(t,{end_time})")
        enable = "*".join(enable_parts)
        drawtext += f":enable='{enable}'"

    # 添加描边
    drawtext += ":box=1:boxcolor=black@0.3:boxborderw=10"

    cmd = [
        ffmpeg_path, "-y",
        "-i", video_path,
        "-vf", drawtext,
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


def add_image_watermark(
    video_path: str,
    watermark_path: str,
    output_path: str = None,
    position: str = "bottom-right",
    opacity: float = 0.8,
    scale: float = 0.2,
    margin_x: int = 30,
    margin_y: int = 30,
    ffmpeg_path: str = r"D:\Ai\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe",
) -> str:
    """
    为视频添加图片水印

    Args:
        video_path: 输入视频路径
        watermark_path: 水印图片路径
        output_path: 输出视频路径（None则自动命名）
        position: 位置
        opacity: 不透明度（0-1）
        scale: 水印缩放比例（相对于视频宽度）
        margin_x: 水平边距
        margin_y: 垂直边距
        ffmpeg_path: ffmpeg路径

    Returns:
        输出视频路径
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"视频不存在: {video_path}")
    if not os.path.exists(watermark_path):
        raise FileNotFoundError(f"水印图片不存在: {watermark_path}")

    if output_path is None:
        base, ext = os.path.splitext(video_path)
        output_path = f"{base}_imgwatermarked{ext}"

    # 位置映射
    pos_map = {
        "top-left": f"{margin_x}:{margin_y}",
        "top-right": f"W-w-{margin_x}:{margin_y}",
        "top-center": f"(W-w)/2:{margin_y}",
        "bottom-left": f"{margin_x}:H-h-{margin_y}",
        "bottom-right": f"W-w-{margin_x}:H-h-{margin_y}",
        "bottom-center": f"(W-w)/2:H-h-{margin_y}",
        "center": "(W-w)/2:(H-h)/2",
    }
    pos = pos_map.get(position, pos_map["bottom-right"])

    # 构建overlay滤镜
    # 先缩放水印，再设置透明度，最后叠加
    filter_str = (
        f"[1:v]scale=iw*{scale}:-1,format=rgba,"
        f"colorchannelmixer=aa={opacity}[wm];"
        f"[0:v][wm]overlay={pos}"
    )

    cmd = [
        ffmpeg_path, "-y",
        "-i", video_path,
        "-i", watermark_path,
        "-filter_complex", filter_str,
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


__all__ = ["add_text_watermark", "add_image_watermark"]


if __name__ == "__main__":
    print("视频水印工具已加载")
    print("可用函数: add_text_watermark, add_image_watermark")
