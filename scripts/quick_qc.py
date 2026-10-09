"""
快速预览质检模块 v1.0
读取剪映工程，自动生成首帧+关键帧预览图，并检查常见问题。

功能：
1. 解析draft_content.json，提取所有片段的位置/缩放/透明度/关键帧
2. 用Pillow合成预览图（首帧+每个关键帧时间点）
3. 自动质检：位置超出屏幕、透明度为0、缩放异常、空轨道等

使用方法：
    python quick_qc.py "D:\\JianyingProDrafts\\...\\工程名"
"""

import logging
logger = logging.getLogger(__name__)

import os
import sys
import json
from typing import List, Dict, Optional, Tuple

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_OK = True
except ImportError:
    PIL_OK = False


def load_draft(draft_path: str) -> Optional[Dict]:
    """加载剪映工程"""
    content_file = os.path.join(draft_path, "draft_content.json")
    if not os.path.exists(content_file):
        # 尝试draft_info.json
        info_file = os.path.join(draft_path, "draft_info.json")
        if os.path.exists(info_file):
            content_file = info_file
        else:
            logger.info(f"❌ 找不到工程文件: {draft_path}")
            return None

    with open(content_file, "r", encoding="utf-8") as f:
        return json.load(f)


def get_canvas_size(data: Dict) -> Tuple[int, int]:
    """获取画布尺寸"""
    canvas = data.get("canvas_config", {})
    w = canvas.get("width", 1080)
    h = canvas.get("height", 1920)
    return w, h


def extract_segments(data: Dict) -> List[Dict]:
    """提取所有视频/图片片段及其关键帧"""
    segments = []
    for track in data.get("tracks", []):
        track_name = track.get("name", "unknown")
        track_type = track.get("type", "")
        for seg in track.get("segments", []):
            seg_info = {
                "id": seg.get("id", ""),
                "track": track_name,
                "type": track_type,
                "start": seg.get("target_timerange", {}).get("start", 0),
                "duration": seg.get("target_timerange", {}).get("duration", 0),
                "material_id": seg.get("material_id", ""),
                "keyframes": {},
            }

            # 提取clip_settings中的默认变换
            clip = seg.get("clip_settings", {})
            transform = clip.get("transform", {})
            seg_info["default_x"] = transform.get("position_x", 0)
            seg_info["default_y"] = transform.get("position_y", 0)
            seg_info["default_scale"] = transform.get("scale", 1.0)
            seg_info["default_alpha"] = clip.get("alpha", 1.0)

            # 提取关键帧（common_keyframes）
            for ckf in seg.get("common_keyframes", []):
                prop = ckf.get("property_type", "")
                kf_list = ckf.get("keyframe_list", [])
                if kf_list:
                    seg_info["keyframes"][prop] = [
                        {
                            "time": kf.get("time_offset", 0),
                            "value": kf.get("values", [0])[0],
                        }
                        for kf in kf_list
                    ]

            segments.append(seg_info)

    return segments


def get_value_at_time(seg_info: Dict, prop: str, time_us: int) -> float:
    """获取某时间点的属性值（线性插值）"""
    default_key = f"default_{prop.replace('KFType', '').lower()}"
    # 简化：直接用默认值或最近的关键帧
    kf_prop_map = {
        "KFTypePositionX": "default_x",
        "KFTypePositionY": "default_y",
        "KFTypeScaleX": "default_scale",
        "KFTypeAlpha": "default_alpha",
    }
    default_val = seg_info.get(kf_prop_map.get(prop, "default_x"), 0)

    kfs = seg_info["keyframes"].get(prop, [])
    if not kfs:
        return default_val

    # 找到时间点前后的关键帧
    before = None
    after = None
    for kf in kfs:
        if kf["time"] <= time_us:
            before = kf
        if kf["time"] >= time_us and after is None:
            after = kf

    if before is None:
        return kfs[0]["value"]
    if after is None or before["time"] == after["time"]:
        return before["value"]

    # 线性插值
    t0, v0 = before["time"], before["value"]
    t1, v1 = after["time"], after["value"]
    ratio = (time_us - t0) / (t1 - t0) if t1 != t0 else 0
    return v0 + (v1 - v0) * ratio


def render_preview(
    segments: List[Dict],
    canvas_w: int,
    canvas_h: int,
    time_us: int,
    output_path: str,
) -> Optional[str]:
    """渲染某时间点的预览图"""
    if not PIL_OK:
        return None

    img = Image.new("RGBA", (canvas_w, canvas_h), (20, 20, 30, 255))
    draw = ImageDraw.Draw(img)

    # 画网格
    for x in range(0, canvas_w, canvas_w // 4):
        draw.line([(x, 0), (x, canvas_h)], fill=(50, 50, 70, 128), width=1)
    for y in range(0, canvas_h, canvas_h // 4):
        draw.line([(0, y), (canvas_w, y)], fill=(50, 50, 70, 128), width=1)

    # 画中心十字
    draw.line([(canvas_w//2, 0), (canvas_w//2, canvas_h)], fill=(100, 100, 150, 128), width=1)
    draw.line([(0, canvas_h//2), (canvas_w, canvas_h//2)], fill=(100, 100, 150, 128), width=1)

    # 渲染每个片段（按轨道顺序）
    colors = [
        (255, 100, 100), (100, 255, 100), (100, 100, 255),
        (255, 255, 100), (255, 100, 255), (100, 255, 255),
    ]
    for i, seg in enumerate(segments):
        # 检查片段是否在当前时间可见
        if time_us < seg["start"] or time_us > seg["start"] + seg["duration"]:
            continue

        x = get_value_at_time(seg, "KFTypePositionX", time_us)
        y = get_value_at_time(seg, "KFTypePositionY", time_us)
        scale = get_value_at_time(seg, "KFTypeScaleX", time_us)
        alpha = get_value_at_time(seg, "KFTypeAlpha", time_us)

        # 转换坐标：剪映坐标(-1~1) -> 像素
        px = int((x + 1) / 2 * canvas_w)
        py = int((1 - y) / 2 * canvas_h)  # y正=上，所以反转
        size = int(80 * scale)

        color = colors[i % len(colors)]
        a = int(255 * max(0, min(1, alpha)))

        # 画矩形代表片段
        draw.rectangle(
            [px - size//2, py - size//2, px + size//2, py + size//2],
            fill=color + (a,),
            outline=(255, 255, 255, 200),
            width=2,
        )

        # 标注轨道名
        try:
            font = ImageFont.truetype("arial.ttf", 14)
        except Exception:
            font = ImageFont.load_default()
        draw.text((px - size//2, py - size//2 - 18), seg["track"][:8], fill=(255,255,255,200), font=font)

    # 时间标注
    draw.text((10, 10), f"t={time_us/1e6:.2f}s", fill=(255,255,255,200), font=font)

    img.save(output_path)
    return output_path


def quality_check(segments: List[Dict], canvas_w: int, canvas_h: int) -> List[str]:
    """自动质检，返回问题列表"""
    issues = []

    for seg in segments:
        name = f"{seg['track']}/{seg['id'][:8]}"

        # 检查所有关键帧时间点
        all_times = set([0])
        for prop, kfs in seg["keyframes"].items():
            for kf in kfs:
                all_times.add(kf["time"])

        for t in all_times:
            x = get_value_at_time(seg, "KFTypePositionX", t)
            y = get_value_at_time(seg, "KFTypePositionY", t)
            alpha = get_value_at_time(seg, "KFTypeAlpha", t)
            scale = get_value_at_time(seg, "KFTypeScaleX", t)

            if abs(x) > 1.5:
                issues.append(f"⚠️ {name} t={t/1e6:.1f}s: x={x:.2f} 超出屏幕")
            if abs(y) > 1.5:
                issues.append(f"⚠️ {name} t={t/1e6:.1f}s: y={y:.2f} 超出屏幕")
            if alpha == 0 and t == 0 and "KFTypeAlpha" not in seg["keyframes"]:
                issues.append(f"⚠️ {name}: 初始透明度为0（可能不可见）")
            if scale == 0:
                issues.append(f"⚠️ {name} t={t/1e6:.1f}s: 缩放为0")
            if scale > 3:
                issues.append(f"⚠️ {name} t={t/1e6:.1f}s: 缩放={scale:.1f} 过大")

        # 检查t=0是否有完整初始状态
        has_x = any(kf["time"] == 0 for kf in seg["keyframes"].get("KFTypePositionX", []))
        has_y = any(kf["time"] == 0 for kf in seg["keyframes"].get("KFTypePositionY", []))
        has_alpha = any(kf["time"] == 0 for kf in seg["keyframes"].get("KFTypeAlpha", []))
        if seg["keyframes"] and (not has_x or not has_y or not has_alpha):
            missing = []
            if not has_x: missing.append("position_x")
            if not has_y: missing.append("position_y")
            if not has_alpha: missing.append("alpha")
            issues.append(f"❌ {name}: t=0缺少初始关键帧: {', '.join(missing)}")

    return issues


def quick_qc(draft_path: str, output_dir: str = None) -> Dict:
    """
    快速质检主函数

    Args:
        draft_path: 剪映工程路径
        output_dir: 预览图输出目录

    Returns:
        质检结果字典
    """
    logger.info("=" * 60)
    logger.info(f"快速质检: {os.path.basename(draft_path)}")
    logger.info("=" * 60)

    data = load_draft(draft_path)
    if not data:
        return {"status": "failed", "reason": "无法加载工程"}

    canvas_w, canvas_h = get_canvas_size(data)
    logger.info(f"画布: {canvas_w}x{canvas_h}")

    segments = extract_segments(data)
    logger.info(f"片段数: {len(segments)}")

    # 收集所有关键帧时间点
    all_times = set([0])
    for seg in segments:
        for prop, kfs in seg["keyframes"].items():
            for kf in kfs:
                all_times.add(kf["time"])
    all_times = sorted(all_times)[:8]  # 最多8个时间点
    logger.info(f"预览时间点: {[f'{t/1e6:.1f}s' for t in all_times]}")

    # 生成预览图
    if output_dir is None:
        output_dir = os.path.join(draft_path, "qc_preview")
    os.makedirs(output_dir, exist_ok=True)

    preview_images = []
    for t in all_times:
        out_path = os.path.join(output_dir, f"preview_{int(t/1e6*10):04d}.png")
        result = render_preview(segments, canvas_w, canvas_h, t, out_path)
        if result:
            preview_images.append(result)

    # 质检
    issues = quality_check(segments, canvas_w, canvas_h)

    logger.info(f"\n{'='*60}")
    logger.info(f"质检结果: {len(issues)} 个问题")
    logger.info(f"{'='*60}")
    for issue in issues:
        logger.info(f"  {issue}")

    if not issues:
        logger.info("  ✅ 未发现明显问题")

    return {
        "status": "success",
        "canvas": (canvas_w, canvas_h),
        "segment_count": len(segments),
        "preview_count": len(preview_images),
        "preview_dir": output_dir,
        "issues": issues,
    }


if __name__ == "__main__":
    if len(sys.argv) > 1:
        draft_path = sys.argv[1]
    else:
        draft_path = r"D:\JianyingProDrafts\JianyingPro Drafts\坐标验证"

    result = quick_qc(draft_path)
    logger.info(f"\n预览图: {result.get('preview_dir', 'N/A')}")
