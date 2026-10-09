#!/usr/bin/env python3
"""
AI Video Editor 冒烟测试套件
快速验证核心模块可用性，每次修改后运行

用法:
    python test_smoke.py              # 运行所有测试
    python test_smoke.py --quick      # 快速模式（仅语法+导入）
    python test_smoke.py --module xxx # 测试指定模块
"""
import argparse
import importlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict

# 路径
RUNTIME = Path(__file__).parent
PROJECT_ROOT = RUNTIME.parent.parent

# 核心模块列表（必须可导入）
CORE_MODULES = [
    "paths",
    "director_engine",
    "script_parser",
    "instruction_translator",
    "central_orchestrator",
    "jianying_executor",
    "audio_mixer",
    "auto_beat",
    "mask_keyframe",
    "remotion_executor",
    "effect_library",
    "script_enhancer",
]

# 语法检查范围
SYNTAX_DIRS = [RUNTIME]


class SmokeTest:
    """冒烟测试执行器"""

    def __init__(self):
        self.results = []
        self.passed = 0
        self.failed = 0
        self.skipped = 0

    def _record(self, name: str, passed: bool, detail: str = "", skipped: bool = False):
        status = "✅" if passed else ("⏭️" if skipped else "❌")
        self.results.append((name, passed, skipped, detail))
        if skipped:
            self.skipped += 1
        elif passed:
            self.passed += 1
        else:
            self.failed += 1
        print(f"  {status} {name}" + (f" - {detail}" if detail else ""))

    def test_syntax(self) -> bool:
        """测试1: 所有Python文件语法检查"""
        print("\n[测试1] 语法检查")
        all_pass = True
        total = 0
        for d in SYNTAX_DIRS:
            for f in Path(d).rglob("*.py"):
                if "__pycache__" in str(f):
                    continue
                total += 1
                result = subprocess.run(
                    [sys.executable, "-m", "py_compile", str(f)],
                    capture_output=True, text=True
                )
                if result.returncode != 0:
                    all_pass = False
                    print(f"  ❌ {f.name}: {result.stderr[:100]}")
        self._record(f"语法检查 ({total}文件)", all_pass, f"{total}个文件")
        return all_pass

    def test_imports(self) -> bool:
        """测试2: 核心模块导入"""
        print("\n[测试2] 核心模块导入")
        all_pass = True
        sys.path.insert(0, str(RUNTIME))
        for mod_name in CORE_MODULES:
            try:
                importlib.import_module(mod_name)
                self._record(f"导入 {mod_name}", True)
            except Exception as e:
                all_pass = False
                self._record(f"导入 {mod_name}", False, str(e)[:80])
        return all_pass

    def test_paths(self) -> bool:
        """测试3: 路径配置"""
        print("\n[测试3] 路径配置")
        try:
            sys.path.insert(0, str(RUNTIME))
            from paths import PATHS
            required = ["project_root", "runtime_dir", "jianying_drafts_root"]
            missing = [k for k in required if k not in PATHS]
            if missing:
                self._record("路径配置", False, f"缺少: {missing}")
                return False
            # 检查关键路径存在
            existing = 0
            for key in ["jianying_drafts_root", "jianying_skill_root", "skill_root"]:
                p = PATHS.get(key, "")
                if p and os.path.exists(p):
                    existing += 1
            self._record("路径配置", True, f"{len(PATHS)}个路径, {existing}个存在")
            return True
        except Exception as e:
            self._record("路径配置", False, str(e)[:80])
            return False

    def test_jianying_executor(self) -> bool:
        """测试4: 剪映执行器基本功能"""
        print("\n[测试4] 剪映执行器")
        try:
            sys.path.insert(0, str(RUNTIME))
            from jianying_executor import JianyingExecutor
            # 仅检查类可实例化，不实际创建工程
            self._record("JianyingExecutor类", True, "可导入")
            return True
        except Exception as e:
            self._record("JianyingExecutor类", False, str(e)[:80])
            return False

    def test_remotion_executor(self) -> bool:
        """测试5: Remotion执行器"""
        print("\n[测试5] Remotion执行器")
        try:
            sys.path.insert(0, str(RUNTIME))
            from remotion_executor import RemotionExecutor
            exe = RemotionExecutor()
            self._record("RemotionExecutor", True, f"可用={exe.available}")
            return True
        except Exception as e:
            self._record("RemotionExecutor", False, str(e)[:80])
            return False

    def test_audio_mixer(self) -> bool:
        """测试6: 音频混音器"""
        print("\n[测试6] 音频混音器")
        try:
            sys.path.insert(0, str(RUNTIME))
            from audio_mixer import AudioMixer
            self._record("AudioMixer", True, "可导入")
            return True
        except Exception as e:
            self._record("MultiTrackMixer", False, str(e)[:80])
            return False

    def test_mask_keyframe(self) -> bool:
        """测试7: 蒙版关键帧工具"""
        print("\n[测试7] 蒙版关键帧")
        try:
            sys.path.insert(0, str(RUNTIME))
            from mask_keyframe import MASK_KF_TYPES, CURVE_PRESETS, apply_mask_expand
            self._record("mask_keyframe", True,
                        f"{len(MASK_KF_TYPES)}属性, {len(CURVE_PRESETS)}曲线")
            return True
        except Exception as e:
            self._record("mask_keyframe", False, str(e)[:80])
            return False

    def test_config_files(self) -> bool:
        """测试8: 配置文件有效性"""
        print("\n[测试8] 配置文件")
        configs = [
            PROJECT_ROOT / "adapter_config.json",
            PROJECT_ROOT / "llm_config.json",
        ]
        all_pass = True
        for cfg in configs:
            if cfg.exists():
                try:
                    with open(cfg, "r", encoding="utf-8") as f:
                        json.load(f)
                    self._record(cfg.name, True)
                except Exception as e:
                    all_pass = False
                    self._record(cfg.name, False, str(e)[:60])
            else:
                self._record(cfg.name, True, "不存在(跳过)")
        return all_pass

    def test_external_tools(self) -> bool:
        """测试9: 外部工具可用性"""
        print("\n[测试9] 外部工具")
        tools = {
            "ffmpeg": ["-version"],
            "ffprobe": ["-version"],
            "node": ["--version"],
        }
        all_pass = True
        for tool, args in tools.items():
            try:
                result = subprocess.run([tool] + args, capture_output=True, text=True, timeout=10)
                version = result.stdout.split("\n")[0][:50] if result.stdout else ""
                self._record(tool, result.returncode == 0, version)
                if result.returncode != 0:
                    all_pass = False
            except FileNotFoundError:
                self._record(tool, False, "未安装")
                all_pass = False
            except Exception as e:
                self._record(tool, False, str(e)[:50])
                all_pass = False
        return all_pass

    def run(self, quick: bool = False, module: str = None) -> Dict:
        """运行所有测试"""
        start = time.time()
        print("=" * 60)
        print("AI Video Editor 冒烟测试")
        print("=" * 60)

        if module:
            # 只测试指定模块
            test_map = {
                "syntax": self.test_syntax,
                "imports": self.test_imports,
                "paths": self.test_paths,
                "jianying": self.test_jianying_executor,
                "remotion": self.test_remotion_executor,
                "audio": self.test_audio_mixer,
                "mask": self.test_mask_keyframe,
                "config": self.test_config_files,
                "tools": self.test_external_tools,
            }
            if module in test_map:
                test_map[module]()
            else:
                print(f"未知模块: {module}")
        else:
            self.test_syntax()
            self.test_imports()
            self.test_paths()
            if not quick:
                self.test_jianying_executor()
                self.test_remotion_executor()
                self.test_audio_mixer()
                self.test_mask_keyframe()
                self.test_config_files()
                self.test_external_tools()

        elapsed = time.time() - start
        print("\n" + "=" * 60)
        print(f"测试完成: {self.passed}通过, {self.failed}失败, {self.skipped}跳过")
        print(f"耗时: {elapsed:.1f}秒")
        print("=" * 60)

        return {
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
            "elapsed": round(elapsed, 1),
            "results": [
                {"name": n, "passed": p, "skipped": s, "detail": d}
                for n, p, s, d in self.results
            ],
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Video Editor 冒烟测试")
    parser.add_argument("--quick", action="store_true", help="快速模式")
    parser.add_argument("--module", help="测试指定模块")
    parser.add_argument("--json", action="store_true", help="输出JSON结果")
    args = parser.parse_args()

    tester = SmokeTest()
    result = tester.run(quick=args.quick, module=args.module)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))

    sys.exit(1 if result["failed"] > 0 else 0)
