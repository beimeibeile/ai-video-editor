"""
视频绿幕抠像与背景替换工具
使用ffmpeg chromakey滤镜实现绿幕/蓝幕抠像和背景替换
"""
import os
import subprocess
from typing import Optional, Tuple


def chroma_key(
    video_path: str,
    output_path: str = None,
    color: str = "green",  # green / blue / red / custom
    similarity: float = 0.3,  # 0.01 ~ 1.0
    blend: float = 0.1,  # 0.0 ~ 1.0
    ffmpeg_path: str = r"D:\Ai\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe",
) -> str:
    """
    视频绿幕抠像（输出透明背景WebM或带alpha通道的视频）

    Args:
        video_path: 输入视频路径
        output_path: 输出视频路径（建议.webm格式以保留alpha通道）
        color: 背景颜色（green/blue/red/custom）
        similarity: 颜色相似度（0.01-1.0，越大抠除范围越大）
        blend: 边缘融合度（0-1，越大边缘越柔和）
        ffmpeg_path: ffmpeg路径

    Returns:
        输出视频路径
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"视频不存在: {video_path}")

    if output_path is None:
        base, ext = os.path.splitext(video_path)
        output_path = f"{base}_chromakey.webm"

    # 颜色映射
    color_map = {
        "green": "0x00FF00",
        "blue": "0x0000FF",
        "red": "0xFF0000",
    }
    color_hex = color_map.get(color, color)

    # chromakey滤镜
    filter_str = f"chromakey={color_hex}:{similarity}:{blend},format=yuva420p"

    cmd = [
        ffmpeg_path, "-y",
        "-i", video_path,
        "-vf", filter_str,
        "-c:v", "libvpx-vp9",
        "-b:v", "2M",
        "-c:a", "libvorbis",
        output_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg失败: {result.stderr[-500:]}")

    return output_path


def replace_background(
    foreground_video: str,
    background_image: str,
    output_path: str = None,
    color: str = "green",
    similarity: float = 0.3,
    blend: float = 0.1,
    ffmpeg_path: str = r"D:\Ai\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe",
) -> str:
    """
    绿幕视频背景替换

    Args:
        foreground_video: 前景视频路径（绿幕视频）
        background_image: 背景图片路径
        output_path: 输出视频路径
        color: 背景颜色（green/blue/red）
        similarity: 颜色相似度
        blend: 边缘融合度
        ffmpeg_path: ffmpeg路径

    Returns:
        输出视频路径
    """
    if not os.path.exists(foreground_video):
        raise FileNotFoundError(f"前景视频不存在: {foreground_video}")
    if not os.path.exists(background_image):
        raise FileNotFoundError(f"背景图片不存在: {background_image}")

    if output_path is None:
        base, ext = os.path.splitext(foreground_video)
        output_path = f"{base}_bgreplaced{ext}"

    # 颜色映射
    color_map = {
        "green": "0x00FF00",
        "blue": "0x0000FF",
        "red": "0xFF0000",
    }
    color_hex = color_map.get(color, color)

    # 先抠像，再叠加背景
    # [0:v]是前景视频，[1:v]是背景图片
    # 背景图片需要循环播放以匹配视频长度
    filter_str = (
        f"[0:v]chromakey={color_hex}:{similarity}:{blend}[fg];"
        f"[1:v]loop=loop=-1:size=1:start=0,scale=iw:ih[bg];"
        f"[bg][fg]overlay=shortest=1"
    )

    cmd = [
        ffmpeg_path, "-y",
        "-i", foreground_video,
        "-i", background_image,
        "-filter_complex", filter_str,
        "-c:a", "copy",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "20",
        output_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg失败: {result.stderr[-500:]}")

    return output_path


def color_key_replace(
    video_path: str,
    output_path: str = None,
    target_color: str = "green",
    replacement_color: str = "black",
    similarity: float = 0.3,
    ffmpeg_path: str = r"D:\Ai\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe",
) -> str:
    """
    将视频中指定颜色替换为另一种颜色（简单颜色替换）

    Args:
        video_path: 输入视频路径
        output_path: 输出视频路径
        target_color: 目标颜色（green/blue/red/white/black或十六进制）
        replacement_color: 替换颜色
        similarity: 颜色相似度
        ffmpeg_path: ffmpeg路径

    Returns:
        输出视频路径
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"视频不存在: {video_path}")

    if output_path is None:
        base, ext = os.path.splitext(video_path)
        output_path = f"{base}_colorreplace{ext}"

    # 颜色映射
    color_map = {
        "green": "0x00FF00",
        "blue": "0x0000FF",
        "red": "0xFF0000",
        "white": "0xFFFFFF",
        "black": "0x000000",
    }
    target_hex = color_map.get(target_color, target_color)
    replace_hex = color_map.get(replacement_color, replacement_color)

    # 使用colorkey滤镜将目标颜色变为透明，然后填充替换颜色
    filter_str = f"colorkey={target_hex}:{similarity}:0.1,format=rgba,colorchannelmixer=rr=0:gg=0:bb=0:aa=0[bg];[bg]drawbox=x=0:y=0:w=iw:h=ih:color={replace_hex}:t=fill[base];[base][0:v]overlay"

    # 简化方案：直接用chromakey+纯色背景
    filter_str = (
        f"[0:v]chromakey={target_hex}:{similarity}:0.1[fg];"
        f"color=c={replace_hex}:s=1920x1080:d=1[bg];"
        f"[bg][fg]overlay=shortest=1"
    )

    cmd = [
        ffmpeg_path, "-y",
        "-i", video_path,
        "-filter_complex", filter_str,
        "-c:a", "copy",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "20",
        output_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg失败: {result.stderr[-500:]}")

    return output_path


__all__ = ["chroma_key", "replace_background", "color_key_replace"]


if __name__ == "__main__":
    print("视频绿幕抠像工具已加载")
    print("可用函数: chroma_key, replace_background, color_key_replace")
