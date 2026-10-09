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
    logger.info(result["instruction_sequence_path"])
    logger.info(result["execution_report_path"])
"""

import os
import json
from typing import Dict, Any

from script_parser import ScriptParser
from instruction_translator import InstructionTranslator
from central_orchestrator import CentralOrchestrator
from script_enhancer import ScriptEnhancer
from script_rewriter import ScriptRewriter, RewriteConstraints
from structured_script import health_check as script_health_check
import logging
logger = logging.getLogger(__name__)


class DirectorEngine:
    """
    导演引擎：P23解析 → P23增强 → P24翻译 → P25调度

    输入：自然语言剧本
    输出：指令序列JSON + 执行报告
    """

    def __init__(self, work_dir: str = None, use_llm: bool = True):
        self.work_dir = work_dir or os.path.join(
            r"D:\DobaoWork_Project\Ai_Video_Editor", "director_engine_output"
        )
        os.makedirs(self.work_dir, exist_ok=True)

        self.parser = ScriptParser()
        self.enhancer = ScriptEnhancer(use_llm=use_llm)
        self.rewriter = ScriptRewriter(use_llm=use_llm)
        self.translator = InstructionTranslator()
        self.orchestrator = CentralOrchestrator(work_dir=self.work_dir)

        self.last_parsed = None
        self.last_enhanced = None
        self.last_rewrite_result = None
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
        rewrite_mode: str = None,
        rewrite_constraints: RewriteConstraints = None,
    ) -> Dict[str, Any]:
        """
        一键生成：剧本 → 分镜 → 指令 → 调度

        Args:
            script: 自然语言剧本（或创意描述，当rewrite_mode=creative时）
            title: 项目标题
            duration: 目标时长（秒）
            style: 视频风格
            dry_run: True=只生成指令不实际执行，False=实际执行
            output_dir: 输出目录
            rewrite_mode: 剧本改写加工模式（None=不做改写，直接解析；"creative"=创意生成；"adapt"=改编改写）
            rewrite_constraints: 改写约束参数（RewriteConstraints对象，None则用默认）

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

        logger.info(f"\n{'='*60}")
        logger.info(f"导演引擎启动: {title}")
        if rewrite_mode:
            logger.info(f"  改写模式: {'创意生成' if rewrite_mode == 'creative' else '改编改写'}")
        logger.info(f"{'='*60}")

        # ===== 剧本改写加工（可选前置步骤）=====
        if rewrite_mode:
            logger.info(f"\n[P22+] 剧本改写加工...")
            constraints = rewrite_constraints or RewriteConstraints(
                style=style,
                duration=duration,
            )
            rewrite_result = self.rewriter.rewrite(
                input_text=script,
                mode=rewrite_mode,
                constraints=constraints,
                title=title,
            )
            self.last_rewrite_result = rewrite_result

            # 保存改写结果
            rewrite_path = os.path.join(out_dir, f"{title}_rewrite.json")
            rewrite_result.save(rewrite_path)
            logger.info(f"  改写结果: {rewrite_path}")

            # 用改写后的final_script直接进入P24翻译（改写内部已包含P23解析+增强）
            enhanced = rewrite_result.final_script
            parsed = rewrite_result.base_script
            self.last_parsed = parsed
            self.last_enhanced = enhanced

            parsed_path = os.path.join(out_dir, f"{title}_parsed.json")
            with open(parsed_path, "w", encoding="utf-8") as f:
                json.dump(parsed, f, ensure_ascii=False, indent=2)

            enhanced_path = os.path.join(out_dir, f"{title}_enhanced.json")
            with open(enhanced_path, "w", encoding="utf-8") as f:
                json.dump(enhanced, f, ensure_ascii=False, indent=2)
        else:
            # ===== P23: 剧本解析 =====
            logger.info(f"\n[P23] 剧本结构化解析...")
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
            logger.info(f"  分镜JSON: {parsed_path}")

            # ===== P23+: 深度语义增强 =====
            logger.info(f"\n[P23+] 深度语义增强...")
            enhanced = self.enhancer.enhance(parsed, raw_script=script)
            self.last_enhanced = enhanced

            enhanced_path = os.path.join(out_dir, f"{title}_enhanced.json")
            with open(enhanced_path, "w", encoding="utf-8") as f:
                json.dump(enhanced, f, ensure_ascii=False, indent=2)
            logger.info(f"  增强JSON: {enhanced_path}")
            if enhanced.get("structure"):
                logger.info(f"  剧情结构: {enhanced['structure'].get('summary', '')}")

        # ===== 质量门检查 =====
        logger.info(f"\n[质量门] 剧本质量检查...")
        quality_text = script
        if rewrite_mode and self.last_rewrite_result:
            quality_text = getattr(self.last_rewrite_result, 'final_script_text', None) or script
        try:
            quality_report = script_health_check(quality_text, title=title, target_duration=duration)
            logger.info(f"  质量门: {quality_report['passed']}/{quality_report['total']} 通过")
            for gate in quality_report['quality_gates']:
                status = "✅" if gate['passed'] else "❌"
                logger.info(f"    {status} {gate['name']}: {gate['message']}")
        except Exception as e:
            logger.info(f"  ⚠️  质量门检查异常: {e}")
            quality_report = None

        # ===== P24: 指令翻译 =====
        logger.info(f"\n[P24] 指令翻译...")
        sequence = self.translator.translate(enhanced)
        self.last_sequence = sequence
        self.translator.print_summary()

        instr_path = os.path.join(out_dir, f"{title}_instructions.json")
        self.translator.save_json(instr_path)

        # ===== P25: 中央调度 =====
        logger.info(f"\n[P25] 中央调度({'模拟执行' if dry_run else '实际执行'})...")
        deep_analysis = enhanced.get("deep_analysis") if enhanced else None
        self.orchestrator.build_tasks_from_instructions(self.translator.to_json(), deep_analysis=deep_analysis)
        report = self.orchestrator.execute(dry_run=dry_run)
        self.last_report = report

        report_path = os.path.join(out_dir, f"{title}_report.json")
        self.orchestrator.save_report(report_path)

        # ===== 结果汇总 =====
        result = {
            "title": title,
            "duration": duration,
            "style": style,
            "rewrite_mode": rewrite_mode,
            "parsed_script": parsed,
            "enhanced_script": enhanced,
            "instruction_sequence": self.translator.to_json(),
            "execution_report": {
                "total_tasks": report.total_tasks,
                "success_count": report.success_count,
                "failed_count": report.failed_count,
                "skipped_count": report.skipped_count,
                "total_duration": report.total_duration,
            },
            "parsed_script_path": parsed_path,
            "enhanced_script_path": enhanced_path,
            "instruction_sequence_path": instr_path,
            "execution_report_path": report_path,
            "stats": {
                "characters": len(enhanced.get("characters", [])),
                "scenes": len(enhanced.get("scenes", [])),
                "tts_instructions": len(sequence.tts_instructions),
                "keyframe_instructions": len(sequence.keyframe_instructions),
                "audio_instructions": len(sequence.audio_instructions),
                "sfx_instructions": len(sequence.sfx_instructions),
                "effect_instructions": len(sequence.effect_instructions),
                "text_instructions": len(sequence.text_instructions),
                "total_tasks": report.total_tasks,
                "llm_enhanced": enhanced.get("enhanced_by_llm", False),
                "rewrite_mode": rewrite_mode,
                "rewrite_stages": self.last_rewrite_result.stages_completed if self.last_rewrite_result else [],
                "quality_gates_passed": quality_report['passed'] if quality_report else None,
                "quality_gates_total": quality_report['total'] if quality_report else None,
            },
            "quality_report": quality_report,
        }

        logger.info(f"\n{'='*60}")
        logger.info(f"导演引擎完成: {title}")
        if rewrite_mode:
            logger.info(f"  改写模式: {rewrite_mode}")
            logger.info(f"  改写阶段: {', '.join(result['stats']['rewrite_stages'])}")
        logger.info(f"  角色: {result['stats']['characters']}个")
        logger.info(f"  场景: {result['stats']['scenes']}个")
        logger.info(f"  TTS指令: {result['stats']['tts_instructions']}条")
        logger.info(f"  关键帧指令: {result['stats']['keyframe_instructions']}条")
        logger.info(f"  音轨指令: {result['stats']['audio_instructions']}条")
        logger.info(f"  音效指令: {result['stats']['sfx_instructions']}条")
        logger.info(f"  调度任务: {result['stats']['total_tasks']}个")
        if quality_report:
            logger.info(f"  质量门: {quality_report['passed']}/{quality_report['total']} 通过")
        logger.info(f"  LLM增强: {'是' if result['stats']['llm_enhanced'] else '否（规则增强）'}")
        logger.info(f"  输出目录: {out_dir}")
        logger.info(f"{'='*60}\n")

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

    def execute_only(self, instruction_sequence: Dict, dry_run: bool = True,
                     deep_analysis: Dict = None):
        """只执行P25调度"""
        self.orchestrator.build_tasks_from_instructions(instruction_sequence, deep_analysis=deep_analysis)
        report = self.orchestrator.execute(dry_run=dry_run)
        self.last_report = report
        return report


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
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

    logger.info(f"\n✅ 演示完成")
    logger.info(f"   分镜JSON: {result['parsed_script_path']}")
    logger.info(f"   指令序列: {result['instruction_sequence_path']}")
    logger.info(f"   执行报告: {result['execution_report_path']}")
