"""
多层图片堆叠入场特效
基于教程《关键帧练习》封装

效果描述：
多张图片以画中画形式从屏幕下方依次滑入，形成堆叠排列效果
每张图片有轻微的缩放和旋转，营造层次感

制作手法：
1. 多张图片作为画中画添加到不同轨道
2. 每张图片设置起始位置在屏幕下方（Y偏移）
3. 添加位置关键帧：起始在屏幕外 → 结束在目标位置
4. 每张图片依次延迟入场（stagger）
5. 可选：轻微旋转和缩放增加层次感

依赖：
- jianying-editor skill (JyProject)
- ffmpeg (可选，用于图片预处理)
"""

import logging
logger = logging.getLogger(__name__)


import os
import sys
import uuid
from typing import List, Dict, Any, Tuple

skill_root = r"C:\Users\Administrator\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills\jianying-editor"
sys.path.insert(0, os.path.join(skill_root, "scripts"))
from jy_wrapper import JyProject
import pyJianYingDraft as draft


def create_stack_intro(
    project_name: str,
    images: List[str],
    width: int = 1080,
    height: int = 1920,
    duration: float = 5.0,
    stagger: float = 0.4,
    slide_duration: float = 0.8,
    layout: str = "grid",
    scale_range: Tuple[float, float] = (0.25, 0.35),
    rotation_range: Tuple[float, float] = (-5, 5),
    output_dir: str = None,
) -> Dict[str, Any]:
    """
    创建多层图片堆叠入场效果工程

    Args:
        project_name: 工程名
        images: 图片路径列表（最多8张）
        width: 画布宽
        height: 画布高
        duration: 总时长（秒）
        stagger: 每张图片入场延迟（秒）
        slide_duration: 单张图片滑入动画时长（秒）
        layout: 排列方式 ("grid"=网格, "diagonal"=对角线, "stack"=堆叠, "scatter"=散列)
        scale_range: 图片缩放范围 (min, max)
        rotation_range: 旋转角度范围 (min, max)
        output_dir: 素材输出目录

    Returns:
        工程信息字典
    """
    if not images:
        return {"status": "failed", "reason": "图片列表为空"}

    images = images[:8]  # 最多8张
    n = len(images)

    # 计算每张图片的目标位置
    positions = _calculate_positions(n, width, height, layout)

    # 创建工程
    logger.info(f"\n[1/3] 创建工程: {project_name} ({width}x{height})")
    project = JyProject(project_name, width=width, height=height, overwrite=True)

    # 添加黑色背景
    bg_color = "#1a1a2e"
    bg_path = os.path.join(output_dir or ".", f"bg_{uuid.uuid4().hex[:8]}.png")
    _create_solid_bg(bg_path, width, height, bg_color)
    project.add_media_safe(
        bg_path, start_time="0s", duration=f"{duration}s", track_name="Background"
    )

    # 添加每张图片
    logger.info(f"[2/3] 添加 {n} 张图片（{layout}布局）")
    segments = []
    for i, img_path in enumerate(images):
        if not os.path.exists(img_path):
            logger.info(f"  ⚠️  图片不存在: {img_path}")
            continue

        start_time = i * stagger
        track_name = f"Stack_{i}"

        seg = project.add_media_safe(
            img_path,
            start_time=f"{start_time}s",
            duration=f"{duration - start_time}s",
            track_name=track_name,
        )
        if seg:
            segments.append((i, seg))
            logger.info(f"  ✅ 图片{i}: {os.path.basename(img_path)}")

    # 保存工程
    logger.info(f"[3/3] 保存工程")
    result = project.save()
    draft_path = result.get("draft_path", "")

    # 注入位置关键帧
    if draft_path and segments:
        _inject_stack_keyframes(
            draft_path, segments, positions, width, height,
            stagger, slide_duration, scale_range, rotation_range
        )

    return {
        "status": "success",
        "project_name": project_name,
        "draft_path": draft_path,
        "image_count": len(segments),
        "duration": duration,
        "layout": layout,
    }


def _calculate_positions(
    n: int, width: int, height: int, layout: str
) -> List[Tuple[float, float]]:
    """
    计算每张图片的目标位置（归一化坐标，-1到1）

    Args:
        n: 图片数量
        width: 画布宽
        height: 画布高
        layout: 排列方式

    Returns:
        位置列表 [(x, y), ...]，归一化坐标
    """
    positions = []

    if layout == "grid":
        # 网格布局：2列或3列
        cols = 2 if n <= 4 else 3
        rows = (n + cols - 1) // cols
        for i in range(n):
            row = i // cols
            col = i % cols
            x = (col - (cols - 1) / 2) * 0.5
            y = (row - (rows - 1) / 2) * 0.4
            positions.append((x, y))

    elif layout == "diagonal":
        # 对角线布局
        for i in range(n):
            t = i / max(n - 1, 1)
            x = -0.5 + t * 1.0
            y = -0.4 + t * 0.8
            positions.append((x, y))

    elif layout == "stack":
        # 堆叠布局：轻微偏移
        for i in range(n):
            x = (i - (n - 1) / 2) * 0.05
            y = (i - (n - 1) / 2) * 0.05
            positions.append((x, y))

    elif layout == "scatter":
        # 散列布局：随机但有规律
        import math
        for i in range(n):
            angle = i * (2 * math.pi / n)
            radius = 0.35
            x = math.cos(angle) * radius
            y = math.sin(angle) * radius * 0.8
            positions.append((x, y))

    else:
        # 默认网格
        return _calculate_positions(n, width, height, "grid")

    return positions


def _inject_stack_keyframes(
    draft_path: str,
    segments: List[Tuple[int, Any]],
    positions: List[Tuple[float, float]],
    width: int,
    height: int,
    stagger: float,
    slide_duration: float,
    scale_range: Tuple[float, float],
    rotation_range: Tuple[float, float],
):
    """
    注入堆叠入场关键帧到草稿

    Args:
        draft_path: 草稿目录路径
        segments: (index, segment) 列表
        positions: 目标位置列表
        width: 画布宽
        height: 画布高
        stagger: 入场延迟
        slide_duration: 滑入时长
        scale_range: 缩放范围
        rotation_range: 旋转范围
    """
    import json

    content_file = os.path.join(draft_path, "draft_content.json")
    if not os.path.exists(content_file):
        content_file = os.path.join(draft_path, "draft_info.json")
    if not os.path.exists(content_file):
        logger.info(f"❌ 草稿文件不存在: {draft_path}")
        return

    try:
        with open(content_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 按轨道名匹配片段
        track_segments = {}
        for track in data.get("tracks", []):
            track_name = track.get("name", "")
            for seg in track.get("segments", []):
                if track_name.startswith("Stack_"):
                    idx = int(track_name.split("_")[1])
                    track_segments[idx] = seg

        injected = 0
        for idx, seg in track_segments.items():
            if idx >= len(positions):
                continue

            target_x, target_y = positions[idx]
            start_time_us = int(idx * stagger * 1e6)
            slide_us = int(slide_duration * 1e6)

            # 计算缩放和旋转
            import random
            random.seed(idx * 42)
            scale = scale_range[0] + random.random() * (scale_range[1] - scale_range[0])
            rotation = rotation_range[0] + random.random() * (rotation_range[1] - rotation_range[0])

            # 起始位置：屏幕下方
            start_y = target_y + 1.5  # 屏幕下方
            start_x = target_x + random.uniform(-0.2, 0.2)

            # 添加位置X关键帧
            _add_keyframe(seg, "KFPositionX", [
                (start_time_us, start_x),
                (start_time_us + slide_us, target_x),
            ])

            # 添加位置Y关键帧
            _add_keyframe(seg, "KFPositionY", [
                (start_time_us, start_y),
                (start_time_us + slide_us, target_y),
            ])

            # 添加缩放关键帧
            _add_keyframe(seg, "KFScaleX", [
                (start_time_us, scale * 0.8),
                (start_time_us + slide_us, scale),
            ])
            _add_keyframe(seg, "KFScaleY", [
                (start_time_us, scale * 0.8),
                (start_time_us + slide_us, scale),
            ])

            # 添加旋转关键帧
            _add_keyframe(seg, "KFRotation", [
                (start_time_us, rotation + 10),
                (start_time_us + slide_us, rotation),
            ])

            injected += 1

        with open(content_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # 同步到draft_info.json
        info_file = os.path.join(draft_path, "draft_info.json")
        if os.path.exists(info_file) and info_file != content_file:
            with open(info_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"  ✅ 已注入 {injected} 个图片的堆叠入场关键帧")
    except Exception as e:
        logger.error(f"❌ 注入关键帧失败: {e}")


def _add_keyframe(seg: dict, property_type: str, keyframes: List[Tuple[int, float]]):
    """
    给片段添加关键帧

    Args:
        seg: 片段JSON对象
        property_type: 关键帧属性类型
        keyframes: [(time_us, value), ...]
    """
    if "common_keyframes" not in seg:
        seg["common_keyframes"] = []

    # 检查是否已存在该属性的关键帧列表
    for kf_list in seg["common_keyframes"]:
        if kf_list.get("property_type") == property_type:
            # 追加关键帧
            for time_us, value in keyframes:
                kf_list["keyframe_list"].append({
                    "curveType": "Line",
                    "graphID": "",
                    "id": uuid.uuid4().hex.upper(),
                    "left_control": {"x": 0.0, "y": 0.0},
                    "right_control": {"x": 0.0, "y": 0.0},
                    "time_offset": time_us,
                    "values": [value],
                })
            kf_list["keyframe_list"].sort(key=lambda x: x["time_offset"])
            return

    # 创建新的关键帧列表
    kf_list = {
        "id": uuid.uuid4().hex.upper(),
        "keyframe_list": [],
        "material_id": "",
        "property_type": property_type,
    }
    for time_us, value in keyframes:
        kf_list["keyframe_list"].append({
            "curveType": "Line",
            "graphID": "",
            "id": uuid.uuid4().hex.upper(),
            "left_control": {"x": 0.0, "y": 0.0},
            "right_control": {"x": 0.0, "y": 0.0},
            "time_offset": time_us,
            "values": [value],
        })
    seg["common_keyframes"].append(kf_list)


def _create_solid_bg(path: str, width: int, height: int, color: str):
    """创建纯色背景图"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        from PIL import Image
        img = Image.new("RGB", (width, height), color)
        img.save(path)
    except ImportError:
        # 使用ffmpeg创建
        import subprocess
        ffmpeg = r"D:\Ai\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe"
        subprocess.run([
            ffmpeg, "-y",
            "-f", "lavfi", "-i", f"color=c={color}:s={width}x{height}:d=1",
            "-frames:v", "1", path
        ], capture_output=True)


# 预设布局配置
LAYOUT_PRESETS = {
    "grid": {
        "name": "网格排列",
        "desc": "2-3列整齐网格，适合产品展示",
        "scale_range": (0.28, 0.32),
        "rotation_range": (-2, 2),
    },
    "diagonal": {
        "name": "对角线排列",
        "desc": "从左下到右上对角线，有动感",
        "scale_range": (0.25, 0.30),
        "rotation_range": (-8, 8),
    },
    "stack": {
        "name": "堆叠排列",
        "desc": "轻微偏移堆叠，层次感强",
        "scale_range": (0.35, 0.40),
        "rotation_range": (-3, 3),
    },
    "scatter": {
        "name": "散列排列",
        "desc": "圆形散列，活泼有趣",
        "scale_range": (0.22, 0.28),
        "rotation_range": (-10, 10),
    },
}


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("多层图片堆叠入场特效")
    logger.info("=" * 60)
    logger.info("\n可用布局:")
    for name, cfg in LAYOUT_PRESETS.items():
        logger.info(f"  {name}: {cfg['name']} - {cfg['desc']}")
    logger.info("\n使用方法:")
    logger.info("  create_stack_intro(")
    logger.info("    project_name='测试',")
    logger.info("    images=['img1.jpg', 'img2.jpg', 'img3.jpg'],")
    logger.info("    layout='grid',")
    logger.info("    duration=5.0")
    logger.info("  )")
