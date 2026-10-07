"""
环境检测模块
检测 ai-video-editor 运行所需的所有外部依赖，首次使用时提示用户安装缺失组件。

检测项：
- DaVinci Resolve / Fusion（特效合成）
- ComfyUI（AI算力）
- 剪映（工程合成）
- ffmpeg（视频处理）
- Python 依赖（Pillow, numpy等）
"""

import os
import sys
import json
import shutil
import subprocess
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class EnvCheckResult:
    """单项检测结果"""
    name: str
    available: bool
    version: str = ""
    path: str = ""
    message: str = ""
    install_url: str = ""
    install_hint: str = ""


@dataclass
class EnvReport:
    """环境检测报告"""
    timestamp: str = ""
    all_passed: bool = False
    results: List[EnvCheckResult] = field(default_factory=list)
    missing: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "all_passed": self.all_passed,
            "missing": self.missing,
            "results": [asdict(r) for r in self.results],
        }

    def to_markdown(self) -> str:
        lines = ["# 环境检测报告", ""]
        status = "✅ 全部通过" if self.all_passed else f"❌ 缺失 {len(self.missing)} 项"
        lines.append(f"**状态**: {status}")
        lines.append(f"**时间**: {self.timestamp}")
        lines.append("")
        lines.append("| 组件 | 状态 | 版本 | 路径 |")
        lines.append("|---|---|---|---|")
        for r in self.results:
            icon = "✅" if r.available else "❌"
            lines.append(f"| {r.name} | {icon} | {r.version} | {r.path} |")
        if self.missing:
            lines.append("")
            lines.append("## 缺失组件安装指引")
            for r in self.results:
                if not r.available:
                    lines.append(f"### {r.name}")
                    lines.append(f"- {r.install_hint}")
                    if r.install_url:
                        lines.append(f"- 下载: {r.install_url}")
                    lines.append("")
        return "\n".join(lines)


class EnvChecker:
    """环境检测器"""

    # DaVinci Resolve 常见安装路径
    DAVINCI_PATHS = [
        r"C:\Program Files\Blackmagic Design\DaVinci Resolve\Resolve.exe",
        r"C:\Program Files (x86)\Blackmagic Design\DaVinci Resolve\Resolve.exe",
    ]
    DAVINCI_RENDER_PATHS = [
        r"C:\Program Files\Blackmagic Design\DaVinci Resolve\Resolve.exe",
    ]
    DAVINCI_FUSION_SCRIPT_PATHS = [
        r"C:\Program Files\Blackmagic Design\DaVinci Resolve\Fusion\Scripts",
    ]

    # ComfyUI 常见路径
    COMFYUI_PATHS = [
        r"D:\Ai\ComfyUI-aki-v3.2\ComfyUI\main.py",
        r"D:\Ai\ComfyUI\main.py",
        r"C:\ComfyUI\main.py",
    ]
    COMFYUI_API_URL = "http://127.0.0.1:8188"

    # 剪映常见路径
    JIANYING_PATHS = [
        r"C:\Users\Administrator\Downloads\JianyingPro_5.9（windows版本）\5.9.0.11632\JianyingPro.exe",
        r"C:\Program Files\JianyingPro\JianyingPro.exe",
    ]
    JIANYING_DRAFT_PATHS = [
        r"D:\JianyingProDrafts\JianyingPro Drafts",
        r"C:\Users\Administrator\AppData\Local\JianyingPro\User Data\Projects\com.lveditor.draft",
    ]

    # ffmpeg 常见路径
    FFMPEG_PATHS = [
        r"D:\Ai\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe",
        r"C:\ffmpeg\bin\ffmpeg.exe",
    ]

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.report = EnvReport()

    def check_all(self) -> EnvReport:
        """执行全部检测"""
        from datetime import datetime
        self.report = EnvReport(timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        # 按优先级检测
        self.report.results.append(self._check_davinci())
        self.report.results.append(self._check_comfyui())
        self.report.results.append(self._check_jianying())
        self.report.results.append(self._check_ffmpeg())
        self.report.results.append(self._check_python_deps())

        # 汇总
        self.report.missing = [r.name for r in self.report.results if not r.available]
        self.report.all_passed = len(self.report.missing) == 0

        return self.report

    def check_davinci(self) -> EnvCheckResult:
        """仅检测 DaVinci Resolve"""
        return self._check_davinci()

    def _check_davinci(self) -> EnvCheckResult:
        """检测 DaVinci Resolve / Fusion"""
        for path in self.DAVINCI_PATHS:
            if os.path.exists(path):
                version = self._get_file_version(path)
                # 检测 Fusion 脚本目录
                fusion_scripts = os.path.join(os.path.dirname(path), "Fusion", "Scripts")
                fusion_ok = os.path.exists(fusion_scripts)
                msg = f"已安装 (Fusion脚本: {'✅' if fusion_ok else '❌'})"
                return EnvCheckResult(
                    name="DaVinci Resolve",
                    available=True,
                    version=version,
                    path=path,
                    message=msg,
                )

        # 检测注册表
        reg_version = self._get_registry_value(
            r"HKLM:\SOFTWARE\Blackmagic Design\DaVinci Resolve", "Version"
        )
        if reg_version:
            return EnvCheckResult(
                name="DaVinci Resolve",
                available=True,
                version=reg_version,
                path="(注册表检测)",
                message="已安装 (注册表检测)",
            )

        return EnvCheckResult(
            name="DaVinci Resolve",
            available=False,
            message="未安装",
            install_url="https://www.blackmagicdesign.com/cn/products/davinciresolve",
            install_hint="下载免费版 DaVinci Resolve（不带 Studio），约 3.5GB，安装时全部默认即可。Fusion 页面用于粒子、文字动画、光效等高级特效合成。",
        )

    def _check_comfyui(self) -> EnvCheckResult:
        """检测 ComfyUI"""
        # 检测 API 是否可访问
        try:
            import urllib.request
            req = urllib.request.Request(self.COMFYUI_API_URL + "/system_stats")
            with urllib.request.urlopen(req, timeout=3) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read())
                    return EnvCheckResult(
                        name="ComfyUI",
                        available=True,
                        version=f"API在线 (设备: {data.get('devices', [{}])[0].get('name', '未知')})",
                        path=self.COMFYUI_API_URL,
                        message="服务运行中",
                    )
        except Exception:
            pass

        # 检测安装路径
        for path in self.COMFYUI_PATHS:
            if os.path.exists(path):
                return EnvCheckResult(
                    name="ComfyUI",
                    available=True,
                    version="(未启动)",
                    path=os.path.dirname(path),
                    message="已安装但服务未启动，运行 main.py 启动",
                )

        return EnvCheckResult(
            name="ComfyUI",
            available=False,
            message="未安装",
            install_url="https://github.com/comfyanonymous/ComfyUI",
            install_hint="AI 视频/图片生成算力引擎。推荐使用 ComfyUI-aki 整合包，内置常用插件和模型。",
        )

    def _check_jianying(self) -> EnvCheckResult:
        """检测剪映"""
        for path in self.JIANYING_PATHS:
            if os.path.exists(path):
                version = self._get_file_version(path)
                return EnvCheckResult(
                    name="剪映",
                    available=True,
                    version=version,
                    path=path,
                    message="已安装",
                )

        return EnvCheckResult(
            name="剪映",
            available=False,
            message="未安装",
            install_url="https://www.capcut.cn/",
            install_hint="视频工程合成工具。推荐 5.9 版本（API 兼容性最好），安装后禁止自动更新。",
        )

    def _check_ffmpeg(self) -> EnvCheckResult:
        """检测 ffmpeg"""
        # 检测 PATH 中的 ffmpeg
        ffmpeg_path = shutil.which("ffmpeg")
        if ffmpeg_path:
            version = self._get_ffmpeg_version(ffmpeg_path)
            return EnvCheckResult(
                name="ffmpeg",
                available=True,
                version=version,
                path=ffmpeg_path,
                message="已安装 (PATH)",
            )

        # 检测常见路径
        for path in self.FFMPEG_PATHS:
            if os.path.exists(path):
                version = self._get_ffmpeg_version(path)
                return EnvCheckResult(
                    name="ffmpeg",
                    available=True,
                    version=version,
                    path=path,
                    message="已安装",
                )

        return EnvCheckResult(
            name="ffmpeg",
            available=False,
            message="未安装",
            install_url="https://www.gyan.dev/ffmpeg/builds/",
            install_hint="视频处理基础工具。下载 release-full 版本，解压后将 bin 目录加入系统 PATH。",
        )

    def _check_python_deps(self) -> EnvCheckResult:
        """检测 Python 依赖"""
        missing = []
        deps = {
            "PIL": "Pillow",
            "numpy": "numpy",
            "requests": "requests",
        }
        for mod, pkg in deps.items():
            try:
                __import__(mod)
            except ImportError:
                missing.append(pkg)

        if not missing:
            return EnvCheckResult(
                name="Python 依赖",
                available=True,
                version=f"Python {sys.version.split()[0]}",
                path=sys.executable,
                message="全部已安装",
            )

        return EnvCheckResult(
            name="Python 依赖",
            available=False,
            message=f"缺失: {', '.join(missing)}",
            install_hint=f"运行: pip install {' '.join(missing)}",
        )

    def _get_file_version(self, path: str) -> str:
        """获取文件版本"""
        try:
            from win32com.client import Dispatch
            ver_parser = Dispatch("Scripting.FileSystemObject")
            info = ver_parser.GetFileVersion(path)
            return info or "未知"
        except Exception:
            pass
        try:
            import ctypes
            result = ctypes.windll.version.GetFileVersionInfoSizeW(path, None)
            if result:
                res = ctypes.create_string_buffer(result)
                ctypes.windll.version.GetFileVersionInfoW(path, 0, result, res)
                return "已检测"
        except Exception:
            pass
        return "未知"

    def _get_ffmpeg_version(self, path: str) -> str:
        """获取 ffmpeg 版本"""
        try:
            result = subprocess.run(
                [path, "-version"],
                capture_output=True, text=True, timeout=5
            )
            first_line = result.stdout.split("\n")[0]
            return first_line.replace("ffmpeg version ", "").split(" ")[0]
        except Exception:
            return "未知"

    def _get_registry_value(self, key_path: str, value_name: str) -> Optional[str]:
        """读取注册表值"""
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path)
            value, _ = winreg.QueryValueEx(key, value_name)
            winreg.CloseKey(key)
            return str(value)
        except Exception:
            return None

    def save_report(self, output_path: str, report: Optional[EnvReport] = None) -> str:
        """保存检测报告"""
        rpt = report or self.report
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(rpt.to_dict(), f, ensure_ascii=False, indent=2)
        return output_path


def check_environment(config: Optional[Dict[str, Any]] = None) -> EnvReport:
    """便捷函数：执行全部环境检测"""
    checker = EnvChecker(config)
    return checker.check_all()


def check_davinci_resolve() -> EnvCheckResult:
    """便捷函数：仅检测 DaVinci Resolve"""
    checker = EnvChecker()
    return checker.check_davinci()


if __name__ == "__main__":
    print("=" * 60)
    print("ai-video-editor 环境检测")
    print("=" * 60)
    report = check_environment()
    print(report.to_markdown())
