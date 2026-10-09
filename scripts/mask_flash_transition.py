"""
蒙版展开快闪特效模块 v3
基于抖音教学视频"剪映怎么制作蒙版展开快闪"封装

核心原理（真正蒙版关键帧版）：
1. 多个画中画轨道叠加纯色块
2. 每个色块添加矩形蒙版
3. 通过蒙版大小/位置关键帧实现"从一侧展开"效果
   - KFTypeMaskSizeX = 长度（垂直方向，比例）
   - KFTypeMaskSizeY = 宽度（水平方向，比例）
   - KFTypeMaskPostionX/Y = 位置（剪映拼写错误Postion）
4. 多轨道时序错开，形成依次展开的快闪节奏

依赖：
- mask_keyframe.py（蒙版关键帧工具，已逆向6属性）
- ffmpeg（生成纯色素材）
"""

import logging
logger = logging.getLogger(__name__)


import os
import sys
import json
import uuid
import subprocess
from typing import List, Tuple, Optional, Dict, Any, Literal

# 探测 jianying-editor skill 路径
SKILL_ROOT = next((p for p in [
    os.getenv("JY_SKILL_ROOT", "").strip(),
    r"C:\Users\Administrator\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills\jianying-editor",
    r"C:\Users\Administrator\AppData\Local\DoubaoWork\User Data\Default\.doubaowork\agent_mode\workspace\.user_skills\jianying-editor",
] if p and os.path.exists(os.path.join(p, "scripts", "jy_wrapper.py"))), None)

if SKILL_ROOT:
    sys.path.insert(0, os.path.join(SKILL_ROOT, "scripts"))
    from jy_wrapper import JyProject
    import pyJianYingDraft as draft
else:
    raise ImportError("Could not find jianying-editor skill root.")

# 导入蒙版关键帧工具
_AV_SKILL = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _AV_SKILL)
try:
    from mask_keyframe import apply_mask_expand, apply_mask_keyframe, save_with_mask_keyframes
    _MASK_KF_AVAILABLE = True
except ImportError:
    _MASK_KF_AVAILABLE = False
    logger.info("⚠️  mask_keyframe.py 不可用，将使用scale模拟")

try:
    from paths import FFMPEG
except ImportError:
    FFMPEG = r"D:\Ai\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe"

# 展开方向
ExpandDirection = Literal["left", "right", "top", "bottom", "center", "horizontal", "vertical"]


# ──────────────────────────────────────────────
# 纯色素材生成
# ──────────────────────────────────────────────

def create_solid_color_image(
    color: Tuple[int, int, int],
    width: int = 1080,
    height: int = 1920,
    output_path: str = None,
) -> str:
    """用ffmpeg生成纯色PNG图片"""
    if output_path is None:
        output_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            f"solid_{color[0]}_{color[1]}_{color[2]}.png"
        )
    hex_color = f"0x{color[0]:02x}{color[1]:02x}{color[2]:02x}"
    cmd = [FFMPEG, "-y", "-f", "lavfi", "-i", f"color=c={hex_color}:s={width}x{height}",
           "-frames:v", "1", output_path]
    subprocess.run(cmd, capture_output=True, timeout=30)
    return output_path


# ──────────────────────────────────────────────
# 给片段添加矩形蒙版（静态）
# ──────────────────────────────────────────────

def add_rect_mask_to_segment(segment, canvas_w: int = 1080, canvas_h: int = 1920):
    """
    给片段添加矩形蒙版（全屏初始状态）
    pyJianYingDraft的Mask类：center_x/y以半素材宽/高为单位，中心=0,0
    size=蒙版高度(像素)，rect_width=蒙版宽度(像素)

    Args:
        segment: VideoSegment实例
        canvas_w: 画布宽
        canvas_h: 画布高
    """
    try:
        segment.add_mask(
            draft.MaskType.矩形,
            center_x=0.0,   # 画面中心（半素材宽为单位）
            center_y=0.0,   # 画面中心（半素材高为单位）
            size=canvas_h,  # 蒙版高度=画布高度
            rect_width=canvas_w,  # 蒙版宽度=画布宽度
            rotation=0,
            feather=0,
            round_corner=0
        )
        return True
    except Exception as e:
        logger.error(f"  ⚠️  添加蒙版失败: {e}")
        return False


# ──────────────────────────────────────────────
# 基础版：多色块依次展开快闪（真正蒙版关键帧）
# ──────────────────────────────────────────────

def create_mask_flash_basic(
    project_name: str,
    colors: List[Tuple[int, int, int]],
    width: int = 1080,
    height: int = 1920,
    block_duration: float = 0.8,
    stagger_delay: float = 0.12,
    expand_duration: float = 0.35,
    directions: Optional[List[ExpandDirection]] = None,
    output_dir: str = None,
) -> Dict[str, Any]:
    """
    创建基础版蒙版展开快闪工程（真正蒙版关键帧版）

    每个色块一个画中画轨道，通过蒙版大小/位置关键帧实现展开效果，
    多轨道时序错开形成依次展开的快闪节奏。

    Args:
        project_name: 工程名
        colors: 颜色列表，每个颜色对应一个色块
        width: 画布宽
        height: 画布高
        block_duration: 每个色块持续时长（秒）
        stagger_delay: 相邻色块起始时间差（秒）
        expand_duration: 展开动画时长（秒）
        directions: 每个色块的展开方向，None则交替left/right/top/bottom
        output_dir: 纯色素材输出目录

    Returns:
        工程信息字典
    """
    if output_dir is None:
        output_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "mask_flash_assets"
        )
    os.makedirs(output_dir, exist_ok=True)

    # 默认方向交替
    if directions is None:
        all_dirs = ["left", "right", "top", "bottom", "horizontal", "vertical"]
        directions = [all_dirs[i % len(all_dirs)] for i in range(len(colors))]

    # 1. 生成纯色素材
    logger.info(f"[1/4] 生成 {len(colors)} 个纯色素材")
    color_images = []
    for i, color in enumerate(colors):
        img_path = os.path.join(output_dir, f"block_{i}.png")
        create_solid_color_image(color, width, height, img_path)
        color_images.append(img_path)

    # 2. 创建工程
    logger.info(f"[2/4] 创建工程: {project_name} ({width}x{height})")
    project = JyProject(project_name, width=width, height=height, overwrite=True)

    # 3. 添加画中画轨道 + 蒙版 + 展开关键帧
    logger.info(f"[3/4] 添加 {len(colors)} 个画中画轨道 + 蒙版展开关键帧")
    segments = []
    total_duration = (len(colors) - 1) * stagger_delay + block_duration
    expand_us = int(expand_duration * 1e6)

    for i, (img_path, direction) in enumerate(zip(color_images, directions)):
        start_time = i * stagger_delay
        track_name = f"FlashBlock_{i}"

        seg = project.add_media_safe(
            img_path,
            start_time=f"{start_time}s",
            duration=f"{block_duration}s",
            track_name=track_name
        )

        if seg:
            # 添加矩形蒙版
            add_rect_mask_to_segment(seg, width, height)

            # 添加蒙版展开关键帧（如果mask_keyframe可用）
            if _MASK_KF_AVAILABLE:
                apply_mask_expand(
                    project, seg,
                    start_us=0,
                    duration_us=expand_us,
                    direction=direction,
                    canvas_w=width,
                    canvas_h=height,
                    curve="EASE_OUT"
                )
            else:
                # 回退：使用scale+transform模拟
                _add_scale_expand(seg, 0, expand_us, direction, width, height)

            # 出场淡出
            fade_start_us = int((block_duration - 0.2) * 1e6)
            if fade_start_us > expand_us:
                seg.add_keyframe(draft.KeyframeProperty.alpha, fade_start_us, 1.0)
                seg.add_keyframe(draft.KeyframeProperty.alpha, int(block_duration * 1e6), 0.0)

            segments.append(seg)
            logger.info(f"  ✅ 色块 {i}: 方向={direction}, 起始={start_time:.2f}s")

    # 4. 保存（自动注入蒙版关键帧）
    logger.info(f"[4/4] 保存工程（自动注入蒙版关键帧）")
    if _MASK_KF_AVAILABLE:
        result = save_with_mask_keyframes(project)
    else:
        result = project.save()

    draft_dir = os.path.join(project.root, project.name)
    return {
        "project_name": project_name,
        "draft_path": draft_dir,
        "segments_count": len(segments),
        "total_duration": total_duration,
        "colors": colors,
        "directions": directions,
        "mask_keyframes": _MASK_KF_AVAILABLE,
    }


# ──────────────────────────────────────────────
# 回退方案：scale+transform模拟展开
# ──────────────────────────────────────────────

def _add_scale_expand(
    segment,
    start_us: int,
    duration_us: int,
    direction: ExpandDirection,
    canvas_w: int,
    canvas_h: int,
    curve: str = "EASE_OUT",
):
    """使用scale+transform模拟蒙版展开（回退方案）"""
    end_us = start_us + duration_us
    curve_preset = getattr(draft.Keyframe, curve, draft.Keyframe.EASE_OUT)

    if direction in ("left", "right"):
        segment.add_keyframe(draft.KeyframeProperty.scale_x, start_us, 0.01, **curve_preset)
        segment.add_keyframe(draft.KeyframeProperty.scale_x, end_us, 1.0, **curve_preset)
        segment.uniform_scale = False
        tx = -0.5 if direction == "left" else 0.5
        segment.add_keyframe(draft.KeyframeProperty.position_x, start_us, tx, **curve_preset)
        segment.add_keyframe(draft.KeyframeProperty.position_x, end_us, 0.0, **curve_preset)
    elif direction in ("top", "bottom"):
        segment.add_keyframe(draft.KeyframeProperty.scale_y, start_us, 0.01, **curve_preset)
        segment.add_keyframe(draft.KeyframeProperty.scale_y, end_us, 1.0, **curve_preset)
        segment.uniform_scale = False
        ty = -0.5 if direction == "top" else 0.5
        segment.add_keyframe(draft.KeyframeProperty.position_y, start_us, ty, **curve_preset)
        segment.add_keyframe(draft.KeyframeProperty.position_y, end_us, 0.0, **curve_preset)
    elif direction == "center":
        segment.add_keyframe(draft.KeyframeProperty.scale_x, start_us, 0.01, **curve_preset)
        segment.add_keyframe(draft.KeyframeProperty.scale_x, end_us, 1.0, **curve_preset)
        segment.add_keyframe(draft.KeyframeProperty.scale_y, start_us, 0.01, **curve_preset)
        segment.add_keyframe(draft.KeyframeProperty.scale_y, end_us, 1.0, **curve_preset)
        segment.uniform_scale = False
    elif direction == "horizontal":
        segment.add_keyframe(draft.KeyframeProperty.scale_x, start_us, 0.01, **curve_preset)
        segment.add_keyframe(draft.KeyframeProperty.scale_x, end_us, 1.0, **curve_preset)
        segment.uniform_scale = False
    elif direction == "vertical":
        segment.add_keyframe(draft.KeyframeProperty.scale_y, start_us, 0.01, **curve_preset)
        segment.add_keyframe(draft.KeyframeProperty.scale_y, end_us, 1.0, **curve_preset)
        segment.uniform_scale = False


# ──────────────────────────────────────────────
# 条纹扫描快闪（横向色块 + 蒙版扫描）
# ──────────────────────────────────────────────

def create_stripe_flash(
    project_name: str,
    colors: List[Tuple[int, int, int]],
    width: int = 1080,
    height: int = 1920,
    total_duration: float = 2.0,
    stripe_count: int = 5,
    output_dir: str = None,
) -> Dict[str, Any]:
    """
    创建条纹扫描快闪工程（真正蒙版关键帧版）

    多个横向条纹色块，通过蒙版位置关键帧依次从上到下扫描展开。

    Args:
        project_name: 工程名
        colors: 颜色列表
        width: 画布宽
        height: 画布高
        total_duration: 总时长（秒）
        stripe_count: 条纹数量
        output_dir: 素材输出目录
    """
    if output_dir is None:
        output_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "mask_flash_assets"
        )
    os.makedirs(output_dir, exist_ok=True)

    # 生成纯色素材
    logger.info(f"[1/3] 生成纯色素材")
    color_images = []
    for i, color in enumerate(colors[:stripe_count]):
        img_path = os.path.join(output_dir, f"stripe_{i}.png")
        create_solid_color_image(color, width, height, img_path)
        color_images.append(img_path)

    # 创建工程
    logger.info(f"[2/3] 创建工程: {project_name}")
    project = JyProject(project_name, width=width, height=height, overwrite=True)

    # 添加条纹轨道 + 蒙版扫描
    logger.info(f"[3/3] 添加 {stripe_count} 个条纹轨道 + 蒙版扫描动画")
    stripe_h = height / stripe_count
    segments = []

    for i, img_path in enumerate(color_images):
        track_name = f"Stripe_{i}"
        # 每个条纹占据屏幕的一部分
        y_pos = -1.0 + (2 * i + 1) / stripe_count

        seg = project.add_media_safe(
            img_path,
            start_time="0s",
            duration=f"{total_duration}s",
            track_name=track_name
        )

        if seg:
            # 设置初始位置和缩放（条纹布局）
            seg.clip_settings = draft.ClipSettings(
                transform_x=0.0,
                transform_y=y_pos,
                scale_x=1.0,
                scale_y=1.0 / stripe_count
            )
            seg.uniform_scale = False

            # 添加矩形蒙版
            add_rect_mask_to_segment(seg, width, height)

            # 蒙版扫描动画：位置从上到下移动
            if _MASK_KF_AVAILABLE:
                stagger = i * 0.08
                scan_us = int(0.3 * 1e6)
                start_us = int(stagger * 1e6)

                # 蒙版从上方扫到下方
                apply_mask_keyframe(project, seg, "position_y", start_us, -1.0, "EASE_OUT")
                apply_mask_keyframe(project, seg, "position_y", start_us + scan_us, 0.0, "EASE_OUT")
                # 蒙版高度从0到全屏
                apply_mask_keyframe(project, seg, "size_x", start_us, 0.001, "EASE_OUT")
                apply_mask_keyframe(project, seg, "size_x", start_us + scan_us, 1.0, "EASE_OUT")

            segments.append(seg)

    # 保存
    if _MASK_KF_AVAILABLE:
        result = save_with_mask_keyframes(project)
    else:
        result = project.save()

    draft_dir = os.path.join(project.root, project.name)
    return {
        "project_name": project_name,
        "draft_path": draft_dir,
        "segments_count": len(segments),
        "stripe_count": stripe_count,
    }


# ──────────────────────────────────────────────
# 工具：给现有工程的片段添加蒙版展开效果
# ──────────────────────────────────────────────

def apply_expand_to_segments(
    project,
    segments: List,
    direction: ExpandDirection = "left",
    expand_duration: float = 0.3,
    stagger_delay: float = 0.1,
    canvas_w: int = 1080,
    canvas_h: int = 1920,
) -> bool:
    """
    给现有工程的一组片段添加蒙版展开效果

    Args:
        project: JyProject实例
        segments: 片段列表
        direction: 展开方向
        expand_duration: 展开时长（秒）
        stagger_delay: 相邻片段延迟（秒）
        canvas_w: 画布宽
        canvas_h: 画布高
    """
    if not segments:
        return False

    expand_us = int(expand_duration * 1e6)

    for i, seg in enumerate(segments):
        # 添加矩形蒙版
        add_rect_mask_to_segment(seg, canvas_w, canvas_h)

        # 添加蒙版展开关键帧
        if _MASK_KF_AVAILABLE:
            start_us = int(i * stagger_delay * 1e6)
            apply_mask_expand(
                project, seg, start_us, expand_us,
                direction=direction,
                canvas_w=canvas_w, canvas_h=canvas_h,
                curve="EASE_OUT"
            )

    return True


# ──────────────────────────────────────────────
# 预设配色方案
# ──────────────────────────────────────────────

COLOR_PRESETS = {
    "cyberpunk": [(0, 255, 255), (255, 0, 255), (255, 255, 0), (0, 255, 0)],
    "warm": [(255, 100, 50), (255, 200, 50), (255, 150, 100), (200, 80, 30)],
    "cool": [(50, 100, 255), (100, 200, 255), (150, 100, 255), (50, 200, 200)],
    "mono": [(255, 255, 255), (200, 200, 200), (150, 150, 150), (100, 100, 100)],
    "neon": [(255, 0, 128), (0, 255, 128), (128, 0, 255), (255, 128, 0)],
    "pastel": [(255, 200, 200), (200, 255, 200), (200, 200, 255), (255, 255, 200)],
}


# ──────────────────────────────────────────────
# v4: 四角汇聚快闪（双轴向对角线展开+旋转）
# ──────────────────────────────────────────────

def create_mask_flash_v4(
    project_name: str,
    colors: List[Tuple[int, int, int]] = None,
    width: int = 1080,
    height: int = 1920,
    block_duration: float = 1.2,
    stagger_delay: float = 0.08,
    expand_duration: float = 0.4,
    mode: str = "diagonal",  # diagonal / rotate / mixed
    output_dir: str = None,
) -> Dict[str, Any]:
    """
    创建v4蒙版快闪工程：四角汇聚+双轴向展开

    4个色块从四个角落同时/错峰向中心对角线展开，
    最终汇聚成完整画面。比单轴向展开更有视觉冲击力。

    Args:
        project_name: 工程名
        colors: 4个颜色，None则用cyberpunk预设
        width/height: 画布尺寸
        block_duration: 每个色块持续时长
        stagger_delay: 相邻色块起始时间差
        expand_duration: 展开动画时长
        mode: diagonal(对角线展开) / rotate(旋转展开) / mixed(混合)
        output_dir: 素材输出目录

    Returns:
        工程信息字典
    """
    if colors is None:
        colors = COLOR_PRESETS["cyberpunk"]
    colors = colors[:4]  # 最多4个色块

    if output_dir is None:
        output_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "mask_flash_assets"
        )
    os.makedirs(output_dir, exist_ok=True)

    # 四角展开方向映射
    corner_directions = ["diagonal_tl", "diagonal_tr", "diagonal_bl", "diagonal_br"]
    if mode == "rotate":
        corner_directions = ["rotate", "rotate", "rotate", "rotate"]
    elif mode == "mixed":
        corner_directions = ["diagonal_tl", "rotate", "diagonal_br", "center_rotate"]

    # 1. 生成纯色素材
    logger.info(f"[1/4] 生成 {len(colors)} 个纯色素材")
    color_images = []
    for i, color in enumerate(colors):
        img_path = os.path.join(output_dir, f"v4_block_{i}.png")
        create_solid_color_image(color, width, height, img_path)
        color_images.append(img_path)

    # 2. 创建工程
    logger.info(f"[2/4] 创建工程: {project_name} ({width}x{height}, mode={mode})")
    project = JyProject(project_name, width=width, height=height, overwrite=True)

    # 3. 添加画中画轨道 + 蒙版 + 双轴向展开关键帧
    logger.info(f"[3/4] 添加 {len(colors)} 个画中画轨道 + 四角汇聚展开")
    segments = []
    total_duration = (len(colors) - 1) * stagger_delay + block_duration
    expand_us = int(expand_duration * 1e6)

    for i, (img_path, direction) in enumerate(zip(color_images, corner_directions)):
        start_time = i * stagger_delay
        track_name = f"V4Block_{i}"

        seg = project.add_media_safe(
            img_path,
            start_time=f"{start_time}s",
            duration=f"{block_duration}s",
            track_name=track_name
        )

        if seg:
            # 添加矩形蒙版
            add_rect_mask_to_segment(seg, width, height)

            # 添加蒙版展开关键帧（双轴向对角线展开）
            if _MASK_KF_AVAILABLE:
                apply_mask_expand(
                    project, seg,
                    start_us=0,
                    duration_us=expand_us,
                    direction=direction,
                    canvas_w=width,
                    canvas_h=height,
                    curve="EASE_OUT"
                )
            else:
                _add_scale_expand(seg, 0, expand_us, "center", width, height)

            # 出场淡出
            fade_start_us = int((block_duration - 0.15) * 1e6)
            if fade_start_us > expand_us:
                seg.add_keyframe(draft.KeyframeProperty.alpha, fade_start_us, 1.0)
                seg.add_keyframe(draft.KeyframeProperty.alpha, int(block_duration * 1e6), 0.0)

            segments.append(seg)
            corner_name = ["左上", "右上", "左下", "右下"][i]
            logger.info(f"  ✅ 色块 {i}({corner_name}): 方向={direction}, 起始={start_time:.2f}s")

    # 4. 保存
    logger.info(f"[4/4] 保存工程")
    if _MASK_KF_AVAILABLE:
        result = save_with_mask_keyframes(project)
    else:
        result = project.save()

    draft_dir = os.path.join(project.root, project.name)
    return {
        "project_name": project_name,
        "draft_path": draft_dir,
        "segments_count": len(segments),
        "total_duration": total_duration,
        "colors": colors,
        "mode": mode,
        "directions": corner_directions,
        "version": "v4",
    }


# ──────────────────────────────────────────────
# v5: 网格错峰快闪（2x2网格，每格从中心展开）
# ──────────────────────────────────────────────

def create_mask_flash_v5(
    project_name: str,
    colors: List[Tuple[int, int, int]] = None,
    width: int = 1080,
    height: int = 1920,
    block_duration: float = 1.0,
    stagger_delay: float = 0.06,
    expand_duration: float = 0.35,
    output_dir: str = None,
) -> Dict[str, Any]:
    """
    创建v5网格错峰快闪：2x2网格，每格从自身中心展开

    4个色块占据画面四分之一区域，从各自中心向四周展开，
    错峰时序形成波浪式展开效果。

    Args:
        project_name: 工程名
        colors: 4个颜色
        width/height: 画布尺寸
        block_duration: 持续时长
        stagger_delay: 错峰延迟
        expand_duration: 展开时长
        output_dir: 素材目录

    Returns:
        工程信息字典
    """
    if colors is None:
        colors = COLOR_PRESETS["neon"]
    colors = colors[:4]

    if output_dir is None:
        output_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "mask_flash_assets"
        )
    os.makedirs(output_dir, exist_ok=True)

    # 2x2网格位置（position_x/y单位：半个画布，-1~1）
    # 左上(-0.5,-0.5) 右上(0.5,-0.5) 左下(-0.5,0.5) 右下(0.5,0.5)
    grid_positions = [(-0.5, -0.5), (0.5, -0.5), (-0.5, 0.5), (0.5, 0.5)]
    # 展开顺序：左上→右下→右上→左下（对角线波浪）
    expand_order = [0, 3, 1, 2]

    # 1. 生成纯色素材
    logger.info(f"[1/4] 生成 {len(colors)} 个纯色素材")
    color_images = []
    for i, color in enumerate(colors):
        img_path = os.path.join(output_dir, f"v5_block_{i}.png")
        create_solid_color_image(color, width, height, img_path)
        color_images.append(img_path)

    # 2. 创建工程
    logger.info(f"[2/4] 创建工程: {project_name} (2x2网格错峰)")
    project = JyProject(project_name, width=width, height=height, overwrite=True)

    # 3. 添加轨道 + 网格位置 + 中心展开
    logger.info(f"[3/4] 添加 {len(colors)} 个网格色块 + 错峰展开")
    segments = []
    total_duration = (len(colors) - 1) * stagger_delay + block_duration
    expand_us = int(expand_duration * 1e6)

    for order_idx, color_idx in enumerate(expand_order):
        img_path = color_images[color_idx]
        px, py = grid_positions[color_idx]
        start_time = order_idx * stagger_delay
        track_name = f"V5Grid_{color_idx}"

        seg = project.add_media_safe(
            img_path,
            start_time=f"{start_time}s",
            duration=f"{block_duration}s",
            track_name=track_name
        )

        if seg:
            # 设置初始位置（网格四分之一）
            seg.clip_settings = draft.ClipSettings(
                transform_x=px,
                transform_y=py,
                scale_x=0.5,
                scale_y=0.5,
            )
            seg.uniform_scale = False

            # 添加矩形蒙版
            add_rect_mask_to_segment(seg, width, height)

            # 蒙版从中心展开（size_x/size_y同时0→1）
            if _MASK_KF_AVAILABLE:
                apply_mask_expand(
                    project, seg,
                    start_us=0,
                    duration_us=expand_us,
                    direction="center",
                    canvas_w=width,
                    canvas_h=height,
                    curve="EASE_OUT"
                )

            # 出场淡出
            fade_start_us = int((block_duration - 0.15) * 1e6)
            if fade_start_us > expand_us:
                seg.add_keyframe(draft.KeyframeProperty.alpha, fade_start_us, 1.0)
                seg.add_keyframe(draft.KeyframeProperty.alpha, int(block_duration * 1e6), 0.0)

            segments.append(seg)
            corner = ["左上", "右上", "左下", "右下"][color_idx]
            logger.info(f"  ✅ 网格{corner}: 起始={start_time:.2f}s, 顺序={order_idx+1}")

    # 4. 保存
    logger.info(f"[4/4] 保存工程")
    if _MASK_KF_AVAILABLE:
        result = save_with_mask_keyframes(project)
    else:
        result = project.save()

    draft_dir = os.path.join(project.root, project.name)
    return {
        "project_name": project_name,
        "draft_path": draft_dir,
        "segments_count": len(segments),
        "total_duration": total_duration,
        "colors": colors,
        "version": "v5",
        "grid": "2x2",
    }


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("蒙版展开快闪特效模块 v5")
    logger.info("=" * 60)
    logger.info(f"\n蒙版关键帧工具: {'✅ 可用' if _MASK_KF_AVAILABLE else '❌ 不可用(回退scale模拟)'}")
    logger.info("\n核心函数:")
    logger.info("  create_solid_color_image(color, w, h, path) - 生成纯色图片")
    logger.info("  create_mask_flash_basic(name, colors, ...) - v3基础版快闪(单轴向)")
    logger.info("  create_mask_flash_v4(name, colors, mode=...) - v4四角汇聚(双轴向对角线/旋转)")
    logger.info("  create_mask_flash_v5(name, colors, ...) - v5网格错峰(2x2中心展开)")
    logger.info("  create_stripe_flash(name, colors, ...) - 条纹扫描快闪")
    logger.info("\nv4模式: diagonal(对角线) / rotate(旋转) / mixed(混合)")
    logger.info("\n预设配色:")
    for name in COLOR_PRESETS:
        logger.info(f"  {name}")
