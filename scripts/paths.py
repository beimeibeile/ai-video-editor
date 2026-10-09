"""
统一路径配置模块
所有模块应从此处读取路径，避免硬编码
支持环境变量覆盖
"""

import logging
logger = logging.getLogger(__name__)


import os
from typing import Dict, Any


# ============ 项目根目录 ============
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_RUNTIME_DIR = os.path.dirname(_THIS_DIR)
PROJECT_ROOT = os.environ.get(
    "AVE_PROJECT_ROOT",
    r"D:\DobaoWork_Project\Ai_Video_Editor"
)

# ============ Skill目录 ============
SKILL_ROOT = os.environ.get(
    "AVE_SKILL_ROOT",
    r"C:\Users\Administrator\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills"
)

SKILLS = {
    "ai_video_editor": os.path.join(SKILL_ROOT, "ai-video-editor"),
    "jianying_editor": os.path.join(SKILL_ROOT, "jianying-editor"),
    "comfyui_controls": os.path.join(SKILL_ROOT, "comfyui-controls-skill"),
    "blender_controls": os.path.join(SKILL_ROOT, "blender-controls-skill"),
    "remotion_controls": os.path.join(SKILL_ROOT, "remotion-controls-skill"),
    "anysearch": os.path.join(SKILL_ROOT, "anysearch-skill"),
}

# ============ Runtime目录 ============
RUNTIME_ROOT = os.environ.get(
    "AVE_RUNTIME_ROOT",
    os.path.join(PROJECT_ROOT, "ai-video-editor-runtime")
)
RUNTIME_SCRIPTS = os.path.join(RUNTIME_ROOT, "scripts")
RUNTIME_CAPABILITIES = os.path.join(RUNTIME_ROOT, "capabilities")

# ============ 剪映相关 ============
JIANYING_DRAFTS_ROOT = os.environ.get(
    "AVE_JIANYING_DRAFTS",
    r"C:\Users\Administrator\AppData\Local\JianyingPro\User Data\Projects\com.lveditor.draft"
)
JIANYING_SKILL_SCRIPTS = os.path.join(SKILLS["jianying_editor"], "scripts")
JIANYING_VENDOR = os.path.join(JIANYING_SKILL_SCRIPTS, "vendor", "pyJianYingDraft")

# ============ 外部工具 ============
FFMPEG = os.environ.get("AVE_FFMPEG", r"D:\Ai\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe")
FFPROBE = os.environ.get("AVE_FFPROBE", r"D:\Ai\ffmpeg-master-latest-win64-gpl\bin\ffprobe.exe")
PYTHON = os.environ.get("AVE_PYTHON", r"D:\Ai\ComfyUI-aki-v3.2\python\python.exe")
BLENDER = os.environ.get("AVE_BLENDER", r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe")

# ============ 服务地址 ============
COMFYUI_URL = os.environ.get("AVE_COMFYUI_URL", "http://127.0.0.1:8188")
COMFYUI_API = f"{COMFYUI_URL}/api"

# ============ 项目子目录 ============
MATERIAL_DIR = os.path.join(PROJECT_ROOT, "material")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "out")
EFFECT_CATALOG = os.path.join(PROJECT_ROOT, "effect_catalog", "effect_catalog.json")
EFFECT_PRESETS = os.path.join(PROJECT_ROOT, "effect_catalog", "effect_presets.json")
USER_DIRECTORY = os.path.join(PROJECT_ROOT, "User Directory")
DOCS_DIR = os.path.join(PROJECT_ROOT, "docs")
KNOWLEDGE_BASE = os.path.join(PROJECT_ROOT, "knowledge_base")

# ============ 字体目录 ============
FONT_DIR = r"C:\Windows\Fonts"
FONTS = {
    "msyh": os.path.join(FONT_DIR, "msyh.ttc"),
    "msyhbd": os.path.join(FONT_DIR, "msyhbd.ttc"),
    "arial": os.path.join(FONT_DIR, "arial.ttf"),
    "arialbd": os.path.join(FONT_DIR, "arialbd.ttf"),
}


def get_all_paths() -> Dict[str, Any]:
    return {
        "PROJECT_ROOT": PROJECT_ROOT,
        "SKILL_ROOT": SKILL_ROOT,
        "RUNTIME_ROOT": RUNTIME_ROOT,
        "RUNTIME_SCRIPTS": RUNTIME_SCRIPTS,
        "JIANYING_DRAFTS_ROOT": JIANYING_DRAFTS_ROOT,
        "FFMPEG": FFMPEG,
        "FFPROBE": FFPROBE,
        "PYTHON": PYTHON,
        "BLENDER": BLENDER,
        "COMFYUI_URL": COMFYUI_URL,
        "MATERIAL_DIR": MATERIAL_DIR,
        "OUTPUT_DIR": OUTPUT_DIR,
        "EFFECT_CATALOG": EFFECT_CATALOG,
        "USER_DIRECTORY": USER_DIRECTORY,
        "SKILLS": SKILLS,
        "FONTS": FONTS,
    }


def verify_paths() -> Dict[str, bool]:
    checks = {
        "PROJECT_ROOT": os.path.isdir(PROJECT_ROOT),
        "SKILL_ROOT": os.path.isdir(SKILL_ROOT),
        "RUNTIME_SCRIPTS": os.path.isdir(RUNTIME_SCRIPTS),
        "JIANYING_DRAFTS_ROOT": os.path.isdir(JIANYING_DRAFTS_ROOT),
        "FFMPEG": os.path.isfile(FFMPEG),
        "FFPROBE": os.path.isfile(FFPROBE),
        "PYTHON": os.path.isfile(PYTHON),
        "EFFECT_CATALOG": os.path.isfile(EFFECT_CATALOG),
        "MATERIAL_DIR": os.path.isdir(MATERIAL_DIR),
    }
    for skill_name, skill_path in SKILLS.items():
        checks[f"skill_{skill_name}"] = os.path.isdir(skill_path)
    return checks


def setup_sys_path():
    import sys
    paths_to_add = [
        RUNTIME_SCRIPTS,
        JIANYING_SKILL_SCRIPTS,
        JIANYING_VENDOR,
        SKILLS["ai_video_editor"],
        os.path.join(SKILLS["ai_video_editor"], "scripts"),
    ]
    for p in paths_to_add:
        if p and os.path.isdir(p) and p not in sys.path:
            sys.path.insert(0, p)


if __name__ == "__main__":
    logger.info("=== 路径配置验证 ===")
    results = verify_paths()
    for name, exists in results.items():
        status = "OK" if exists else "MISSING"
        logger.info(f"  [{status}] {name}")
    logger.info(f"\n总计: {sum(results.values())}/{len(results)} 路径存在")