"""
视频后处理工具
使用ffmpeg实现视频降噪、锐化、模糊、稳定等后处理功能
"""
import os
import subprocess
from typing import Optional


def denoise_video(
    video_path: str,
    output_path: str = None,
    strength: float = 4.0,  # 1.0 ~ 10.0
    ffmpeg_path: str = r"D:\Ai\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe",
) -> str:
    """
    视频降噪（hqdn3d滤镜）

    Args:
        video_path: 输入视频路径
        output_path: 输出视频路径
        strength: 降噪强度（1-10，4为中等）
        ffmpeg_path: ffmpeg路径

    Returns:
        输出视频路径
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"视频不存在: {video_path}")

    if output_path is None:
        base, ext = os.path.splitext(video_path)
        output_path = f"{base}_denoised{ext}"

    # hqdn3d参数: luma_spatial, chroma_spatial, luma_tmp, chroma_tmp
    lum_spat = strength
    chrom_spat = strength * 0.75
    lum_tmp = strength * 1.5
    chrom_tmp = strength * 1.5

    filter_str = f"hqdn3d={lum_spat}:{chrom_spat}:{lum_tmp}:{chrom_tmp}"

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

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg失败: {result.stderr[-500:]}")

    return output_path


def sharpen_video(
    video_path: str,
    output_path: str = None,
    strength: float = 1.0,  # 0.1 ~ 3.0
    ffmpeg_path: str = r"D:\Ai\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe",
) -> str:
    """
    视频锐化（unsharp滤镜）

    Args:
        video_path: 输入视频路径
        output_path: 输出视频路径
        strength: 锐化强度（0.1-3，1为中等）
        ffmpeg_path: ffmpeg路径

    Returns:
        输出视频路径
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"视频不存在: {video_path}")

    if output_path is None:
        base, ext = os.path.splitext(video_path)
        output_path = f"{base}_sharpened{ext}"

    # unsharp参数: luma_msize_x, luma_msize_y, luma_amount
    amount = strength * 0.8
    filter_str = f"unsharp=5:5:{amount}:5:5:{amount * 0.5}"

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

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg失败: {result.stderr[-500:]}")

    return output_path


def blur_video(
    video_path: str,
    output_path: str = None,
    strength: float = 5.0,  # 1 ~ 30
    ffmpeg_path: str = r"D:\Ai\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe",
) -> str:
    """
    视频模糊（boxblur滤镜）

    Args:
        video_path: 输入视频路径
        output_path: 输出视频路径
        strength: 模糊强度（1-30，5为中等）
        ffmpeg_path: ffmpeg路径

    Returns:
        输出视频路径
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"视频不存在: {video_path}")

    if output_path is None:
        base, ext = os.path.splitext(video_path)
        output_path = f"{base}_blurred{ext}"

    filter_str = f"boxblur={strength}:1"

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

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg失败: {result.stderr[-500:]}")

    return output_path


def stabilize_video(
    video_path: str,
    output_path: str = None,
    ffmpeg_path: str = r"D:\Ai\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe",
) -> str:
    """
    视频稳定（vidstabdetect + vidstabtransform两步处理）

    Args:
        video_path: 输入视频路径
        output_path: 输出视频路径
        ffmpeg_path: ffmpeg路径

    Returns:
        输出视频路径
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"视频不存在: {video_path}")

    if output_path is None:
        base, ext = os.path.splitext(video_path)
        output_path = f"{base}_stabilized{ext}"

    # Step 1: 检测运动
    transform_file = output_path + ".trf"
    cmd1 = [
        ffmpeg_path, "-y",
        "-i", video_path,
        "-vf", f"vidstabdetect=result={transform_file}:shakiness=10:accuracy=15",
        "-f", "null",
        "-"
    ]
    result1 = subprocess.run(cmd1, capture_output=True, text=True, timeout=600)
    if result1.returncode != 0:
        raise RuntimeError(f"稳定检测失败: {result1.stderr[-500:]}")

    # Step 2: 应用稳定
    cmd2 = [
        ffmpeg_path, "-y",
        "-i", video_path,
        "-vf", f"vidstabtransform=input={transform_file}:zoom=5:smoothing=30",
        "-c:a", "copy",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "20",
        output_path
    ]
    result2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=600)
    if result2.returncode != 0:
        raise RuntimeError(f"稳定变换失败: {result2.stderr[-500:]}")

    # 清理临时文件
    try:
        os.remove(transform_file)
    except Exception:
        pass

    return output_path


def enhance_video(
    video_path: str,
    output_path: str = None,
    denoise: bool = True,
    sharpen: bool = True,
    denoise_strength: float = 3.0,
    sharpen_strength: float = 0.8,
    ffmpeg_path: str = r"D:\Ai\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe",
) -> str:
    """
    综合视频增强（降噪+锐化）

    Args:
        video_path: 输入视频路径
        output_path: 输出视频路径
        denoise: 是否降噪
        sharpen: 是否锐化
        denoise_strength: 降噪强度
        sharpen_strength: 锐化强度
        ffmpeg_path: ffmpeg路径

    Returns:
        输出视频路径
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"视频不存在: {video_path}")

    if output_path is None:
        base, ext = os.path.splitext(video_path)
        output_path = f"{base}_enhanced{ext}"

    filters = []
    if denoise:
        lum_spat = denoise_strength
        filters.append(f"hqdn3d={lum_spat}:{lum_spat*0.75}:{lum_spat*1.5}:{lum_spat*1.5}")
    if sharpen:
        amount = sharpen_strength * 0.8
        filters.append(f"unsharp=5:5:{amount}:5:5:{amount*0.5}")

    if not filters:
        raise ValueError("至少需要启用一种增强效果")

    filter_str = ",".join(filters)

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

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg失败: {result.stderr[-500:]}")

    return output_path


__all__ = ["denoise_video", "sharpen_video", "blur_video", "stabilize_video", "enhance_video"]


if __name__ == "__main__":
    print("视频后处理工具已加载")
    print("可用函数: denoise_video, sharpen_video, blur_video, stabilize_video, enhance_video")
