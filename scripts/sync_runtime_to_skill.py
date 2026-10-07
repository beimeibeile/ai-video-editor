#!/usr/bin/env python3
"""
Skill/Runtime 模块自动同步脚本
runtime为唯一代码源，自动同步runtime中的工具模块到skill目录

用法:
    python sync_runtime_to_skill.py              # 同步所有差异模块
    python sync_runtime_to_skill.py --dry-run    # 仅显示差异，不同步
    python sync_runtime_to_skill.py --module xxx # 同步指定模块
    python sync_runtime_to_skill.py --list       # 列出所有可同步模块
"""
import argparse
import filecmp
import hashlib
import os
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# 路径配置
try:
    from paths import PATHS
    RUNTIME_DIR = Path(PATHS.get("runtime_dir", "")) / "scripts"
    SKILL_DIR = Path(PATHS.get("skill_root", "")) / "scripts"
except ImportError:
    RUNTIME_DIR = Path(__file__).parent
    SKILL_DIR = Path(
        r"C:\Users\Administrator\AppData\Local\Doubao\User Data\Default"
        r"\.doubao\agent_mode\workspace\.user_skills\ai-video-editor\scripts"
    )

# 不同步的文件（runtime特有，不应复制到skill）
EXCLUDE_FILES = {
    "paths.py",           # runtime特有配置
    "remotion_executor.py",  # runtime特有执行器
    "test_smoke.py",     # 测试文件
    "run.py",            # 入口点
    "__init__.py",
}


def file_hash(path: Path) -> str:
    """计算文件MD5哈希"""
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def scan_modules() -> Dict[str, Tuple[Path, Path]]:
    """扫描runtime和skill中的同名模块"""
    modules = {}

    if not RUNTIME_DIR.exists():
        print(f"❌ runtime目录不存在: {RUNTIME_DIR}")
        return modules

    runtime_files = {f.name: f for f in RUNTIME_DIR.glob("*.py")
                     if f.name not in EXCLUDE_FILES}

    if SKILL_DIR.exists():
        skill_files = {f.name: f for f in SKILL_DIR.glob("*.py")}
    else:
        skill_files = {}

    for name, rt_path in runtime_files.items():
        sk_path = skill_files.get(name)
        modules[name] = (rt_path, sk_path)

    return modules


def compare_modules(modules: Dict[str, Tuple[Path, Path]]) -> List[Dict]:
    """比较模块差异"""
    diffs = []

    for name, (rt_path, sk_path) in sorted(modules.items()):
        rt_hash = file_hash(rt_path)
        rt_size = rt_path.stat().st_size
        rt_mtime = rt_path.stat().st_mtime

        if sk_path is None:
            diffs.append({
                "name": name,
                "status": "new",
                "runtime": str(rt_path),
                "skill": None,
                "runtime_size": rt_size,
                "skill_size": 0,
                "runtime_hash": rt_hash,
                "skill_hash": None,
            })
        else:
            sk_hash = file_hash(sk_path)
            sk_size = sk_path.stat().st_size
            sk_mtime = sk_path.stat().st_mtime

            if rt_hash != sk_hash:
                # runtime更新
                rt_newer = rt_mtime > sk_mtime
                diffs.append({
                    "name": name,
                    "status": "outdated" if rt_newer else "runtime_older",
                    "runtime": str(rt_path),
                    "skill": str(sk_path),
                    "runtime_size": rt_size,
                    "skill_size": sk_size,
                    "runtime_hash": rt_hash,
                    "skill_hash": sk_hash,
                    "runtime_newer": rt_newer,
                    "size_diff": rt_size - sk_size,
                })

    return diffs


def sync_module(name: str, rt_path: Path, sk_path: Path, dry_run: bool = False) -> bool:
    """同步单个模块"""
    if dry_run:
        if sk_path is None:
            print(f"  [新增] {name} -> {SKILL_DIR}")
        else:
            print(f"  [更新] {name} ({rt_path.stat().st_size}B -> skill)")
        return True

    try:
        SKILL_DIR.mkdir(parents=True, exist_ok=True)
        target = SKILL_DIR / name
        shutil.copy2(rt_path, target)
        print(f"  ✅ {name}")
        return True
    except Exception as e:
        print(f"  ❌ {name}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Runtime→Skill模块同步")
    parser.add_argument("--dry-run", action="store_true", help="仅显示差异")
    parser.add_argument("--module", help="同步指定模块")
    parser.add_argument("--list", action="store_true", help="列出所有模块")
    parser.add_argument("--force", action="store_true", help="强制同步所有（即使runtime更旧）")
    args = parser.parse_args()

    print("=" * 60)
    print("Runtime → Skill 模块同步")
    print("=" * 60)
    print(f"Runtime: {RUNTIME_DIR}")
    print(f"Skill:   {SKILL_DIR}")
    print()

    modules = scan_modules()
    print(f"扫描到 {len(modules)} 个可同步模块")

    if args.list:
        print("\n模块列表:")
        for name, (rt, sk) in sorted(modules.items()):
            status = "✅ 同步" if sk and file_hash(rt) == file_hash(sk) else \
                     "🆕 新增" if sk is None else "🔄 差异"
            print(f"  {status} {name}")
        return

    diffs = compare_modules(modules)

    if not diffs:
        print("\n✅ 所有模块已同步，无差异")
        return

    # 过滤
    if args.module:
        diffs = [d for d in diffs if d["name"] == args.module]
        if not diffs:
            print(f"\n未找到模块: {args.module}")
            return

    if not args.force:
        # 只同步runtime更新的或新增的
        to_sync = [d for d in diffs if d["status"] in ("new", "outdated")]
        skipped = [d for d in diffs if d["status"] == "runtime_older"]
    else:
        to_sync = diffs
        skipped = []

    print(f"\n差异: {len(diffs)}个 (同步{len(to_sync)}个, 跳过{len(skipped)}个)")
    print("-" * 60)

    for d in diffs:
        if d["status"] == "new":
            print(f"  🆕 {d['name']} (新增, {d['runtime_size']}B)")
        elif d["status"] == "outdated":
            print(f"  🔄 {d['name']} (skill过期, 差异{d.get('size_diff', 0):+d}B)")
        elif d["status"] == "runtime_older":
            print(f"  ⏭️  {d['name']} (runtime较旧, 跳过)")

    if skipped and not args.force:
        print(f"\n⚠️  {len(skipped)}个模块runtime版本较旧，使用--force强制覆盖")

    if args.dry_run:
        print(f"\n[dry-run] 将同步 {len(to_sync)} 个模块")
        return

    print(f"\n同步中...")
    success = 0
    for d in to_sync:
        if sync_module(d["name"], Path(d["runtime"]),
                       Path(d["skill"]) if d["skill"] else None,
                       dry_run=False):
            success += 1

    print(f"\n✅ 完成: {success}/{len(to_sync)} 个模块已同步")


if __name__ == "__main__":
    main()
