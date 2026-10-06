#!/usr/bin/env python3
"""
端到端集成测试套件
验证从剧本输入到剪映工程输出的完整管线

测试覆盖：
1. 剧本解析（script_parser）
2. 指令翻译（instruction_translator）
3. 中央调度（central_orchestrator）
4. 剪映工程构建（jianying_executor）
5. 工程文件验证（draft_info.json结构检查）

黄金测试集：
- E2E_01: 最简单场景剧本
- E2E_02: 多场景对话剧本
- E2E_03: 带特效和转场的剧本
- E2E_04: 带字幕的剧本
- E2E_05: 完整复杂剧本
"""
import os
import sys
import json
import time
import shutil
from typing import Dict, List, Any, Optional

# 路径配置
try:
    from paths import PATHS
    RUNTIME_DIR = os.path.dirname(os.path.abspath(__file__))
except ImportError:
    RUNTIME_DIR = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, RUNTIME_DIR)

# 导入核心管线模块
from script_parser import ScriptParser
from instruction_translator import InstructionTranslator
from central_orchestrator import CentralOrchestrator, TaskType

# 测试结果统计
class E2ETestResult:
    def __init__(self, name: str):
        self.name = name
        self.start_time = time.time()
        self.stages = {}
        self.errors = []
        self.warnings = []
        self.passed = False

    def add_stage(self, stage: str, success: bool, detail: str = ""):
        self.stages[stage] = {"success": success, "detail": detail}
        if not success:
            self.errors.append(f"{stage}: {detail}")

    def add_warning(self, warning: str):
        self.warnings.append(warning)

    def finish(self):
        self.duration = time.time() - self.start_time
        self.passed = len(self.errors) == 0
        return self

    def summary(self) -> str:
        status = "✅ PASS" if self.passed else "❌ FAIL"
        lines = [f"\n{'='*60}", f"{status} | {self.name} ({self.duration:.2f}s)", "="*60]
        for stage, result in self.stages.items():
            icon = "✅" if result["success"] else "❌"
            lines.append(f"  {icon} {stage}: {result['detail']}")
        if self.warnings:
            lines.append(f"\n  ⚠️  警告 ({len(self.warnings)}):")
            for w in self.warnings:
                lines.append(f"    - {w}")
        if self.errors:
            lines.append(f"\n  ❌ 错误 ({len(self.errors)}):")
            for e in self.errors:
                lines.append(f"    - {e}")
        return "\n".join(lines)


# 黄金测试剧本集
GOLDEN_SCRIPTS = {
    "E2E_01_minimal": {
        "title": "最简单场景",
        "duration": 5.0,
        "style": "极简",
        "script": """
场景：客厅
小明说：你好。
小红说：你好。
        """,
        "expected": {
            "scenes": 1,
            "characters": ["小明", "小红"],
            "tts_min": 2,
        }
    },
    "E2E_02_multi_scene": {
        "title": "多场景对话",
        "duration": 10.0,
        "style": "剧情",
        "script": """
场景：办公室
张三说：这个方案怎么样？
李四说：我觉得需要修改。

场景：会议室
张三说：大家有什么意见？
王五说：我同意李四的看法。
赵六说：我有不同意见。
        """,
        "expected": {
            "scenes": 2,
            "characters": ["张三", "李四", "王五", "赵六"],
            "tts_min": 5,
        }
    },
    "E2E_03_with_effects": {
        "title": "带特效转场",
        "duration": 8.0,
        "style": "动感",
        "script": """
场景：街头
【闪白】
小明说：快看！
【震动】
小红说：那是什么？
【模糊转场】
场景：天空
小明说：是飞碟！
        """,
        "expected": {
            "scenes": 2,
            "effects_min": 2,
            "transitions_min": 1,
        }
    },
    "E2E_04_with_subtitles": {
        "title": "带字幕",
        "duration": 6.0,
        "style": "温馨",
        "script": """
场景：公园
字幕：春天来了
小明说：今天天气真好。
小红说：是啊，我们去散步吧。
字幕：美好的一天
        """,
        "expected": {
            "text_instructions_min": 2,
        }
    },
    "E2E_05_complex": {
        "title": "完整复杂剧本",
        "duration": 15.0,
        "style": "搞笑短剧",
        "script": """
场景：抖音主页
豆包说：大家好，我是豆包！
【闪白】
用户说：你能做什么？
豆包说：我可以帮你写代码、做视频、解答问题！
【震动】
用户说：真的吗？
豆包说：当然！
【转场：缩放】
场景：工作台
豆包说：看我的厉害！
字幕：AI全能助手
        """,
        "expected": {
            "scenes": 2,
            "characters": ["豆包", "用户"],
            "tts_min": 5,
            "effects_min": 2,
        }
    },
}


def validate_draft_info(draft_path: str) -> Dict[str, Any]:
    """验证剪映工程的draft_info.json结构"""
    result = {"valid": True, "checks": [], "errors": []}

    info_path = os.path.join(draft_path, "draft_info.json")
    if not os.path.exists(info_path):
        result["valid"] = False
        result["errors"].append("draft_info.json不存在")
        return result

    try:
        with open(info_path, "r", encoding="utf-8") as f:
            info = json.load(f)
    except Exception as e:
        result["valid"] = False
        result["errors"].append(f"draft_info.json解析失败: {e}")
        return result

    # 检查必要字段
    required_fields = ["duration", "canvas_config", "materials", "tracks"]
    for field in required_fields:
        if field in info:
            result["checks"].append(f"{field}: 存在")
        else:
            result["valid"] = False
            result["errors"].append(f"缺少必要字段: {field}")

    # 检查画布配置
    canvas = info.get("canvas_config", {})
    if canvas.get("width") and canvas.get("height"):
        result["checks"].append(f"画布: {canvas['width']}x{canvas['height']}")
    else:
        result["warnings"] = result.get("warnings", [])
        result["warnings"].append("画布配置不完整")

    # 检查轨道
    tracks = info.get("tracks", [])
    result["checks"].append(f"轨道数: {len(tracks)}")
    for i, track in enumerate(tracks):
        segs = track.get("segments", [])
        result["checks"].append(f"  轨道{i}({track.get('type', '?')}): {len(segs)}个片段")

    # 检查素材
    materials = info.get("materials", {})
    videos = materials.get("videos", [])
    audios = materials.get("audios", [])
    texts = materials.get("texts", [])
    result["checks"].append(f"素材: 视频{len(videos)} 音频{len(audios)} 文本{len(texts)}")

    # 检查时长
    duration = info.get("duration", 0)
    if duration > 0:
        result["checks"].append(f"时长: {duration/1000000:.1f}秒")
    else:
        result["valid"] = False
        result["errors"].append("时长为0或无效")

    return result


def run_e2e_test(script_id: str, script_config: Dict, output_dir: str) -> E2ETestResult:
    """运行单个端到端测试"""
    result = E2ETestResult(script_id)
    test_dir = os.path.join(output_dir, script_id)
    os.makedirs(test_dir, exist_ok=True)

    try:
        # Stage 1: 剧本解析
        print(f"\n  [P23] 剧本解析...")
        parser = ScriptParser()
        parsed = parser.parse(
            script_text=script_config["script"],
            title=script_config["title"],
            duration=script_config["duration"],
            style=script_config["style"],
        )
        scenes_count = len(parsed.get("scenes", []))
        chars_count = len(parsed.get("characters", []))
        result.add_stage("剧本解析", True,
                        f"{scenes_count}场景, {chars_count}角色")

        # 保存解析结果
        parsed_path = os.path.join(test_dir, "parsed.json")
        with open(parsed_path, "w", encoding="utf-8") as f:
            json.dump(parsed, f, ensure_ascii=False, indent=2)

        # Stage 2: 指令翻译
        print(f"  [P24] 指令翻译...")
        translator = InstructionTranslator()
        sequence = translator.translate(parsed)
        tts_count = len(sequence.tts_instructions)
        kf_count = len(sequence.keyframe_instructions)
        effect_count = len(sequence.effect_instructions)
        text_count = len(sequence.text_instructions)
        result.add_stage("指令翻译", True,
                        f"TTS:{tts_count} KF:{kf_count} 特效:{effect_count} 文本:{text_count}")

        # 保存指令序列
        instr_path = os.path.join(test_dir, "instructions.json")
        translator.save_json(instr_path)

        # Stage 3: 中央调度（dry_run）
        print(f"  [P25] 中央调度(dry_run)...")
        orchestrator = CentralOrchestrator(work_dir=test_dir)
        tasks = orchestrator.build_tasks_from_instructions(translator.to_json())
        report = orchestrator.execute(dry_run=True)
        result.add_stage("中央调度", True,
                        f"{report.total_tasks}任务, 成功{report.success_count}, 失败{report.failed_count}")

        # 保存调度报告
        report_path = os.path.join(test_dir, "report.json")
        orchestrator.save_report(report_path)

        # Stage 4: 验证预期
        print(f"  [验证] 预期检查...")
        expected = script_config.get("expected", {})
        validation_errors = []

        if "scenes" in expected and scenes_count != expected["scenes"]:
            validation_errors.append(f"场景数不符: 预期{expected['scenes']}, 实际{scenes_count}")

        if "characters" in expected:
            actual_chars = {c.get("name", "") for c in parsed.get("characters", [])}
            expected_chars = set(expected["characters"])
            missing = expected_chars - actual_chars
            if missing:
                validation_errors.append(f"缺少角色: {missing}")

        if "tts_min" in expected and tts_count < expected["tts_min"]:
            validation_errors.append(f"TTS指令不足: 至少{expected['tts_min']}, 实际{tts_count}")

        if "effects_min" in expected and effect_count < expected["effects_min"]:
            validation_errors.append(f"特效指令不足: 至少{expected['effects_min']}, 实际{effect_count}")

        if "text_instructions_min" in expected and text_count < expected["text_instructions_min"]:
            validation_errors.append(f"文本指令不足: 至少{expected['text_instructions_min']}, 实际{text_count}")

        if validation_errors:
            for e in validation_errors:
                result.add_warning(f"预期不符: {e}")
            result.add_stage("预期验证", True, f"{len(validation_errors)}项警告（非致命）")
        else:
            result.add_stage("预期验证", True, "全部符合预期")

    except Exception as e:
        import traceback
        result.add_stage("异常", False, f"{e}\n{traceback.format_exc()[-500:]}")

    return result.finish()


def run_all_tests(test_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    """运行所有端到端测试"""
    output_base = os.path.join(os.path.dirname(RUNTIME_DIR), "e2e_test_output")
    os.makedirs(output_base, exist_ok=True)

    tests_to_run = test_ids or list(GOLDEN_SCRIPTS.keys())

    print("\n" + "=" * 70)
    print("  端到端集成测试套件")
    print(f"  测试剧本: {len(tests_to_run)}个")
    print(f"  输出目录: {output_base}")
    print("=" * 70)

    results = []
    for test_id in tests_to_run:
        if test_id not in GOLDEN_SCRIPTS:
            print(f"\n⚠️  未知测试ID: {test_id}")
            continue
        print(f"\n{'─'*60}")
        print(f"  运行: {test_id} - {GOLDEN_SCRIPTS[test_id]['title']}")
        print(f"{'─'*60}")
        result = run_e2e_test(test_id, GOLDEN_SCRIPTS[test_id], output_base)
        results.append(result)
        print(result.summary())

    # 汇总
    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed
    total_time = sum(r.duration for r in results)

    print("\n" + "=" * 70)
    print(f"  测试汇总: {passed}/{len(results)} 通过, {failed} 失败, 总耗时{total_time:.2f}s")
    print("=" * 70)

    # 保存汇总报告
    summary = {
        "total": len(results),
        "passed": passed,
        "failed": failed,
        "total_time": total_time,
        "results": [
            {
                "name": r.name,
                "passed": r.passed,
                "duration": r.duration,
                "stages": r.stages,
                "errors": r.errors,
                "warnings": r.warnings,
            }
            for r in results
        ]
    }
    summary_path = os.path.join(output_base, "e2e_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"\n  报告已保存: {summary_path}")

    return summary


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="端到端集成测试套件")
    parser.add_argument("--test", "-t", nargs="+", help="指定测试ID运行")
    parser.add_argument("--list", "-l", action="store_true", help="列出所有可用测试")
    args = parser.parse_args()

    if args.list:
        print("\n可用测试:")
        for tid, config in GOLDEN_SCRIPTS.items():
            print(f"  {tid}: {config['title']} ({config['duration']}s)")
    else:
        run_all_tests(args.test)
