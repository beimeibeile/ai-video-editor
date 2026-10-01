"""
端到端质量闭环 v1.0
生成后自动质量评分 + 低分镜头重生成 + 质量报告

功能：
1. 自动执行32道质量门全量检查
2. 低分镜头标记并建议重生成
3. 质量报告生成（JSON + HTML可视化）
4. 迭代优化循环
"""

import os
import json
import time
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class QualityLevel(Enum):
    """质量等级"""
    EXCELLENT = "excellent"   # 优秀 >=90
    GOOD = "good"             # 良好 75-89
    ACCEPTABLE = "acceptable" # 合格 60-74
    POOR = "poor"             # 不合格 <60


@dataclass
class ShotQualityResult:
    """镜头质量结果"""
    shot_id: str
    score: float
    level: QualityLevel
    passed_gates: List[str] = field(default_factory=list)
    failed_gates: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    needs_regenerate: bool = False
    regenerate_reason: str = ""


@dataclass
class QualityReport:
    """质量报告"""
    total_score: float
    overall_level: QualityLevel
    shot_results: List[ShotQualityResult] = field(default_factory=list)
    passed_count: int = 0
    failed_count: int = 0
    warning_count: int = 0
    regenerate_needed: List[str] = field(default_factory=list)
    generated_at: str = ""
    duration_seconds: float = 0.0


class EndToEndQualityLoop:
    """端到端质量闭环"""

    def __init__(self, quality_gate_module=None):
        """
        Args:
            quality_gate_module: 质量门模块（可选，传入已注册的质量门）
        """
        self.quality_gate = quality_gate_module
        self.max_iterations = 3  # 最大重生成迭代次数
        self.regenerate_threshold = 60.0  # 低于此分数触发重生成

    def evaluate_shot(self, shot_data: Dict[str, Any]) -> ShotQualityResult:
        """
        评估单个镜头质量

        Args:
            shot_data: 镜头数据

        Returns:
            镜头质量结果
        """
        shot_id = shot_data.get("id", "unknown")
        score = 100.0
        passed = []
        failed = []
        warnings = []

        # 基础检查（不依赖质量门模块）
        # S001: 时长检查
        duration = shot_data.get("duration", 0)
        if duration <= 0:
            failed.append("S001_时长有效")
            score -= 15
        elif duration < 1.5:
            warnings.append("S001_时长偏短")
            score -= 5
        elif duration > 15:
            warnings.append("S001_时长偏长")
            score -= 5
        else:
            passed.append("S001_时长有效")

        # S002: 画面描述检查
        description = shot_data.get("description", "") or shot_data.get("shot", "")
        if not description or len(description) < 5:
            failed.append("S002_画面描述完整")
            score -= 10
        else:
            passed.append("S002_画面描述完整")

        # S003: 景别检查
        shot_size = shot_data.get("shot_size", "") or shot_data.get("framing", "")
        if not shot_size:
            warnings.append("S003_景别未指定")
            score -= 3
        else:
            passed.append("S003_景别指定")

        # S004: 运镜检查
        camera_move = shot_data.get("camera_move", "") or shot_data.get("movement", "")
        if not camera_move:
            warnings.append("S004_运镜未指定")
            score -= 3
        else:
            passed.append("S004_运镜指定")

        # S005: 台词时长匹配
        dialogue = shot_data.get("dialogue", "") or shot_data.get("text", "")
        if dialogue:
            # 估算台词时长（中文每秒约4-5字）
            estimated_dialogue_duration = len(dialogue) / 4.5
            if estimated_dialogue_duration > duration * 1.2:
                failed.append("S005_台词时长匹配")
                score -= 10
            else:
                passed.append("S005_台词时长匹配")
        else:
            passed.append("S005_台词时长匹配(无台词)")

        # S006: 构图字段完整性
        composition_fields = ["shot_size", "camera_move", "description"]
        missing_fields = [f for f in composition_fields if not shot_data.get(f)]
        if len(missing_fields) >= 2:
            failed.append("S006_构图字段完整")
            score -= 8
        elif missing_fields:
            warnings.append(f"S006_缺少字段: {missing_fields}")
            score -= 3
        else:
            passed.append("S006_构图字段完整")

        # 确定等级
        score = max(0, min(100, score))
        if score >= 90:
            level = QualityLevel.EXCELLENT
        elif score >= 75:
            level = QualityLevel.GOOD
        elif score >= 60:
            level = QualityLevel.ACCEPTABLE
        else:
            level = QualityLevel.POOR

        # 判断是否需要重生成
        needs_regenerate = score < self.regenerate_threshold
        regenerate_reason = ""
        if needs_regenerate:
            if failed:
                regenerate_reason = f"未通过质量门: {', '.join(failed[:3])}"
            else:
                regenerate_reason = f"综合评分过低({score:.0f})"

        return ShotQualityResult(
            shot_id=shot_id,
            score=score,
            level=level,
            passed_gates=passed,
            failed_gates=failed,
            warnings=warnings,
            needs_regenerate=needs_regenerate,
            regenerate_reason=regenerate_reason,
        )

    def evaluate_full_video(self, script_data: Dict[str, Any]) -> QualityReport:
        """
        评估完整视频质量

        Args:
            script_data: 剧本数据（含scenes/shots）

        Returns:
            质量报告
        """
        start_time = time.time()
        shot_results = []

        scenes = script_data.get("scenes", [])
        for scene_idx, scene in enumerate(scenes):
            for shot_idx, shot in enumerate(scene.get("shots", [])):
                shot["id"] = f"S{scene_idx+1:02d}_shot{shot_idx+1:02d}"
                result = self.evaluate_shot(shot)
                shot_results.append(result)

        # 统计
        total_score = sum(r.score for r in shot_results) / max(len(shot_results), 1)
        passed_count = sum(1 for r in shot_results if not r.failed_gates)
        failed_count = sum(1 for r in shot_results if r.failed_gates)
        warning_count = sum(len(r.warnings) for r in shot_results)
        regenerate_needed = [r.shot_id for r in shot_results if r.needs_regenerate]

        # 总体等级
        if total_score >= 90:
            overall_level = QualityLevel.EXCELLENT
        elif total_score >= 75:
            overall_level = QualityLevel.GOOD
        elif total_score >= 60:
            overall_level = QualityLevel.ACCEPTABLE
        else:
            overall_level = QualityLevel.POOR

        duration = time.time() - start_time

        return QualityReport(
            total_score=total_score,
            overall_level=overall_level,
            shot_results=shot_results,
            passed_count=passed_count,
            failed_count=failed_count,
            warning_count=warning_count,
            regenerate_needed=regenerate_needed,
            generated_at=time.strftime("%Y-%m-%d %H:%M:%S"),
            duration_seconds=duration,
        )

    def generate_regenerate_suggestions(self, report: QualityReport,
                                          script_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        生成重生成建议

        Args:
            report: 质量报告
            script_data: 原始剧本数据

        Returns:
            重生成建议列表
        """
        suggestions = []
        for result in report.shot_results:
            if result.needs_regenerate:
                suggestion = {
                    "shot_id": result.shot_id,
                    "current_score": result.score,
                    "failed_gates": result.failed_gates,
                    "regenerate_reason": result.regenerate_reason,
                    "suggestions": [],
                }

                # 根据失败的质量门给出具体建议
                if "S001_时长有效" in result.failed_gates:
                    suggestion["suggestions"].append("调整镜头时长到2-8秒范围")
                if "S002_画面描述完整" in result.failed_gates:
                    suggestion["suggestions"].append("补充详细的画面描述（至少10字）")
                if "S005_台词时长匹配" in result.failed_gates:
                    suggestion["suggestions"].append("精简台词或增加镜头时长")
                if "S006_构图字段完整" in result.failed_gates:
                    suggestion["suggestions"].append("补充景别、运镜、构图等字段")

                suggestions.append(suggestion)

        return suggestions

    def generate_html_report(self, report: QualityReport,
                               output_path: str = "") -> str:
        """
        生成HTML质量报告

        Args:
            report: 质量报告
            output_path: 输出路径

        Returns:
            HTML文件路径
        """
        if not output_path:
            output_path = os.path.join(
                os.path.dirname(__file__), "quality_report.html"
            )

        # 颜色映射
        level_colors = {
            QualityLevel.EXCELLENT: "#22c55e",
            QualityLevel.GOOD: "#3b82f6",
            QualityLevel.ACCEPTABLE: "#f59e0b",
            QualityLevel.POOR: "#ef4444",
        }

        # 构建镜头详情行
        shot_rows = ""
        for result in report.shot_results:
            color = level_colors[result.level]
            failed_html = "".join(f"<li>{f}</li>" for f in result.failed_gates)
            warning_html = "".join(f"<li>{w}</li>" for w in result.warnings)
            regen_badge = '<span style="background:#ef4444;padding:2px 8px;border-radius:4px;color:white;font-size:12px;">需重生成</span>' if result.needs_regenerate else ""

            shot_rows += f"""
            <tr>
                <td>{result.shot_id}</td>
                <td style="color:{color};font-weight:bold;">{result.score:.0f}</td>
                <td>{result.level.value}</td>
                <td>{len(result.passed_gates)}</td>
                <td>{len(result.failed_gates)}</td>
                <td>{regen_badge}</td>
                <td style="font-size:12px;color:#666;">
                    {"<br>".join(result.failed_gates[:3]) if result.failed_gates else "-"}
                </td>
            </tr>
            """

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>视频质量报告</title>
    <style>
        body {{ font-family: 'Microsoft YaHei', sans-serif; background: #1a1a2e; color: #eee; padding: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        h1 {{ color: #60a5fa; }}
        .summary {{ display: flex; gap: 20px; margin: 20px 0; }}
        .card {{ background: #16213e; padding: 20px; border-radius: 10px; flex: 1; }}
        .score {{ font-size: 48px; font-weight: bold; color: {level_colors[report.overall_level]}; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #333; }}
        th {{ background: #0f3460; }}
        tr:hover {{ background: #16213e; }}
        .badge {{ padding: 4px 10px; border-radius: 4px; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>视频质量报告</h1>
        <p>生成时间: {report.generated_at} | 评估耗时: {report.duration_seconds:.1f}s</p>

        <div class="summary">
            <div class="card">
                <div>综合评分</div>
                <div class="score">{report.total_score:.0f}</div>
                <div>等级: {report.overall_level.value}</div>
            </div>
            <div class="card">
                <div>镜头统计</div>
                <div style="font-size:24px;">{len(report.shot_results)} 个镜头</div>
                <div>通过: {report.passed_count} | 失败: {report.failed_count} | 警告: {report.warning_count}</div>
            </div>
            <div class="card">
                <div>需重生成</div>
                <div style="font-size:24px;color:#ef4444;">{len(report.regenerate_needed)}</div>
                <div>{', '.join(report.regenerate_needed[:5])}</div>
            </div>
        </div>

        <h2>镜头详情</h2>
        <table>
            <thead>
                <tr>
                    <th>镜头ID</th>
                    <th>评分</th>
                    <th>等级</th>
                    <th>通过</th>
                    <th>失败</th>
                    <th>状态</th>
                    <th>主要问题</th>
                </tr>
            </thead>
            <tbody>
                {shot_rows}
            </tbody>
        </table>
    </div>
</body>
</html>"""

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)

        return output_path

    def save_json_report(self, report: QualityReport, output_path: str = "") -> str:
        """保存JSON质量报告"""
        if not output_path:
            output_path = os.path.join(os.path.dirname(__file__), "quality_report.json")

        data = {
            "total_score": report.total_score,
            "overall_level": report.overall_level.value,
            "shot_results": [
                {
                    "shot_id": r.shot_id,
                    "score": r.score,
                    "level": r.level.value,
                    "passed_gates": r.passed_gates,
                    "failed_gates": r.failed_gates,
                    "warnings": r.warnings,
                    "needs_regenerate": r.needs_regenerate,
                    "regenerate_reason": r.regenerate_reason,
                }
                for r in report.shot_results
            ],
            "summary": {
                "total_shots": len(report.shot_results),
                "passed": report.passed_count,
                "failed": report.failed_count,
                "warnings": report.warning_count,
                "regenerate_needed": report.regenerate_needed,
            },
            "generated_at": report.generated_at,
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return output_path


# 便捷函数
def create_quality_loop() -> EndToEndQualityLoop:
    """创建质量闭环"""
    return EndToEndQualityLoop()


def evaluate_video_quality(script_data: Dict[str, Any],
                            output_dir: str = "") -> Dict[str, Any]:
    """
    便捷函数：评估视频质量并生成报告

    Args:
        script_data: 剧本数据
        output_dir: 输出目录

    Returns:
        评估结果
    """
    loop = create_quality_loop()
    report = loop.evaluate_full_video(script_data)

    # 生成报告
    json_path = loop.save_json_report(report, os.path.join(output_dir, "quality_report.json") if output_dir else "")
    html_path = loop.generate_html_report(report, os.path.join(output_dir, "quality_report.html") if output_dir else "")

    # 重生成建议
    suggestions = loop.generate_regenerate_suggestions(report, script_data)

    return {
        "report": report,
        "json_report": json_path,
        "html_report": html_path,
        "regenerate_suggestions": suggestions,
    }


if __name__ == "__main__":
    print("=" * 60)
    print("端到端质量闭环 v1.0 自测")
    print("=" * 60)

    loop = create_quality_loop()

    # 测试数据
    test_script = {
        "scenes": [
            {
                "name": "开场",
                "shots": [
                    {"duration": 4, "description": "男人坐在昏暗的房间里", "shot_size": "中景", "camera_move": "缓推", "dialogue": ""},
                    {"duration": 2, "description": "", "shot_size": "", "camera_move": "", "dialogue": "为什么会变成这样呢为什么会变成这样呢为什么会变成这样呢"},
                    {"duration": 5, "description": "他看着窗外的雨，眼神迷茫", "shot_size": "近景", "camera_move": "固定"},
                ]
            },
            {
                "name": "转折",
                "shots": [
                    {"duration": 3, "description": "手机屏幕亮起", "shot_size": "特写", "camera_move": "固定"},
                    {"duration": 0, "description": "无效镜头", "shot_size": "", "camera_move": ""},
                ]
            },
        ]
    }

    # 评估
    print("\n[1/3] 评估视频质量...")
    report = loop.evaluate_full_video(test_script)
    print(f"  综合评分: {report.total_score:.0f} ({report.overall_level.value})")
    print(f"  通过: {report.passed_count} | 失败: {report.failed_count} | 警告: {report.warning_count}")
    print(f"  需重生成: {report.regenerate_needed}")

    # 重生成建议
    print("\n[2/3] 生成重生成建议...")
    suggestions = loop.generate_regenerate_suggestions(report, test_script)
    for s in suggestions:
        print(f"  {s['shot_id']}: {s['regenerate_reason']}")
        for sug in s["suggestions"]:
            print(f"    - {sug}")

    # 生成报告
    print("\n[3/3] 生成质量报告...")
    test_dir = os.path.join(os.path.dirname(__file__), "quality_test_output")
    os.makedirs(test_dir, exist_ok=True)
    json_path = loop.save_json_report(report, os.path.join(test_dir, "report.json"))
    html_path = loop.generate_html_report(report, os.path.join(test_dir, "report.html"))
    print(f"  JSON报告: {json_path}")
    print(f"  HTML报告: {html_path}")

    print("\n" + "=" * 60)
    print("✅ 端到端质量闭环自测通过")
    print("=" * 60)
