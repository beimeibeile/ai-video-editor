#!/usr/bin/env python3
"""
Skill/Runtime 妯″潡鑷姩鍚屾鑴氭湰
runtime涓哄敮涓€浠ｇ爜婧愶紝鑷姩鍚屾runtime涓殑宸ュ叿妯″潡鍒皊kill鐩綍

鐢ㄦ硶:
    python sync_runtime_to_skill.py              # 鍚屾鎵€鏈夊樊寮傛ā鍧?
    python sync_runtime_to_skill.py --dry-run    # 浠呮樉绀哄樊寮傦紝涓嶅悓姝?
    python sync_runtime_to_skill.py --module xxx # 鍚屾鎸囧畾妯″潡
    python sync_runtime_to_skill.py --list       # 鍒楀嚭鎵€鏈夊彲鍚屾妯″潡
"""
import argparse
import filecmp
import hashlib
import os
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Tuple
import logging
logger = logging.getLogger(__name__)

# 璺緞閰嶇疆
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

# 涓嶅悓姝ョ殑鏂囦欢锛坮untime鐗规湁锛屼笉搴斿鍒跺埌skill锛?
EXCLUDE_FILES = {
    "paths.py",           # runtime鐗规湁閰嶇疆
    "remotion_executor.py",  # runtime鐗规湁鎵ц鍣?
    "test_smoke.py",     # 娴嬭瘯鏂囦欢
    "run.py",            # 鍏ュ彛鐐?
    "__init__.py",
}


def file_hash(path: Path) -> str:
    """璁＄畻鏂囦欢MD5鍝堝笇"""
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def scan_modules() -> Dict[str, Tuple[Path, Path]]:
    """鎵弿runtime鍜宻kill涓殑鍚屽悕妯″潡"""
    modules = {}

    if not RUNTIME_DIR.exists():
        logger.info(f"鉂?runtime鐩綍涓嶅瓨鍦? {RUNTIME_DIR}")
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
    """姣旇緝妯″潡宸紓"""
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
                # runtime鏇存柊
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
    """鍚屾鍗曚釜妯″潡"""
    if dry_run:
        if sk_path is None:
            logger.info(f"  [鏂板] {name} -> {SKILL_DIR}")
        else:
            logger.info(f"  [鏇存柊] {name} ({rt_path.stat().st_size}B -> skill)")
        return True

    try:
        SKILL_DIR.mkdir(parents=True, exist_ok=True)
        target = SKILL_DIR / name
        shutil.copy2(rt_path, target)
        logger.info(f"  鉁?{name}")
        return True
    except Exception as e:
        logger.info(f"  鉂?{name}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Runtime鈫扴kill妯″潡鍚屾")
    parser.add_argument("--dry-run", action="store_true", help="浠呮樉绀哄樊寮?)
    parser.add_argument("--module", help="鍚屾鎸囧畾妯″潡")
    parser.add_argument("--list", action="store_true", help="鍒楀嚭鎵€鏈夋ā鍧?)
    parser.add_argument("--force", action="store_true", help="寮哄埗鍚屾鎵€鏈夛紙鍗充娇runtime鏇存棫锛?)
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("Runtime 鈫?Skill 妯″潡鍚屾")
    logger.info("=" * 60)
    logger.info(f"Runtime: {RUNTIME_DIR}")
    logger.info(f"Skill:   {SKILL_DIR}")
    logger.info("")

    modules = scan_modules()
    logger.info(f"鎵弿鍒?{len(modules)} 涓彲鍚屾妯″潡")

    if args.list:
        logger.info("\n妯″潡鍒楄〃:")
        for name, (rt, sk) in sorted(modules.items()):
            status = "鉁?鍚屾" if sk and file_hash(rt) == file_hash(sk) else \
                     "馃啎 鏂板" if sk is None else "馃攧 宸紓"
            logger.info(f"  {status} {name}")
        return

    diffs = compare_modules(modules)

    if not diffs:
        logger.info("\n鉁?鎵€鏈夋ā鍧楀凡鍚屾锛屾棤宸紓")
        return

    # 杩囨护
    if args.module:
        diffs = [d for d in diffs if d["name"] == args.module]
        if not diffs:
            logger.info(f"\n鏈壘鍒版ā鍧? {args.module}")
            return

    if not args.force:
        # 鍙悓姝untime鏇存柊鐨勬垨鏂板鐨?
        to_sync = [d for d in diffs if d["status"] in ("new", "outdated")]
        skipped = [d for d in diffs if d["status"] == "runtime_older"]
    else:
        to_sync = diffs
        skipped = []

    logger.info(f"\n宸紓: {len(diffs)}涓?(鍚屾{len(to_sync)}涓? 璺宠繃{len(skipped)}涓?")
    logger.info("-" * 60)

    for d in diffs:
        if d["status"] == "new":
            logger.info(f"  馃啎 {d['name']} (鏂板, {d['runtime_size']}B)")
        elif d["status"] == "outdated":
            logger.info(f"  馃攧 {d['name']} (skill杩囨湡, 宸紓{d.get('size_diff', 0):+d}B)")
        elif d["status"] == "runtime_older":
            logger.info(f"  鈴笍  {d['name']} (runtime杈冩棫, 璺宠繃)")

    if skipped and not args.force:
        logger.info(f"\n鈿狅笍  {len(skipped)}涓ā鍧梤untime鐗堟湰杈冩棫锛屼娇鐢?-force寮哄埗瑕嗙洊")

    if args.dry_run:
        logger.info(f"\n[dry-run] 灏嗗悓姝?{len(to_sync)} 涓ā鍧?)
        return

    logger.info(f"\n鍚屾涓?..")
    success = 0
    for d in to_sync:
        if sync_module(d["name"], Path(d["runtime"]),
                       Path(d["skill"]) if d["skill"] else None,
                       dry_run=False):
            success += 1

    logger.info(f"\n鉁?瀹屾垚: {success}/{len(to_sync)} 涓ā鍧楀凡鍚屾")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
