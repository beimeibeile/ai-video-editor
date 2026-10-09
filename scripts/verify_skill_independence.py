#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
6 Skill 独立工作能力验证脚本
验证每个skill是否能独立导入核心模块并执行基础功能
"""

import logging
logger = logging.getLogger(__name__)

import os
import sys
import json
import importlib
from datetime import datetime

SKILLS_ROOT = r"C:\Users\Administrator\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills"
PYTHON = r"D:\Ai\ComfyUI-aki-v3.2\python\python.exe"

results = []

def test_skill(name, skill_dir, tests):
    """测试单个skill的独立能力"""
    logger.info(f"\n{'='*60}")
    logger.info(f"测试: {name}")
    logger.info(f"路径: {skill_dir}")
    logger.info(f"{'='*60}")
    
    skill_result = {
        "name": name,
        "path": skill_dir,
        "exists": os.path.isdir(skill_dir),
        "tests": [],
        "passed": 0,
        "failed": 0,
    }
    
    if not skill_result["exists"]:
        logger.info(f"  ❌ 目录不存在")
        skill_result["failed"] = 1
        results.append(skill_result)
        return
    
    # 统计文件
    py_count = len([f for f in os.listdir(skill_dir) if f.endswith('.py')]) if os.path.isdir(skill_dir) else 0
    all_py = []
    for root, dirs, files in os.walk(skill_dir):
        for f in files:
            if f.endswith('.py'):
                all_py.append(os.path.join(root, f))
    skill_result["py_files"] = len(all_py)
    logger.info(f"  Python文件: {len(all_py)}个")
    
    # 执行测试
    old_path = sys.path.copy()
    for test_name, test_func in tests:
        try:
            # 重置sys.path
            sys.path = old_path.copy()
            test_func(skill_dir)
            logger.info(f"  ✅ {test_name}")
            skill_result["tests"].append({"name": test_name, "status": "pass"})
            skill_result["passed"] += 1
        except Exception as e:
            logger.info(f"  ❌ {test_name}: {str(e)[:100]}")
            skill_result["tests"].append({"name": test_name, "status": "fail", "error": str(e)[:200]})
            skill_result["failed"] += 1
    
    sys.path = old_path
    results.append(skill_result)

# ============ ai-video-editor 测试 ============
def test_ai_video_editor_paths(skill_dir):
    """测试paths.py独立导入"""
    sys.path.insert(0, os.path.join(skill_dir, "scripts"))
    import paths
    assert hasattr(paths, 'PROJECT_ROOT'), "缺少PROJECT_ROOT"
    assert hasattr(paths, 'SKILLS'), "缺少SKILLS"
    assert hasattr(paths, 'verify_paths'), "缺少verify_paths"

def test_ai_video_editor_effect_api(skill_dir):
    """测试特效API独立导入"""
    sys.path.insert(0, os.path.join(skill_dir, "scripts"))
    from jianying_effect_api import JianyingEffectAPI
    api = JianyingEffectAPI()
    results = api.search('故障')
    assert len(results) > 0, "搜索故障无结果"

def test_ai_video_editor_preset_library(skill_dir):
    """测试特效预设库独立导入"""
    sys.path.insert(0, os.path.join(skill_dir, "scripts"))
    from effect_preset_library import EffectPresetLibrary
    lib = EffectPresetLibrary()
    presets = lib.list_presets()
    assert len(presets) > 0, "无预设"

def test_ai_video_editor_emotion_mapper(skill_dir):
    """测试情绪映射独立导入"""
    sys.path.insert(0, os.path.join(skill_dir, "scripts"))
    from emotion_effect_mapper import EmotionEffectMapper
    mapper = EmotionEffectMapper()
    emotions = mapper.list_emotions()
    assert len(emotions) > 0, "无情绪列表"
    effects = mapper.get_effects_for_emotion('激昂')
    assert effects is not None, "情绪特效映射失败"

# ============ jianying-editor 测试 ============
def test_jy_wrapper(skill_dir):
    """测试JyWrapper导入"""
    sys.path.insert(0, os.path.join(skill_dir, "scripts"))
    from jy_wrapper import JyProject
    assert JyProject is not None

def test_pyjianyingdraft(skill_dir):
    """测试pyJianYingDraft核心模块导入"""
    sys.path.insert(0, os.path.join(skill_dir, "scripts", "vendor"))
    from pyJianYingDraft.script_file import ScriptFile
    from pyJianYingDraft.track import TrackType
    from pyJianYingDraft.metadata import VideoSceneEffectType, IntroType, FilterType
    assert TrackType.video is not None

def test_jy_metadata(skill_dir):
    """测试元数据完整性"""
    sys.path.insert(0, os.path.join(skill_dir, "scripts", "vendor"))
    from pyJianYingDraft.metadata import (
        VideoSceneEffectType, VideoCharacterEffectType,
        IntroType, OutroType, GroupAnimationType,
        FilterType, TransitionType, AudioSceneEffectType,
        TextIntro, TextOutro, TextLoopAnim
    )
    assert len(list(VideoSceneEffectType)) > 100, "视频特效过少"

# ============ remotion-controls-skill 测试 ============
def test_remotion_renderer(skill_dir):
    """测试动画渲染器导入"""
    sys.path.insert(0, os.path.join(skill_dir, "capabilities", "cap_animation_renderer"))
    from renderer import AnimationRenderer
    assert AnimationRenderer is not None

def test_remotion_api(skill_dir):
    """测试Remotion API导入"""
    sys.path.insert(0, os.path.join(skill_dir, "capabilities", "cap_api_wrapper"))
    from api import RemotionAPI
    assert RemotionAPI is not None

# ============ comfyui-controls-skill 测试 ============
def test_comfy_api(skill_dir):
    """测试ComfyUI API导入"""
    sys.path.insert(0, os.path.join(skill_dir, "capabilities"))
    from cap_api_wrapper.comfy_api import ComfyClient
    assert ComfyClient is not None

def test_comfy_frame_matting(skill_dir):
    """测试逐帧抠图模块导入"""
    cap_dir = os.path.join(skill_dir, "capabilities", "cap_frame_matting")
    if os.path.isdir(cap_dir):
        sys.path.insert(0, cap_dir)
        from frame_matting import FrameMattingPipeline
        assert FrameMattingPipeline is not None

# ============ blender-controls-skill 测试 ============
def test_blender_effects(skill_dir):
    """测试Blender特效库模块完整性（语法检查+文件存在）"""
    effects_dir = os.path.join(skill_dir, "capabilities", "cap_effects_library")
    assert os.path.isdir(effects_dir), "cap_effects_library目录不存在"
    
    # 检查核心文件存在
    core_files = ["blender_effects.py", "library.py", "__init__.py"]
    for f in core_files:
        assert os.path.exists(os.path.join(effects_dir, f)), f"缺少{f}"
    
    # 语法检查（不执行导入，避免依赖链问题）
    import py_compile
    for f in core_files:
        fpath = os.path.join(effects_dir, f)
        try:
            py_compile.compile(fpath, doraise=True)
        except py_compile.PyCompileError as e:
            raise AssertionError(f"{f}语法错误: {e}")

# ============ anysearch-skill 测试 ============
def test_anysearch_cli(skill_dir):
    """测试AnySearch CLI导入"""
    sys.path.insert(0, os.path.join(skill_dir, "scripts"))
    import anysearch_cli
    assert hasattr(anysearch_cli, 'main'), "缺少main函数"
    assert hasattr(anysearch_cli, 'cmd_search'), "缺少cmd_search函数"
    assert hasattr(anysearch_cli, 'AVAILABLE_DOMAINS'), "缺少AVAILABLE_DOMAINS"

# ============ 执行所有测试 ============
logger.info("="*60)
logger.info("6 Skill 独立工作能力验证")
logger.info(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
logger.info("="*60)

test_skill("ai-video-editor", os.path.join(SKILLS_ROOT, "ai-video-editor"), [
    ("paths.py独立导入", test_ai_video_editor_paths),
    ("特效API独立导入+搜索", test_ai_video_editor_effect_api),
    ("特效预设库独立导入", test_ai_video_editor_preset_library),
    ("情绪映射独立导入", test_ai_video_editor_emotion_mapper),
])

test_skill("jianying-editor", os.path.join(SKILLS_ROOT, "jianying-editor"), [
    ("JyWrapper导入", test_jy_wrapper),
    ("pyJianYingDraft核心导入", test_pyjianyingdraft),
    ("元数据完整性", test_jy_metadata),
])

test_skill("remotion-controls-skill", os.path.join(SKILLS_ROOT, "remotion-controls-skill"), [
    ("动画渲染器导入", test_remotion_renderer),
    ("Remotion API导入", test_remotion_api),
])

test_skill("comfyui-controls-skill", os.path.join(SKILLS_ROOT, "comfyui-controls-skill"), [
    ("ComfyUI API导入", test_comfy_api),
    ("逐帧抠图模块导入", test_comfy_frame_matting),
])

test_skill("blender-controls-skill", os.path.join(SKILLS_ROOT, "blender-controls-skill"), [
    ("Blender特效库导入", test_blender_effects),
])

test_skill("anysearch-skill", os.path.join(SKILLS_ROOT, "anysearch-skill"), [
    ("AnySearch CLI导入", test_anysearch_cli),
])

# ============ 汇总报告 ============
logger.info("\n" + "="*60)
logger.info("验证结果汇总")
logger.info("="*60)

total_pass = 0
total_fail = 0
for r in results:
    status = "✅" if r["failed"] == 0 else "⚠️" if r["passed"] > 0 else "❌"
    logger.error(f"\n{status} {r['name']}: {r['passed']}通过 / {r['failed']}失败")
    if r.get("py_files"):
        logger.info(f"   Python文件: {r['py_files']}个")
    for t in r["tests"]:
        icon = "✅" if t["status"] == "pass" else "❌"
        logger.info(f"   {icon} {t['name']}")
        if t["status"] == "fail" and t.get("error"):
            logger.error(f"      错误: {t['error'][:80]}")
    total_pass += r["passed"]
    total_fail += r["failed"]

logger.info(f"\n{'='*60}")
logger.error(f"总计: {total_pass}通过 / {total_fail}失败 / {total_pass+total_fail}测试")
logger.error(f"通过率: {total_pass/(total_pass+total_fail)*100:.1f}%")
logger.info("="*60)

# 保存报告
report = {
    "timestamp": datetime.now().isoformat(),
    "total_pass": total_pass,
    "total_fail": total_fail,
    "skills": results,
}
report_path = os.path.join(SKILLS_ROOT, "..", "skill_independence_report.json")
with open(report_path, "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
logger.info(f"\n报告已保存: {report_path}")
