"""
蒙版展开快闪特效模块 v2
基于抖音教学视频"剪映怎么制作蒙版展开快闪"封装

核心原理：
1. 多个画中画轨道叠加纯色块
2. 每个色块通过 scale + transform 关键帧实现"从一侧展开"效果
   （scale_x从0→1模拟横向展开，配合transform_x调整展开中心）
3. 多轨道时序错开，形成依次展开的快闪节奏
4. 可选添加矩形蒙版增加视觉层次

进阶版：复合片段 + 线性蒙版旋转90° + 贝塞尔曲线关键帧（需GUI手动完成）
"""

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
# 展开动画核心：给片段添加scale+transform关键帧
# ──────────────────────────────────────────────

def add_expand_animation(
    segment,
    start_us: int,
    duration_us: int,
    direction: ExpandDirection = "left",
    canvas_w: int = 1080,
    canvas_h: int = 1920,
    curve: str = "EASE_OUT",
) -> None:
    """给片段添加展开动画（通过scale+transform关键帧模拟蒙版展开）

    Args:
        segment: VideoSegment实例
        start_us: 动画起始时间（微秒，相对片段开头）
        duration_us: 动画持续时间（微秒）
        direction: 展开方向
        canvas_w: 画布宽
        canvas_h: 画布高
        curve: 缓动曲线 - EASE_IN / EASE_OUT / EASE_IN_OUT / Line
    """
    end_us = start_us + duration_us
    curve_preset = getattr(draft.Keyframe, curve, draft.Keyframe.EASE_OUT)

    if direction in ("left", "right"):
        # 横向展开：scale_x从0→1，transform_x配合调整
        # 从左侧展开：transform_x从-0.5→0（左边缘固定）
        # 从右侧展开：transform_x从0.5→0（右边缘固定）
        segment.add_keyframe(draft.KeyframeProperty.scale_x, start_us, 0.01, **curve_preset)
        segment.add_keyframe(draft.KeyframeProperty.scale_x, end_us, 1.0, **curve_preset)
        segment.uniform_scale = False

        if direction == "left":
            segment.add_keyframe(draft.KeyframeProperty.position_x, start_us, -0.5, **curve_preset)
            segment.add_keyframe(draft.KeyframeProperty.position_x, end_us, 0.0, **curve_preset)
        else:  # right
            segment.add_keyframe(draft.KeyframeProperty.position_x, start_us, 0.5, **curve_preset)
            segment.add_keyframe(draft.KeyframeProperty.position_x, end_us, 0.0, **curve_preset)

    elif direction in ("top", "bottom"):
        # 纵向展开：scale_y从0→1
        segment.add_keyframe(draft.KeyframeProperty.scale_y, start_us, 0.01, **curve_preset)
        segment.add_keyframe(draft.KeyframeProperty.scale_y, end_us, 1.0, **curve_preset)
        segment.uniform_scale = False

        if direction == "top":
            segment.add_keyframe(draft.KeyframeProperty.position_y, start_us, -0.5, **curve_preset)
            segment.add_keyframe(draft.KeyframeProperty.position_y, end_us, 0.0, **curve_preset)
        else:  # bottom
            segment.add_keyframe(draft.KeyframeProperty.position_y, start_us, 0.5, **curve_preset)
            segment.add_keyframe(draft.KeyframeProperty.position_y, end_us, 0.0, **curve_preset)

    elif direction == "center":
        # 中心展开：scale_x和scale_y同时从0→1
        segment.add_keyframe(draft.KeyframeProperty.scale_x, start_us, 0.01, **curve_preset)
        segment.add_keyframe(draft.KeyframeProperty.scale_x, end_us, 1.0, **curve_preset)
        segment.add_keyframe(draft.KeyframeProperty.scale_y, start_us, 0.01, **curve_preset)
        segment.add_keyframe(draft.KeyframeProperty.scale_y, end_us, 1.0, **curve_preset)
        segment.uniform_scale = False

    elif direction == "horizontal":
        # 水平双向展开：scale_x从0→1，中心固定
        segment.add_keyframe(draft.KeyframeProperty.scale_x, start_us, 0.01, **curve_preset)
        segment.add_keyframe(draft.KeyframeProperty.scale_x, end_us, 1.0, **curve_preset)
        segment.uniform_scale = False

    elif direction == "vertical":
        # 垂直双向展开：scale_y从0→1，中心固定
        segment.add_keyframe(draft.KeyframeProperty.scale_y, start_us, 0.01, **curve_preset)
        segment.add_keyframe(draft.KeyframeProperty.scale_y, end_us, 1.0, **curve_preset)
        segment.uniform_scale = False


# ──────────────────────────────────────────────
# 基础版：多色块依次展开快闪
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
    add_rect_mask: bool = False,
    output_dir: str = None,
) -> Dict[str, Any]:
    """创建基础版蒙版展开快闪工程

    每个色块一个画中画轨道，通过scale+transform关键帧实现展开效果，
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
        add_rect_mask: 是否添加矩形蒙版（增加视觉层次）
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
    print(f"[1/4] 生成 {len(colors)} 个纯色素材")
    color_images = []
    for i, color in enumerate(colors):
        img_path = os.path.join(output_dir, f"block_{i}.png")
        create_solid_color_image(color, width, height, img_path)
        color_images.append(img_path)

    # 2. 创建工程
    print(f"[2/4] 创建工程: {project_name} ({width}x{height})")
    project = JyProject(project_name, width=width, height=height, overwrite=True)

    # 3. 添加画中画轨道 + 展开动画
    print(f"[3/4] 添加 {len(colors)} 个画中画轨道 + 展开动画")
    segments = []
    total_duration = (len(colors) - 1) * stagger_delay + block_duration

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
            # 添加展开动画
            expand_us = int(expand_duration * 1e6)
            add_expand_animation(
                seg, 0, expand_us,
                direction=direction,
                canvas_w=width, canvas_h=height,
                curve="EASE_OUT"
            )

            # 可选：添加矩形蒙版
            if add_rect_mask:
                try:
                    seg.add_mask(
                        draft.MaskType.矩形,
                        center_x=width / 2, center_y=height / 2,
                        size=height, rect_width=width,
                        rotation=0, feather=0, round_corner=0
                    )
                except Exception:
                    pass

            # 出场淡出
            fade_start_us = int((block_duration - 0.2) * 1e6)
            if fade_start_us > expand_us:
                seg.add_keyframe(draft.KeyframeProperty.alpha, fade_start_us, 1.0)
                seg.add_keyframe(draft.KeyframeProperty.alpha, int(block_duration * 1e6), 0.0)

            segments.append(seg)
            print(f"  ✅ 色块 {i}: 方向={direction}, 起始={start_time:.2f}s")

    # 4. 保存
    print(f"[4/4] 保存工程")
    project.save()

    draft_dir = os.path.join(project.root, project.name)
    return {
        "project_name": project_name,
        "draft_path": draft_dir,
        "segments_count": len(segments),
        "total_duration": total_duration,
        "colors": colors,
        "directions": directions,
    }


# ──────────────────────────────────────────────
# 进阶版：条纹扫描快闪（横向色块 + 线性蒙版效果模拟）
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
    """创建条纹扫描快闪工程

    多个横向条纹色块，通过scale_y关键帧依次从上到下展开，
    模拟线性蒙版旋转90°的扫描效果。

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
    print(f"[1/3] 生成纯色素材")
    color_images = []
    for i, color in enumerate(colors[:stripe_count]):
        img_path = os.path.join(output_dir, f"stripe_{i}.png")
        create_solid_color_image(color, width, height, img_path)
        color_images.append(img_path)

    # 创建工程
    print(f"[2/3] 创建工程: {project_name}")
    project = JyProject(project_name, width=width, height=height, overwrite=True)

    # 添加条纹轨道
    print(f"[3/3] 添加 {stripe_count} 个条纹轨道 + 扫描动画")
    stripe_h = height / stripe_count
    segments = []

    for i, img_path in enumerate(color_images):
        track_name = f"Stripe_{i}"
        # 每个条纹占据屏幕的一部分
        y_pos = -1.0 + (2 * i + 1) / stripe_count  # -1到1范围
        scale_y_val = 1.0 / stripe_count

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
                scale_y=scale_y_val
            )
            seg.uniform_scale = False

            # 条纹展开动画：scale_y从0→目标值，依次错开
            stagger = i * 0.08
            expand_us = int(0.3 * 1e6)
            start_us = int(stagger * 1e6)

            seg.add_keyframe(draft.KeyframeProperty.scale_y, start_us, 0.01, **draft.Keyframe.EASE_OUT)
            seg.add_keyframe(draft.KeyframeProperty.scale_y, start_us + expand_us, scale_y_val, **draft.Keyframe.EASE_OUT)

            segments.append(seg)

    project.save()

    draft_dir = os.path.join(project.root, project.name)
    return {
        "project_name": project_name,
        "draft_path": draft_dir,
        "segments_count": len(segments),
        "stripe_count": stripe_count,
    }


# ──────────────────────────────────────────────
# 工具：给现有工程的片段添加展开效果
# ──────────────────────────────────────────────

def apply_expand_to_segments(
    project,
    segments: List,
    direction: ExpandDirection = "left",
    expand_duration: float = 0.3,
    stagger_delay: float = 0.1,
) -> bool:
    """给现有工程的一组片段添加展开效果

    Args:
        project: JyProject实例
        segments: 片段列表
        direction: 展开方向
        expand_duration: 展开时长（秒）
        stagger_delay: 相邻片段延迟（秒）
    """
    if not segments:
        return False

    canvas_w = getattr(project, 'width', 1080)
    canvas_h = getattr(project, 'height', 1920)
    expand_us = int(expand_duration * 1e6)

    for i, seg in enumerate(segments):
        start_us = int(i * stagger_delay * 1e6)
        add_expand_animation(
            seg, start_us, expand_us,
            direction=direction,
            canvas_w=canvas_w, canvas_h=canvas_h,
            curve="EASE_OUT"
        )

    project.save()
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


if __name__ == "__main__":
    print("=" * 60)
    print("蒙版展开快闪特效模块 v2")
    print("=" * 60)
    print("\n核心函数:")
    print("  create_solid_color_image(color, w, h, path) - 生成纯色图片")
    print("  add_expand_animation(seg, start, dur, direction) - 给片段加展开动画")
    print("  create_mask_flash_basic(name, colors, ...) - 基础版快闪工程")
    print("  create_stripe_flash(name, colors, ...) - 条纹扫描快闪工程")
    print("  apply_expand_to_segments(project, segs, ...) - 给现有片段加效果")
    print("\n预设配色:")
    for name in COLOR_PRESETS:
        print(f"  {name}")
    print("\n展开方向: left / right / top / bottom / center / horizontal / vertical")
