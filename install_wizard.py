"""
一键安装与环境配置向导 v1.0
自动检测环境、安装依赖、生成配置、验证结果

使用方法：
    python install_wizard.py
    python install_wizard.py --check    # 仅检测不安装
    python install_wizard.py --fix      # 自动修复缺失项
"""
import os
import sys
import json
import shutil
import subprocess
import platform
from typing import Dict, List, Tuple, Optional

# 颜色输出
class Color:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'

def cprint(text, color=''):
    print(f"{color}{text}{Color.END}")

# 技能根目录
SKILL_ROOT = os.path.dirname(os.path.abspath(__file__))


class EnvironmentChecker:
    """环境检测器"""

    def __init__(self):
        self.results = {}
        self.warnings = []
        self.errors = []

    def check_python(self) -> Dict:
        """检测Python环境"""
        version = sys.version.split()[0]
        major, minor = map(int, version.split('.')[:2])
        ok = (major >= 3 and minor >= 10)
        result = {
            "name": "Python",
            "version": version,
            "path": sys.executable,
            "status": "ok" if ok else "error",
            "required": ">= 3.10",
        }
        if not ok:
            self.errors.append(f"Python版本过低: {version}，需要 >= 3.10")
        return result

    def check_pip_packages(self) -> Dict:
        """检测Python依赖包"""
        required = {
            "requests": "requests",
            "PIL": "pillow",
        }
        optional = {
            "numpy": "numpy",
            "websocket": "websocket-client",
            "aiohttp": "aiohttp",
        }
        missing_required = []
        missing_optional = []
        installed = {}

        for module, package in required.items():
            try:
                mod = __import__(module)
                installed[package] = getattr(mod, '__version__', 'unknown')
            except ImportError:
                missing_required.append(package)

        for module, package in optional.items():
            try:
                __import__(module)
            except ImportError:
                missing_optional.append(package)

        status = "ok" if not missing_required else "error"
        if missing_required:
            self.errors.append(f"缺少必需依赖: {', '.join(missing_required)}")
        if missing_optional:
            self.warnings.append(f"缺少可选依赖: {', '.join(missing_optional)}")

        return {
            "name": "Python依赖",
            "installed": installed,
            "missing_required": missing_required,
            "missing_optional": missing_optional,
            "status": status,
        }

    def check_jianying(self) -> Dict:
        """检测剪映"""
        # 常见安装路径
        candidates = [
            r"C:\JianyingPro_5.9\JianyingPro.exe",
            r"C:\Program Files\JianyingPro\JianyingPro.exe",
            r"C:\Program Files (x86)\JianyingPro\JianyingPro.exe",
            os.path.expanduser(r"~\AppData\Local\JianyingPro\JianyingPro.exe"),
        ]
        found = None
        for path in candidates:
            if os.path.exists(path):
                found = path
                break

        # 检测草稿目录
        draft_dirs = [
            r"D:\JianyingProDrafts\JianyingPro Drafts",
            os.path.expanduser(r"~\AppData\Local\JianyingPro\User Data\Projects\com.lveditor.draft"),
        ]
        draft_dir = None
        for d in draft_dirs:
            if os.path.exists(d):
                draft_dir = d
                break

        status = "ok" if found else "warning"
        if not found:
            self.warnings.append("未检测到剪映，部分功能不可用（需要剪映5.9）")

        return {
            "name": "剪映",
            "path": found,
            "draft_dir": draft_dir,
            "status": status,
            "required": "5.9 (推荐)",
        }

    def check_comfyui(self) -> Dict:
        """检测ComfyUI"""
        candidates = [
            r"D:\Ai\ComfyUI-aki-v3.2\ComfyUI\main.py",
            r"C:\ComfyUI\main.py",
            r"D:\ComfyUI\main.py",
        ]
        found = None
        for path in candidates:
            if os.path.exists(path):
                found = os.path.dirname(path)
                break

        # 检测API是否可访问
        api_ok = False
        try:
            import requests
            resp = requests.get("http://127.0.0.1:8188/system_stats", timeout=2)
            api_ok = resp.status_code == 200
        except:
            pass

        status = "ok" if (found and api_ok) else ("warning" if found else "error")
        if not found:
            self.warnings.append("未检测到ComfyUI，AI素材生成功能不可用")
        elif not api_ok:
            self.warnings.append("ComfyUI未启动，AI素材生成功能暂不可用（启动后自动恢复）")

        return {
            "name": "ComfyUI",
            "path": found,
            "api": "http://127.0.0.1:8188",
            "api_running": api_ok,
            "status": status,
        }

    def check_blender(self) -> Dict:
        """检测Blender"""
        candidates = [
            r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 4.1\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender\blender.exe",
        ]
        found = None
        for path in candidates:
            if os.path.exists(path):
                found = path
                break

        status = "ok" if found else "warning"
        if not found:
            self.warnings.append("未检测到Blender，3D特效功能不可用（可选）")

        return {
            "name": "Blender",
            "path": found,
            "status": status,
            "required": "5.0+ (可选)",
        }

    def check_ffmpeg(self) -> Dict:
        """检测ffmpeg"""
        candidates = [
            r"D:\Ai\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe",
            r"C:\ffmpeg\bin\ffmpeg.exe",
        ]
        found = None
        for path in candidates:
            if os.path.exists(path):
                found = path
                break

        # 尝试PATH中查找
        if not found:
            found = shutil.which("ffmpeg")

        status = "ok" if found else "warning"
        if not found:
            self.warnings.append("未检测到ffmpeg，质量门音频检测功能受限（可选）")

        return {
            "name": "ffmpeg",
            "path": found,
            "status": status,
            "required": "latest (可选)",
        }

    def check_all(self) -> Dict:
        """执行全部检测"""
        cprint("\n" + "="*60, Color.BOLD)
        cprint("🔍 环境检测", Color.CYAN + Color.BOLD)
        cprint("="*60, Color.BOLD)

        checks = [
            self.check_python(),
            self.check_pip_packages(),
            self.check_jianying(),
            self.check_comfyui(),
            self.check_blender(),
            self.check_ffmpeg(),
        ]

        for check in checks:
            status_icon = {"ok": "✅", "warning": "⚠️", "error": "❌"}[check["status"]]
            status_color = {"ok": Color.GREEN, "warning": Color.YELLOW, "error": Color.RED}[check["status"]]
            version = check.get("version", "")
            path = check.get("path", "") or check.get("api", "") or ""
            path_short = path if len(path) < 50 else path[:47] + "..."
            cprint(f"  {status_icon} {check['name']:12s} {version:10s} {path_short}", status_color)

        self.results = {c["name"]: c for c in checks}

        # 汇总
        ok_count = sum(1 for c in checks if c["status"] == "ok")
        warn_count = sum(1 for c in checks if c["status"] == "warning")
        err_count = sum(1 for c in checks if c["status"] == "error")

        cprint(f"\n📊 检测结果: {ok_count}项通过, {warn_count}项警告, {err_count}项错误", Color.BOLD)

        if self.warnings:
            cprint("\n⚠️ 警告:", Color.YELLOW)
            for w in self.warnings:
                cprint(f"   - {w}", Color.YELLOW)

        if self.errors:
            cprint("\n❌ 错误:", Color.RED)
            for e in self.errors:
                cprint(f"   - {e}", Color.RED)

        return {
            "checks": self.results,
            "summary": {"ok": ok_count, "warning": warn_count, "error": err_count},
            "warnings": self.warnings,
            "errors": self.errors,
        }


class InstallWizard:
    """安装向导"""

    def __init__(self):
        self.checker = EnvironmentChecker()

    def install_dependencies(self) -> bool:
        """安装Python依赖"""
        cprint("\n" + "="*60, Color.BOLD)
        cprint("📦 安装Python依赖", Color.CYAN + Color.BOLD)
        cprint("="*60, Color.BOLD)

        packages = ["requests", "pillow", "numpy"]
        cprint(f"  正在安装: {', '.join(packages)}", Color.BLUE)

        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "--upgrade"] + packages,
                capture_output=True, text=True, timeout=120
            )
            if result.returncode == 0:
                cprint("  ✅ 依赖安装成功", Color.GREEN)
                return True
            else:
                cprint(f"  ❌ 依赖安装失败: {result.stderr[:200]}", Color.RED)
                return False
        except Exception as e:
            cprint(f"  ❌ 依赖安装异常: {e}", Color.RED)
            return False

    def generate_env(self) -> str:
        """生成.env配置文件"""
        cprint("\n" + "="*60, Color.BOLD)
        cprint("⚙️  生成配置文件", Color.CYAN + Color.BOLD)
        cprint("="*60, Color.BOLD)

        env_path = os.path.join(SKILL_ROOT, ".env")
        example_path = os.path.join(SKILL_ROOT, ".env.example")

        # 检测到的路径
        comfyui_path = self.checker.results.get("ComfyUI", {}).get("path", "")
        jianying_path = self.checker.results.get("剪映", {}).get("path", "")
        blender_path = self.checker.results.get("Blender", {}).get("path", "")
        ffmpeg_path = self.checker.results.get("ffmpeg", {}).get("path", "")
        draft_dir = self.checker.results.get("剪映", {}).get("draft_dir", "")

        env_content = f"""# AI Video Editor 配置文件
# 自动生成于 {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

# ComfyUI 配置
COMFYUI_URL=http://127.0.0.1:8188
COMFYUI_PATH={comfyui_path or 'D:\\\\Ai\\\\ComfyUI-aki-v3.2\\\\ComfyUI'}

# 剪映配置
JIANYING_PATH={jianying_path or 'C:\\\\JianyingPro_5.9\\\\JianyingPro.exe'}
JIANYING_DRAFT_DIR={draft_dir or 'D:\\\\JianyingProDrafts\\\\JianyingPro Drafts'}

# Blender 配置（可选）
BLENDER_PATH={blender_path or ''}

# ffmpeg 配置（可选）
FFMPEG_PATH={ffmpeg_path or ''}

# 输出配置
OUTPUT_DIR=./output
DEFAULT_WIDTH=1080
DEFAULT_HEIGHT=1920
DEFAULT_FPS=30

# 质量门配置
QUALITY_GATE_ENABLED=true
FRAME_ALIGN_ENABLED=true
"""

        with open(env_path, 'w', encoding='utf-8') as f:
            f.write(env_content)

        cprint(f"  ✅ 配置文件已生成: {env_path}", Color.GREEN)
        cprint(f"  📝 包含: ComfyUI/剪映/Blender/ffmpeg 路径", Color.BLUE)
        return env_path

    def verify_installation(self) -> bool:
        """验证安装"""
        cprint("\n" + "="*60, Color.BOLD)
        cprint("✅ 安装验证", Color.CYAN + Color.BOLD)
        cprint("="*60, Color.BOLD)

        all_ok = True

        # 验证核心模块可导入
        test_modules = [
            ("cap_script_quality", "剧本质量引擎"),
            ("cap_promo_generator", "宣传视频生成器"),
        ]
        sys.path.insert(0, os.path.join(SKILL_ROOT, "capabilities"))
        for module, name in test_modules:
            try:
                __import__(module)
                cprint(f"  ✅ {name} 可正常导入", Color.GREEN)
            except Exception as e:
                cprint(f"  ❌ {name} 导入失败: {e}", Color.RED)
                all_ok = False

        # 验证.env存在
        env_path = os.path.join(SKILL_ROOT, ".env")
        if os.path.exists(env_path):
            cprint("  ✅ 配置文件存在", Color.GREEN)
        else:
            cprint("  ⚠️ 配置文件不存在", Color.YELLOW)
            all_ok = False

        return all_ok

    def run(self, fix=False):
        """运行安装向导"""
        cprint("\n" + "🎬"*30, Color.CYAN)
        cprint("  AI Video Editor 一键安装向导", Color.CYAN + Color.BOLD)
        cprint("🎬"*30, Color.CYAN)

        # Step 1: 环境检测
        report = self.checker.check_all()

        if not fix:
            cprint("\n💡 提示: 使用 --fix 参数自动安装依赖并生成配置", Color.YELLOW)
            return report

        # Step 2: 安装依赖
        if self.checker.errors or any(p.get("missing_required") for p in [self.checker.results.get("Python依赖", {})]):
            self.install_dependencies()
        else:
            cprint("\n  ✅ 依赖已满足，跳过安装", Color.GREEN)

        # Step 3: 生成配置
        self.generate_env()

        # Step 4: 验证
        success = self.verify_installation()

        # 最终报告
        cprint("\n" + "="*60, Color.BOLD)
        if success:
            cprint("🎉 安装完成！所有核心功能可用", Color.GREEN + Color.BOLD)
            cprint("\n下一步:", Color.BOLD)
            cprint("  1. 启动剪映5.9", Color.BLUE)
            cprint("  2. 启动ComfyUI（如需AI素材）", Color.BLUE)
            cprint("  3. 运行用户工作台: python user_workbench/server.py", Color.BLUE)
            cprint("  4. 打开浏览器访问: http://localhost:8080", Color.BLUE)
        else:
            cprint("⚠️ 安装完成，但部分功能需要手动配置", Color.YELLOW + Color.BOLD)
            cprint("  请查看上方警告信息", Color.YELLOW)
        cprint("="*60, Color.BOLD)

        return report


def main():
    import argparse
    parser = argparse.ArgumentParser(description="AI Video Editor 一键安装向导")
    parser.add_argument("--check", action="store_true", help="仅检测环境，不安装")
    parser.add_argument("--fix", action="store_true", help="自动安装依赖并生成配置")
    args = parser.parse_args()

    wizard = InstallWizard()
    if args.check:
        wizard.checker.check_all()
    else:
        wizard.run(fix=args.fix or not args.check)


if __name__ == "__main__":
    main()
