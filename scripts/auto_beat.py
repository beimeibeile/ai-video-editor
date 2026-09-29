"""
自动卡点模块
分析BGM音频能量/节拍，自动生成切点时间线

功能：
- analyze_audio_energy: 用ffmpeg分析音频能量曲线
- detect_beats: 检测能量峰值（节拍点）
- generate_beat_timeline: 生成卡点时间线（切点列表）
- apply_beat_cuts: 根据卡点时间线自动切分视频片段
"""
import os
import sys
import json
import subprocess
import re

FFMPEG = r"D:\Ai\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe"
FFPROBE = r"D:\Ai\ffmpeg-master-latest-win64-gpl\bin\ffprobe.exe"


def analyze_audio_energy(audio_path: str, fps: int = 10) -> list:
    """
    用ffmpeg分析音频能量曲线

    Args:
        audio_path: 音频文件路径
        fps: 采样率（每秒多少个能量点，默认10）

    Returns:
        能量值列表 [0.0-1.0]
    """
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"音频文件不存在: {audio_path}")

    # 使用astats滤镜获取RMS能量
    cmd = [
        FFMPEG, "-i", audio_path,
        "-af", f"astats=metadata=1:reset=1,ametadata=print:key=lavfi.astats.Overall.RMS_level",
        "-f", "null", "-"
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    output = result.stderr

    # 解析RMS_level值
    energies = []
    for line in output.split('\n'):
        match = re.search(r'RMS_level=([-\d.]+|inf)', line)
        if match:
            val = match.group(1)
            if val in ('-inf', 'inf', '-'):
                energy = 0.0
            else:
                try:
                    rms = float(val)
                    if rms <= -60:
                        energy = 0.0
                    else:
                        energy = min(1.0, (rms + 60) / 60)
                except ValueError:
                    energy = 0.0
            energies.append(energy)

    return energies


def detect_beats(energies: list, threshold: float = 0.6,
                  min_interval: float = 0.3, fps: int = 10) -> list:
    """
    检测能量峰值（节拍点）

    Args:
        energies: 能量值列表
        threshold: 峰值阈值（0-1）
        min_interval: 最小间隔（秒）
        fps: 能量采样率

    Returns:
        节拍时间点列表（秒）
    """
    if not energies:
        return []

    beats = []
    min_samples = int(min_interval * fps)
    last_beat = -min_samples

    for i in range(1, len(energies) - 1):
        # 局部峰值检测
        if (energies[i] > threshold and
            energies[i] > energies[i-1] and
            energies[i] > energies[i+1] and
            i - last_beat >= min_samples):
            beats.append(i / fps)
            last_beat = i

    return beats


def generate_beat_timeline(audio_path: str, duration: float = None,
                            threshold: float = 0.6,
                            min_interval: float = 0.3,
                            max_interval: float = 2.0) -> dict:
    """
    生成卡点时间线

    Args:
        audio_path: 音频文件路径
        duration: 视频总时长（None则用音频时长）
        threshold: 峰值阈值
        min_interval: 最小切点间隔
        max_interval: 最大切点间隔（超过则强制切分）

    Returns:
        {
            "beats": [节拍时间点...],
            "cuts": [切点时间点...],
            "duration": 总时长,
            "energy_curve": [能量值...],
        }
    """
    # 获取音频时长
    if duration is None:
        cmd = [FFPROBE, "-v", "quiet", "-print_format", "json",
               "-show_format", audio_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        info = json.loads(result.stdout)
        duration = float(info["format"]["duration"])

    # 分析能量
    energies = analyze_audio_energy(audio_path, fps=10)

    # 检测节拍
    beats = detect_beats(energies, threshold, min_interval, fps=10)

    # 生成切点：节拍点 + 强制最大间隔
    cuts = []
    last_cut = 0.0

    for beat in beats:
        if beat - last_cut >= min_interval:
            cuts.append(beat)
            last_cut = beat

    # 确保不超过最大间隔
    i = 0
    while i < len(cuts) - 1:
        if cuts[i+1] - cuts[i] > max_interval:
            # 在中间插入切点
            mid = (cuts[i] + cuts[i+1]) / 2
            cuts.insert(i+1, mid)
        else:
            i += 1

    # 确保最后一个切点不超过duration
    cuts = [c for c in cuts if c < duration]
    if not cuts or cuts[-1] < duration - 0.5:
        cuts.append(duration)

    return {
        "beats": beats,
        "cuts": cuts,
        "duration": duration,
        "energy_curve": energies,
        "beat_count": len(beats),
        "cut_count": len(cuts),
    }


def apply_beat_cuts(project, video_clips: list, timeline: dict,
                     track_name: str = "VideoTrack",
                     transition_type: str = "叠化",
                     transition_duration: float = 0.2) -> list:
    """
    根据卡点时间线自动切分并排列视频片段

    Args:
        project: JyProject实例
        video_clips: 视频素材路径列表
        timeline: generate_beat_timeline的返回结果
        track_name: 轨道名
        transition_type: 转场类型
        transition_duration: 转场时长（秒）

    Returns:
        片段列表
    """
    import pyJianYingDraft as draft

    cuts = timeline["cuts"]
    segments = []
    current_time = 0.0

    for i, cut in enumerate(cuts):
        if i >= len(video_clips):
            break

        clip_duration = cut - current_time
        if clip_duration <= 0:
            continue

        seg = project.add_media_safe(
            video_clips[i],
            start_time=f"{current_time:.2f}s",
            duration=f"{clip_duration:.2f}s",
            track_name=track_name,
        )
        if seg:
            segments.append(seg)

        # 添加转场（加在前一个片段上）
        if len(segments) > 1:
            try:
                trans_enum = getattr(draft.TransitionType, transition_type,
                                      draft.TransitionType.叠化)
                segments[-2].add_transition(
                    trans_enum,
                    duration=int(transition_duration * 1_000_000)
                )
            except Exception:
                pass

        current_time = cut

    return segments


if __name__ == "__main__":
    print("自动卡点模块已加载")
    print("功能:")
    print("  - analyze_audio_energy: 分析音频能量")
    print("  - detect_beats: 检测节拍点")
    print("  - generate_beat_timeline: 生成卡点时间线")
    print("  - apply_beat_cuts: 应用卡点切分")
