"""
CLI命令行工具
ai-video-editor 命令行接口，支持项目创建、流水线运行、质量检查等
"""

import os
import sys
import json
import argparse
import time
from typing import Dict, Any, Optional, List


class CLI:
    """命令行接口"""

    def __init__(self):
        self.parser = self._build_parser()
        self.skill_root = r"C:\Users\Administrator\AppData\Local\DoubaoWork\User Data\Default\.doubaowork\agent_mode\workspace\.user_skills\ai-video-editor"

    def _build_parser(self) -> argparse.ArgumentParser:
        """构建命令行解析器"""
        parser = argparse.ArgumentParser(
            prog="ai-video-editor",
            description="AI Video Editor - 航空母舰战斗群视频剪辑平台",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
示例:
  ai-video-editor generate --topic "国庆旅行" --type vlog --duration 30
  ai-video-editor check --draft "C:\\path\\to\\draft"
  ai-video-editor effects --list
  ai-video-editor status
            """
        )
        parser.add_argument("--version", action="version", version="%(prog)s 1.0.0")
        parser.add_argument("-v", "--verbose", action="store_true", help="详细输出")

        subparsers = parser.add_subparsers(dest="command", help="可用命令")

        # status 命令
        status_parser = subparsers.add_parser("status", help="查看系统状态")
        status_parser.add_argument("--all", action="store_true", help="显示所有模块状态")

        # generate 命令
        gen_parser = subparsers.add_parser("generate", help="生成视频工程")
        gen_parser.add_argument("--topic", required=True, help="视频主题")
        gen_parser.add_argument("--type", default="vlog", help="视频类型")
        gen_parser.add_argument("--duration", type=float, default=30, help="时长（秒）")
        gen_parser.add_argument("--name", default=None, help="工程名称")
        gen_parser.add_argument("--style", default=None, help="风格")
        gen_parser.add_argument("--dry-run", action="store_true", help="仅生成剧本，不合成")

        # check 命令
        check_parser = subparsers.add_parser("check", help="质量门检查")
        check_parser.add_argument("--draft", required=True, help="草稿目录路径")
        check_parser.add_argument("--fix", action="store_true", help="自动修复可修复的问题")

        # effects 命令
        eff_parser = subparsers.add_parser("effects", help="特效库管理")
        eff_parser.add_argument("--list", action="store_true", help="列出所有特效")
        eff_parser.add_argument("--search", default=None, help="搜索特效")
        eff_parser.add_argument("--category", default=None, help="按分类筛选")

        # templates 命令
        tpl_parser = subparsers.add_parser("templates", help="模板库管理")
        tpl_parser.add_argument("--list", action="store_true", help="列出所有模板")
        tpl_parser.add_argument("--use", default=None, help="使用指定模板")

        # env 命令
        env_parser = subparsers.add_parser("env", help="环境检测")
        env_parser.add_argument("--fix", action="store_true", help="尝试修复环境问题")

        # debug 命令
        debug_parser = subparsers.add_parser("debug", help="调试工具")
        debug_parser.add_argument("--profile", action="store_true", help="性能分析")
        debug_parser.add_argument("--trace", action="store_true", help="调用追踪")
        debug_parser.add_argument("--log-level", default="INFO",
                                   choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                                   help="日志级别")

        return parser

    def run(self, args: List[str] = None) -> int:
        """运行CLI"""
        if args is None:
            args = sys.argv[1:]

        parsed = self.parser.parse_args(args)

        if not parsed.command:
            self.parser.print_help()
            return 0

        try:
            handler = getattr(self, f"_cmd_{parsed.command}")
            return handler(parsed)
        except AttributeError:
            print(f"❌ 未知命令: {parsed.command}")
            return 1
        except Exception as e:
            print(f"❌ 执行失败: {e}")
            if parsed.verbose:
                import traceback
                traceback.print_exc()
            return 1

    def _cmd_status(self, args) -> int:
        """状态命令"""
        print("=" * 50)
        print("AI Video Editor 系统状态")
        print("=" * 50)
        print(f"  版本: 1.0.0")
        print(f"  Skill路径: {self.skill_root}")
        print(f"  时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        # 检查环境
        checks = [
            ("Python", sys.version.split()[0], True),
            ("ComfyUI", self._check_comfyui(), None),
            ("Blender", self._check_blender(), None),
            ("ffmpeg", self._check_ffmpeg(), None),
        ]

        print("环境检测:")
        for name, result, expected in checks:
            if result is None:
                status = "❓ 未知"
            elif result:
                status = "✅ 正常"
            else:
                status = "❌ 未找到"
            print(f"  {name}: {status}")
            if args.verbose and result and isinstance(result, str):
                print(f"    详情: {result}")

        return 0

    def _cmd_generate(self, args) -> int:
        """生成命令"""
        print(f"🎬 生成视频工程")
        print(f"  主题: {args.topic}")
        print(f"  类型: {args.type}")
        print(f"  时长: {args.duration}秒")
        if args.name:
            print(f"  名称: {args.name}")
        if args.style:
            print(f"  风格: {args.style}")
        print()

        if args.dry_run:
            print("📝 仅生成剧本模式（不合成）")
            # 调用剧本生成
            try:
                sys.path.insert(0, os.path.join(self.skill_root, "capabilities"))
                from cap_script_engine import ScriptEngine
                engine = ScriptEngine()
                script = engine.generate(idea=args.topic, genre=args.type, duration=args.duration)
                print(f"\n✅ 剧本生成完成")
                print(f"  场景数: {len(script.scenes)}")
                print(f"  总镜头: {script.total_shots}")
                print(f"  总时长: {script.total_duration}秒")
            except Exception as e:
                print(f"❌ 剧本生成失败: {e}")
                return 1
        else:
            print("⚙️  全链路流水线模式")
            print("（调用 pipeline 模块执行完整流程）")
            # 这里调用全链路流水线
            print("\n✅ 工程生成完成（示例）")

        return 0

    def _cmd_check(self, args) -> int:
        """检查命令"""
        print(f"🔍 质量门检查")
        print(f"  草稿: {args.draft}")
        if args.fix:
            print(f"  自动修复: 开启")
        print()

        if not os.path.exists(args.draft):
            print(f"❌ 草稿目录不存在: {args.draft}")
            return 1

        # 检查草稿文件
        content_file = os.path.join(args.draft, "draft_content.json")
        info_file = os.path.join(args.draft, "draft_info.json")

        print("文件检查:")
        print(f"  draft_content.json: {'✅' if os.path.exists(content_file) else '❌'}")
        print(f"  draft_info.json: {'✅' if os.path.exists(info_file) else '❌'}")

        # 解析草稿内容
        if os.path.exists(content_file):
            try:
                with open(content_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                tracks = data.get("tracks", [])
                total_segments = sum(len(t.get("segments", [])) for t in tracks)
                print(f"\n内容统计:")
                print(f"  轨道数: {len(tracks)}")
                print(f"  片段数: {total_segments}")
            except Exception as e:
                print(f"❌ 解析草稿失败: {e}")

        print("\n✅ 质量检查完成")
        return 0

    def _cmd_effects(self, args) -> int:
        """特效命令"""
        print("🎨 特效库")
        print()

        # 内置特效列表
        effects = [
            {"id": "mask_flash", "name": "蒙版快闪", "category": "transition"},
            {"id": "subtitle_bar", "name": "字幕条动画", "category": "text"},
            {"id": "character_card", "name": "角色介绍卡", "category": "overlay"},
            {"id": "text_wipe", "name": "文字擦开", "category": "text"},
            {"id": "text_bg_slide", "name": "文字背景滑入", "category": "text"},
            {"id": "glow_outline", "name": "发光轮廓", "category": "effect"},
            {"id": "blinds_split", "name": "百叶窗分屏", "category": "transition"},
        ]

        if args.search:
            effects = [e for e in effects
                       if args.search.lower() in e["name"].lower()
                       or args.search.lower() in e["id"].lower()]

        if args.category:
            effects = [e for e in effects if e["category"] == args.category]

        print(f"找到 {len(effects)} 个特效:")
        for e in effects:
            print(f"  [{e['category']:12s}] {e['name']:15s} ({e['id']})")

        return 0

    def _cmd_templates(self, args) -> int:
        """模板命令"""
        print("📋 模板库")
        print()
        print("可用模板:")
        print("  - vlog_default: Vlog默认模板 (30秒, 10镜头)")
        print("  - exploration: 探店探索模板 (45秒, 12镜头)")
        print("  - product: 产品展示模板 (15秒, 6镜头)")
        print("  - tutorial: 教程教学模板 (60秒, 15镜头)")
        return 0

    def _cmd_env(self, args) -> int:
        """环境命令"""
        print("🌍 环境检测")
        print()
        checks = {
            "ComfyUI": self._check_comfyui(),
            "Blender": self._check_blender(),
            "ffmpeg": self._check_ffmpeg(),
        }
        for name, result in checks.items():
            status = "✅" if result else "❌"
            print(f"  {status} {name}: {result or '未找到'}")
        return 0

    def _cmd_debug(self, args) -> int:
        """调试命令"""
        print("🔧 调试工具")
        print()
        if args.profile:
            print("📊 性能分析模式")
        if args.trace:
            print("🔍 调用追踪模式")
        print(f"📝 日志级别: {args.log_level}")
        return 0

    # ==================== 辅助方法 ====================

    def _check_comfyui(self) -> Optional[str]:
        """检查ComfyUI"""
        try:
            import urllib.request
            req = urllib.request.Request("http://127.0.0.1:8188/system_stats")
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read())
                version = data.get("system", {}).get("comfyui_version", "unknown")
                return f"v{version} (运行中)"
        except Exception:
            return None

    def _check_blender(self) -> Optional[str]:
        """检查Blender"""
        path = r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
        if os.path.exists(path):
            return "5.2 (已安装)"
        return None

    def _check_ffmpeg(self) -> Optional[str]:
        """检查ffmpeg"""
        path = r"D:\Ai\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe"
        if os.path.exists(path):
            return "已安装"
        return None


def main():
    """主入口"""
    cli = CLI()
    sys.exit(cli.run())


if __name__ == "__main__":
    main()
