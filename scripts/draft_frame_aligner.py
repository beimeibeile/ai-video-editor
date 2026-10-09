r"""`n剪映工程帧对齐后处理工具
import logging
logger = logging.getLogger(__name__)
对已生成的draft_content.json进行帧对齐修正，确保所有时间点对齐到fps帧边界

使用方法:
    from draft_frame_aligner import align_draft_to_frames
    align_draft_to_frames(r"D:\JianyingProDrafts\MyProject", fps=30)
"""
import os
import json
import shutil
from typing import Dict, Any


def align_to_frame(timestamp_us: int, fps: int = 30) -> int:
    """将微秒时间戳对齐到帧边界"""
    frame_dur_us = int(1_000_000 / fps)
    return round(timestamp_us / frame_dur_us) * frame_dur_us


def align_draft_to_frames(draft_dir: str, fps: int = 30, backup: bool = True) -> Dict[str, Any]:
    """
    对剪映工程进行帧对齐修正

    Args:
        draft_dir: 草稿目录路径
        fps: 帧率（默认30）
        backup: 是否备份原文件

    Returns:
        修正统计信息
    """
    content_file = os.path.join(draft_dir, "draft_content.json")
    info_file = os.path.join(draft_dir, "draft_info.json")

    if not os.path.exists(content_file):
        return {"status": "failed", "reason": "draft_content.json不存在"}

    # 备份
    if backup:
        shutil.copy2(content_file, content_file + ".bak")
        if os.path.exists(info_file):
            shutil.copy2(info_file, info_file + ".bak")

    stats = {
        "segments_modified": 0,
        "timestamps_modified": 0,
        "transitions_modified": 0,
        "keyframes_modified": 0,
    }

    def _align_file(filepath: str) -> bool:
        """对齐单个JSON文件"""
        if not os.path.exists(filepath):
            return False
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            logger.error(f"  读取失败: {e}")
            return False

        modified = False

        # 对齐轨道片段
        for track in data.get("tracks", []):
            for seg in track.get("segments", []):
                tr = seg.get("target_timerange", {})
                if "start" in tr:
                    old_start = tr["start"]
                    new_start = align_to_frame(old_start, fps)
                    if new_start != old_start:
                        tr["start"] = new_start
                        stats["timestamps_modified"] += 1
                        modified = True
                if "duration" in tr:
                    old_dur = tr["duration"]
                    new_dur = align_to_frame(old_dur, fps)
                    if new_dur != old_dur:
                        tr["duration"] = new_dur
                        stats["timestamps_modified"] += 1
                        modified = True

                # 对齐源时间范围
                sr = seg.get("source_timerange") or {}
                if "start" in sr:
                    old = sr["start"]
                    new = align_to_frame(old, fps)
                    if new != old:
                        sr["start"] = new
                        modified = True
                if "duration" in sr:
                    old = sr["duration"]
                    new = align_to_frame(old, fps)
                    if new != old:
                        sr["duration"] = new
                        modified = True

                # 对齐转场
                for trans in seg.get("transitions", []):
                    if "start" in trans:
                        old = trans["start"]
                        new = align_to_frame(old, fps)
                        if new != old:
                            trans["start"] = new
                            stats["transitions_modified"] += 1
                            modified = True
                    if "duration" in trans:
                        old = trans["duration"]
                        new = align_to_frame(old, fps)
                        if new != old:
                            trans["duration"] = new
                            modified = True

                # 对齐关键帧时间
                for kf_group in seg.get("common_keyframes", []):
                    for kf in kf_group.get("keyframe_list", []):
                        if "time_offset" in kf:
                            old = kf["time_offset"]
                            new = align_to_frame(old, fps)
                            if new != old:
                                kf["time_offset"] = new
                                stats["keyframes_modified"] += 1
                                modified = True

                if modified:
                    stats["segments_modified"] += 1

        # 对齐画布配置中的时长
        canvas = data.get("canvas_config", {})
        if "duration" in canvas:
            old = canvas["duration"]
            new = align_to_frame(old, fps)
            if new != old:
                canvas["duration"] = new
                modified = True

        if modified:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        return modified

    # 对齐content和info
    logger.info(f"对齐 draft_content.json...")
    _align_file(content_file)
    if os.path.exists(info_file):
        logger.info(f"对齐 draft_info.json...")
        _align_file(info_file)

    stats["status"] = "success"
    stats["fps"] = fps
    logger.info(f"\n✅ 帧对齐完成:")
    logger.info(f"   修改片段: {stats['segments_modified']}")
    logger.info(f"   修改时间点: {stats['timestamps_modified']}")
    logger.info(f"   修改转场: {stats['transitions_modified']}")
    logger.info(f"   修改关键帧: {stats['keyframes_modified']}")
    logger.info(f"   备份: .bak文件")
    return stats


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        draft_dir = sys.argv[1]
    else:
        draft_dir = r"D:\JianyingProDrafts\JianyingPro Drafts\P0_E2E_Test"

    logger.info(f"帧对齐: {draft_dir}")
    align_draft_to_frames(draft_dir, fps=30)
