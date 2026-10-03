"""
导演引擎统一入口（Director Engine）
系统核心：读懂人类剧本 → 翻译成机器指令 → 指挥调度执行

一句话生成视频：
    from director_engine import DirectorEngine
    engine = DirectorEngine()
    result = engine.generate(
        script="豆包在头像框里开心地比耶，突然被机器人打了一拳...",
        title="豆包被打",
        duration=20,
    )
    print(result["instruction_sequence_path"])
    print(result["execution_report_path"])
"""

import os
import json
from typing import Dict, Any, Optional

from script_parser import ScriptParser
from instruction_translator import InstructionTranslator
from central_orchestrator import CentralOrchestrator


class DirectorEngine:
    """
    导演引擎：P23解析 → P24翻译 → P25调度

    输入：自然语言剧本
    输出：指令序列JSON + 执行报告
    """

    def __init__(self, work_dir: str = None):
        self.work_dir = work_dir or os.path.join(
            os.path.expanduser("~"), "Videos", "剪映导出",
            "Doubao_Jianying-editor", "director_engine_output"
        )
        os.makedirs(self.work_dir, exist_ok=True)

        self.parser = ScriptParser()
        self.translator = InstructionTranslator()
        self.orchestrator = CentralOrchestrator(work_dir=self.work_dir)

        self.last_parsed = None
        self.last_sequence = None
        self.last_report = None

    def generate(
        self,
        script: str,
        title: str = "未命名",
        duration: float = 20.0,
        style: str = "通用",
        dry_run: bool = True,
        output_dir: str = None,
    ) -> Dict[str, Any]:
        """
        一键生成：剧本 → 分镜 → 指令 → 调度

        Args:
            script: 自然语言剧本
            title: 项目标题
            duration: 目标时长（秒）
            style: 视频风格
            dry_run: True=只生成指令不实际执行，False=实际执行
            output_dir: 输出目录

        Returns:
            {
                "title": 项目标题,
                "parsed_script": 分镜JSON,
                "instruction_sequence": 指令序列,
                "execution_report": 执行报告,
                "parsed_script_path": 分镜文件路径,
                "instruction_sequence_path": 指令序列文件路径,
                "execution_report_path": 执行报告文件路径,
            }
        """
        out_dir = output_dir or self.work_dir
        os.makedirs(out_dir, exist_ok=True)

        print(f"\n{'='*60}")
        print(f"导演引擎启动: {title}")
        print(f"{'='*60}")

        # ===== P23: 剧本解析 =====
        print(f"\n[P23] 剧本结构化解析...")
        parsed = self.parser.parse(
            script_text=script,
            title=title,
            duration=duration,
            style=style,
        )
        self.last_parsed = parsed
        self.parser.print_summary()

        parsed_path = os.path.join(out_dir, f"{title}_parsed.json")
        with open(parsed_path, "w", encoding="utf-8") as f:
            json.dump(parsed, f, ensure_ascii=False, indent=2)
        print(f"  分镜JSON: {parsed_path}")

        # ===== P24: 指令翻译 =====
        print(f"\n[P24] 指令翻译...")
        sequence = self.translator.translate(parsed)
        self.last_sequence = sequence
        self.translator.print_summary()

        instr_path = os.path.join(out_dir, f"{title}_instructions.json")
        self.translator.save_json(instr_path)

        # ===== P25: 中央调度 =====
        print(f"\n[P25] 中央调度({'模拟执行' if dry_run else '实际执行'})...")
        self.orchestrator.build_tasks_from_instructions(self.translator.to_json())
        report = self.orchestrator.execute(dry_run=dry_run)
        self.last_report = report

        report_path = os.path.join(out_dir, f"{title}_report.json")
        self.orchestrator.save_report(report_path)

        # ===== 结果汇总 =====
        result = {
            "title": title,
            "duration": duration,
            "style": style,
            "parsed_script": parsed,
            "instruction_sequence": self.translator.to_json(),
            "execution_report": {
                "total_tasks": report.total_tasks,
                "success_count": report.success_count,
                "failed_count": report.failed_count,
                "skipped_count": report.skipped_count,
                "total_duration": report.total_duration,
            },
            "parsed_script_path": parsed_path,
            "instruction_sequence_path": instr_path,
            "execution_report_path": report_path,
            "stats": {
                "characters": len(parsed.get("characters", [])),
                "scenes": len(parsed.get("scenes", [])),
                "tts_instructions": len(sequence.tts_instructions),
                "keyframe_instructions": len(sequence.keyframe_instructions),
                "audio_instructions": len(sequence.audio_instructions),
                "effect_instructions": len(sequence.effect_instructions),
                "text_instructions": len(sequence.text_instructions),
                "total_tasks": report.total_tasks,
            },
        }

        print(f"\n{'='*60}")
        print(f"导演引擎完成: {title}")
        print(f"  角色: {result['stats']['characters']}个")
        print(f"  场景: {result['stats']['scenes']}个")
        print(f"  TTS指令: {result['stats']['tts_instructions']}条")
        print(f"  关键帧指令: {result['stats']['keyframe_instructions']}条")
        print(f"  音轨指令: {result['stats']['audio_instructions']}条")
        print(f"  调度任务: {result['stats']['total_tasks']}个")
        print(f"  输出目录: {out_dir}")
        print(f"{'='*60}\n")

        return result

    def parse_only(self, script: str, title: str = "未命名",
                   duration: float = 20.0, style: str = "通用") -> Dict:
        """只执行P23解析"""
        parsed = self.parser.parse(script, title=title, duration=duration, style=style)
        self.last_parsed = parsed
        return parsed

    def translate_only(self, parsed_script: Dict) -> Dict:
        """只执行P24翻译"""
        sequence = self.translator.translate(parsed_script)
        self.last_sequence = sequence
        return self.translator.to_json()

    def execute_only(self, instruction_sequence: Dict, dry_run: bool = True):
        """只执行P25调度"""
        self.orchestrator.build_tasks_from_instructions(instruction_sequence)
        report = self.orchestrator.execute(dry_run=dry_run)
        self.last_report = report
        return report


if __name__ == "__main__":
    # 演示：一键生成
    engine = DirectorEngine()

    test_script = """
    豆包在抖音主页的头像框里开心地比耶，向大家打招呼说大家好呀。
    突然机器人一拳打在豆包脸上，豆包被打得飞出去，委屈地说好痛啊。
    豆包从头像框里掉出来，摔在作品列表上。
    女杀手出现，一脚把豆包踢回头像框里。
    豆包爬回头像框，得意地比耶，结果又被机器人打了一拳。
    """

    result = engine.generate(
        script=test_script,
        title="豆包被打_导演引擎演示",
        duration=20,
        style="搞笑短剧",
        dry_run=True,
    )

    print(f"\n✅ 演示完成")
    print(f"   分镜JSON: {result['parsed_script_path']}")
    print(f"   指令序列: {result['instruction_sequence_path']}")
    print(f"   执行报告: {result['execution_report_path']}")
