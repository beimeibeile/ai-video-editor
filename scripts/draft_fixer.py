"""
剪映工程创建后修复工具 v1.0

解决PIT-025问题：用jianying-editor创建的工程剪映草稿列表不显示
根本原因：三重缺失（双目录/辅助文件/索引未注册）

使用方式：
    python draft_fixer.py --draft <工程目录> --reference <参照工程目录>
    python draft_fixer.py --draft "D:/JianyingProDrafts/JianyingPro Drafts/豆包被打_v9" --reference "C:/Users/.../com.lveditor.draft/豆包被打_v7_简化版"

修复流程：
1. 从参照工程复制辅助文件（不覆盖draft_info.json和materials）
2. 计算实际素材大小
3. 更新root_meta_info.json索引（tm_duration/size/timestamp）
4. 验证工程完整性
"""

import logging
logger = logging.getLogger(__name__)


import os
import sys
import json
import shutil
import time
import hashlib
from typing import Dict, List, Optional, Tuple

# ============= 配置 =============

# 剪映实际管理目录（C盘）
JIANYING_DRAFTS_ROOT = r"C:\Users\Administrator\AppData\Local\JianyingPro\User Data\Projects\com.lveditor.draft"

# 索引文件
ROOT_META_FILE = os.path.join(JIANYING_DRAFTS_ROOT, "root_meta_info.json")

# 辅助文件白名单（从参照工程复制，不覆盖核心文件）
AUXILIARY_FILES = [
    "draft_cover.jpg",
    "draft_content.json",
    "attachment_pc_common.json",
    "timeline_layout.json",
    "draft_meta_info.json",
    "draft_settings",
    "key_value.json",
]

# 辅助目录白名单
AUXILIARY_DIRS = [
    "Timelines",
    "log",
]

# 不覆盖的核心文件
CORE_FILES = [
    "draft_info.json",
    "materials",
]


def calculate_dir_size(path: str) -> int:
    """计算目录总大小（字节）"""
    total = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            try:
                total += os.path.getsize(fp)
            except OSError:
                pass
    return total


def get_draft_duration(draft_dir: str) -> int:
    """从draft_info.json获取工程时长（微秒）"""
    info_path = os.path.join(draft_dir, "draft_info.json")
    if not os.path.exists(info_path):
        return 20000000  # 默认20秒

    try:
        with open(info_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # 尝试从tracks获取最大结束时间
        duration = 0
        for track in data.get("tracks", []):
            for seg in track.get("segments", []):
                tr = seg.get("target_timerange", {})
                end = tr.get("start", 0) + tr.get("duration", 0)
                if end > duration:
                    duration = end
        return duration if duration > 0 else 20000000
    except Exception:
        return 20000000


def copy_auxiliary_files(draft_dir: str, reference_dir: str) -> Tuple[int, List[str]]:
    """从参照工程复制辅助文件"""
    copied = []
    skipped = []

    if not os.path.exists(reference_dir):
        return 0, [f"参照工程不存在: {reference_dir}"]

    # 复制文件
    for fname in AUXILIARY_FILES:
        src = os.path.join(reference_dir, fname)
        dst = os.path.join(draft_dir, fname)

        if not os.path.exists(src):
            continue

        # 核心文件不覆盖
        if fname in CORE_FILES and os.path.exists(dst):
            skipped.append(fname)
            continue

        try:
            if os.path.isdir(src):
                if os.path.exists(dst):
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
            copied.append(fname)
        except Exception as e:
            skipped.append(f"{fname}: {e}")

    # 复制目录
    for dname in AUXILIARY_DIRS:
        src = os.path.join(reference_dir, dname)
        dst = os.path.join(draft_dir, dname)

        if not os.path.exists(src):
            continue

        try:
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            copied.append(dname + "/")
        except Exception as e:
            skipped.append(f"{dname}/: {e}")

    return len(copied), copied + [f"跳过: {s}" for s in skipped]


def update_root_meta(draft_dir: str, draft_name: str) -> bool:
    """更新root_meta_info.json索引"""
    if not os.path.exists(ROOT_META_FILE):
        logger.info(f"  ❌ 索引文件不存在: {ROOT_META_FILE}")
        return False

    try:
        with open(ROOT_META_FILE, "r", encoding="utf-8") as f:
            meta = json.load(f)
    except Exception as e:
        logger.error(f"  ❌ 读取索引失败: {e}")
        return False

    # 计算实际大小和时长
    actual_size = calculate_dir_size(draft_dir)
    actual_duration = get_draft_duration(draft_dir)
    current_ts = int(time.time() * 1000)

    # 查找或创建条目
    all_drafts = meta.get("all_draft_store", [])
    found = False

    for entry in all_drafts:
        if entry.get("draft_name") == draft_name:
            entry["tm_duration"] = actual_duration
            entry["draft_timeline_materials_size_"] = actual_size
            entry["tm_draft_modified"] = current_ts
            entry["draft_root_path"] = draft_dir
            found = True
            logger.info(f"  ✅ 更新已有条目: {draft_name}")
            logger.info(f"     时长: {actual_duration/1e6:.1f}s, 大小: {actual_size/1e6:.1f}MB")
            break

    if not found:
        # 创建新条目
        new_entry = {
            "draft_name": draft_name,
            "draft_id": hashlib.md5(draft_name.encode()).hexdigest()[:16],
            "draft_root_path": draft_dir,
            "tm_duration": actual_duration,
            "draft_timeline_materials_size_": actual_size,
            "tm_draft_modified": current_ts,
            "tm_draft_created": current_ts,
            "draft_type": 0,
        }
        all_drafts.append(new_entry)
        logger.info(f"  ✅ 创建新条目: {draft_name}")

    # 按修改时间降序排序（最新的在前面）
    all_drafts.sort(key=lambda x: x.get("tm_draft_modified", 0), reverse=True)
    meta["all_draft_store"] = all_drafts

    # 备份原文件
    backup_path = ROOT_META_FILE + ".bak"
    shutil.copy2(ROOT_META_FILE, backup_path)

    # 写入
    try:
        with open(ROOT_META_FILE, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        logger.info(f"  ✅ 索引已更新（备份: {backup_path}）")
        return True
    except Exception as e:
        logger.error(f"  ❌ 写入索引失败: {e}")
        # 恢复备份
        shutil.copy2(backup_path, ROOT_META_FILE)
        return False


def verify_draft(draft_dir: str) -> Dict:
    """验证工程完整性"""
    result = {
        "draft_dir": draft_dir,
        "exists": os.path.exists(draft_dir),
        "core_files": {},
        "auxiliary_files": {},
        "materials_count": 0,
        "total_size": 0,
    }

    if not result["exists"]:
        return result

    # 检查核心文件
    for fname in ["draft_info.json", "draft_meta_info.json"]:
        fpath = os.path.join(draft_dir, fname)
        result["core_files"][fname] = os.path.exists(fpath)

    # 检查辅助文件
    for fname in ["draft_cover.jpg", "draft_content.json", "Timelines"]:
        fpath = os.path.join(draft_dir, fname)
        result["auxiliary_files"][fname] = os.path.exists(fpath)

    # 统计素材
    materials_dir = os.path.join(draft_dir, "materials")
    if os.path.exists(materials_dir):
        result["materials_count"] = len(os.listdir(materials_dir))

    result["total_size"] = calculate_dir_size(draft_dir)

    return result


def fix_draft(draft_dir: str, reference_dir: Optional[str] = None) -> Dict:
    """完整修复流程"""
    draft_name = os.path.basename(draft_dir)
    logger.info(f"\n{'='*60}")
    logger.info(f"修复工程: {draft_name}")
    logger.info(f"路径: {draft_dir}")
    logger.info(f"{'='*60}")

    # Step 1: 验证当前状态
    logger.info("\n[Step 1] 验证当前状态...")
    before = verify_draft(draft_dir)
    logger.info(f"  核心文件: {before['core_files']}")
    logger.info(f"  辅助文件: {before['auxiliary_files']}")
    logger.info(f"  素材数量: {before['materials_count']}")
    logger.info(f"  总大小: {before['total_size']/1e6:.1f}MB")

    # Step 2: 复制辅助文件
    if reference_dir:
        logger.info(f"\n[Step 2] 从参照工程复制辅助文件...")
        logger.info(f"  参照: {reference_dir}")
        count, details = copy_auxiliary_files(draft_dir, reference_dir)
        logger.info(f"  复制了 {count} 个文件/目录")
        for d in details:
            logger.info(f"    - {d}")
    else:
        logger.warning("\n[Step 2] 跳过辅助文件复制（未指定参照工程）")

    # Step 3: 更新索引
    logger.info("\n[Step 3] 更新剪映草稿索引...")
    index_ok = update_root_meta(draft_dir, draft_name)

    # Step 4: 验证修复结果
    logger.info("\n[Step 4] 验证修复结果...")
    after = verify_draft(draft_dir)
    logger.info(f"  核心文件: {after['core_files']}")
    logger.info(f"  辅助文件: {after['auxiliary_files']}")
    logger.info(f"  素材数量: {after['materials_count']}")
    logger.info(f"  总大小: {after['total_size']/1e6:.1f}MB")

    # 汇总
    all_core_ok = all(after["core_files"].values())
    all_aux_ok = all(after["auxiliary_files"].values())
    has_materials = after["materials_count"] > 0

    logger.info(f"\n{'='*60}")
    logger.info(f"修复结果:")
    logger.info(f"  核心文件: {'✅' if all_core_ok else '❌'}")
    logger.info(f"  辅助文件: {'✅' if all_aux_ok else '⚠️ ' + str(after['auxiliary_files'])}")
    logger.info(f"  素材文件: {'✅' if has_materials else '❌ 无素材'}")
    logger.info(f"  索引更新: {'✅' if index_ok else '❌'}")
    logger.info(f"{'='*60}")

    return {
        "draft_name": draft_name,
        "before": before,
        "after": after,
        "index_updated": index_ok,
        "success": all_core_ok and has_materials and index_ok,
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="剪映工程创建后修复工具")
    parser.add_argument("--draft", required=True, help="工程目录路径")
    parser.add_argument("--reference", help="参照工程目录（用于复制辅助文件）")
    parser.add_argument("--verify-only", action="store_true", help="仅验证不修复")
    args = parser.parse_args()

    if args.verify_only:
        result = verify_draft(args.draft)
        logger.info(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        fix_draft(args.draft, args.reference)
