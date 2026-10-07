"""
系统深度全面检验 v1.0
结构调整后全链路验证：底层skill + 适配层 + 核心模块 + 端到端
"""
import os
import sys
import json
import time
import traceback
from pathlib import Path

# ============================================================
# 配置
# ============================================================
PYTHON = sys.executable
SKILLS_ROOT = Path(r"C:\Users\Administrator\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills")
AI_VIDEO = SKILLS_ROOT / "ai-video-editor"

RESULTS = {"passed": [], "failed": [], "warnings": [], "info": []}

def check(name, func):
    """执行单个检查"""
    try:
        result = func()
        if result is True or result is None:
            RESULTS["passed"].append(name)
            print(f"  ✅ {name}")
        else:
            RESULTS["warnings"].append(f"{name}: {result}")
            print(f"  ⚠️  {name}: {result}")
    except Exception as e:
        RESULTS["failed"].append(f"{name}: {type(e).__name__}: {e}")
        print(f"  ❌ {name}: {type(e).__name__}: {e}")
        traceback.print_exc()

def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

# ============================================================
# 1. 底层skill冒烟测试
# ============================================================
section("1. 底层Skill冒烟测试")

def test_comfyui():
    os.chdir(SKILLS_ROOT / "comfyui-controls-skill")
    r = os.popen(f'"{PYTHON}" tests/test_smoke.py 2>&1').read()
    return "0 failed" in r

def test_blender():
    os.chdir(SKILLS_ROOT / "blender-controls-skill")
    r = os.popen(f'"{PYTHON}" tests/test_smoke.py 2>&1').read()
    return "0 failed" in r

def test_anysearch():
    os.chdir(SKILLS_ROOT / "anysearch-skill")
    r = os.popen(f'"{PYTHON}" tests/test_smoke.py 2>&1').read()
    return "0 failed" in r

def test_remotion():
    os.chdir(SKILLS_ROOT / "remotion-controls-skill")
    r = os.popen(f'"{PYTHON}" tests/test_smoke.py 2>&1').read()
    return "0 failed" in r

check("comfyui-controls-skill 冒烟测试", test_comfyui)
check("blender-controls-skill 冒烟测试", test_blender)
check("anysearch-skill 冒烟测试", test_anysearch)
check("remotion-controls-skill 冒烟测试", test_remotion)

# ============================================================
# 2. 适配层验证
# ============================================================
section("2. 剪映适配层验证")

sys.path.insert(0, str(AI_VIDEO))
sys.path.insert(0, str(AI_VIDEO / "scripts"))

def test_adapter_import():
    from adapters.jianying_adapter import (
        VideoSegment, AudioSegment, TextSegment, EffectSegment, FilterSegment,
        Transition, VideoMaterial, AudioMaterial, TextStyle, TextBorder, TextShadow,
        Timerange, tim, Track, TrackType, Keyframe, KeyframeProperty, KeyframeList,
        VideoAnimation, Text_animation, SegmentAnimations, ClipSettings,
        ScriptFile, DraftFolder, IntroType, OutroType, GroupAnimationType,
        TextIntro, TextOutro, TextLoopAnim, VideoSceneEffectType, FilterType,
        AudioSceneEffectType, ToneEffectType, SpeechToSongType,
        EffectEnum, AnimationMeta, EffectMeta, FontType, MaskType, MaskMeta,
        TransitionType, JianyingDraft,
    )
    return True

def test_adapter_jianyingdraft():
    from adapters.jianying_adapter import JianyingDraft
    # 验证JianyingDraft类有8个便捷方法
    methods = ["add_video", "add_audio", "add_text", "add_effect",
               "add_filter", "add_animation", "add_keyframe", "save"]
    missing = [m for m in methods if not hasattr(JianyingDraft, m)]
    if missing:
        return f"缺少方法: {missing}"
    return True

def test_adapter_intro_count():
    from adapters.jianying_adapter import IntroType
    free_count = sum(1 for e in IntroType if not e.value.is_vip)
    if free_count < 30:
        return f"免费入场动画仅{free_count}种（预期≥30）"
    return True

check("适配层全部类导入（30+类）", test_adapter_import)
check("JianyingDraft高层封装8方法", test_adapter_jianyingdraft)
check("免费入场动画数量≥30", test_adapter_intro_count)

# ============================================================
# 3. ai-video-editor核心模块导入
# ============================================================
section("3. ai-video-editor核心模块导入")

CORE_MODULES = [
    "jianying_executor",
    "artistic_subtitle",
    "enhanced_subtitle",
    "build_video",
    "clone_template",
    "photo_slideshow_generator",
    "multi_track_mixer",
    "tts_executor",
    "script_understanding_engine",
    "easy_build",
    "auto_beat",
    "camera_moves",
    "character_card",
    "mask_flash_transition",
    "text_wipe_animation",
    "subtitle_bar",
    "intro_builder",
    "compound_segment",
    "mask_keyframe",
    "text_layout",
    "blender_effects",
]

def test_core_import(mod):
    def _test():
        __import__(mod)
        return True
    return _test

for mod in CORE_MODULES:
    check(f"模块导入: {mod}", test_core_import(mod))

# ============================================================
# 4. 能力注册中心验证
# ============================================================
section("4. 能力注册中心验证")

def test_registry_skills():
    from adapters.capability_registry import get_registry
    reg = get_registry()
    skills = reg.list_skills()
    active = [s for s in skills if s["status"] == "active"]
    if len(active) < 6:
        return f"仅{len(active)}个active skill（预期≥6）"
    return True

def test_registry_capabilities():
    from adapters.capability_registry import get_registry
    reg = get_registry()
    caps = reg.list_capabilities()
    if len(caps) < 20:
        return f"仅{len(caps)}个能力（预期≥20）"
    return True

def test_registry_lookup():
    from adapters.capability_registry import get_registry
    reg = get_registry()
    cap = reg.get_capability("draft_creation")
    if cap is None:
        return "draft_creation能力未找到"
    if cap.priority < 8:
        return f"draft_creation优先级{cap.priority}（预期≥8）"
    return True

def test_registry_health():
    from adapters.capability_registry import get_registry
    reg = get_registry()
    health = reg.check_health()
    missing = [k for k, v in health.items() if v != "active"]
    if missing:
        return f"以下skill不健康: {missing}"
    return True

check("注册中心≥6个active skill", test_registry_skills)
check("注册中心≥20个能力", test_registry_capabilities)
check("能力查找draft_creation", test_registry_lookup)
check("健康检查全部active", test_registry_health)

# ============================================================
# 5. 解耦验证（无直接import pyJianYingDraft）
# ============================================================
section("5. 解耦验证")

def test_no_direct_import():
    """检查scripts/下是否还有直接import pyJianYingDraft的文件"""
    scripts_dir = AI_VIDEO / "scripts"
    offenders = []
    for py in scripts_dir.rglob("*.py"):
        content = py.read_text(encoding="utf-8", errors="ignore")
        if "import pyJianYingDraft" in content or "from pyJianYingDraft" in content:
            # 排除迁移脚本自身
            if "migrate_to_adapter" not in py.name:
                offenders.append(py.name)
    if offenders:
        return f"仍有{len(offenders)}个文件直接import: {offenders[:5]}"
    return True

def test_adapter_is_single_entry():
    """验证适配层是唯一直接import pyJianYingDraft的地方"""
    adapter = AI_VIDEO / "adapters" / "jianying_adapter.py"
    content = adapter.read_text(encoding="utf-8")
    if "import pyJianYingDraft" not in content:
        return "适配层未import pyJianYingDraft（异常）"
    return True

check("scripts/无直接import pyJianYingDraft", test_no_direct_import)
check("适配层是唯一入口", test_adapter_is_single_entry)

# ============================================================
# 6. 端到端验证（创建最小剪映工程）
# ============================================================
section("6. 端到端验证（适配层创建最小工程）")

def test_e2e_create_draft():
    """通过适配层创建一个最小剪映工程并保存"""
    import tempfile
    from adapters.jianying_adapter import (
        JianyingDraft, Timerange, VideoMaterial, VideoSegment,
        TextSegment, TextStyle, IntroType,
    )

    # 创建1x1红色PNG作为测试素材
    test_img = Path(tempfile.gettempdir()) / "sys_check_test.png"
    with open(test_img, "wb") as f:
        # 最小1x1红色PNG
        f.write(bytes.fromhex(
            "89504e470d0a1a0a0000000d4948445200000001000000010802000000907753de"
            "0000000c4944415408d763f8cf0000000300015bb85b1f0000000049454e44ae426082"
        ))

    draft = JianyingDraft("sys_check_e2e", 1080, 1920)
    draft.add_video(str(test_img), 0, 3.0)
    draft.add_text("系统检验", 0.5, 2.0, x=0, y=-0.3, font_size=60)
    result = draft.save()

    # 清理
    try:
        test_img.unlink()
    except:
        pass

    if result and "status" in result and result["status"] == "SUCCESS":
        return True
    return f"保存失败: {result}"

check("端到端: 适配层创建+保存工程", test_e2e_create_draft)

# ============================================================
# 7. 工程化文件完整性
# ============================================================
section("7. 工程化文件完整性")

REQUIRED_FILES = {
    "comfyui-controls-skill": ["pyproject.toml", "requirements.txt", "tests/test_smoke.py",
                                "examples/01_minimal_status.py", "docs/API_REFERENCE.md", "rules/usage_rules.md"],
    "blender-controls-skill": ["pyproject.toml", "requirements.txt", "tests/test_smoke.py",
                                "examples/01_minimal_status.py", "docs/API_REFERENCE.md", "rules/usage_rules.md"],
    "anysearch-skill": ["pyproject.toml", "tests/test_smoke.py",
                         "examples/01_cli_search.py", "docs/API_REFERENCE.md", "rules/usage_rules.md"],
    "remotion-controls-skill": ["pyproject.toml", "requirements.txt", "tests/test_smoke.py",
                                 "examples/01_keyframe_animation.py", "docs/API_REFERENCE.md", "rules/usage_rules.md"],
    "ai-video-editor": ["adapters/jianying_adapter.py", "adapters/capability_registry.py",
                         "INDEPENDENT_CAPABILITIES.md", "docs/SKILL_TEMPLATE.md",
                         "docs/PR_PS_AE_RESEARCH.md", "scripts/migrate_to_adapter.py"],
}

def check_files(skill, files):
    def _test():
        missing = []
        for f in files:
            if not (SKILLS_ROOT / skill / f).exists():
                missing.append(f)
        if missing:
            return f"缺少: {missing}"
        return True
    return _test

for skill, files in REQUIRED_FILES.items():
    check(f"{skill} 工程化文件完整", check_files(skill, files))

# ============================================================
# 8. 硬编码路径扫描
# ============================================================
section("8. 硬编码路径扫描（新代码）")

def test_hardcoded_paths():
    """扫描adapters/和新建文件中的硬编码路径"""
    check_dirs = [AI_VIDEO / "adapters"]
    offenders = []
    for d in check_dirs:
        for py in d.rglob("*.py"):
            content = py.read_text(encoding="utf-8", errors="ignore")
            for line in content.split("\n"):
                if "C:\\Users" in line and "#" not in line.split("C:\\Users")[0]:
                    offenders.append(f"{py.name}: {line.strip()[:60]}")
    if offenders:
        return f"发现{len(offenders)}处硬编码路径（适配层中可接受）"
    return True

check("硬编码路径扫描", test_hardcoded_paths)

# ============================================================
# 汇总
# ============================================================
section("检验汇总")

total = len(RESULTS["passed"]) + len(RESULTS["failed"]) + len(RESULTS["warnings"])
print(f"\n  总计: {total}项检查")
print(f"  ✅ 通过: {len(RESULTS['passed'])}")
print(f"  ⚠️  警告: {len(RESULTS['warnings'])}")
print(f"  ❌ 失败: {len(RESULTS['failed'])}")

if RESULTS["failed"]:
    print(f"\n  失败项:")
    for f in RESULTS["failed"]:
        print(f"    - {f}")

if RESULTS["warnings"]:
    print(f"\n  警告项:")
    for w in RESULTS["warnings"]:
        print(f"    - {w}")

# 保存结果
report = {
    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    "total": total,
    "passed": len(RESULTS["passed"]),
    "warnings": len(RESULTS["warnings"]),
    "failed": len(RESULTS["failed"]),
    "failed_items": RESULTS["failed"],
    "warning_items": RESULTS["warnings"],
}
report_path = AI_VIDEO / "tests" / "system_check_report.json"
with open(report_path, "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
print(f"\n  报告已保存: {report_path}")

sys.exit(1 if RESULTS["failed"] else 0)
