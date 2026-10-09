"""
蒙版关键帧工具模块 v3
采用标记+注入模式（与混合模式一致）：
1. apply_mask_keyframe() 标记需要注入的关键帧
2. save_with_mask_keyframes() 保存并自动注入到 draft_content.json

蒙版关键帧逆向结果（剪映5.9验证通过）：
- 存储位置: draft_content.json 的片段 common_keyframes 数组
- 蒙版config: width=像素, height=比例(0-1, 相对画布高度)
- KFTypeMaskSizeX: 长度(人眼视角高/垂直, 比例相对画布高度)
- KFTypeMaskSizeY: 宽度(人眼视角宽/水平, 比例相对画布高度)
- KFTypeMaskPostionX: 水平位置(比例, 半个画布宽度为单位, -1~1)
- KFTypeMaskPostionY: 垂直位置(比例, 半个画布高度为单位, -1~1)
- KFTypeMaskRotation: 旋转角度(度)
- KFTypeMaskFeather: 羽化(0-1)

注意: 剪映官方拼写错误 Postion(少一个i), 不是 Position
"""

import logging
logger = logging.getLogger(__name__)


import os
import json
import uuid
import shutil

# 蒙版关键帧属性类型映射（注意Postion拼写）
# KFTypeMaskSizeX=剪映面板"长"=人眼视角宽(水平)，全屏=canvas_w/canvas_h
# KFTypeMaskSizeY=剪映面板"宽"=人眼视角高(垂直)，全屏=1.0
MASK_KF_TYPES = {
    "size_x": "KFTypeMaskSizeX",       # 水平宽度(比例)
    "size_y": "KFTypeMaskSizeY",       # 垂直高度(比例)
    "position_x": "KFTypeMaskPostionX",  # 水平位置(剪映拼写错误Postion)
    "position_y": "KFTypeMaskPostionY",  # 垂直位置
    "rotation": "KFTypeMaskRotation",    # 旋转角度
    "feather": "KFTypeMaskFeather",      # 羽化
    "round_corner": "KFTypeMaskRoundCorner",  # 圆角(未验证)
}

# 缓动曲线预设
CURVE_PRESETS = {
    "EASE_IN": {"curve_type": "Bezier", "left_control": (0.42, 0.0), "right_control": (1.0, 1.0)},
    "EASE_OUT": {"curve_type": "Bezier", "left_control": (0.0, 0.0), "right_control": (0.58, 1.0)},
    "EASE_IN_OUT": {"curve_type": "Bezier", "left_control": (0.42, 0.0), "right_control": (0.58, 1.0)},
    "Line": {"curve_type": "Line", "left_control": (0.0, 0.0), "right_control": (0.0, 0.0)},
}


def apply_mask_keyframe(
    project,
    segment,
    property_name: str,
    time_offset_us: int,
    value: float,
    curve: str = "EASE_OUT",
) -> bool:
    """
    标记需要注入的蒙版关键帧（在 save_with_mask_keyframes 时注入）

    Args:
        project: JyProject 实例
        segment: VideoSegment 实例
        property_name: 蒙版属性名（size_x/size_y/position_x/position_y/rotation/feather）
        time_offset_us: 时间偏移（微秒，相对片段开头）
        value: 属性值（见模块文档说明各属性单位）
        curve: 缓动曲线（EASE_IN/EASE_OUT/EASE_IN_OUT/Line）

    Returns:
        bool: 是否成功
    """
    property_type = MASK_KF_TYPES.get(property_name)
    if not property_type:
        logger.info(f"❌ 不支持的蒙版属性: {property_name}，可用: {list(MASK_KF_TYPES.keys())}")
        return False

    cp = CURVE_PRESETS.get(curve, CURVE_PRESETS["EASE_OUT"])

    seg_id = segment.id if hasattr(segment, 'id') else str(id(segment))
    seg_material_id = segment.material_id if hasattr(segment, 'material_id') else None

    if not hasattr(project, '_mask_kf_patches'):
        project._mask_kf_patches = []

    project._mask_kf_patches.append({
        "segment_id": seg_id,
        "segment_material_id": seg_material_id,
        "property_type": property_type,
        "time_offset": time_offset_us,
        "value": value,
        "curve_type": cp["curve_type"],
        "left_control": cp["left_control"],
        "right_control": cp["right_control"],
    })
    return True


def apply_mask_expand(
    project,
    segment,
    start_us: int,
    duration_us: int,
    direction: str = "left",
    canvas_w: int = 1080,
    canvas_h: int = 1920,
    curve: str = "EASE_OUT",
) -> bool:
    """
    给片段添加蒙版展开动画（标记关键帧，保存时注入）

    Args:
        project: JyProject 实例
        segment: VideoSegment 实例
        start_us: 动画起始时间（微秒，相对片段开头）
        duration_us: 动画持续时间（微秒）
        direction: 展开方向（left/right/top/bottom/center/horizontal/vertical）
        canvas_w: 画布宽
        canvas_h: 画布高
        curve: 缓动曲线

    Returns:
        bool: 是否成功
    """
    end_us = start_us + duration_us

    # 注意：KFTypeMaskSizeX=水平宽度，全屏=1.0
    #       KFTypeMaskSizeY=垂直高度，全屏=1.0
    full_w = 1.0  # 水平全屏
    full_h = 1.0  # 垂直全屏

    if direction in ("left", "right"):
        # 横向展开：水平宽度(size_x)从0→全屏，垂直高度(size_y)保持全屏
        apply_mask_keyframe(project, segment, "size_x", start_us, 0.001, curve)
        apply_mask_keyframe(project, segment, "size_x", end_us, full_w, curve)
        apply_mask_keyframe(project, segment, "size_y", start_us, full_h, curve)
        apply_mask_keyframe(project, segment, "size_y", end_us, full_h, curve)
        # 位置：边缘固定，中心从边缘→中心
        # position_x单位：半个画布宽，-1=左边缘，0=中心，1=右边缘
        if direction == "left":
            apply_mask_keyframe(project, segment, "position_x", start_us, -1.0, curve)
            apply_mask_keyframe(project, segment, "position_x", end_us, 0.0, curve)
        else:
            apply_mask_keyframe(project, segment, "position_x", start_us, 1.0, curve)
            apply_mask_keyframe(project, segment, "position_x", end_us, 0.0, curve)

    elif direction in ("top", "bottom"):
        # 纵向展开：垂直高度(size_y)从0→全屏，水平宽度(size_x)保持全屏
        apply_mask_keyframe(project, segment, "size_y", start_us, 0.001, curve)
        apply_mask_keyframe(project, segment, "size_y", end_us, full_h, curve)
        apply_mask_keyframe(project, segment, "size_x", start_us, full_w, curve)
        apply_mask_keyframe(project, segment, "size_x", end_us, full_w, curve)
        # 位置：边缘固定，中心从边缘→中心
        # position_y单位：半个画布高，-1=上边缘，0=中心，1=下边缘
        if direction == "top":
            apply_mask_keyframe(project, segment, "position_y", start_us, -1.0, curve)
            apply_mask_keyframe(project, segment, "position_y", end_us, 0.0, curve)
        else:
            apply_mask_keyframe(project, segment, "position_y", start_us, 1.0, curve)
            apply_mask_keyframe(project, segment, "position_y", end_us, 0.0, curve)

    elif direction == "center":
        # 中心展开：宽高同时从0→全屏
        apply_mask_keyframe(project, segment, "size_x", start_us, 0.001, curve)
        apply_mask_keyframe(project, segment, "size_x", end_us, full_w, curve)
        apply_mask_keyframe(project, segment, "size_y", start_us, 0.001, curve)
        apply_mask_keyframe(project, segment, "size_y", end_us, full_h, curve)

    elif direction == "horizontal":
        # 水平双向展开：宽度从0→全屏，中心固定
        apply_mask_keyframe(project, segment, "size_x", start_us, 0.001, curve)
        apply_mask_keyframe(project, segment, "size_x", end_us, full_w, curve)
        apply_mask_keyframe(project, segment, "size_y", start_us, full_h, curve)
        apply_mask_keyframe(project, segment, "size_y", end_us, full_h, curve)

    elif direction == "vertical":
        # 垂直双向展开：高度从0→全屏，中心固定
        apply_mask_keyframe(project, segment, "size_y", start_us, 0.001, curve)
        apply_mask_keyframe(project, segment, "size_y", end_us, full_h, curve)
        apply_mask_keyframe(project, segment, "size_x", start_us, full_w, curve)
        apply_mask_keyframe(project, segment, "size_x", end_us, full_w, curve)

    elif direction in ("diagonal_tl", "diagonal_tr", "diagonal_bl", "diagonal_br"):
        # 对角线展开：宽高同时从0→全屏，位置从角落→中心
        apply_mask_keyframe(project, segment, "size_x", start_us, 0.001, curve)
        apply_mask_keyframe(project, segment, "size_x", end_us, full_w, curve)
        apply_mask_keyframe(project, segment, "size_y", start_us, 0.001, curve)
        apply_mask_keyframe(project, segment, "size_y", end_us, full_h, curve)
        # 位置：从角落→中心
        px_start = -1.0 if "tl" in direction or "bl" in direction else 1.0
        py_start = -1.0 if "tl" in direction or "tr" in direction else 1.0
        apply_mask_keyframe(project, segment, "position_x", start_us, px_start, curve)
        apply_mask_keyframe(project, segment, "position_x", end_us, 0.0, curve)
        apply_mask_keyframe(project, segment, "position_y", start_us, py_start, curve)
        apply_mask_keyframe(project, segment, "position_y", end_us, 0.0, curve)

    elif direction == "rotate":
        # 旋转展开：宽高同时从0→全屏，同时旋转
        apply_mask_keyframe(project, segment, "size_x", start_us, 0.001, curve)
        apply_mask_keyframe(project, segment, "size_x", end_us, full_w, curve)
        apply_mask_keyframe(project, segment, "size_y", start_us, 0.001, curve)
        apply_mask_keyframe(project, segment, "size_y", end_us, full_h, curve)
        apply_mask_keyframe(project, segment, "rotation", start_us, 90.0, curve)
        apply_mask_keyframe(project, segment, "rotation", end_us, 0.0, curve)

    elif direction == "center_rotate":
        # 中心旋转展开：从中心展开同时旋转
        apply_mask_keyframe(project, segment, "size_x", start_us, 0.001, curve)
        apply_mask_keyframe(project, segment, "size_x", end_us, full_w, curve)
        apply_mask_keyframe(project, segment, "size_y", start_us, 0.001, curve)
        apply_mask_keyframe(project, segment, "size_y", end_us, full_h, curve)
        apply_mask_keyframe(project, segment, "rotation", start_us, -45.0, curve)
        apply_mask_keyframe(project, segment, "rotation", end_us, 0.0, curve)

    return True


def _fix_mask_config_units(data: dict, canvas_h: int = 1920) -> None:
    """修正蒙版config的单位：height从像素转为比例"""
    for mask in data.get("materials", {}).get("masks", []):
        if mask.get("type") == "mask":
            h = mask["config"].get("height", 0)
            if h > 1.0:  # 像素值需要转换
                mask["config"]["height"] = h / canvas_h


def inject_mask_keyframes_to_draft(draft_path: str, patches: list, canvas_h: int = 1920) -> bool:
    """
    将蒙版关键帧注入到 draft_content.json（在 project.save() 后调用）

    Args:
        draft_path: 草稿目录路径
        patches: 蒙版关键帧补丁列表
        canvas_h: 画布高度（用于修正蒙版config单位）

    Returns:
        bool: 是否成功
    """
    if not patches:
        return True

    content_file = os.path.join(draft_path, "draft_content.json")
    info_file = os.path.join(draft_path, "draft_info.json")

    if not os.path.exists(content_file):
        if os.path.exists(info_file):
            shutil.copy2(info_file, content_file)
        else:
            logger.info(f"❌ 草稿文件不存在: {draft_path}")
            return False

    try:
        with open(content_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 修正蒙版config单位
        _fix_mask_config_units(data, canvas_h)

        # 按片段分组补丁
        seg_patches = {}
        for patch in patches:
            seg_id = patch.get("segment_id")
            if seg_id not in seg_patches:
                seg_patches[seg_id] = []
            seg_patches[seg_id].append(patch)

        injected = 0
        for track in data.get("tracks", []):
            for seg in track.get("segments", []):
                seg_id = seg.get("id", "")
                seg_material_id = seg.get("material_id", "")

                matching_patches = []
                for sid, patches_list in seg_patches.items():
                    for p in patches_list:
                        if p.get("segment_id") == seg_id or p.get("segment_material_id") == seg_material_id:
                            matching_patches.append(p)

                if not matching_patches:
                    continue

                if "common_keyframes" not in seg:
                    seg["common_keyframes"] = []

                # 按属性分组
                prop_kfs = {}
                for patch in matching_patches:
                    prop_type = patch["property_type"]
                    if prop_type not in prop_kfs:
                        prop_kfs[prop_type] = []
                    prop_kfs[prop_type].append({
                        "curveType": patch["curve_type"],
                        "graphID": "",
                        "id": uuid.uuid4().hex.upper(),
                        "left_control": {"x": patch["left_control"][0], "y": patch["left_control"][1]},
                        "right_control": {"x": patch["right_control"][0], "y": patch["right_control"][1]},
                        "time_offset": patch["time_offset"],
                        "values": [patch["value"]],
                    })

                # 合并到片段的 common_keyframes
                existing_props = [kf.get("property_type") for kf in seg["common_keyframes"]]
                for prop_type, kf_list in prop_kfs.items():
                    if prop_type in existing_props:
                        for kf in seg["common_keyframes"]:
                            if kf.get("property_type") == prop_type:
                                kf["keyframe_list"].extend(kf_list)
                                kf["keyframe_list"].sort(key=lambda x: x["time_offset"])
                                break
                    else:
                        seg["common_keyframes"].append({
                            "id": uuid.uuid4().hex.upper(),
                            "keyframe_list": kf_list,
                            "material_id": "",
                            "property_type": prop_type,
                        })
                    injected += len(kf_list)

        with open(content_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # 同步到 draft_info.json
        if os.path.exists(info_file):
            with open(info_file, "r", encoding="utf-8") as f:
                info_data = json.load(f)
            _fix_mask_config_units(info_data, canvas_h)
            for track in info_data.get("tracks", []):
                for seg in track.get("segments", []):
                    seg_id = seg.get("id", "")
                    seg_material_id = seg.get("material_id", "")
                    for sid, patches_list in seg_patches.items():
                        if any(p.get("segment_id") == seg_id or p.get("segment_material_id") == seg_material_id for p in patches_list):
                            # 复制content中的关键帧
                            for ct in data.get("tracks", []):
                                for cs in ct.get("segments", []):
                                    if cs.get("id") == seg_id and cs.get("common_keyframes"):
                                        seg["common_keyframes"] = cs["common_keyframes"]
            with open(info_file, "w", encoding="utf-8") as f:
                json.dump(info_data, f, ensure_ascii=False, indent=2)

        logger.info(f"  ✅ 已注入 {injected} 个蒙版关键帧")
        return True
    except Exception as e:
        logger.error(f"❌ 注入蒙版关键帧失败: {e}")
        return False


def save_with_mask_keyframes(project, canvas_h: int = 1920) -> dict:
    """
    保存工程并自动注入蒙版关键帧

    Args:
        project: JyProject 实例
        canvas_h: 画布高度

    Returns:
        dict: 保存结果
    """
    result = project.save()
    draft_path = result.get("draft_path", "")

    patches = getattr(project, '_mask_kf_patches', [])
    if patches and draft_path:
        inject_mask_keyframes_to_draft(draft_path, patches, canvas_h)
        result["mask_keyframes_injected"] = len(patches)
    else:
        result["mask_keyframes_injected"] = 0

    return result


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("蒙版关键帧工具模块 v3")
    logger.info("=" * 60)
    logger.info("\n支持的蒙版关键帧属性:")
    for name, kf_type in MASK_KF_TYPES.items():
        logger.info(f"  {name}: {kf_type}")
    logger.warning("\n注意: 位置属性剪映拼写为 Postion(非Position)")
    logger.info("\n使用方法:")
    logger.info("  apply_mask_keyframe(project, segment, 'size_y', 0, 0.05)")
    logger.info("  apply_mask_keyframe(project, segment, 'size_y', 3000000, 0.56)")
    logger.info("  apply_mask_expand(project, segment, 0, 500000, direction='left')")
    logger.info("  save_with_mask_keyframes(project)  # 保存并自动注入")
