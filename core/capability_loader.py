"""
能力模块加载器（增强版）
自动发现 capabilities/ 下的所有模块，支持依赖声明、环境检测、降级策略
"""
import os
import importlib
import sys
from typing import Dict, List, Optional

CAPABILITIES_DIR = os.path.join(os.path.dirname(__file__), "..", "capabilities")

# 能力模块依赖声明（模块名 -> 依赖的环境模块列表）
# 环境模块：comfyui, jianying, anysearch, ffmpeg, python_deps, blender
CAPABILITY_DEPENDENCIES = {
    "cap_comfyui_runner": ["comfyui", "python_deps"],
    "cap_material_creator": ["python_deps"],
    "cap_video_analyzer": ["ffmpeg", "python_deps"],
    "cap_subtitle_designer": ["python_deps"],
    "cap_effect_library": ["jianying"],
    "cap_keyframe_engine": ["jianying"],
    "cap_audio_designer": ["ffmpeg", "python_deps"],
    "cap_search": ["anysearch", "python_deps"],
    "cap_blender_runner": ["blender", "python_deps"],
    # cap_creative下的模块
    "movie_storyboard": ["python_deps"],
    "hunyuan_i2v_runner": ["comfyui", "python_deps"],
    "short_video_composer": ["jianying", "python_deps"],
    "real_bgm_generator": ["ffmpeg", "python_deps"],
    "dual_mode_pipeline": ["comfyui", "jianying", "python_deps"],
    "tag_engine": ["python_deps"],
    "sound_engine": ["ffmpeg", "python_deps"],
    "short_video_pipeline": ["jianying", "python_deps"],
}

# 能力模块降级方案（模块名 -> 降级说明）
CAPABILITY_FALLBACK = {
    "cap_comfyui_runner": "跳过算力相关功能，使用基础方案（不超分/不抠图/不人脸统一）",
    "cap_video_analyzer": "跳过视频自动分析，用户手动提供分镜信息",
    "cap_effect_library": "跳过特效自动添加，用户手动在剪映中添加",
    "cap_keyframe_engine": "跳过关键帧自动生成，使用静态图片",
    "cap_audio_designer": "跳过音频自动设计，使用默认BGM或无音频",
    "cap_search": "跳过网络搜索，使用内置知识和用户提供的信息",
}

# 已注册的能力模块
_REGISTRY: Dict[str, dict] = {}


def discover_capabilities() -> Dict[str, dict]:
    """扫描capabilities目录，发现所有能力模块并检测依赖"""
    from .environment import env

    if not os.path.exists(CAPABILITIES_DIR):
        return {}

    env.check_all()

    for name in os.listdir(CAPABILITIES_DIR):
        path = os.path.join(CAPABILITIES_DIR, name)
        if os.path.isdir(path) and name.startswith("cap_"):
            skill_md = os.path.join(path, "SKILL.md")
            if os.path.exists(skill_md):
                # 检查依赖
                deps = CAPABILITY_DEPENDENCIES.get(name, ["python_deps"])
                missing_deps = [d for d in deps if not env.is_available(d)]

                if not missing_deps:
                    status = "available"
                elif all(d in CAPABILITY_FALLBACK for d in [name]):
                    status = "degraded"
                else:
                    status = "unavailable"

                _REGISTRY[name] = {
                    "name": name,
                    "path": path,
                    "skill_md": skill_md,
                    "status": status,
                    "dependencies": deps,
                    "missing_dependencies": missing_deps,
                    "fallback": CAPABILITY_FALLBACK.get(name, "无降级方案，功能不可用"),
                }

    # 扫描cap_creative下的.py模块
    creative_dir = os.path.join(CAPABILITIES_DIR, "cap_creative")
    if os.path.exists(creative_dir):
        for fname in os.listdir(creative_dir):
            if fname.endswith('.py') and not fname.startswith('_'):
                mod_name = fname[:-3]
                mod_path = os.path.join(creative_dir, fname)
                deps = CAPABILITY_DEPENDENCIES.get(mod_name, ["python_deps"])
                missing_deps = [d for d in deps if not env.is_available(d)]

                if not missing_deps:
                    status = "available"
                elif mod_name in CAPABILITY_FALLBACK:
                    status = "degraded"
                else:
                    status = "unavailable"

                _REGISTRY[f"cap_creative.{mod_name}"] = {
                    "name": f"cap_creative.{mod_name}",
                    "path": mod_path,
                    "skill_md": None,
                    "status": status,
                    "dependencies": deps,
                    "missing_dependencies": missing_deps,
                    "fallback": CAPABILITY_FALLBACK.get(mod_name, "无降级方案，功能不可用"),
                    "category": "creative",
                }

    return _REGISTRY


def get_capability(name: str) -> Optional[dict]:
    """获取能力模块信息"""
    if not _REGISTRY:
        discover_capabilities()
    return _REGISTRY.get(name)


def list_capabilities(status: str = None) -> List[str]:
    """列出所有能力模块，可按状态过滤"""
    if not _REGISTRY:
        discover_capabilities()
    if status:
        return [n for n, info in _REGISTRY.items() if info["status"] == status]
    return list(_REGISTRY.keys())


def is_capability_available(name: str) -> bool:
    """判断能力模块是否可用（available或degraded）"""
    cap = get_capability(name)
    if cap is None:
        return False
    return cap["status"] in ("available", "degraded")


def load_capability(name: str):
    """
    动态加载能力模块

    Returns:
        模块对象或None（不可用时返回None）
    """
    cap = get_capability(name)
    if cap is None or cap["status"] == "unavailable":
        return None

    cap_path = os.path.join(CAPABILITIES_DIR, name)
    if not os.path.exists(cap_path):
        return None

    if cap_path not in sys.path:
        sys.path.insert(0, os.path.dirname(CAPABILITIES_DIR))

    try:
        module = importlib.import_module(f"capabilities.{name}")
        return module
    except ImportError as e:
        print(f"⚠️  加载能力模块 {name} 失败: {e}")
        return None


def get_capability_report() -> str:
    """获取能力模块状态报告（用于展示）"""
    if not _REGISTRY:
        discover_capabilities()

    lines = ["=== 能力模块状态 ==="]
    status_icons = {"available": "✅", "degraded": "⚠️", "unavailable": "❌"}
    for name, info in sorted(_REGISTRY.items()):
        icon = status_icons.get(info["status"], "❓")
        lines.append(f"  {icon} {name}: {info['status']}")
        if info["missing_dependencies"]:
            lines.append(f"      缺失依赖: {', '.join(info['missing_dependencies'])}")
            lines.append(f"      降级方案: {info['fallback']}")
    return "\n".join(lines)
