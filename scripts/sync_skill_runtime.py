"""
Skill/Runtime 自动同步脚本
比较skill目录和runtime目录中的相同文件，检测差异并同步
用法: python sync_skill_runtime.py [--check] [--sync] [--force skill|runtime]
"""

import os
import sys
import hashlib
import shutil
import argparse
from typing import Dict, List, Tuple
import logging
logger = logging.getLogger(__name__)


def file_md5(filepath: str) -> str:
    """计算文件MD5"""
    h = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def scan_dir(directory: str, extensions: List[str] = None) -> Dict[str, str]:
    """扫描目录，返回 {相对路径: 绝对路径}"""
    if extensions is None:
        extensions = [".py", ".md", ".json", ".txt", ".yaml", ".yml"]
    result = {}
    if not os.path.isdir(directory):
        return result
    for root, dirs, files in os.walk(directory):
        # 跳过.git和__pycache__
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__", "node_modules")]
        for f in files:
            if any(f.endswith(ext) for ext in extensions):
                full = os.path.join(root, f)
                rel = os.path.relpath(full, directory)
                result[rel] = full
    return result


def compare_dirs(dir_a: str, dir_b: str, label_a: str, label_b: str) -> Dict:
    """比较两个目录，返回差异报告"""
    files_a = scan_dir(dir_a)
    files_b = scan_dir(dir_b)

    only_in_a = []
    only_in_b = []
    identical = []
    different = []

    all_keys = set(files_a.keys()) | set(files_b.keys())
    for key in sorted(all_keys):
        if key in files_a and key not in files_b:
            only_in_a.append(key)
        elif key not in files_a and key in files_b:
            only_in_b.append(key)
        else:
            md5_a = file_md5(files_a[key])
            md5_b = file_md5(files_b[key])
            if md5_a == md5_b:
                identical.append(key)
            else:
                different.append((key, md5_a, md5_b))

    return {
        "label_a": label_a,
        "label_b": label_b,
        "dir_a": dir_a,
        "dir_b": dir_b,
        "only_in_a": only_in_a,
        "only_in_b": only_in_b,
        "identical": identical,
        "different": different,
        "total_a": len(files_a),
        "total_b": len(files_b),
    }


def sync_file(src: str, dst: str, dry_run: bool = False) -> bool:
    """同步单个文件"""
    dst_dir = os.path.dirname(dst)
    if not os.path.isdir(dst_dir):
        os.makedirs(dst_dir, exist_ok=True)
    if dry_run:
        logger.info(f"  [DRY] {src} -> {dst}")
        return True
    try:
        shutil.copy2(src, dst)
        return True
    except Exception as e:
        logger.info(f"  [ERROR] {src} -> {dst}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Skill/Runtime 自动同步")
    parser.add_argument("--check", action="store_true", help="仅检查差异，不同步")
    parser.add_argument("--sync", action="store_true", help="执行同步（以runtime为准）")
    parser.add_argument("--force", choices=["skill", "runtime"], help="强制以某方为准同步")
    parser.add_argument("--dry-run", action="store_true", help="试运行，不实际复制")
    args = parser.parse_args()

    # 路径配置
    try:
        from paths import SKILLS, RUNTIME_SCRIPTS
    except ImportError:
        SKILLS = {
            "ai_video_editor": r"C:\Users\Administrator\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills\ai-video-editor",
        }
        RUNTIME_SCRIPTS = r"D:\DobaoWork_Project\Ai_Video_Editor\ai-video-editor-runtime\scripts"

    skill_scripts = os.path.join(SKILLS["ai_video_editor"], "scripts")
    skill_adapters = os.path.join(SKILLS["ai_video_editor"], "adapters")
    runtime_root = os.path.dirname(RUNTIME_SCRIPTS)
    runtime_adapters = os.path.join(runtime_root, "adapters")

    logger.info("=" * 60)
    logger.info("Skill/Runtime 同步检查")
    logger.info("=" * 60)
    logger.info(f"Skill scripts: {skill_scripts}")
    logger.info(f"Runtime scripts: {RUNTIME_SCRIPTS}")
    logger.info(f"Skill adapters: {skill_adapters}")
    logger.info(f"Runtime adapters: {runtime_adapters}")
    logger.info("")

    # 比较scripts目录
    report = compare_dirs(skill_scripts, RUNTIME_SCRIPTS, "skill", "runtime")

    logger.info(f"Skill文件数: {report['total_a']}")
    logger.info(f"Runtime文件数: {report['total_b']}")
    logger.info(f"相同文件: {len(report['identical'])}")
    logger.info(f"仅在Skill: {len(report['only_in_a'])}")
    logger.info(f"仅在Runtime: {len(report['only_in_b'])}")
    logger.info(f"内容不同: {len(report['different'])}")
    logger.info("")

    # 比较adapters目录（如果存在）
    adapters_report = None
    if os.path.isdir(skill_adapters) and os.path.isdir(runtime_adapters):
        adapters_report = compare_dirs(skill_adapters, runtime_adapters, "skill", "runtime")
        logger.info(f"[adapters] Skill: {adapters_report['total_a']}, Runtime: {adapters_report['total_b']}, 不同: {len(adapters_report['different'])}, 仅Runtime: {len(adapters_report['only_in_b'])}")
        logger.info("")

    if report["different"]:
        logger.info("--- 内容不同的文件 ---")
        for key, md5_a, md5_b in report["different"]:
            logger.info(f"  {key}")
            logger.info(f"    skill:   {md5_a[:12]}")
            logger.info(f"    runtime: {md5_b[:12]}")
        logger.info("")

    if report["only_in_a"]:
        logger.info("--- 仅在Skill中的文件 ---")
        for key in report["only_in_a"][:20]:
            logger.info(f"  {key}")
        if len(report["only_in_a"]) > 20:
            logger.info(f"  ... 还有 {len(report['only_in_a']) - 20} 个")
        logger.info("")

    if report["only_in_b"]:
        logger.info("--- 仅在Runtime中的文件 ---")
        for key in report["only_in_b"][:20]:
            logger.info(f"  {key}")
        if len(report["only_in_b"]) > 20:
            logger.info(f"  ... 还有 {len(report['only_in_b']) - 20} 个")
        logger.info("")

    # 同步逻辑
    if args.check or (not args.sync and not args.force):
        logger.info("提示: 使用 --sync 执行同步（以runtime为准），--force skill/runtime 强制方向")
        return

    def sync_directory(source_dir, target_dir, report, label):
        """同步单个目录"""
        logger.info(f"\n--- 同步{label}: {source_dir} -> {target_dir} ---")
        synced = 0
        errors = 0
        # 同步不同的文件
        for key, _, _ in report["different"]:
            src = os.path.join(source_dir, key)
            dst = os.path.join(target_dir, key)
            if sync_file(src, dst, args.dry_run):
                synced += 1
            else:
                errors += 1
        # 同步仅在源目录的文件
        only_in_source = report["only_in_b"] if source_dir == RUNTIME_SCRIPTS or source_dir == runtime_adapters else report["only_in_a"]
        for key in only_in_source:
            src = os.path.join(source_dir, key)
            dst = os.path.join(target_dir, key)
            if sync_file(src, dst, args.dry_run):
                synced += 1
            else:
                errors += 1
        logger.info(f"{label}同步完成: {synced} 个文件同步, {errors} 个错误")
        return synced, errors

    # 同步scripts目录
    source_dir = RUNTIME_SCRIPTS
    target_dir = skill_scripts
    if args.force == "skill":
        source_dir = skill_scripts
        target_dir = RUNTIME_SCRIPTS
    sync_directory(source_dir, target_dir, report, "scripts")

    # 同步adapters目录
    if adapters_report and os.path.isdir(skill_adapters) and os.path.isdir(runtime_adapters):
        source_adapters = runtime_adapters
        target_adapters = skill_adapters
        if args.force == "skill":
            source_adapters = skill_adapters
            target_adapters = runtime_adapters
        sync_directory(source_adapters, target_adapters, adapters_report, "adapters")

    if args.dry_run:
        logger.info("\n(试运行模式，未实际复制)")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()