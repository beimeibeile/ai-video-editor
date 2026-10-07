"""
自动卡点模块 v2
分析BGM音频能量/节拍，自动生成切点时间线
吸收高版本剪映草稿（卡点123）的操作方法：
- 从beats数据读取AI节拍检测时间戳
- 多轨道卡点编排（7条video轨道分层）
- 卡点强度分级（强/中/弱对应不同特效）
- effect轨道卡点触发

功能：
- analyze_audio_energy: 用ffmpeg分析音频能量曲线
- detect_beats: 检测能量峰值（节拍点）
- load_beats_from_draft: 从高版本草稿beats数据读取时间戳
- classify_beat_intensity: 卡点强度分级
- generate_beat_timeline: 生成卡点时间线（切点列表）
- generate_multi_track_beat_edit: 多轨道卡点编排
- apply_beat_cuts: 根据卡点时间线自动切分视频片段
- apply_beat_effects: 根据卡点强度应用特效
"""
import os
import sys
import json
import subprocess
import re
from typing import List, Dict, Tuple, Optional

FFMPEG = r"D:\Ai\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe"
FFPROBE = r"D:\Ai\ffmpeg-master-latest-win64-gpl\bin\ffprobe.exe"


def load_beats_from_draft(draft_dir: str) -> Dict:
    """
    从高版本剪映草稿的beats数据读取AI节拍检测时间戳

    Args:
        draft_dir: 草稿目录（包含template.json.bak）

    Returns:
        {
            "beats": [时间戳(秒)...],
            "bpm": 估算BPM,
            "source": "ai_detection" | "manual",
            "count": 节拍数,
        }
    """
    bak_path = os.path.join(draft_dir, 'template.json.bak')
    if not os.path.exists(bak_path):
        return {"beats": [], "bpm": 0, "source": "none", "count": 0}

    with open(bak_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    beats_material = data.get('materials', {}).get('beats', [])
    if not beats_material:
        return {"beats": [], "bpm": 0, "source": "none", "count": 0}

    beat_data = beats_material[0] if isinstance(beats_material, list) else beats_material
    user_beats = beat_data.get('user_beats', [])
    enable_ai = beat_data.get('enable_ai_beats', False)

    # user_beats可能是时间戳数组（微秒）或对象数组
    beats_sec = []
    for b in user_beats:
        if isinstance(b, (int, float)):
            beats_sec.append(b / 1e6)  # 微秒转秒
        elif isinstance(b, dict):
            t = b.get('time', b.get('time_offset', 0))
            beats_sec.append(t / 1e6 if t > 1e6 else t)

    # 估算BPM
    bpm = 0
    if len(beats_sec) >= 2:
        intervals = [beats_sec[i+1] - beats_sec[i] for i in range(len(beats_sec)-1)]
        if intervals:
            avg_interval = sum(intervals) / len(intervals)
            if avg_interval > 0:
                bpm = int(60 / avg_interval)

    return {
        "beats": sorted(beats_sec),
        "bpm": bpm,
        "source": "ai_detection" if enable_ai else "manual",
        "count": len(beats_sec),
    }


def classify_beat_intensity(beats: List[float], energies: List[float] = None,
                             fps: int = 10) -> List[Dict]:
    """
    卡点强度分级（强/中/弱），对应不同特效强度

    Args:
        beats: 节拍时间点列表（秒）
        energies: 能量曲线（可选，用于计算强度）
        fps: 能量采样率

    Returns:
        [{time, intensity: "strong"/"medium"/"weak", energy}]
    """
    if not beats:
        return []

    # 计算节拍间隔（用于无能量曲线时估算强度）
    intervals = []
    for i in range(len(beats)):
        if i < len(beats) - 1:
            intervals.append(beats[i+1] - beats[i])
        else:
            intervals.append(intervals[-1] if intervals else 0.5)

    avg_interval = sum(intervals) / len(intervals) if intervals else 0.5

    result = []
    for i, beat in enumerate(beats):
        if energies:
            idx = min(int(beat * fps), len(energies) - 1)
            energy = energies[idx] if idx >= 0 else 0.5
        else:
            # 无能量曲线时，根据节拍间隔估算强度
            # 间隔越短→节奏越快→强度越高
            interval = intervals[i]
            if interval < avg_interval * 0.7:
                energy = 0.85  # 快节奏=强
            elif interval < avg_interval * 1.2:
                energy = 0.6   # 中速=中
            else:
                energy = 0.35  # 慢节奏=弱

        # 强度分级
        if energy >= 0.7:
            intensity = "strong"
        elif energy >= 0.45:
            intensity = "medium"
        else:
            intensity = "weak"

        result.append({
            "time": beat,
            "intensity": intensity,
            "energy": round(energy, 3),
            "index": i,
        })

    return result


def generate_multi_track_beat_edit(beat_data: Dict, num_tracks: int = 4,
                                    min_interval: float = 0.3) -> Dict:
    """
    多轨道卡点编排（吸收卡点123的7轨道分层结构）

    将卡点分配到多条轨道，形成视觉层次：
    - 强卡点：主轨道（大画面/主素材）
    - 中卡点：副轨道（装饰/叠加）
    - 弱卡点：effect轨道（特效/转场）

    Args:
        beat_data: load_beats_from_draft或generate_beat_timeline的结果
        num_tracks: 轨道数（默认4）
        min_interval: 最小间隔

    Returns:
        {
            "tracks": [
                {"name": "Main", "segments": [{start, end, intensity}]},
                ...
            ],
            "total_segments": 总数,
        }
    """
    beats = beat_data.get('beats', [])
    if not beats:
        return {"tracks": [], "total_segments": 0}

    # 强度分级
    classified = beat_data.get('classified', [])
    if not classified:
        classified = classify_beat_intensity(beats)

    # 按强度分配轨道
    tracks = [{"name": f"Track_{i}", "segments": []} for i in range(num_tracks)]

    # 轨道分配策略：
    # Track 0 (Main): 强卡点
    # Track 1 (Sub): 中卡点
    # Track 2 (Overlay): 弱卡点+装饰
    # Track 3 (Effect): 特效触发点
    for i, beat in enumerate(classified):
        start = beat['time']
        end = beats[i + 1] if i + 1 < len(beats) else start + 1.0
        duration = end - start

        if duration < min_interval:
            continue

        if beat['intensity'] == 'strong':
            track_idx = 0
        elif beat['intensity'] == 'medium':
            track_idx = 1 if num_tracks > 1 else 0
        else:
            track_idx = 2 if num_tracks > 2 else 0

        tracks[track_idx]['segments'].append({
            'start': round(start, 3),
            'end': round(end, 3),
            'duration': round(duration, 3),
            'intensity': beat['intensity'],
            'beat_index': beat['index'],
        })

    # Effect轨道：所有卡点都是特效触发点
    if num_tracks > 3:
        tracks[3]['name'] = 'Effect'
        for beat in classified:
            tracks[3]['segments'].append({
                'start': round(beat['time'], 3),
                'end': round(beat['time'] + 0.3, 3),
                'duration': 0.3,
                'intensity': beat['intensity'],
                'beat_index': beat['index'],
            })

    total = sum(len(t['segments']) for t in tracks)
    return {"tracks": tracks, "total_segments": total}


def apply_beat_effects(project, beat_data: Dict,
                        effect_map: Dict = None) -> List:
    """
    根据卡点强度应用特效

    Args:
        project: JyProject实例
        beat_data: 卡点数据（含classified强度分级）
        effect_map: 强度→特效映射 {
            "strong": {"type": "mask_flash", "duration": 0.3},
            "medium": {"type": "transition", "name": "叠化"},
            "weak": {"type": "scale_pulse", "intensity": 0.05},
        }

    Returns:
        应用的特效列表
    """
    if effect_map is None:
        effect_map = {
            "strong": {"type": "mask_flash", "duration": 0.3, "colors": "neon"},
            "medium": {"type": "transition", "name": "叠化", "duration": 0.2},
            "weak": {"type": "scale_pulse", "intensity": 0.05},
        }

    classified = beat_data.get('classified', [])
    if not classified:
        beats = beat_data.get('beats', [])
        classified = classify_beat_intensity(beats)

    applied = []
    for beat in classified:
        intensity = beat['intensity']
        effect_cfg = effect_map.get(intensity, {})
        effect_type = effect_cfg.get('type', 'none')

        if effect_type == 'none':
            continue

        applied.append({
            'time': beat['time'],
            'intensity': intensity,
            'effect': effect_type,
            'config': effect_cfg,
        })

    return applied


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

    # 强度分级
    classified = classify_beat_intensity(beats, energies, fps=10)

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
        "classified": classified,
        "cuts": cuts,
        "duration": duration,
        "energy_curve": energies,
        "beat_count": len(beats),
        "cut_count": len(cuts),
        "strong_count": sum(1 for c in classified if c['intensity'] == 'strong'),
        "medium_count": sum(1 for c in classified if c['intensity'] == 'medium'),
        "weak_count": sum(1 for c in classified if c['intensity'] == 'weak'),
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
    # pyJianYingDraft已迁移到适配层
import os as _os, sys as _sys
_AVR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _AVR not in _sys.path: _sys.path.insert(0, _AVR)

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
                trans_enum = getattr(TransitionType, transition_type,
                                      TransitionType.叠化)
                segments[-2].add_transition(
                    trans_enum,
                    duration=int(transition_duration * 1_000_000)
                )
            except Exception:
                pass

        current_time = cut

    return segments


if __name__ == "__main__":
    print("=" * 60)
    print("自动卡点模块 v2")
    print("=" * 60)
    print("\n功能:")
    print("  - analyze_audio_energy: 分析音频能量")
    print("  - detect_beats: 检测节拍点")
    print("  - load_beats_from_draft: 从高版本草稿读取AI节拍")
    print("  - classify_beat_intensity: 卡点强度分级(强/中/弱)")
    print("  - generate_beat_timeline: 生成卡点时间线")
    print("  - generate_multi_track_beat_edit: 多轨道卡点编排")
    print("  - apply_beat_cuts: 应用卡点切分")
    print("  - apply_beat_effects: 根据强度应用特效")

    # 测试从高版本草稿读取beats
    draft_dir = r'D:\JianyingProDrafts\JianyingPro Drafts\卡点123'
    if os.path.exists(draft_dir):
        print(f"\n--- 测试: 从卡点123读取beats ---")
        beat_data = load_beats_from_draft(draft_dir)
        print(f"  来源: {beat_data['source']}")
        print(f"  BPM: {beat_data['bpm']}")
        print(f"  节拍数: {beat_data['count']}")
        if beat_data['beats']:
            print(f"  前5个节拍: {[round(b, 2) for b in beat_data['beats'][:5]]}")

        # 多轨道编排
        multi = generate_multi_track_beat_edit(beat_data, num_tracks=4)
        print(f"\n  多轨道编排: {multi['total_segments']}个片段")
        for t in multi['tracks']:
            print(f"    {t['name']}: {len(t['segments'])}个片段")
    else:
        print(f"\n草稿不存在: {draft_dir}")
