#!/usr/bin/env python3
"""
硬编码路径迁移扫描器
扫描runtime中所有.py文件的硬编码路径，生成迁移报告
支持自动替换常见路径模式为paths.py引用

用法:
    python migrate_hardcoded_paths.py --scan       # 仅扫描生成报告
    python migrate_hardcoded_paths.py --apply      # 应用安全替换
    python migrate_hardcoded_paths.py --file xxx   # 扫描指定文件
"""

import logging
logger = logging.getLogger(__name__)

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Dict, List

RUNTIME = Path(__file__).parent

# 可安全替换的路径模式 -> paths.py key
# 同时支持正斜杠和反斜杠（实际文件中主要用反斜杠r"..."）
SAFE_REPLACEMENTS = [
    # === 反斜杠版本（实际文件中主要用这个）===
    # Skill目录
    (r"C:\Users\Administrator\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills\ai-video-editor",
     'PATHS["skill_root"]'),
    (r"C:\Users\Administrator\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills\jianying-editor",
     'PATHS["jianying_skill_root"]'),
    (r"C:\Users\Administrator\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills\remotion-controls-skill",
     'PATHS["remotion_skill_root"]'),
    # 剪映草稿
    (r"C:\Users\Administrator\AppData\Local\JianyingPro\User Data\Projects\com.lveditor.draft",
     'PATHS["jianying_drafts_root"]'),
    # LocalAppData
    (r"C:\Users\Administrator\AppData\Local", 'PATHS["localappdata"]'),
    # 用户目录
    (r"C:\Users\Administrator", 'PATHS["userprofile"]'),
    # Python
    (r"D:\Ai\ComfyUI-aki-v3.2\python\python.exe", 'PATHS["python_exe"]'),
    # D盘剪映草稿
    (r"D:\JianyingProDrafts\JianyingPro Drafts", 'PATHS["jianying_drafts_d_drive"]'),
    # ComfyUI
    ("http://127.0.0.1:8188", 'PATHS["comfyui_url"]'),
    ("127.0.0.1:8188", 'PATHS["comfyui_address"]'),
]

# 路径正则（匹配r"..."或"..."中的Windows路径）
PATH_PATTERNS = [
    re.compile(r'r["\']([A-Za-z]:\\[^"\']+)["\']'),  # r"C:\..."
    re.compile(r'["\']([A-Za-z]:\\[^"\']+)["\']'),    # "C:\..."
    re.compile(r'["\']([A-Za-z]:/[^"\']+)["\']'),     # "C:/..."
]


def scan_file(filepath: Path) -> List[Dict]:
    """扫描单个文件中的硬编码路径"""
    findings = []
    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception:
        return findings

    lines = content.split("\n")
    for lineno, line in enumerate(lines, 1):
        # 跳过import行和注释
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith("import") or stripped.startswith("from"):
            continue

        for pattern in PATH_PATTERNS:
            for match in pattern.finditer(line):
                path_str = match.group(1)
                # 检查是否可以安全替换
                replacement = None
                for old, new in SAFE_REPLACEMENTS:
                    if path_str.startswith(old) or path_str == old:
                        replacement = new
                        break

                findings.append({
                    "file": str(filepath),
                    "line": lineno,
                    "path": path_str,
                    "context": stripped[:80],
                    "replaceable": replacement is not None,
                    "replacement": replacement,
                })
    return findings


def scan_all() -> List[Dict]:
    """扫描所有.py文件"""
    all_findings = []
    for f in RUNTIME.glob("*.py"):
        if f.name in ("paths.py", "migrate_hardcoded_paths.py", "test_smoke.py"):
            continue
        all_findings.extend(scan_file(f))
    return all_findings


def generate_report(findings: List[Dict]) -> str:
    """生成迁移报告"""
    files = {}
    for f in findings:
        fname = os.path.basename(f["file"])
        if fname not in files:
            files[fname] = []
        files[fname].append(f)

    replaceable = [f for f in findings if f["replaceable"]]
    not_replaceable = [f for f in findings if not f["replaceable"]]

    report = []
    report.append("=" * 70)
    report.append("硬编码路径迁移报告")
    report.append("=" * 70)
    report.append(f"扫描文件: {len(files)}个")
    report.append(f"发现硬编码路径: {len(findings)}处")
    report.append(f"  可安全替换: {len(replaceable)}处")
    report.append(f"  需手动处理: {len(not_replaceable)}处")
    report.append("")

    if replaceable:
        report.append("-" * 70)
        report.append("可安全替换的路径:")
        report.append("-" * 70)
        for f in replaceable[:30]:  # 最多显示30条
            report.append(f"  {os.path.basename(f['file'])}:{f['line']}")
            report.append(f"    原: {f['path'][:60]}")
            report.append(f"    替: {f['replacement']}")
        if len(replaceable) > 30:
            report.append(f"  ... 还有{len(replaceable)-30}处")
        report.append("")

    if not_replaceable:
        report.append("-" * 70)
        report.append("需手动处理的路径:")
        report.append("-" * 70)
        # 按路径前缀分组
        prefixes = {}
        for f in not_replaceable:
            # 取前两级目录作为前缀
            parts = f["path"].replace("\\", "/").split("/")
            prefix = "/".join(parts[:3]) if len(parts) >= 3 else f["path"]
            if prefix not in prefixes:
                prefixes[prefix] = 0
            prefixes[prefix] += 1

        for prefix, count in sorted(prefixes.items(), key=lambda x: -x[1]):
            report.append(f"  {prefix} ({count}处)")
        report.append("")

    return "\n".join(report)


def apply_replacements(findings: List[Dict], dry_run: bool = True) -> int:
    """应用安全替换"""
    replaced = 0
    # 按文件分组
    by_file = {}
    for f in findings:
        if f["replaceable"]:
            if f["file"] not in by_file:
                by_file[f["file"]] = []
            by_file[f["file"]].append(f)

    for filepath, file_findings in by_file.items():
        try:
            content = Path(filepath).read_text(encoding="utf-8")
            original = content

            for f in file_findings:
                for old, new in SAFE_REPLACEMENTS:
                    if old in content:
                        content = content.replace(old, new)
                        replaced += 1

            if content != original and not dry_run:
                # 添加paths import（如果还没有）
                if "from paths import" not in content and "import paths" not in content:
                    # 在第一个import后添加
                    lines = content.split("\n")
                    insert_idx = 0
                    for i, line in enumerate(lines):
                        if line.startswith("import ") or line.startswith("from "):
                            insert_idx = i + 1
                    lines.insert(insert_idx, "from paths import PATHS")
                    content = "\n".join(lines)

                Path(filepath).write_text(content, encoding="utf-8")
                logger.info(f"  ✅ {os.path.basename(filepath)}")
            elif content != original and dry_run:
                logger.info(f"  [dry-run] {os.path.basename(filepath)}")
        except Exception as e:
            logger.info(f"  ❌ {os.path.basename(filepath)}: {e}")

    return replaced


def main():
    parser = argparse.ArgumentParser(description="硬编码路径迁移扫描器")
    parser.add_argument("--scan", action="store_true", help="仅扫描生成报告")
    parser.add_argument("--apply", action="store_true", help="应用安全替换")
    parser.add_argument("--dry-run", action="store_true", help="预览替换")
    parser.add_argument("--file", help="扫描指定文件")
    args = parser.parse_args()

    logger.info("扫描硬编码路径...")

    if args.file:
        findings = scan_file(Path(args.file))
    else:
        findings = scan_all()

    report = generate_report(findings)
    logger.info(report)

    if args.apply or args.dry_run:
        logger.info("\n应用安全替换...")
        count = apply_replacements(findings, dry_run=args.dry_run)
        logger.info(f"\n替换完成: {count}处")

    # 保存报告
    report_path = RUNTIME.parent / "path_migration_report.txt"
    report_path.write_text(report, encoding="utf-8")
    logger.info(f"\n报告已保存: {report_path}")


if __name__ == "__main__":
    main()
