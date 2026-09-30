"""
环境检测模块
检测 ai-video-editor 运行所需的所有外部依赖，首次使用时提示用户安装缺失组件。

检测项：
- Blender（3D特效合成）
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

    # Blender 常见安装路径
    BLENDER_PATHS = [
        r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 4.1\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 4.0\blender.exe",
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
        self.report.results.append(self._check_blender())
        self.report.results.append(self._check_comfyui())
        self.report.results.append(self._check_jianying())
        self.report.results.append(self._check_ffmpeg())
        self.report.results.append(self._check_python_deps())

        # 汇总
        self.report.missing = [r.name for r in self.report.results if not r.available]
        self.report.all_passed = len(self.report.missing) == 0

        return self.report

    def check_blender(self) -> EnvCheckResult:
        """仅检测 Blender"""
        return self._check_blender()

    def _check_blender(self) -> EnvCheckResult:
        """检测 Blender（3D特效合成）"""
        for path in self.BLENDER_PATHS:
            if os.path.exists(path):
                version = self._get_file_version(path)
                return EnvCheckResult(
                    name="Blender",
                    available=True,
                    version=version,
                    path=path,
                    message="已安装",
                )
        return EnvCheckResult(
            name="Blender",
            available=False,
            message="未安装",
            install_url="https://www.blender.org/download/",
            install_hint="下载免费版 Blender（约350MB），用于3D文字动画、粒子特效、高级合成。",
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


def check_blender() -> EnvCheckResult:
    """便捷函数：仅检测 Blender"""
    checker = EnvChecker()
    return checker.check_blender()


@dataclass
class EnvStrategy:
    """环境适配策略"""
    mode: str = "full"  # full / standard / minimal / basic
    description: str = ""
    enabled_features: List[str] = field(default_factory=list)
    disabled_features: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    install_commands: Dict[str, str] = field(default_factory=dict)

    def to_markdown(self) -> str:
        lines = ["## 系统工作策略", ""]
        lines.append(f"**模式**: {self.mode}")
        lines.append(f"**说明**: {self.description}")
        lines.append("")
        if self.enabled_features:
            lines.append("### ✅ 可用功能")
            for f in self.enabled_features:
                lines.append(f"- {f}")
            lines.append("")
        if self.disabled_features:
            lines.append("### ⚠️ 受限功能")
            for f in self.disabled_features:
                lines.append(f"- {f}")
            lines.append("")
        if self.warnings:
            lines.append("### ⚠️ 注意事项")
            for w in self.warnings:
                lines.append(f"- {w}")
            lines.append("")
        if self.install_commands:
            lines.append("### 📦 安装触发指令")
            lines.append("需要安装缺失组件时，发送以下指令给助手：")
            lines.append("")
            for name, cmd in self.install_commands.items():
                lines.append(f"- **{name}**: `{cmd}`")
            lines.append("")
        return "\n".join(lines)


class EnvStrategyGenerator:
    """环境策略生成器"""

    # 功能与依赖映射
    FEATURE_DEPS = {
        "剪映工程合成": ["剪映", "ffmpeg"],
        "AI视频生成(LTX/混元)": ["ComfyUI"],
        "AI图片生成": ["ComfyUI"],
        "Blender 3D特效(粒子/文字)": ["Blender"],
        "Blender片头生成": ["Blender"],
        "ffmpeg动效(Ken Burns/转场)": ["ffmpeg"],
        "素材处理(格式转换/抽帧)": ["ffmpeg"],
        "图片处理(轮廓/渐变生成)": ["Python 依赖"],
        "字幕烧录": ["ffmpeg", "Python 依赖"],
    }

    def generate(self, report: EnvReport) -> EnvStrategy:
        """根据检测报告生成适配策略"""
        available = {r.name for r in report.results if r.available}
        missing = {r.name for r in report.results if not r.available}

        # 判断模式
        if not missing:
            mode = "full"
            description = "全部依赖已安装，所有功能可用"
        elif "剪映" not in missing and "ffmpeg" not in missing and "Python 依赖" not in missing:
            mode = "standard"
            description = "核心剪辑功能可用，AI/Blender特效需安装对应依赖"
        elif "剪映" not in missing and "ffmpeg" not in missing:
            mode = "minimal"
            description = "基础剪辑可用，图片处理和AI特效受限"
        else:
            mode = "basic"
            description = "核心依赖缺失，仅能进行创意规划和分镜设计"

        # 计算可用/受限功能
        enabled = []
        disabled = []
        for feature, deps in self.FEATURE_DEPS.items():
            if all(d in available for d in deps):
                enabled.append(feature)
            else:
                missing_deps = [d for d in deps if d not in available]
                disabled.append(f"{feature} (缺失: {', '.join(missing_deps)})")

        # 警告
        warnings = []
        if "ComfyUI" in missing:
            warnings.append("未安装ComfyUI，AI视频/图片生成功能不可用。可使用剪映内置特效和ffmpeg动效替代。")
        if "Blender" in missing:
            warnings.append("未安装Blender，3D文字动画、粒子特效、高级合成等功能不可用。可使用剪映内置特效替代。")
        if "剪映" in missing:
            warnings.append("未安装剪映，无法进行工程合成和导出。仅能进行创意规划、分镜设计和素材准备。")
        if "ffmpeg" in missing:
            warnings.append("未安装ffmpeg，视频处理、格式转换、字幕烧录等功能不可用。")

        # 安装指令
        install_commands = {}
        for r in report.results:
            if not r.available:
                if r.name == "Python 依赖":
                    install_commands[r.name] = "安装Python依赖"
                elif r.name == "ffmpeg":
                    install_commands[r.name] = "安装ffmpeg"
                elif r.name == "剪映":
                    install_commands[r.name] = "安装剪映5.9"
                elif r.name == "ComfyUI":
                    install_commands[r.name] = "安装ComfyUI"
                elif r.name == "Blender":
                    install_commands[r.name] = "安装Blender"

        return EnvStrategy(
            mode=mode,
            description=description,
            enabled_features=enabled,
            disabled_features=disabled,
            warnings=warnings,
            install_commands=install_commands,
        )


def check_environment_with_strategy(config: Optional[Dict[str, Any]] = None) -> Tuple[EnvReport, EnvStrategy]:
    """便捷函数：执行环境检测并生成策略"""
    report = check_environment(config)
    generator = EnvStrategyGenerator()
    strategy = generator.generate(report)
    return report, strategy


def generate_detailed_report(report: EnvReport, strategy: EnvStrategy) -> str:
    """生成详细环境报告（含策略分析和安装指引）"""
    lines = []
    lines.append(report.to_markdown())
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(strategy.to_markdown())
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 用户选择")
    lines.append("")
    lines.append("请选择以下操作：")
    lines.append("")
    lines.append("1. **继续使用当前环境** - 接受功能限制，使用可用功能完成任务")
    lines.append("2. **安装缺失依赖** - 发送上方对应安装指令，助手将引导安装")
    lines.append("3. **稍后再问** - 本次跳过，下次运行时重新检测")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 各组件功能影响详解")
    lines.append("")
    lines.append("### 剪映（核心依赖）")
    lines.append("- 影响：工程创建、片段编排、转场、字幕、特效、导出")
    lines.append("- 替代：无（必须安装）")
    lines.append("")
    lines.append("### ffmpeg（核心依赖）")
    lines.append("- 影响：视频格式转换、抽帧、Ken Burns动效、转场合成、字幕烧录")
    lines.append("- 替代：剪映内置部分功能，但批量处理和自定义动效受限")
    lines.append("")
    lines.append("### ComfyUI（可选依赖）")
    lines.append("- 影响：AI视频生成（LTX-2.5/混元）、AI图片生成、图生视频、首尾帧视频")
    lines.append("- 替代：使用用户提供的素材图片/视频，或使用ffmpeg动效")
    lines.append("")
    lines.append("### Blender（可选依赖）")
    lines.append("- 影响：3D文字动画、粒子特效、高级合成、Blender 3D片头")
    lines.append("- 替代：剪映内置特效（粒子/光效/文字动画），效果略逊但够用")
    lines.append("")
    lines.append("### Python 依赖（核心依赖）")
    lines.append("- 影响：图片处理（轮廓生成、渐变、纯色图）、数据处理、API调用")
    lines.append("- 替代：无（必须安装）")
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    print("=" * 60)
    print("ai-video-editor 环境检测")
    print("=" * 60)
    report, strategy = check_environment_with_strategy()
    print(generate_detailed_report(report, strategy))
