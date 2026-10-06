"""
统一路径配置模块
所有硬编码路径集中管理，避免70个文件各自维护路径
使用方式：from paths import PATHS, get_path
"""
import os
from typing import Dict, Any


def _env(key: str, default: str) -> str:
    """优先从环境变量读取，否则用默认值"""
    return os.environ.get(key, default)


# 基础路径
USERPROFILE = os.environ.get("USERPROFILE", r"C:\Users\Administrator")
LOCALAPPDATA = os.environ.get("LOCALAPPDATA", os.path.join(USERPROFILE, "AppData", "Local"))
APPDATA = os.environ.get("APPDATA", os.path.join(USERPROFILE, "AppData", "Roaming"))

# 项目根目录（本文件位于 runtime/scripts/，向上两级）
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# 核心路径配置
PATHS: Dict[str, str] = {
    # 基础目录
    "userprofile": USERPROFILE,
    "localappdata": LOCALAPPDATA,
    "appdata": APPDATA,

    # 项目目录
    "project_root": PROJECT_ROOT,
    "runtime_dir": os.path.join(PROJECT_ROOT, "ai-video-editor-runtime"),
    "runtime_scripts": os.path.join(PROJECT_ROOT, "ai-video-editor-runtime", "scripts"),
    "scripts_dir": os.path.join(PROJECT_ROOT, "scripts"),
    "material_dir": os.path.join(PROJECT_ROOT, "material"),
    "output_dir": os.path.join(PROJECT_ROOT, "out"),
    "debug_dir": os.path.join(PROJECT_ROOT, "debug"),
    "knowledge_base": os.path.join(PROJECT_ROOT, "knowledge_base"),
    "test_dir": os.path.join(PROJECT_ROOT, "director_engine_test"),

    # Skill目录
    "skill_root": _env("AI_VIDEO_EDITOR_SKILL",
        os.path.join(LOCALAPPDATA, "Doubao", "User Data", "Default",
                     ".doubao", "agent_mode", "workspace", ".user_skills", "ai-video-editor")),
    "jianying_skill_root": _env("JIANYING_SKILL",
        os.path.join(LOCALAPPDATA, "Doubao", "User Data", "Default",
                     ".doubao", "agent_mode", "workspace", ".user_skills", "jianying-editor")),
    "remotion_skill_root": _env("REMOTION_SKILL",
        os.path.join(LOCALAPPDATA, "Doubao", "User Data", "Default",
                     ".doubao", "agent_mode", "workspace", ".user_skills", "remotion-controls-skill")),

    # 剪映
    "jianying_drafts_root": _env("JIANYING_DRAFTS",
        os.path.join(LOCALAPPDATA, "JianyingPro", "User Data", "Projects", "com.lveditor.draft")),
    "jianying_drafts_d_drive": r"D:\JianyingProDrafts\JianyingPro Drafts",
    "jianying_exe": _env("JIANYING_EXE",
        r"C:\Program Files\JianyingPro\JianyingPro.exe"),

    # Python环境
    "python_exe": _env("PYTHON_EXE",
        r"D:\Ai\ComfyUI-aki-v3.2\python\python.exe"),

    # ComfyUI
    "comfyui_address": _env("COMFYUI_ADDRESS", "127.0.0.1:8188"),
    "comfyui_url": _env("COMFYUI_URL", "http://127.0.0.1:8188"),

    # 开发工作台
    "dev_workbench": "http://127.0.0.1:8000",

    # 配置文件
    "adapter_config": os.path.join(PROJECT_ROOT, "adapter_config.json"),
    "llm_config": os.path.join(PROJECT_ROOT, "llm_config.json"),
    "rewrite_memory": os.path.join(PROJECT_ROOT, "rewrite_memory.json"),

    # ffmpeg
    "ffmpeg_exe": _env("FFMPEG", "ffmpeg"),
    "ffprobe_exe": _env("FFPROBE", "ffprobe"),
}


def get_path(key: str) -> str:
    """获取路径，不存在的key返回空字符串"""
    return PATHS.get(key, "")


def ensure_dir(key: str) -> str:
    """获取路径并确保目录存在"""
    p = PATHS.get(key, "")
    if p and not os.path.exists(p):
        os.makedirs(p, exist_ok=True)
    return p


def list_paths() -> None:
    """打印所有路径配置（调试用）"""
    print("=" * 60)
    print("路径配置")
    print("=" * 60)
    for k, v in sorted(PATHS.items()):
        exists = "✅" if os.path.exists(v) else "❌"
        print(f"  {exists} {k}: {v}")
    print("=" * 60)


if __name__ == "__main__":
    list_paths()
