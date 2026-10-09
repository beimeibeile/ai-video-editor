"""
混合模式扫描工具
扫描剪映草稿目录，自动识别并逆向所有混合模式的effect_id和resource_id

使用方法：
1. 在剪映中新建工程，给片段设置不同的混合模式
2. 保存草稿
3. 运行本工具扫描草稿目录，自动提取混合模式映射表
"""

import logging
logger = logging.getLogger(__name__)


import os
import json
import glob
from typing import Dict, List, Any


def scan_draft_for_mix_modes(draft_path: str) -> List[Dict[str, Any]]:
    """
    扫描单个草稿，提取其中的混合模式

    Args:
        draft_path: 草稿目录路径

    Returns:
        混合模式列表
    """
    content_file = os.path.join(draft_path, "draft_content.json")
    if not os.path.exists(content_file):
        content_file = os.path.join(draft_path, "draft_info.json")
    if not os.path.exists(content_file):
        return []

    try:
        with open(content_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return []

    mix_modes = []
    materials = data.get("materials", {})
    effects = materials.get("effects", [])

    for effect in effects:
        if effect.get("type") == "mix_mode":
            mix_modes.append({
                "name": effect.get("name", ""),
                "effect_id": effect.get("effect_id", ""),
                "resource_id": effect.get("resource_id", ""),
                "path": effect.get("path", ""),
                "value": effect.get("value", 1.0),
                "draft": os.path.basename(draft_path),
            })

    return mix_modes


def scan_all_drafts(drafts_root: str = None) -> Dict[str, Dict[str, Any]]:
    """
    扫描所有草稿，提取混合模式映射表

    Args:
        drafts_root: 草稿根目录（单个路径或None自动扫描所有候选目录）

    Returns:
        混合模式映射表 {name: {effect_id, resource_id, path}}
    """
    all_modes = {}

    if drafts_root is None:
        # 自动扫描所有候选目录
        candidates = [
            r"C:\Users\Administrator\AppData\Local\JianyingPro\User Data\Projects\com.lveditor.draft",
            r"D:\JianyingProDrafts\JianyingPro Drafts",
        ]
        roots_to_scan = [p for p in candidates if os.path.exists(p)]
    else:
        roots_to_scan = [drafts_root]

    if not roots_to_scan:
        logger.info(f"❌ 没有找到草稿目录")
        return {}

    for root in roots_to_scan:
        logger.info(f"扫描草稿目录: {root}")
        draft_dirs = [d for d in glob.glob(os.path.join(root, "*")) if os.path.isdir(d)]

        for draft_dir in draft_dirs:
            modes = scan_draft_for_mix_modes(draft_dir)
            for mode in modes:
                name = mode["name"]
                if name and name not in all_modes:
                    all_modes[name] = {
                        "effect_id": mode["effect_id"],
                        "resource_id": mode["resource_id"],
                        "path": mode["path"],
                        "source_draft": mode["draft"],
                    }
                    logger.info(f"  ✅ 发现混合模式: {name} (effect_id={mode['effect_id']})")
                logger.info(f"  ✅ 发现混合模式: {name} (effect_id={mode['effect_id']})")

    logger.info(f"\n共发现 {len(all_modes)} 种混合模式")
    return all_modes


def update_mix_mode_module(mapping: Dict[str, Dict[str, Any]], module_path: str = None):
    """
    更新mix_mode.py中的MIX_MODES字典

    Args:
        mapping: 混合模式映射表
        module_path: mix_mode.py路径
    """
    if module_path is None:
        module_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "mix_mode.py"
        )

    if not os.path.exists(module_path):
        logger.info(f"❌ mix_mode.py不存在: {module_path}")
        return

    # 中文名→英文key映射
    name_to_key = {
        "正片叠底": "multiply",
        "滤色": "screen",
        "叠加": "overlay",
        "变暗": "darken",
        "变亮": "lighten",
        "颜色减淡": "color_dodge",
        "颜色加深": "color_burn",
        "强光": "hard_light",
        "柔光": "soft_light",
        "差值": "difference",
        "排除": "exclusion",
    }

    # 读取现有文件
    with open(module_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 生成新的MIX_MODES字典
    lines = ["MIX_MODES = {"]
    for name, info in mapping.items():
        key = name_to_key.get(name, name)
        path_hash = os.path.basename(info["path"]) if info["path"] else ""
        lines.append(f'    "{key}": {{')
        lines.append(f'        "name": "{name}",')
        lines.append(f'        "effect_id": "{info["effect_id"]}",')
        lines.append(f'        "resource_id": "{info["resource_id"]}",')
        lines.append(f'        "path_hash": "{path_hash}",')
        lines.append(f'    }},')
    lines.append("}")

    new_mapping = "\n".join(lines)

    # 替换现有MIX_MODES字典
    import re
    pattern = r"MIX_MODES = \{.*?\n\}"
    content = re.sub(pattern, new_mapping, content, flags=re.DOTALL)

    with open(module_path, "w", encoding="utf-8") as f:
        f.write(content)

    logger.info(f"✅ 已更新mix_mode.py，共{len(mapping)}种混合模式")


def export_mapping_json(mapping: Dict[str, Dict[str, Any]], output_path: str):
    """
    导出混合模式映射表为JSON

    Args:
        mapping: 混合模式映射表
        output_path: 输出路径
    """
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)
    logger.info(f"✅ 映射表已导出: {output_path}")


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("混合模式扫描工具")
    logger.info("=" * 60)

    # 扫描所有草稿
    mapping = scan_all_drafts()

    if mapping:
        # 导出JSON
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "effects")
        os.makedirs(output_dir, exist_ok=True)
        export_mapping_json(mapping, os.path.join(output_dir, "mix_mode_mapping.json"))

        # 更新mix_mode.py
        update_mix_mode_module(mapping)
    else:
        logger.info("\n⚠️  未发现混合模式")
        logger.info("请在剪映中设置混合模式后保存草稿，再运行本工具")
