"""
批量迁移脚本: 将ai-video-editor中直接import pyJianYingDraft的文件
迁移到通过adapters.jianying_adapter访问。

用法:
    python scripts/migrate_to_adapter.py [--dry-run] [--file <specific_file>]

迁移规则:
1. `# pyJianYingDraft已迁移到适配层
import os as _os, sys as _sys
_AVR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _AVR not in _sys.path: _sys.path.insert(0, _AVR)` → 从适配层导入所需类，替换draft.引用
2. `from pyJianYingDraft.xxx import Yyy` → `from adapters.jianying_adapter import Yyy`
3. `from adapters.jianying_adapter import Xxx` → `from adapters.jianying_adapter import Xxx`
"""
import os
import re
import sys
import argparse
from pathlib import Path

AI_VIDEO_ROOT = Path(__file__).parent.parent

# 需要扫描的目录
SCAN_DIRS = ["scripts", "capabilities", "workbench", "."]

# import模式 → 适配层映射
IMPORT_PATTERNS = [
    # from adapters.jianying_adapter import Yyy → from adapters.jianying_adapter import Yyy
    (r'from pyJianYingDraft\.metadata\.\w+ import ([\w, ]+)',
     r'from adapters.jianying_adapter import \1'),
    # from adapters.jianying_adapter import Xxx → from adapters.jianying_adapter import Xxx
    (r'from pyJianYingDraft import ([\w, ]+)',
     r'from adapters.jianying_adapter import \1'),
    # # pyJianYingDraft已迁移到适配层
import os as _os, sys as _sys
_AVR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _AVR not in _sys.path: _sys.path.insert(0, _AVR) → 注释+适配层路径注入
    (r'# pyJianYingDraft已迁移到适配层
import os as _os, sys as _sys
_AVR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _AVR not in _sys.path: _sys.path.insert(0, _AVR)',
     '# pyJianYingDraft已迁移到适配层\nimport os as _os, sys as _sys\n_AVR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))\nif _AVR not in _sys.path: _sys.path.insert(0, _AVR)'),
]

# draft.xxx → xxx (需要先确认xxx在适配层中导出)
DRAFT_REPLACEMENTS = [
    "MaskType", "KeyframeProperty", "Keyframe", "KeyframeList",
    "Timerange", "tim", "Track", "TrackType",
    "VideoSegment", "AudioSegment", "TextSegment",
    "EffectSegment", "FilterSegment", "Transition",
    "VideoMaterial", "AudioMaterial", "TextStyle", "TextBorder",
    "VideoAnimation", "Text_animation", "SegmentAnimations",
    "ClipSettings", "MediaSegment", "BaseSegment",
    "ScriptFile", "DraftFolder",
    "IntroType", "OutroType", "GroupAnimationType",
    "TextIntro", "TextOutro", "TextLoopAnim",
    "VideoSceneEffectType", "VideoCharacterEffectType", "FilterType",
    "AudioSceneEffectType", "ToneEffectType", "SpeechToSongType",
    "EffectEnum", "AnimationMeta", "EffectMeta",
    "FontType", "MaskMeta", "TransitionType",
]


def migrate_file(filepath: Path, dry_run: bool = False) -> dict:
    """迁移单个文件"""
    content = filepath.read_text(encoding="utf-8")
    original = content
    changes = []

    # 1. 替换import语句
    for pattern, replacement in IMPORT_PATTERNS:
        new_content, count = re.subn(pattern, replacement, content)
        if count > 0:
            changes.append(f"  import替换: {count}处")
            content = new_content

    # 2. 替换draft.xxx引用（仅当文件中有draft变量时）
    if "draft" in content and "# pyJianYingDraft已迁移到适配层
import os as _os, sys as _sys
_AVR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _AVR not in _sys.path: _sys.path.insert(0, _AVR)" not in content:
        for cls in DRAFT_REPLACEMENTS:
            pattern = rf'\bdraft\.{cls}\b'
            new_content, count = re.subn(pattern, cls, content)
            if count > 0:
                changes.append(f"  draft.{cls} → {cls}: {count}处")
                content = new_content

    if content != original:
        if not dry_run:
            filepath.write_text(content, encoding="utf-8")
        return {"file": str(filepath), "changed": True, "changes": changes}
    return {"file": str(filepath), "changed": False, "changes": []}


def main():
    parser = argparse.ArgumentParser(description="批量迁移pyJianYingDraft到适配层")
    parser.add_argument("--dry-run", action="store_true", help="仅显示变更不写入")
    parser.add_argument("--file", type=str, help="仅迁移指定文件")
    args = parser.parse_args()

    files_to_migrate = []
    if args.file:
        files_to_migrate = [Path(args.file)]
    else:
        for scan_dir in SCAN_DIRS:
            dir_path = AI_VIDEO_ROOT / scan_dir
            if not dir_path.exists():
                continue
            for py_file in dir_path.rglob("*.py"):
                # 跳过adapters目录自身和tests
                if "adapters" in str(py_file) or "tests" in str(py_file):
                    continue
                content = py_file.read_text(encoding="utf-8", errors="ignore")
                if "pyJianYingDraft" in content:
                    files_to_migrate.append(py_file)

    print(f"待迁移文件: {len(files_to_migrate)}个")
    results = []
    for f in files_to_migrate:
        result = migrate_file(f, args.dry_run)
        if result["changed"]:
            results.append(result)
            print(f"\n{'[DRY-RUN] ' if args.dry_run else ''}{f.name}")
            for c in result["changes"]:
                print(c)

    print(f"\n{'预计' if args.dry_run else '实际'}变更文件: {len(results)}/{len(files_to_migrate)}")
    if args.dry_run:
        print("（dry-run模式，未写入文件）")


if __name__ == "__main__":
    main()
