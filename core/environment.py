"""
环境检测模块
启动时检测各依赖环境是否可用，提供能力可用性判断和降级策略
"""
import os
import shutil
import subprocess
from typing import Dict, List, Optional
from .config import config


class EnvironmentChecker:
    """环境检测器"""

    def __init__(self):
        self._cache: Dict[str, dict] = {}
        self._checked = False

    def check_all(self) -> Dict[str, dict]:
        """检测所有环境，返回状态报告"""
        if self._checked:
            return self._cache

        self._cache = {
            "comfyui": self._check_comfyui(),
            "jianying": self._check_jianying(),
            "anysearch": self._check_anysearch(),
            "ffmpeg": self._check_ffmpeg(),
            "python_deps": self._check_python_deps(),
        }
        self._checked = True
        return self._cache

    def _check_comfyui(self) -> dict:
        """检测ComfyUI是否运行"""
        if not config.comfyui_enabled:
            return {"available": False, "reason": "已在配置中禁用"}

        try:
            import requests
            r = requests.get(f"http://{config.comfyui_address}/system_stats", timeout=3)
            if r.status_code == 200:
                stats = r.json()
                return {
                    "available": True,
                    "address": config.comfyui_address,
                    "devices": stats.get("devices", []),
                }
        except Exception as e:
            pass
        return {"available": False, "reason": f"无法连接到 {config.comfyui_address}"}

    def _check_jianying(self) -> dict:
        """检测剪映是否安装"""
        if not config.jianying_enabled:
            return {"available": False, "reason": "已在配置中禁用"}

        # 检查配置的路径
        path = config.jianying_path
        if path and os.path.exists(path):
            return {"available": True, "path": path, "version": config.jianying_version}

        # 检查常见安装路径
        common_paths = [
            r"C:\Program Files\JianyingPro\JianyingPro.exe",
            r"C:\Program Files (x86)\JianyingPro\JianyingPro.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\JianyingPro\JianyingPro.exe"),
        ]
        for p in common_paths:
            if os.path.exists(p):
                return {"available": True, "path": p, "version": "auto-detected"}

        return {"available": False, "reason": "未找到剪映安装路径，请在.env中配置JIANYING_PATH"}

    def _check_anysearch(self) -> dict:
        """检测AnySearch是否可用"""
        if not config.anysearch_enabled:
            return {"available": False, "reason": "未配置API Key"}

        try:
            import requests
            headers = {"Authorization": f"Bearer {config.anysearch_api_key}"}
            r = requests.post(
                f"{config.anysearch_endpoint}/v1/search",
                headers=headers,
                json={"query": "test", "max_results": 1},
                timeout=10,
            )
            if r.status_code == 200 and r.json().get("code") == 0:
                return {"available": True, "endpoint": config.anysearch_endpoint}
        except Exception as e:
            pass
        return {"available": False, "reason": "API Key无效或网络不可达"}

    def _check_ffmpeg(self) -> dict:
        """检测ffmpeg是否可用"""
        ffmpeg = shutil.which("ffmpeg")
        ffprobe = shutil.which("ffprobe")
        if ffmpeg and ffprobe:
            return {"available": True, "ffmpeg": ffmpeg, "ffprobe": ffprobe}
        return {"available": False, "reason": "ffmpeg/ffprobe未在PATH中找到"}

    def _check_python_deps(self) -> dict:
        """检测Python依赖"""
        # 必需依赖（requests, PIL），numpy为可选
        required = ["requests", "PIL"]
        optional = ["numpy"]
        deps = {}
        for dep in required + optional:
            try:
                __import__(dep)
                deps[dep] = True
            except ImportError:
                deps[dep] = False
        all_required = all(deps[d] for d in required)
        missing = [k for k in required if not deps[k]]
        if all_required:
            return {"available": True, "deps": deps, "optional_missing": [k for k in optional if not deps[k]]}
        return {"available": False, "deps": deps, "reason": f"缺失必需依赖: {', '.join(missing)}"}

    def is_available(self, module: str) -> bool:
        """判断某个模块是否可用"""
        if not self._checked:
            self.check_all()
        return self._cache.get(module, {}).get("available", False)

    def get_status(self, module: str) -> dict:
        """获取某个模块的详细状态"""
        if not self._checked:
            self.check_all()
        return self._cache.get(module, {"available": False, "reason": "未检测"})

    def get_summary(self) -> str:
        """获取环境状态摘要（用于展示给用户）"""
        if not self._checked:
            self.check_all()

        lines = ["=== 环境检测报告 ==="]
        icons = {"comfyui": "🎨 ComfyUI", "jianying": "✂️ 剪映", "anysearch": "🔍 AnySearch", "ffmpeg": "🎬 FFmpeg", "python_deps": "🐍 Python依赖"}
        for key, label in icons.items():
            status = self._cache.get(key, {})
            if status.get("available"):
                lines.append(f"  ✅ {label}: 可用")
            else:
                reason = status.get("reason", "未知")
                lines.append(f"  ❌ {label}: 不可用 - {reason}")

        # 能力降级提示
        lines.append("\n=== 能力降级提示 ===")
        if not self.is_available("comfyui"):
            lines.append("  ⚠️  ComfyUI不可用：跳过超分/抠图/人脸统一/三视图/文生图等算力功能")
        if not self.is_available("jianying"):
            lines.append("  ⚠️  剪映不可用：只输出方案和素材，不生成剪映草稿")
        if not self.is_available("anysearch"):
            lines.append("  ⚠️  AnySearch不可用：跳过网络搜索环节，使用内置知识")
        if not self.is_available("ffmpeg"):
            lines.append("  ⚠️  FFmpeg不可用：跳过视频转码/音频提取等操作")

        return "\n".join(lines)

    def get_available_capabilities(self) -> List[str]:
        """获取当前可用的能力列表（用于任务路由决策）"""
        caps = []
        if self.is_available("comfyui"):
            caps.extend(["upscale", "matting", "face_unify", "txt2img", "character_views"])
        if self.is_available("jianying"):
            caps.extend(["draft_creation", "export"])
        if self.is_available("anysearch"):
            caps.append("web_search")
        if self.is_available("ffmpeg"):
            caps.extend(["video_transcode", "audio_extract"])
        return caps


# 全局单例
env = EnvironmentChecker()
