"""
FFmpeg基础工具集
视频转GIF、压缩、裁剪、拼接、提取音频、音量调整等
ai-video-editor项目独立工具模块，不依赖ComfyUI
"""
import os
import subprocess
import shutil
from typing import List, Optional, Tuple

# 默认ffmpeg路径（可通过环境变量覆盖）
DEFAULT_FFMPEG = os.environ.get("FFMPEG_PATH", r"D:\Ai\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe")
DEFAULT_FFPROBE = os.environ.get("FFPROBE_PATH", r"D:\Ai\ffmpeg-master-latest-win64-gpl\bin\ffprobe.exe")


def _get_ffmpeg(ffmpeg_path: str = None) -> str:
    """获取ffmpeg路径，自动检测"""
    if ffmpeg_path and os.path.exists(ffmpeg_path):
        return ffmpeg_path
    if os.path.exists(DEFAULT_FFMPEG):
        return DEFAULT_FFMPEG
    # 尝试PATH中的ffmpeg
    if shutil.which("ffmpeg"):
        return "ffmpeg"
    raise RuntimeError("ffmpeg未找到，请安装ffmpeg或指定ffmpeg_path")


def _get_ffprobe(ffprobe_path: str = None) -> str:
    """获取ffprobe路径，自动检测"""
    if ffprobe_path and os.path.exists(ffprobe_path):
        return ffprobe_path
    if os.path.exists(DEFAULT_FFPROBE):
        return DEFAULT_FFPROBE
    if shutil.which("ffprobe"):
        return "ffprobe"
    raise RuntimeError("ffprobe未找到，请安装ffmpeg或指定ffprobe_path")


def video_to_gif(
    video_path: str,
    output_path: str = None,
    fps: int = 15,
    scale: int = 480,
    ffmpeg_path: str = None,
) -> str:
    """
    视频转GIF

    Args:
        video_path: 输入视频路径
        output_path: 输出GIF路径（None则自动命名）
        fps: GIF帧率
        scale: GIF宽度（高度自动等比）
        ffmpeg_path: ffmpeg路径

    Returns:
        输出GIF路径
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"视频不存在: {video_path}")

    if output_path is None:
        base, _ = os.path.splitext(video_path)
        output_path = f"{base}.gif"

    ffmpeg = _get_ffmpeg(ffmpeg_path)

    # 使用palettegen+paletteuse提升GIF质量
    palette_path = os.path.join(os.path.dirname(output_path), "_tmp_palette.png")

    # 生成调色板
    cmd1 = [ffmpeg, "-y", "-i", video_path,
            "-vf", f"fps={fps},scale={scale}:-1:flags=lanczos,palettegen",
            palette_path]
    subprocess.run(cmd1, capture_output=True, text=True, timeout=120)

    # 使用调色板生成GIF
    cmd2 = [ffmpeg, "-y", "-i", video_path, "-i", palette_path,
            "-lavfi", f"fps={fps},scale={scale}:-1:flags=lanczos[x];[x][1:v]paletteuse",
            output_path]
    subprocess.run(cmd2, capture_output=True, text=True, timeout=120)

    # 清理临时调色板
    try:
        os.remove(palette_path)
    except Exception:
        pass

    if os.path.exists(output_path):
        return output_path
    raise RuntimeError("GIF生成失败")


def compress_video(
    video_path: str,
    output_path: str = None,
    crf: int = 28,
    preset: str = "medium",
    target_size_mb: int = None,
    ffmpeg_path: str = None,
) -> str:
    """
    视频压缩

    Args:
        video_path: 输入视频路径
        output_path: 输出路径（None则自动命名）
        crf: 质量参数（0-51，越小质量越高，默认28）
        preset: 编码速度（ultrafast/superfast/veryfast/faster/fast/medium/slow/slower/veryslow）
        target_size_mb: 目标大小MB（None则用CRF模式）
        ffmpeg_path: ffmpeg路径

    Returns:
        输出视频路径
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"视频不存在: {video_path}")

    if output_path is None:
        base, ext = os.path.splitext(video_path)
        output_path = f"{base}_compressed{ext}"

    ffmpeg = _get_ffmpeg(ffmpeg_path)

    if target_size_mb:
        # 目标大小模式：计算比特率
        ffprobe = _get_ffprobe()
        cmd = [ffprobe, "-v", "quiet", "-print_format", "json",
               "-show_format", video_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        import json
        info = json.loads(result.stdout)
        duration = float(info.get("format", {}).get("duration", 10))
        target_bitrate = int((target_size_mb * 8192) / duration)  # kbps
        cmd = [ffmpeg, "-y", "-i", video_path,
               "-c:v", "libx264", "-b:v", f"{target_bitrate}k",
               "-preset", preset, "-c:a", "aac", "-b:a", "128k",
               output_path]
    else:
        # CRF模式
        cmd = [ffmpeg, "-y", "-i", video_path,
               "-c:v", "libx264", "-crf", str(crf),
               "-preset", preset, "-c:a", "aac", "-b:a", "128k",
               output_path]

    subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    if os.path.exists(output_path):
        return output_path
    raise RuntimeError("视频压缩失败")


def trim_video(
    video_path: str,
    output_path: str = None,
    start_time: str = "0",
    duration: str = None,
    end_time: str = None,
    ffmpeg_path: str = None,
) -> str:
    """
    视频裁剪

    Args:
        video_path: 输入视频路径
        output_path: 输出路径（None则自动命名）
        start_time: 开始时间（秒或HH:MM:SS格式）
        duration: 持续时长（秒或HH:MM:SS格式，与end_time二选一）
        end_time: 结束时间（秒或HH:MM:SS格式，与duration二选一）
        ffmpeg_path: ffmpeg路径

    Returns:
        输出视频路径
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"视频不存在: {video_path}")

    if output_path is None:
        base, ext = os.path.splitext(video_path)
        output_path = f"{base}_trimmed{ext}"

    ffmpeg = _get_ffmpeg(ffmpeg_path)

    cmd = [ffmpeg, "-y", "-ss", str(start_time), "-i", video_path]
    if duration:
        cmd.extend(["-t", str(duration)])
    elif end_time:
        cmd.extend(["-to", str(end_time)])
    cmd.extend(["-c", "copy", output_path])

    subprocess.run(cmd, capture_output=True, text=True, timeout=120)

    if os.path.exists(output_path):
        return output_path
    raise RuntimeError("视频裁剪失败")


def concat_videos(
    video_paths: List[str],
    output_path: str,
    ffmpeg_path: str = None,
) -> str:
    """
    视频拼接（需要相同编码/分辨率/帧率，否则用concat滤镜）

    Args:
        video_paths: 输入视频路径列表
        output_path: 输出路径
        ffmpeg_path: ffmpeg路径

    Returns:
        输出视频路径
    """
    if len(video_paths) < 2:
        raise ValueError("至少需要2个视频")

    for p in video_paths:
        if not os.path.exists(p):
            raise FileNotFoundError(f"视频不存在: {p}")

    ffmpeg = _get_ffmpeg(ffmpeg_path)

    # 创建文件列表
    list_path = os.path.join(os.path.dirname(output_path), "_tmp_concat_list.txt")
    with open(list_path, "w", encoding="utf-8") as f:
        for p in video_paths:
            # ffmpeg concat需要正斜杠或转义反斜杠
            abs_path = os.path.abspath(p).replace("\\", "/")
            f.write(f"file '{abs_path}'\n")

    # 先尝试concat demuxer（快速，需要相同编码）
    cmd = [ffmpeg, "-y", "-f", "concat", "-safe", "0",
           "-i", list_path, "-c", "copy", output_path]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    # 如果失败，用concat滤镜（重新编码，兼容性好）
    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        inputs = []
        for p in video_paths:
            inputs.extend(["-i", p])
        n = len(video_paths)
        filter_str = "".join([f"[{i}:v:0][{i}:a:0]" for i in range(n)])
        filter_str += f"concat=n={n}:v=1:a=1[outv][outa]"
        cmd = [ffmpeg, "-y"] + inputs + [
            "-filter_complex", filter_str,
            "-map", "[outv]", "-map", "[outa]",
            "-c:v", "libx264", "-c:a", "aac",
            output_path
        ]
        subprocess.run(cmd, capture_output=True, text=True, timeout=600)

    # 清理临时文件
    try:
        os.remove(list_path)
    except Exception:
        pass

    if os.path.exists(output_path):
        return output_path
    raise RuntimeError("视频拼接失败")


def extract_audio(
    video_path: str,
    output_path: str = None,
    format: str = "mp3",
    bitrate: str = "192k",
    ffmpeg_path: str = None,
) -> str:
    """
    从视频提取音频

    Args:
        video_path: 输入视频路径
        output_path: 输出音频路径（None则自动命名）
        format: 音频格式（mp3/wav/aac/ogg/flac）
        bitrate: 比特率
        ffmpeg_path: ffmpeg路径

    Returns:
        输出音频路径
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"视频不存在: {video_path}")

    if output_path is None:
        base, _ = os.path.splitext(video_path)
        output_path = f"{base}.{format}"

    ffmpeg = _get_ffmpeg(ffmpeg_path)

    codec_map = {
        "mp3": "libmp3lame",
        "wav": "pcm_s16le",
        "aac": "aac",
        "ogg": "libvorbis",
        "flac": "flac",
    }
    codec = codec_map.get(format, "libmp3lame")

    cmd = [ffmpeg, "-y", "-i", video_path,
           "-vn", "-acodec", codec, "-b:a", bitrate,
           output_path]
    subprocess.run(cmd, capture_output=True, text=True, timeout=120)

    if os.path.exists(output_path):
        return output_path
    raise RuntimeError("音频提取失败")


def adjust_volume(
    video_path: str,
    output_path: str = None,
    volume: float = 1.0,
    ffmpeg_path: str = None,
) -> str:
    """
    调整视频音量

    Args:
        video_path: 输入视频路径
        output_path: 输出路径（None则自动命名）
        volume: 音量倍数（1.0=原始，0.5=一半，2.0=两倍）
        ffmpeg_path: ffmpeg路径

    Returns:
        输出视频路径
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"视频不存在: {video_path}")

    if output_path is None:
        base, ext = os.path.splitext(video_path)
        output_path = f"{base}_vol{volume}{ext}"

    ffmpeg = _get_ffmpeg(ffmpeg_path)

    cmd = [ffmpeg, "-y", "-i", video_path,
           "-af", f"volume={volume}",
           "-c:v", "copy",
           output_path]
    subprocess.run(cmd, capture_output=True, text=True, timeout=120)

    if os.path.exists(output_path):
        return output_path
    raise RuntimeError("音量调整失败")


def change_speed(
    video_path: str,
    output_path: str = None,
    speed: float = 1.0,
    ffmpeg_path: str = None,
) -> str:
    """
    调整视频播放速度

    Args:
        video_path: 输入视频路径
        output_path: 输出路径（None则自动命名）
        speed: 速度倍数（0.5=慢放，2.0=快进，0.25-4.0范围）
        ffmpeg_path: ffmpeg路径

    Returns:
        输出视频路径
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"视频不存在: {video_path}")

    if output_path is None:
        base, ext = os.path.splitext(video_path)
        output_path = f"{base}_speed{speed}{ext}"

    ffmpeg = _get_ffmpeg(ffmpeg_path)

    # setpts滤镜调整视频速度，atempo调整音频速度
    # atempo范围0.5-2.0，超出需要链式
    video_filter = f"setpts={1/speed}*PTS"

    # 音频速度调整
    if 0.5 <= speed <= 2.0:
        audio_filter = f"atempo={speed}"
    elif speed > 2.0:
        # 链式atempo
        n = int(speed // 2) + 1
        step = speed ** (1/n)
        audio_filter = ",".join([f"atempo={step}"] * n)
    else:
        n = int(1/speed // 2) + 1
        step = (1/speed) ** (1/n)
        audio_filter = ",".join([f"atempo={1/step}"] * n)

    cmd = [ffmpeg, "-y", "-i", video_path,
           "-filter_complex",
           f"[0:v]{video_filter}[v];[0:a]{audio_filter}[a]",
           "-map", "[v]", "-map", "[a]",
           "-c:v", "libx264", "-c:a", "aac",
           output_path]
    subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    if os.path.exists(output_path):
        return output_path
    raise RuntimeError("速度调整失败")


def get_video_info_simple(video_path: str, ffprobe_path: str = None) -> dict:
    """
    简化版视频信息获取（不依赖api.py的get_video_info）

    Returns:
        {width, height, fps, duration, codec, has_audio, size_bytes}
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"视频不存在: {video_path}")

    ffprobe = _get_ffprobe(ffprobe_path)
    import json
    cmd = [ffprobe, "-v", "quiet", "-print_format", "json",
           "-show_format", "-show_streams", video_path]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    data = json.loads(result.stdout)

    info = {"width": 0, "height": 0, "fps": 0, "duration": 0,
            "codec": "", "has_audio": False, "size_bytes": 0}

    for stream in data.get("streams", []):
        if stream.get("codec_type") == "video":
            info["width"] = stream.get("width", 0)
            info["height"] = stream.get("height", 0)
            info["codec"] = stream.get("codec_name", "")
            # 解析帧率
            rate = stream.get("r_frame_rate", "0/1")
            if "/" in rate:
                num, den = rate.split("/")
                info["fps"] = round(float(num) / float(den), 2) if float(den) > 0 else 0
        elif stream.get("codec_type") == "audio":
            info["has_audio"] = True

    fmt = data.get("format", {})
    info["duration"] = round(float(fmt.get("duration", 0)), 2)
    info["size_bytes"] = int(fmt.get("size", 0))

    return info


# 导出所有函数
__all__ = [
    "video_to_gif", "compress_video", "trim_video", "concat_videos",
    "extract_audio", "adjust_volume", "change_speed", "get_video_info_simple",
]


if __name__ == "__main__":
    print("FFmpeg基础工具集已加载")
    print("可用函数:")
    for fn in __all__:
        print(f"  - {fn}")
