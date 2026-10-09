"""
百叶窗分屏展开特效
基于教程《13434769778545441》封装

效果原理：
1. 将图片复制N份，每份用蒙版裁剪出一条横向条纹
2. 每条条纹设置不同延迟，交替从左/右展开
3. 最终组合成完整图片，形成百叶窗展开效果

依赖：
- mask_keyframe.py（蒙版关键帧工具）
- jianying-editor（JyProject）
"""

import logging
logger = logging.getLogger(__name__)


import os
import sys
import uuid
from typing import Dict, Any

skill_root = r"C:\Users\Administrator\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills\jianying-editor"
sys.path.insert(0, os.path.join(skill_root, "scripts"))
from jy_wrapper import JyProject
import pyJianYingDraft as draft

try:
    from mask_keyframe import apply_mask_keyframe, save_with_mask_keyframes, MASK_KF_TYPES
    _MASK_KF_AVAILABLE = True
except ImportError:
    _MASK_KF_AVAILABLE = False


def create_blinds_transition(
    project_name: str,
    image_path: str,
    num_strips: int = 6,
    duration: float = 2.0,
    stagger: float = 0.15,
    width: int = 1080,
    height: int = 1920,
    direction: str = "alternate",
    output_dir: str = None,
) -> Dict[str, Any]:
    """
    创建百叶窗分屏展开特效工程

    Args:
        project_name: 工程名
        image_path: 图片路径
        num_strips: 条纹数量（建议4-8）
        duration: 总展开时长（秒）
        stagger: 每条条纹的延迟间隔（秒）
        width: 画布宽
        height: 画布高
        direction: 展开方向（alternate=交替左右，left=全部从左，right=全部从右，center=全部从中心）
        output_dir: 输出目录

    Returns:
        工程信息字典
    """
    if not os.path.exists(image_path):
        return {"status": "failed", "reason": f"图片不存在: {image_path}"}

    if not _MASK_KF_AVAILABLE:
        return {"status": "failed", "reason": "mask_keyframe模块不可用"}

    logger.info(f"\n{'='*60}")
    logger.info(f"百叶窗分屏展开特效")
    logger.info(f"{'='*60}")
    logger.info(f"图片: {image_path}")
    logger.info(f"条纹数: {num_strips}, 总时长: {duration}s, 延迟: {stagger}s")
    logger.info(f"方向: {direction}")

    # 1. 创建工程
    logger.info(f"\n[1/4] 创建工程: {project_name} ({width}x{height})")
    project = JyProject(project_name, width=width, height=height, overwrite=True)

    # 2. 添加N份图片到不同轨道
    logger.info(f"[2/4] 添加 {num_strips} 条条纹到独立轨道")
    segments = []
    strip_height = 1.0 / num_strips  # 每条条纹的高度比例

    for i in range(num_strips):
        track_name = f"BlindsStrip_{i}"
        seg = project.add_media_safe(
            image_path,
            start_time="0s",
            duration=f"{duration + stagger * num_strips + 0.5:.2f}s",
            track_name=track_name,
        )
        if seg:
            segments.append(seg)
            logger.info(f"  ✅ 条纹 {i+1}/{num_strips} -> 轨道 {track_name}")
        else:
            logger.error(f"  ❌ 条纹 {i+1} 添加失败")

    if not segments:
        return {"status": "failed", "reason": "图片添加失败"}

    # 3. 为每条条纹设置蒙版位置和展开动画
    logger.info(f"[3/4] 设置蒙版裁剪和展开动画")
    for i, seg in enumerate(segments):
        # 计算条纹的垂直位置（position_y）
        # position_y: -1=顶部, 0=中心, 1=底部
        # 条纹i的中心位置: from -1 + strip_height/2 + i*strip_height to ...
        # 转换为position_y单位（半个画布高为单位）
        strip_center_y = -1.0 + strip_height / 2 + i * strip_height
        # position_y范围是-1到1，对应整个画布高度
        # 所以strip_center_y需要乘以2？不对，让我重新算
        # position_y=-1是上边缘，position_y=1是下边缘，总范围2.0对应整个画布高度
        # 条纹i的中心（从顶部算起）: strip_height/2 + i*strip_height
        # 转换为position_y: (strip_height/2 + i*strip_height) * 2 - 1
        strip_center_y = (strip_height / 2 + i * strip_height) * 2 - 1

        # 设置蒙版：高度=strip_height，宽度=全屏，位置=条纹中心
        # 起始状态：宽度为0（隐藏）
        # 结束状态：宽度=全屏（显示）

        # 计算这条条纹的展开时间
        strip_start = i * stagger  # 延迟
        strip_duration = duration * 0.6  # 每条的展开时长

        # 决定展开方向
        if direction == "alternate":
            strip_dir = "left" if i % 2 == 0 else "right"
        elif direction == "left":
            strip_dir = "left"
        elif direction == "right":
            strip_dir = "right"
        else:  # center
            strip_dir = "center"

        start_us = int(strip_start * 1e6)
        end_us = int((strip_start + strip_duration) * 1e6)

        # 设置蒙版高度（固定为条纹高度）
        apply_mask_keyframe(project, seg, "size_y", 0, strip_height, "Line")
        apply_mask_keyframe(project, seg, "size_y", end_us + 100000, strip_height, "Line")

        # 设置蒙版垂直位置（固定）
        apply_mask_keyframe(project, seg, "position_y", 0, strip_center_y, "Line")
        apply_mask_keyframe(project, seg, "position_y", end_us + 100000, strip_center_y, "Line")

        # 设置展开动画（水平方向）
        if strip_dir == "left":
            # 从左展开：宽度从0→1，位置从-1→0
            apply_mask_keyframe(project, seg, "size_x", start_us, 0.001, "EASE_OUT")
            apply_mask_keyframe(project, seg, "size_x", end_us, 1.0, "EASE_OUT")
            apply_mask_keyframe(project, seg, "position_x", start_us, -1.0, "EASE_OUT")
            apply_mask_keyframe(project, seg, "position_x", end_us, 0.0, "EASE_OUT")
        elif strip_dir == "right":
            # 从右展开：宽度从0→1，位置从1→0
            apply_mask_keyframe(project, seg, "size_x", start_us, 0.001, "EASE_OUT")
            apply_mask_keyframe(project, seg, "size_x", end_us, 1.0, "EASE_OUT")
            apply_mask_keyframe(project, seg, "position_x", start_us, 1.0, "EASE_OUT")
            apply_mask_keyframe(project, seg, "position_x", end_us, 0.0, "EASE_OUT")
        else:  # center
            # 从中心展开：宽度从0→1，位置固定0
            apply_mask_keyframe(project, seg, "size_x", start_us, 0.001, "EASE_OUT")
            apply_mask_keyframe(project, seg, "size_x", end_us, 1.0, "EASE_OUT")
            apply_mask_keyframe(project, seg, "position_x", start_us, 0.0, "Line")
            apply_mask_keyframe(project, seg, "position_x", end_us, 0.0, "Line")

        logger.info(f"  ✅ 条纹 {i+1}: 位置Y={strip_center_y:.3f}, 方向={strip_dir}, 延迟={strip_start:.2f}s")

    # 4. 保存工程并注入蒙版关键帧
    logger.info(f"[4/4] 保存工程并注入蒙版关键帧")
    result = save_with_mask_keyframes(project, canvas_h=height)
    draft_path = result.get("draft_path", "")

    total_duration = duration + stagger * num_strips

    logger.info(f"\n✅ 百叶窗分屏展开特效创建完成!")
    logger.info(f"   工程: {project_name}")
    logger.info(f"   草稿: {draft_path}")
    logger.info(f"   条纹数: {num_strips}")
    logger.info(f"   总时长: {total_duration:.2f}s")
    logger.info(f"   蒙版关键帧: {result.get('mask_keyframes_injected', 0)}个")

    return {
        "status": "success",
        "project_name": project_name,
        "draft_path": draft_path,
        "num_strips": num_strips,
        "total_duration": total_duration,
        "direction": direction,
        "mask_keyframes": result.get("mask_keyframes_injected", 0),
    }


def add_blinds_to_project(
    project,
    image_path: str,
    start_time: float = 0.0,
    num_strips: int = 6,
    duration: float = 2.0,
    stagger: float = 0.15,
    direction: str = "alternate",
    canvas_h: int = 1920,
) -> Dict[str, Any]:
    """
    在已有工程中添加百叶窗分屏展开效果

    Args:
        project: JyProject 实例
        image_path: 图片路径
        start_time: 起始时间（秒）
        num_strips: 条纹数量
        duration: 展开时长（秒）
        stagger: 延迟间隔（秒）
        direction: 展开方向
        canvas_h: 画布高度

    Returns:
        效果信息字典
    """
    if not _MASK_KF_AVAILABLE:
        return {"status": "failed", "reason": "mask_keyframe模块不可用"}

    segments = []
    strip_height = 1.0 / num_strips
    total_dur = duration + stagger * num_strips + 0.5

    for i in range(num_strips):
        track_name = f"Blinds_{int(start_time*1000)}_{i}"
        seg = project.add_media_safe(
            image_path,
            start_time=f"{start_time:.2f}s",
            duration=f"{total_dur:.2f}s",
            track_name=track_name,
        )
        if seg:
            segments.append(seg)

    for i, seg in enumerate(segments):
        strip_center_y = (strip_height / 2 + i * strip_height) * 2 - 1
        strip_start = start_time + i * stagger
        strip_duration = duration * 0.6

        if direction == "alternate":
            strip_dir = "left" if i % 2 == 0 else "right"
        else:
            strip_dir = direction

        start_us = int(strip_start * 1e6)
        end_us = int((strip_start + strip_duration) * 1e6)

        apply_mask_keyframe(project, seg, "size_y", start_us, strip_height, "Line")
        apply_mask_keyframe(project, seg, "size_y", end_us + 100000, strip_height, "Line")
        apply_mask_keyframe(project, seg, "position_y", start_us, strip_center_y, "Line")
        apply_mask_keyframe(project, seg, "position_y", end_us + 100000, strip_center_y, "Line")

        if strip_dir == "left":
            apply_mask_keyframe(project, seg, "size_x", start_us, 0.001, "EASE_OUT")
            apply_mask_keyframe(project, seg, "size_x", end_us, 1.0, "EASE_OUT")
            apply_mask_keyframe(project, seg, "position_x", start_us, -1.0, "EASE_OUT")
            apply_mask_keyframe(project, seg, "position_x", end_us, 0.0, "EASE_OUT")
        elif strip_dir == "right":
            apply_mask_keyframe(project, seg, "size_x", start_us, 0.001, "EASE_OUT")
            apply_mask_keyframe(project, seg, "size_x", end_us, 1.0, "EASE_OUT")
            apply_mask_keyframe(project, seg, "position_x", start_us, 1.0, "EASE_OUT")
            apply_mask_keyframe(project, seg, "position_x", end_us, 0.0, "EASE_OUT")
        else:
            apply_mask_keyframe(project, seg, "size_x", start_us, 0.001, "EASE_OUT")
            apply_mask_keyframe(project, seg, "size_x", end_us, 1.0, "EASE_OUT")

    return {
        "status": "success",
        "segments": segments,
        "num_strips": num_strips,
    }


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("百叶窗分屏展开特效模块")
    logger.info("=" * 60)
    logger.info(f"\n蒙版关键帧工具: {'✅ 可用' if _MASK_KF_AVAILABLE else '❌ 不可用'}")
    logger.info("\n核心函数:")
    logger.info("  create_blinds_transition(project_name, image_path, ...) - 创建独立工程")
    logger.info("  add_blinds_to_project(project, image_path, ...) - 添加到已有工程")
    logger.info("\n参数说明:")
    logger.info("  num_strips: 条纹数量（建议4-8）")
    logger.info("  duration: 展开时长（秒）")
    logger.info("  stagger: 每条延迟间隔（秒）")
    logger.info("  direction: alternate/left/right/center")
    logger.info("\n使用示例:")
    logger.info("  create_blinds_transition(")
    logger.info("    project_name='百叶窗测试',")
    logger.info("    image_path='photo.jpg',")
    logger.info("    num_strips=6,")
    logger.info("    duration=2.0,")
    logger.info("    stagger=0.15,")
    logger.info("    direction='alternate'")
    logger.info("  )")
