"""
视频色彩校正工具
使用ffmpeg eq滤镜调整视频的亮度/对比度/饱和度/色调/伽马值
支持批量处理和预设风格
"""
import os
import subprocess
from typing import Optional, Dict


def adjust_color(
    video_path: str,
    output_path: str = None,
    brightness: float = 0.0,      # -1.0 ~ 1.0
    contrast: float = 1.0,        # 0.0 ~ 2.0
    saturation: float = 1.0,      # 0.0 ~ 3.0
    gamma: float = 1.0,           # 0.1 ~ 10.0
    gamma_r: float = None,        # 红色通道伽马
    gamma_g: float = None,        # 绿色通道伽马
    gamma_b: float = None,        # 蓝色通道伽马
    ffmpeg_path: str = r"D:\Ai\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe",
) -> str:
    """
    调整视频色彩参数

    Args:
        video_path: 输入视频路径
        output_path: 输出视频路径（None则自动命名）
        brightness: 亮度调整（-1.0到1.0，0为不变）
        contrast: 对比度（0到2，1为不变）
        saturation: 饱和度（0到3，1为不变）
        gamma: 伽马值（0.1到10，1为不变）
        gamma_r: 红色通道伽马（None则使用gamma）
        gamma_g: 绿色通道伽马（None则使用gamma）
        gamma_b: 蓝色通道伽马（None则使用gamma）
        ffmpeg_path: ffmpeg路径

    Returns:
        输出视频路径
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"视频不存在: {video_path}")

    if output_path is None:
        base, ext = os.path.splitext(video_path)
        output_path = f"{base}_color{ext}"

    # 构建eq滤镜参数
    eq_parts = [
        f"brightness={brightness}",
        f"contrast={contrast}",
        f"saturation={saturation}",
    ]

    # 伽马值处理
    if gamma_r is not None or gamma_g is not None or gamma_b is not None:
        if gamma_r is not None:
            eq_parts.append(f"gamma_r={gamma_r}")
        if gamma_g is not None:
            eq_parts.append(f"gamma_g={gamma_g}")
        if gamma_b is not None:
            eq_parts.append(f"gamma_b={gamma_b}")
    else:
        eq_parts.append(f"gamma={gamma}")

    eq_filter = "eq=" + ":".join(eq_parts)

    cmd = [
        ffmpeg_path, "-y",
        "-i", video_path,
        "-vf", eq_filter,
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


# 预设风格
COLOR_PRESETS = {
    "warm": {
        "brightness": 0.05, "contrast": 1.1, "saturation": 1.15,
        "gamma_r": 1.1, "gamma_g": 1.0, "gamma_b": 0.9,
        "desc": "暖色调（适合日落、温馨场景）"
    },
    "cool": {
        "brightness": 0.0, "contrast": 1.1, "saturation": 1.0,
        "gamma_r": 0.9, "gamma_g": 1.0, "gamma_b": 1.1,
        "desc": "冷色调（适合科技、夜景）"
    },
    "vintage": {
        "brightness": 0.05, "contrast": 0.9, "saturation": 0.7,
        "gamma_r": 1.15, "gamma_g": 1.05, "gamma_b": 0.85,
        "desc": "复古怀旧"
    },
    "cinematic": {
        "brightness": -0.05, "contrast": 1.2, "saturation": 0.9,
        "gamma": 1.1,
        "desc": "电影感（高对比低饱和）"
    },
    "vivid": {
        "brightness": 0.05, "contrast": 1.15, "saturation": 1.4,
        "gamma": 1.0,
        "desc": "鲜艳明快"
    },
    "bw": {
        "brightness": 0.0, "contrast": 1.2, "saturation": 0.0,
        "gamma": 1.0,
        "desc": "黑白"
    },
    "fade": {
        "brightness": 0.1, "contrast": 0.85, "saturation": 0.8,
        "gamma": 1.2,
        "desc": "褪色柔和"
    },
    "noir": {
        "brightness": -0.1, "contrast": 1.4, "saturation": 0.0,
        "gamma": 0.9,
        "desc": "黑色电影（高对比黑白）"
    },
}


def apply_preset(
    video_path: str,
    preset_name: str,
    output_path: str = None,
    ffmpeg_path: str = r"D:\Ai\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe",
) -> str:
    """
    应用预设色彩风格

    Args:
        video_path: 输入视频路径
        preset_name: 预设名称（warm/cool/vintage/cinematic/vivid/bw/fade/noir）
        output_path: 输出视频路径
        ffmpeg_path: ffmpeg路径

    Returns:
        输出视频路径
    """
    if preset_name not in COLOR_PRESETS:
        raise ValueError(f"未知预设: {preset_name}，可用: {list(COLOR_PRESETS.keys())}")

    preset = COLOR_PRESETS[preset_name]

    if output_path is None:
        base, ext = os.path.splitext(video_path)
        output_path = f"{base}_{preset_name}{ext}"

    return adjust_color(
        video_path, output_path,
        brightness=preset.get("brightness", 0.0),
        contrast=preset.get("contrast", 1.0),
        saturation=preset.get("saturation", 1.0),
        gamma=preset.get("gamma", 1.0),
        gamma_r=preset.get("gamma_r"),
        gamma_g=preset.get("gamma_g"),
        gamma_b=preset.get("gamma_b"),
        ffmpeg_path=ffmpeg_path,
    )


def list_presets() -> Dict[str, str]:
    """列出所有可用预设及描述"""
    return {name: info["desc"] for name, info in COLOR_PRESETS.items()}


__all__ = ["adjust_color", "apply_preset", "list_presets", "COLOR_PRESETS"]


if __name__ == "__main__":
    print("视频色彩校正工具已加载")
    print("可用预设:")
    for name, desc in list_presets().items():
        print(f"  {name}: {desc}")
