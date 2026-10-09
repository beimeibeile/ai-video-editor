"""
混合模式工具 v1.0 (P22-3)
解决v9的问题：没有使用混合模式表现被打时的光影变化。

剪映混合模式通过draft_content.json片段的blend_mode字段设置。
常见混合模式：
- 正常(normal): 0
- 正片叠底(multiply): 1 - 变暗，适合阴影
- 滤色(screen): 2 - 变亮，适合高光/闪白
- 叠加(overlay): 3 - 对比度增强
- 柔光(soft_light): 4 - 柔和对比
- 强光(hard_light): 5 - 强烈对比
- 颜色减淡(color_dodge): 6
- 颜色加深(color_burn): 7
- 变暗(darken): 8
- 变亮(lighten): 9
- 差值(difference): 10
- 排除(exclusion): 11
- 色相(hue): 12
- 饱和度(saturation): 13
- 颜色(color): 14
- 明度(luminosity): 15

使用方法：
1. 构建工程后，调用set_blend_mode设置片段混合模式
2. 调用add_blend_keyframe添加混合模式关键帧
3. 保存工程
"""

import logging
logger = logging.getLogger(__name__)

import os
import json
import uuid
from typing import List, Dict, Any

# 混合模式映射（名称 -> 剪映内部值）
BLEND_MODES = {
    "normal": 0,
    "multiply": 1,
    "screen": 2,
    "overlay": 3,
    "soft_light": 4,
    "hard_light": 5,
    "color_dodge": 6,
    "color_burn": 7,
    "darken": 8,
    "lighten": 9,
    "difference": 10,
    "exclusion": 11,
    "hue": 12,
    "saturation": 13,
    "color": 14,
    "luminosity": 15,
}

# 中文名称映射
BLEND_MODE_CN = {
    "正常": "normal",
    "正片叠底": "multiply",
    "滤色": "screen",
    "叠加": "overlay",
    "柔光": "soft_light",
    "强光": "hard_light",
    "颜色减淡": "color_dodge",
    "颜色加深": "color_burn",
    "变暗": "darken",
    "变亮": "lighten",
    "差值": "difference",
    "排除": "exclusion",
    "色相": "hue",
    "饱和度": "saturation",
    "颜色": "color",
    "明度": "luminosity",
}


def resolve_blend_mode(mode: str) -> int:
    """解析混合模式名称为内部值"""
    if mode in BLEND_MODES:
        return BLEND_MODES[mode]
    if mode in BLEND_MODE_CN:
        return BLEND_MODES[BLEND_MODE_CN[mode]]
    try:
        return int(mode)
    except (ValueError, TypeError):
        return 0


def set_blend_mode(
    draft_path: str,
    segment_id: str,
    blend_mode: str = "normal",
    opacity: float = 1.0,
) -> bool:
    """
    设置片段的混合模式（直接修改draft_content.json）

    Args:
        draft_path: 草稿目录路径
        segment_id: 片段ID
        blend_mode: 混合模式名称
        opacity: 不透明度（0~1）

    Returns:
        bool: 是否成功
    """
    content_file = os.path.join(draft_path, "draft_content.json")
    info_file = os.path.join(draft_path, "draft_info.json")

    mode_value = resolve_blend_mode(blend_mode)
    modified = False

    for filepath in [content_file, info_file]:
        if not os.path.exists(filepath):
            continue
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            for track in data.get('tracks', []):
                for seg in track.get('segments', []):
                    if seg.get('id', '') == segment_id or seg.get('material_id', '') == segment_id:
                        # 设置混合模式
                        seg['blend_mode'] = mode_value
                        # 设置不透明度
                        if 'clip_settings' not in seg:
                            seg['clip_settings'] = {}
                        seg['clip_settings']['alpha'] = opacity
                        modified = True

            if modified:
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"  ❌ 设置混合模式失败 ({filepath}): {e}")
            return False

    return modified


def add_blend_flash(
    draft_path: str,
    segment_id: str,
    start_us: int,
    duration_us: int,
    flash_mode: str = "screen",
    base_mode: str = "normal",
    intensity: float = 1.0,
) -> bool:
    """
    添加混合模式闪白效果（被打时的光影冲击）

    原理：在被打瞬间切换为滤色模式（变亮），然后恢复正常。

    Args:
        draft_path: 草稿目录路径
        segment_id: 片段ID
        start_us: 开始时间（微秒）
        duration_us: 持续时间（微秒）
        flash_mode: 闪白时的混合模式
        base_mode: 基础混合模式
        intensity: 强度（0~1）

    Returns:
        bool: 是否成功
    """
    content_file = os.path.join(draft_path, "draft_content.json")
    if not os.path.exists(content_file):
        # 尝试用info文件
        content_file = os.path.join(draft_path, "draft_info.json")

    try:
        with open(content_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        flash_value = resolve_blend_mode(flash_mode)
        base_value = resolve_blend_mode(base_mode)
        mid_us = start_us + int(duration_us * 0.3)

        for track in data.get('tracks', []):
            for seg in track.get('segments', []):
                if seg.get('id', '') == segment_id or seg.get('material_id', '') == segment_id:
                    if 'common_keyframes' not in seg:
                        seg['common_keyframes'] = []

                    # 检查是否已有blend_mode关键帧
                    blend_kf = None
                    for kf in seg['common_keyframes']:
                        if kf.get('property_type') == 'KFTypeBlendMode':
                            blend_kf = kf
                            break

                    if blend_kf is None:
                        blend_kf = {
                            'id': uuid.uuid4().hex.upper(),
                            'keyframe_list': [],
                            'material_id': '',
                            'property_type': 'KFTypeBlendMode',
                        }
                        seg['common_keyframes'].append(blend_kf)

                    # 添加关键帧：基础→闪白→恢复
                    blend_kf['keyframe_list'].extend([
                        {
                            'curveType': 'Line',
                            'graphID': '',
                            'id': uuid.uuid4().hex.upper(),
                            'left_control': {'x': 0, 'y': 0},
                            'right_control': {'x': 0, 'y': 0},
                            'time_offset': start_us,
                            'values': [base_value],
                        },
                        {
                            'curveType': 'Line',
                            'graphID': '',
                            'id': uuid.uuid4().hex.upper(),
                            'left_control': {'x': 0, 'y': 0},
                            'right_control': {'x': 0, 'y': 0},
                            'time_offset': mid_us,
                            'values': [flash_value],
                        },
                        {
                            'curveType': 'Line',
                            'graphID': '',
                            'id': uuid.uuid4().hex.upper(),
                            'left_control': {'x': 0, 'y': 0},
                            'right_control': {'x': 0, 'y': 0},
                            'time_offset': start_us + duration_us,
                            'values': [base_value],
                        },
                    ])
                    blend_kf['keyframe_list'].sort(key=lambda x: x['time_offset'])

        with open(content_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # 同步到info文件
        info_file = os.path.join(draft_path, "draft_info.json")
        if os.path.exists(info_file) and content_file != info_file:
            import shutil
            shutil.copy2(content_file, info_file)

        return True
    except Exception as e:
        logger.error(f"  ❌ 添加混合模式闪白失败: {e}")
        return False


def apply_impact_effects(
    draft_path: str,
    character_segments: Dict[str, str],
    impact_times: List[float],
) -> Dict[str, Any]:
    """
    应用被打效果（混合模式闪白+不透明度变化）

    Args:
        draft_path: 草稿目录路径
        character_segments: {角色名: 片段ID}
        impact_times: 被打时间点列表（秒）

    Returns:
        应用结果
    """
    results = {}
    for char_name, seg_id in character_segments.items():
        flashes = 0
        for t in impact_times:
            success = add_blend_flash(
                draft_path,
                seg_id,
                start_us=int(t * 1e6),
                duration_us=300_000,
                flash_mode="screen",
                base_mode="normal",
            )
            if success:
                flashes += 1
        results[char_name] = {"flashes_applied": flashes, "total": len(impact_times)}

    return results


def main():
    logger.info("=" * 60)
    logger.info("  混合模式工具 v1.0 (P22-3)")
    logger.info("=" * 60)
    logger.info("\n支持的混合模式:")
    for cn, en in BLEND_MODE_CN.items():
        logger.info(f"  {cn} ({en}) = {BLEND_MODES[en]}")
    logger.info("\n使用方法:")
    logger.info("  set_blend_mode(draft_path, segment_id, '滤色', 0.8)")
    logger.info("  add_blend_flash(draft_path, segment_id, start_us, duration_us, 'screen')")
    logger.info("  apply_impact_effects(draft_path, {角色: 片段ID}, [9.5, 11.8, 14.9])")
    logger.warning("\n注意: 混合模式关键帧(KFTypeBlendMode)需验证剪映是否支持")


if __name__ == "__main__":
    main()
