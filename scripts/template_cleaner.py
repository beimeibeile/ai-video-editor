"""
剪映模板解锁草稿清洗工具

用于清除从剪映收费/会员模板解锁的草稿中的发布限制标记，
使草稿可以自由编辑和再次发布。

模板标记可能存在于以下文件：
- draft.extra（二进制+Base64加密，最可能包含模板解锁标记）
- draft_agency_config.json（代理配置）
- draft_biz_config.json（商业配置）
- draft_virtual_store.json（虚拟素材库）
- template.tmp / template-2.tmp（模板临时文件）

使用方法：
    from template_cleaner import clean_template_draft
    result = clean_template_draft(r"D:\\JianyingProDrafts\\草稿名", backup=True)
    logger.info(result)

注意：
1. 清洗前会自动备份原草稿
2. 清洗后需要用剪映打开测试能否正常发布
3. 如果清洗后草稿无法打开，从备份恢复
"""

import logging
logger = logging.getLogger(__name__)


import os
import json
import shutil
import time
from typing import Dict, List, Any


# 需要清洗的文件列表
TEMPLATE_MARKER_FILES = [
    "draft.extra",
    "draft_agency_config.json",
    "draft_biz_config.json",
    "draft_virtual_store.json",
    "template.tmp",
    "template-2.tmp",
]

# 需要重置为默认值的JSON文件
DEFAULT_JSON_CONTENT = {
    "draft_agency_config.json": {
        "is_auto_agency_enabled": False,
        "is_auto_agency_popup": False,
        "is_single_agency_mode": False,
        "marterials": None,
        "use_converter": True,
        "video_resolution": 720,
    },
    "draft_biz_config.json": {},
    "draft_virtual_store.json": {
        "draft_materials": [],
        "draft_virtual_store": [
            {"type": 0, "value": []},
            {"type": 1, "value": []},
            {"type": 2, "value": []},
        ],
    },
}


def clean_template_draft(
    draft_path: str,
    backup: bool = True,
    remove_extra: bool = True,
    remove_template_tmp: bool = True,
) -> Dict[str, Any]:
    """
    清洗模板解锁草稿，移除发布限制标记

    Args:
        draft_path: 草稿目录路径
        backup: 是否备份原草稿（默认True）
        remove_extra: 是否删除 draft.extra（默认True）
        remove_template_tmp: 是否删除 template.tmp 文件（默认True）

    Returns:
        清洗结果字典
    """
    result = {
        "draft_path": draft_path,
        "success": False,
        "backup_path": "",
        "cleaned_files": [],
        "skipped_files": [],
        "errors": [],
        "warnings": [],
    }

    # 检查草稿目录是否存在
    if not os.path.isdir(draft_path):
        result["errors"].append(f"草稿目录不存在: {draft_path}")
        return result

    # 检查 draft_content.json 是否存在
    content_file = os.path.join(draft_path, "draft_content.json")
    if not os.path.exists(content_file):
        result["errors"].append("draft_content.json 不存在，不是有效的剪映草稿")
        return result

    # 1. 备份原草稿
    if backup:
        try:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            backup_path = f"{draft_path}_backup_{timestamp}"
            shutil.copytree(draft_path, backup_path)
            result["backup_path"] = backup_path
            logger.info(f"  ✅ 已备份: {backup_path}")
        except Exception as e:
            result["errors"].append(f"备份失败: {e}")
            result["warnings"].append("备份失败，继续清洗可能导致数据丢失")
            # 备份失败时询问是否继续（这里直接继续，但记录警告）

    # 2. 清洗文件
    for filename in TEMPLATE_MARKER_FILES:
        filepath = os.path.join(draft_path, filename)

        if not os.path.exists(filepath):
            result["skipped_files"].append(filename)
            continue

        try:
            # draft.extra：直接删除
            if filename == "draft.extra" and remove_extra:
                os.remove(filepath)
                result["cleaned_files"].append(f"{filename} (已删除)")
                logger.info(f"  ✅ 已删除: {filename}")

            # template.tmp / template-2.tmp：直接删除
            elif filename in ["template.tmp", "template-2.tmp"] and remove_template_tmp:
                os.remove(filepath)
                result["cleaned_files"].append(f"{filename} (已删除)")
                logger.info(f"  ✅ 已删除: {filename}")

            # JSON文件：重置为默认值
            elif filename in DEFAULT_JSON_CONTENT:
                default_content = DEFAULT_JSON_CONTENT[filename]
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(default_content, f, ensure_ascii=False, indent=2)
                result["cleaned_files"].append(f"{filename} (已重置)")
                logger.info(f"  ✅ 已重置: {filename}")

            else:
                result["skipped_files"].append(filename)

        except Exception as e:
            result["errors"].append(f"清洗 {filename} 失败: {e}")
            logger.error(f"  ❌ 清洗失败: {filename} - {e}")

    # 3. 检查 draft_content.json 是否加密
    try:
        with open(content_file, "r", encoding="utf-8") as f:
            first_char = f.read(1)
        if first_char != "{":
            result["warnings"].append(
                "draft_content.json 似乎是加密格式（非明文JSON）。"
                "高版本剪映创建的草稿默认加密，5.9可能无法打开。"
                "建议用5.9剪映打开后另存为新草稿。"
            )
            logger.info(f"  ⚠️  draft_content.json 为加密格式")
    except Exception:
        pass

    # 4. 生成验证清单
    result["success"] = len(result["errors"]) == 0
    result["next_steps"] = [
        "用剪映打开清洗后的草稿，检查内容是否完整",
        "测试能否正常发布（导出或分享）",
        "如果无法打开或内容丢失，从备份恢复",
        "如果发布仍受限，可能标记在 draft_content.json 加密内容中，需进一步研究",
    ]

    logger.info(f"\n{'='*60}")
    logger.error(f"模板清洗完成: {'成功' if result['success'] else '部分失败'}")
    logger.info(f"  清洗文件: {len(result['cleaned_files'])}个")
    logger.warning(f"  跳过文件: {len(result['skipped_files'])}个")
    logger.error(f"  错误: {len(result['errors'])}个")
    if result["warnings"]:
        logger.warning(f"  警告: {len(result['warnings'])}个")
    logger.info(f"{'='*60}")

    return result


def clean_all_template_drafts(
    drafts_root: str,
    backup: bool = True,
) -> List[Dict[str, Any]]:
    """
    批量清洗草稿目录下的所有模板解锁草稿

    Args:
        drafts_root: 草稿根目录
        backup: 是否备份

    Returns:
        清洗结果列表
    """
    results = []
    if not os.path.isdir(drafts_root):
        logger.info(f"❌ 草稿根目录不存在: {drafts_root}")
        return results

    draft_dirs = [
        d for d in os.listdir(drafts_root)
        if os.path.isdir(os.path.join(drafts_root, d))
        and not d.startswith(".")
        and not d.endswith("_backup_")
    ]

    logger.info(f"发现 {len(draft_dirs)} 个草稿目录")

    for draft_name in draft_dirs:
        draft_path = os.path.join(drafts_root, draft_name)
        # 只清洗包含模板标记文件的草稿
        has_marker = any(
            os.path.exists(os.path.join(draft_path, f))
            for f in TEMPLATE_MARKER_FILES
        )
        if has_marker:
            logger.info(f"\n--- 清洗: {draft_name} ---")
            result = clean_template_draft(draft_path, backup=backup)
            results.append(result)
        else:
            logger.warning(f"  跳过（无模板标记）: {draft_name}")

    return results


def restore_from_backup(backup_path: str, target_path: str) -> bool:
    """
    从备份恢复草稿

    Args:
        backup_path: 备份目录路径
        target_path: 目标草稿目录路径

    Returns:
        是否成功
    """
    try:
        if os.path.exists(target_path):
            shutil.rmtree(target_path)
        shutil.copytree(backup_path, target_path)
        logger.info(f"  ✅ 已从备份恢复: {target_path}")
        return True
    except Exception as e:
        logger.error(f"  ❌ 恢复失败: {e}")
        return False


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("剪映模板解锁草稿清洗工具")
    logger.info("=" * 60)
    logger.info("\n使用方法:")
    logger.info("  # 清洗单个草稿")
    logger.info("  from template_cleaner import clean_template_draft")
    logger.info("  result = clean_template_draft(r'D:\\\\JianyingProDrafts\\\\草稿名')")
    logger.info("")
    logger.info("  # 批量清洗")
    logger.info("  from template_cleaner import clean_all_template_drafts")
    logger.info("  results = clean_all_template_drafts(r'D:\\\\JianyingProDrafts')")
    logger.info("")
    logger.info("  # 从备份恢复")
    logger.info("  from template_cleaner import restore_from_backup")
    logger.info("  restore_from_backup('草稿_backup_20260101_120000', '草稿')")
    logger.info("")
