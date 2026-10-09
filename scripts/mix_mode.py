"""
混合模式工具模块
支持在剪映草稿中设置片段的混合模式（正片叠底、滤色、叠加等）

使用方法：
    from mix_mode import apply_mix_mode
    apply_mix_mode(project, segment, mode="multiply")

混合模式通过直接修改draft_content.json实现：
1. 在materials.effects中添加mix_mode类型的effect
2. 将effect id添加到片段的extra_material_refs中
"""

import logging
logger = logging.getLogger(__name__)


import os
import json
import uuid


# 混合模式映射表（从剪映5.9资源目录逆向）
# 每个模式包含: name, effect_id, resource_id, path_hash
MIX_MODES = {
    "multiply": {
        "name": "正片叠底",
        "effect_id": "871333",
        "resource_id": "6758325895519277582",
        "path_hash": "8001e07eefc5d8b69572b977ca14bef9",
    },
    "screen": {
        "name": "滤色",
        "effect_id": "871339",
        "resource_id": "6758325170760323597",
        "path_hash": "d9c1d4ca7ab91df4f48d12b339f2da88",
    },
    "lighten": {
        "name": "变亮",
        "effect_id": "871341",
        "resource_id": "6758324919789949453",
        "path_hash": "b0e90c43dc266a317b05b0cd3ca5bfba",
    },
    "darken": {
        "name": "变暗",
        "effect_id": "871342",
        "resource_id": "6758324839670354445",
        "path_hash": "420c92a2b480dc8e402d9269a5f83515",
    },
    "overlay": {
        "name": "叠加",
        "effect_id": "871340",
        "resource_id": "6758324989931295240",
        "path_hash": "e6a48579910dfe831ba53a6acc6737f9",
    },
    "hard_light": {
        "name": "强光",
        "effect_id": "871338",
        "resource_id": "6758325264670790152",
        "path_hash": "840ca85a1a33e6fc3ea78bbdb2db8f60",
    },
    "soft_light": {
        "name": "柔光",
        "effect_id": "871337",
        "resource_id": "6758325439212556814",
        "path_hash": "042aa15b71b1e17bca0bd928eec6fba7",
    },
    "linear_burn": {
        "name": "线性加深",
        "effect_id": "871336",
        "resource_id": "6758325619253056013",
        "path_hash": "655f3590dd07ece41209fb312348ffe9",
    },
    "color_dodge": {
        "name": "颜色减淡",
        "effect_id": "871334",
        "resource_id": "6758325800031752712",
        "path_hash": "f979dd10def50fad3ffb77c7f0df3db7",
    },
    "color_burn": {
        "name": "颜色加深",
        "effect_id": "871335",
        "resource_id": "6758325724848853518",
        "path_hash": "b76087cda4833f553cf09e82fb81c463",
    },
}


def _get_jianying_resources_path() -> str:
    """获取剪映资源目录路径"""
    candidates = [
        r"C:\Users\Administrator\Downloads\JianyingPro_5.9（windows版本）\5.9.0.11632\Resources",
        r"C:\Program Files\JianyingPro\5.9.0.11632\Resources",
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return candidates[0]


def apply_mix_mode(project, segment, mode: str = "multiply", intensity: float = 1.0) -> bool:
    """
    给片段应用混合模式

    Args:
        project: JyProject 实例
        segment: VideoSegment 实例
        mode: 混合模式名称（multiply/screen/overlay等）
        intensity: 强度（0-1）

    Returns:
        bool: 是否成功
    """
    mode_config = MIX_MODES.get(mode)
    if not mode_config or not mode_config["effect_id"]:
        logger.info(f"❌ 混合模式 '{mode}' 尚未逆向，可用: {[k for k,v in MIX_MODES.items() if v['effect_id']]}")
        return False

    # 生成effect id
    effect_id = str(uuid.uuid4()).upper()

    # 构建mix_mode effect
    res_path = os.path.join(_get_jianying_resources_path(), "MixMode", mode_config["path_hash"])
    mix_effect = {
        "adjust_params": [],
        "algorithm_artifact_path": "",
        "apply_target_type": 0,
        "bloom_params": None,
        "category_id": "",
        "category_name": "",
        "color_match_info": {
            "source_feature_path": "",
            "target_feature_path": "",
            "target_image_path": ""
        },
        "effect_id": mode_config["effect_id"],
        "enable_skin_tone_correction": False,
        "exclusion_group": [],
        "face_adjust_params": [],
        "formula_id": "",
        "id": effect_id,
        "intensity_key": "",
        "multi_language_current": "",
        "name": mode_config["name"],
        "panel_id": "",
        "path": res_path,
        "platform": "all",
        "request_id": "",
        "resource_id": mode_config["resource_id"],
        "source_platform": 0,
        "sub_type": "none",
        "time_range": None,
        "type": "mix_mode",
        "value": intensity,
        "version": ""
    }

    # 标记需要在保存时注入
    if not hasattr(project, '_mix_mode_patches'):
        project._mix_mode_patches = []
    project._mix_mode_patches.append({
        "segment_id": segment.id if hasattr(segment, 'id') else str(id(segment)),
        "segment_material_id": segment.material_id if hasattr(segment, 'material_id') else None,
        "effect": mix_effect,
    })

    logger.info(f"  ✅ 混合模式: {mode_config['name']} (强度{intensity})")
    return True


def inject_mix_modes_to_draft(draft_path: str, patches: list) -> bool:
    """
    将混合模式注入到草稿文件中（在project.save()后调用）

    Args:
        draft_path: 草稿目录路径
        patches: 混合模式补丁列表

    Returns:
        bool: 是否成功
    """
    if not patches:
        return True

    content_file = os.path.join(draft_path, "draft_content.json")
    if not os.path.exists(content_file):
        # 尝试draft_info.json
        content_file = os.path.join(draft_path, "draft_info.json")
    if not os.path.exists(content_file):
        logger.info(f"❌ 草稿文件不存在: {draft_path}")
        return False

    try:
        with open(content_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        materials = data.setdefault("materials", {})
        effects = materials.setdefault("effects", [])

        for patch in patches:
            effect = patch["effect"]
            effects.append(effect)

            # 找到对应片段并添加extra_material_refs
            # 匹配优先级：segment_material_id > segment_id > 索引位置
            matched = False
            for track in data.get("tracks", []):
                for seg in track.get("segments", []):
                    # 优先通过material_id匹配
                    if patch.get("segment_material_id") and seg.get("material_id") == patch["segment_material_id"]:
                        refs = seg.setdefault("extra_material_refs", [])
                        if effect["id"] not in refs:
                            refs.append(effect["id"])
                        matched = True
                        break
                    # 其次通过segment id匹配
                    if patch.get("segment_id") and seg.get("id") == patch["segment_id"]:
                        refs = seg.setdefault("extra_material_refs", [])
                        if effect["id"] not in refs:
                            refs.append(effect["id"])
                        matched = True
                        break
                if matched:
                    break

            if not matched:
                logger.info(f"  ⚠️  未找到匹配片段: segment_id={patch.get('segment_id')}, material_id={patch.get('segment_material_id')}")

        with open(content_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"  ✅ 已注入 {len(patches)} 个混合模式到草稿")
        return True
    except Exception as e:
        logger.error(f"❌ 注入混合模式失败: {e}")
        return False


def save_with_mix_modes(project) -> dict:
    """
    保存工程并自动注入混合模式

    Args:
        project: JyProject 实例

    Returns:
        dict: 保存结果，包含draft_path和mix_mode_injected
    """
    result = project.save()
    draft_path = result.get("draft_path", "")

    patches = getattr(project, '_mix_mode_patches', [])
    if patches and draft_path:
        inject_mix_modes_to_draft(draft_path, patches)
        result["mix_mode_injected"] = len(patches)
    else:
        result["mix_mode_injected"] = 0

    return result


def discover_mix_modes(resources_path: str = None) -> dict:
    """
    从剪映资源目录扫描所有混合模式

    Args:
        resources_path: 剪映Resources目录路径

    Returns:
        dict: 混合模式映射表
    """
    if resources_path is None:
        resources_path = _get_jianying_resources_path()

    mix_dir = os.path.join(resources_path, "MixMode")
    if not os.path.exists(mix_dir):
        logger.info(f"❌ MixMode目录不存在: {mix_dir}")
        return {}

    modes = {}
    for dirname in os.listdir(mix_dir):
        dirpath = os.path.join(mix_dir, dirname)
        if not os.path.isdir(dirpath):
            continue
        # 读取config.json获取名称
        config_file = os.path.join(dirpath, "config.json")
        if os.path.exists(config_file):
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                name = config.get("name", dirname)
                modes[name] = {"path_hash": dirname, "config": config}
            except Exception:
                pass

    logger.info(f"  扫描到 {len(modes)} 个混合模式资源")
    return modes


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("混合模式工具模块")
    logger.info("=" * 60)
    logger.info("\n已逆向的混合模式:")
    for mode, config in MIX_MODES.items():
        status = "✅" if config["effect_id"] else "⏳"
        logger.info(f"  {status} {mode}: {config['name']}")

    logger.info("\n扫描剪映资源目录...")
    discover_mix_modes()
