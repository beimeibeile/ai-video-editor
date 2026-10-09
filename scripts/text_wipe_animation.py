"""
羽化擦开文字动画特效
基于教程《文字排版003》封装

效果原理：
1. 创建文字（宋体简，主文白色+副文米黄色）
2. 为文字添加矩形蒙版+羽化
3. 第一段文字从左向右擦开，第二段从右向左擦开
4. 配合翻书声音效（可选）

依赖：
- mask_keyframe.py（蒙版关键帧工具）
- jianying-editor（JyProject）
"""

import logging
logger = logging.getLogger(__name__)


import os
import sys
import uuid
from typing import Dict, Any, Tuple

skill_root = r"C:\Users\Administrator\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills\jianying-editor"
sys.path.insert(0, os.path.join(skill_root, "scripts"))
from jy_wrapper import JyProject
import pyJianYingDraft as draft

try:
    from mask_keyframe import apply_mask_keyframe, save_with_mask_keyframes
    _MASK_KF_AVAILABLE = True
except ImportError:
    _MASK_KF_AVAILABLE = False


def create_text_wipe_animation(
    project_name: str,
    text_main: str = "组合",
    text_sub: str = "动画",
    duration: float = 3.0,
    width: int = 1080,
    height: int = 1920,
    main_color: Tuple[float, float, float] = (1.0, 1.0, 1.0),
    sub_color: Tuple[float, float, float] = (0.95, 0.9, 0.7),
    font_size: float = 15.0,
    feather: float = 0.3,
    output_dir: str = None,
) -> Dict[str, Any]:
    """
    创建羽化擦开文字动画工程

    Args:
        project_name: 工程名
        text_main: 主文字（先擦开，从左向右）
        text_sub: 副文字（后擦开，从右向左）
        duration: 总时长（秒）
        width: 画布宽
        height: 画布高
        main_color: 主文字颜色 (R, G, B) 0-1
        sub_color: 副文字颜色 (R, G, B) 0-1
        font_size: 字体大小
        feather: 蒙版羽化强度 (0-1)
        output_dir: 输出目录

    Returns:
        工程信息字典
    """
    if not _MASK_KF_AVAILABLE:
        return {"status": "failed", "reason": "mask_keyframe模块不可用"}

    logger.info(f"\n{'='*60}")
    logger.info(f"羽化擦开文字动画特效")
    logger.info(f"{'='*60}")
    logger.info(f"文字: {text_main} + {text_sub}")
    logger.info(f"时长: {duration}s, 羽化: {feather}")

    # 1. 创建工程
    logger.info(f"\n[1/4] 创建工程: {project_name} ({width}x{height})")
    project = JyProject(project_name, width=width, height=height, overwrite=True)

    # 2. 添加主文字（从左向右擦开）
    logger.info(f"[2/4] 添加主文字: {text_main}")
    main_style = draft.TextStyle(size=font_size, color=main_color)
    main_seg = project.add_text_simple(
        text=text_main,
        start_time="0s",
        duration=f"{duration}s",
        track_name="TextMain",
        style=main_style,
    )

    # 3. 添加副文字（从右向左擦开）
    logger.info(f"[3/4] 添加副文字: {text_sub}")
    sub_style = draft.TextStyle(size=font_size, color=sub_color)
    sub_seg = project.add_text_simple(
        text=text_sub,
        start_time="0s",
        duration=f"{duration}s",
        track_name="TextSub",
        style=sub_style,
    )

    # 调整副文字位置（在主文字右侧）
    if sub_seg:
        sub_seg.add_keyframe(
            draft.KeyframeProperty.position_x,
            "0s",
            0.3,
        )

    # 4. 设置蒙版擦开动画
    logger.info(f"[4/4] 设置蒙版擦开动画")
    wipe_duration = duration * 0.4  # 擦开时长占40%

    # 主文字：从左向右擦开
    if main_seg:
        # 起始：宽度为0，位置在左边缘
        apply_mask_keyframe(project, main_seg, "size_x", 0, 0.001, "EASE_OUT")
        apply_mask_keyframe(project, main_seg, "size_x", int(wipe_duration * 1e6), 1.0, "EASE_OUT")
        apply_mask_keyframe(project, main_seg, "position_x", 0, -1.0, "EASE_OUT")
        apply_mask_keyframe(project, main_seg, "position_x", int(wipe_duration * 1e6), 0.0, "EASE_OUT")
        # 高度全屏
        apply_mask_keyframe(project, main_seg, "size_y", 0, 1.0, "Line")
        apply_mask_keyframe(project, main_seg, "size_y", int(wipe_duration * 1e6), 1.0, "Line")
        # 羽化
        apply_mask_keyframe(project, main_seg, "feather", 0, feather, "Line")
        apply_mask_keyframe(project, main_seg, "feather", int(wipe_duration * 1e6), feather, "Line")
        logger.info(f"  ✅ 主文字: 左→右擦开, {wipe_duration:.2f}s")

    # 副文字：从右向左擦开（延迟0.3秒）
    if sub_seg:
        sub_delay = 0.3
        sub_start = int(sub_delay * 1e6)
        sub_end = int((sub_delay + wipe_duration) * 1e6)

        apply_mask_keyframe(project, sub_seg, "size_x", sub_start, 0.001, "EASE_OUT")
        apply_mask_keyframe(project, sub_seg, "size_x", sub_end, 1.0, "EASE_OUT")
        apply_mask_keyframe(project, sub_seg, "position_x", sub_start, 1.0, "EASE_OUT")
        apply_mask_keyframe(project, sub_seg, "position_x", sub_end, 0.3, "EASE_OUT")  # 结束位置偏移
        apply_mask_keyframe(project, sub_seg, "size_y", sub_start, 1.0, "Line")
        apply_mask_keyframe(project, sub_seg, "size_y", sub_end, 1.0, "Line")
        apply_mask_keyframe(project, sub_seg, "feather", sub_start, feather, "Line")
        apply_mask_keyframe(project, sub_seg, "feather", sub_end, feather, "Line")
        logger.info(f"  ✅ 副文字: 右→左擦开, 延迟{sub_delay}s, {wipe_duration:.2f}s")

    # 保存工程并注入蒙版关键帧
    result = save_with_mask_keyframes(project, canvas_h=height)
    draft_path = result.get("draft_path", "")

    logger.info(f"\n✅ 羽化擦开文字动画创建完成!")
    logger.info(f"   工程: {project_name}")
    logger.info(f"   草稿: {draft_path}")
    logger.info(f"   蒙版关键帧: {result.get('mask_keyframes_injected', 0)}个")

    return {
        "status": "success",
        "project_name": project_name,
        "draft_path": draft_path,
        "text_main": text_main,
        "text_sub": text_sub,
        "duration": duration,
        "mask_keyframes": result.get("mask_keyframes_injected", 0),
    }


def add_text_wipe_to_project(
    project,
    text_main: str,
    text_sub: str = "",
    start_time: float = 0.0,
    duration: float = 3.0,
    main_color: Tuple[float, float, float] = (1.0, 1.0, 1.0),
    sub_color: Tuple[float, float, float] = (0.95, 0.9, 0.7),
    font_size: float = 15.0,
    feather: float = 0.3,
    canvas_h: int = 1920,
) -> Dict[str, Any]:
    """
    在已有工程中添加羽化擦开文字动画

    Args:
        project: JyProject 实例
        text_main: 主文字
        text_sub: 副文字（空则只显示主文字）
        start_time: 起始时间（秒）
        duration: 持续时长（秒）
        main_color: 主文字颜色
        sub_color: 副文字颜色
        font_size: 字体大小
        feather: 羽化强度
        canvas_h: 画布高度

    Returns:
        效果信息字典
    """
    if not _MASK_KF_AVAILABLE:
        return {"status": "failed", "reason": "mask_keyframe模块不可用"}

    main_style = draft.TextStyle(size=font_size, color=main_color)
    main_seg = project.add_text_simple(
        text=text_main,
        start_time=f"{start_time:.2f}s",
        duration=f"{duration}s",
        track_name=f"WipeMain_{int(start_time*1000)}",
        style=main_style,
    )

    sub_seg = None
    if text_sub:
        sub_style = draft.TextStyle(size=font_size, color=sub_color)
        sub_seg = project.add_text_simple(
            text=text_sub,
            start_time=f"{start_time:.2f}s",
            duration=f"{duration}s",
            track_name=f"WipeSub_{int(start_time*1000)}",
            style=sub_style,
        )
        if sub_seg:
            sub_seg.add_keyframe(draft.KeyframeProperty.position_x, f"{start_time:.2f}s", 0.3)

    wipe_duration = duration * 0.4
    start_us = int(start_time * 1e6)
    end_us = int((start_time + wipe_duration) * 1e6)

    if main_seg:
        apply_mask_keyframe(project, main_seg, "size_x", start_us, 0.001, "EASE_OUT")
        apply_mask_keyframe(project, main_seg, "size_x", end_us, 1.0, "EASE_OUT")
        apply_mask_keyframe(project, main_seg, "position_x", start_us, -1.0, "EASE_OUT")
        apply_mask_keyframe(project, main_seg, "position_x", end_us, 0.0, "EASE_OUT")
        apply_mask_keyframe(project, main_seg, "size_y", start_us, 1.0, "Line")
        apply_mask_keyframe(project, main_seg, "size_y", end_us, 1.0, "Line")
        apply_mask_keyframe(project, main_seg, "feather", start_us, feather, "Line")
        apply_mask_keyframe(project, main_seg, "feather", end_us, feather, "Line")

    if sub_seg:
        sub_delay = 0.3
        sub_start = int((start_time + sub_delay) * 1e6)
        sub_end = int((start_time + sub_delay + wipe_duration) * 1e6)
        apply_mask_keyframe(project, sub_seg, "size_x", sub_start, 0.001, "EASE_OUT")
        apply_mask_keyframe(project, sub_seg, "size_x", sub_end, 1.0, "EASE_OUT")
        apply_mask_keyframe(project, sub_seg, "position_x", sub_start, 1.0, "EASE_OUT")
        apply_mask_keyframe(project, sub_seg, "position_x", sub_end, 0.3, "EASE_OUT")
        apply_mask_keyframe(project, sub_seg, "size_y", sub_start, 1.0, "Line")
        apply_mask_keyframe(project, sub_seg, "size_y", sub_end, 1.0, "Line")
        apply_mask_keyframe(project, sub_seg, "feather", sub_start, feather, "Line")
        apply_mask_keyframe(project, sub_seg, "feather", sub_end, feather, "Line")

    return {
        "status": "success",
        "main_segment": main_seg,
        "sub_segment": sub_seg,
    }


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("羽化擦开文字动画特效模块")
    logger.info("=" * 60)
    logger.info(f"\n蒙版关键帧工具: {'✅ 可用' if _MASK_KF_AVAILABLE else '❌ 不可用'}")
    logger.info("\n核心函数:")
    logger.info("  create_text_wipe_animation(project_name, text_main, text_sub, ...)")
    logger.info("  add_text_wipe_to_project(project, text_main, text_sub, ...)")
    logger.info("\n参数说明:")
    logger.info("  feather: 蒙版羽化强度 (0-1)，越大边缘越柔和")
    logger.info("  主文字从左向右擦开，副文字从右向左擦开（延迟0.3s）")
    logger.info("\n使用示例:")
    logger.info("  create_text_wipe_animation(")
    logger.info("    project_name='文字擦开测试',")
    logger.info("    text_main='组合',")
    logger.info("    text_sub='动画',")
    logger.info("    duration=3.0,")
    logger.info("    feather=0.3")
    logger.info("  )")
