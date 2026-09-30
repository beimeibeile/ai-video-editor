"""
剪映工程数据提取器
从 draft_content.json 提取剪辑质量门所需的数据

支持的质量门数据：
- total_duration: 总时长（秒）
- fps: 帧率
- segments: 视频片段列表（含start/duration/width/height/is_black_frame）
- transitions: 转场列表
- subtitles: 字幕列表
- aspect_ratio: 画幅信息
"""

import os
import json
from typing import Dict, List, Any, Optional


def extract_draft_data(draft_path: str) -> Dict[str, Any]:
    """
    从剪映工程目录提取质量门所需数据

    Args:
        draft_path: 剪映草稿目录路径（包含 draft_content.json）

    Returns:
        质量门数据字典
    """
    content_file = os.path.join(draft_path, "draft_content.json")
    if not os.path.exists(content_file):
        # 尝试 draft_info.json
        content_file = os.path.join(draft_path, "draft_info.json")
    if not os.path.exists(content_file):
        raise FileNotFoundError(f"草稿文件不存在: {draft_path}")

    with open(content_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    fps = data.get('fps', 30)
    total_duration = data.get('duration', 0) / 1e6  # 微秒转秒

    # 构建转场映射 (id -> transition info)
    materials = data.get('materials', {})
    transition_map = {}
    for trans in materials.get('transitions', []):
        tid = trans.get('id', '')
        if tid:
            transition_map[tid] = {
                'name': trans.get('name', ''),
                'duration': trans.get('duration', 0) / 1e6 if isinstance(trans.get('duration'), (int, float)) else 0,
            }

    # 提取视频片段
    segments = []
    transitions = []
    subtitles = []
    track_types = set()

    for track in data.get('tracks', []):
        track_type = track.get('type', '')
        track_types.add(track_type)

        for seg in track.get('segments', []):
            tr = seg.get('target_timerange', {})
            start = tr.get('start', 0) / 1e6
            duration = tr.get('duration', 0) / 1e6

            if track_type == 'video':
                # 获取片段尺寸
                clip = seg.get('clip', {})
                transform = clip.get('transform', {}) if isinstance(clip, dict) else {}
                width = transform.get('width', 0)
                height = transform.get('height', 0)

                # 检测是否可能为黑屏（纯黑素材或极低alpha）
                is_black = False
                alpha = clip.get('alpha', 1.0) if isinstance(clip, dict) else 1.0
                if alpha < 0.05:
                    is_black = True

                segments.append({
                    'start': start,
                    'duration': duration,
                    'width': width,
                    'height': height,
                    'is_black_frame': is_black,
                    'track': track_type,
                })

                # 检测转场（通过 extra_material_refs 引用 materials.transitions）
                refs = seg.get('extra_material_refs', [])
                for ref in refs:
                    if ref in transition_map:
                        trans_info = transition_map[ref]
                        transitions.append({
                            'start': start,
                            'duration': trans_info['duration'],
                            'name': trans_info['name'],
                        })
                        break

            elif track_type == 'text':
                subtitles.append({
                    'start': start,
                    'duration': duration,
                    'text': seg.get('content', ''),
                })

    # 计算字幕覆盖率
    subtitle_coverage = 0.0
    if subtitles and total_duration > 0:
        covered_time = sum(s['duration'] for s in subtitles)
        subtitle_coverage = min(covered_time / total_duration, 1.0)

    # 画幅信息
    canvas = data.get('canvas_config', {})
    aspect_ratio = canvas.get('ratio', '9:16') if isinstance(canvas, dict) else '9:16'

    return {
        'total_duration': total_duration,
        'max_duration': 180,  # 默认上限3分钟，可外部覆盖
        'fps': fps,
        'segments': segments,
        'transitions': transitions,
        'subtitles': subtitles,
        'subtitle_coverage': subtitle_coverage,
        'aspect_ratio': aspect_ratio,
        'track_types': list(track_types),
        'draft_path': draft_path,
    }


def extract_draft_from_content(content_data: Dict[str, Any], draft_path: str = "") -> Dict[str, Any]:
    """
    从已加载的 draft_content 字典提取数据（无需重新读文件）

    Args:
        content_data: draft_content.json 的字典数据
        draft_path: 草稿路径（可选，用于记录）

    Returns:
        质量门数据字典
    """
    fps = content_data.get('fps', 30)
    total_duration = content_data.get('duration', 0) / 1e6

    segments = []
    transitions = []
    subtitles = []

    for track in content_data.get('tracks', []):
        track_type = track.get('type', '')
        for seg in track.get('segments', []):
            tr = seg.get('target_timerange', {})
            start = tr.get('start', 0) / 1e6
            duration = tr.get('duration', 0) / 1e6

            if track_type == 'video':
                clip = seg.get('clip', {})
                transform = clip.get('transform', {}) if isinstance(clip, dict) else {}
                segments.append({
                    'start': start,
                    'duration': duration,
                    'width': transform.get('width', 0),
                    'height': transform.get('height', 0),
                    'is_black_frame': False,
                })
                if seg.get('transition'):
                    transitions.append({'start': start, 'duration': 0})
            elif track_type == 'text':
                subtitles.append({'start': start, 'duration': duration})

    return {
        'total_duration': total_duration,
        'max_duration': 180,
        'fps': fps,
        'segments': segments,
        'transitions': transitions,
        'subtitles': subtitles,
        'subtitle_coverage': sum(s['duration'] for s in subtitles) / total_duration if total_duration > 0 else 0,
        'aspect_ratio': '9:16',
        'draft_path': draft_path,
    }


if __name__ == "__main__":
    # 测试
    import glob
    drafts_dir = r"D:\JianyingProDrafts\JianyingPro Drafts"
    draft_dirs = sorted(glob.glob(os.path.join(drafts_dir, "*")))
    draft_dirs = [d for d in draft_dirs if os.path.isdir(d)]

    for draft_dir in draft_dirs[:3]:
        if os.path.exists(os.path.join(draft_dir, "draft_content.json")):
            print(f"草稿: {os.path.basename(draft_dir)}")
            data = extract_draft_data(draft_dir)
            print(f"  时长: {data['total_duration']:.1f}s, fps: {data['fps']}")
            print(f"  视频片段: {len(data['segments'])}, 转场: {len(data['transitions'])}, 字幕: {len(data['subtitles'])}")
            print(f"  字幕覆盖率: {data['subtitle_coverage']:.1%}, 画幅: {data['aspect_ratio']}")
            print()
