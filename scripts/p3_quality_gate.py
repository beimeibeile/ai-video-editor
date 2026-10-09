#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P3-5 质量门自动评估系统
5维度评分：技术质量/节奏质量/特效质量/音频质量/内容完整性
输出评分报告+修复建议+自动重生成指令
"""
import os
import json
import subprocess
import logging
from typing import Dict, List, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


FFPROBE = r"D:\Ai\ffmpeg-master-latest-win64-gpl\bin\ffprobe.exe"
FFMPEG = r"D:\Ai\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe"


@dataclass
class DimensionScore:
    """维度评分"""
    name: str
    score: float  # 0-100
    weight: float  # 权重
    issues: List[str] = field(default_factory=list)
    passed: bool = True


@dataclass
class QualityReport:
    """质量评估报告"""
    file_path: str
    total_score: float
    dimensions: List[DimensionScore] = field(default_factory=list)
    passed: bool = False
    auto_regenerate: bool = False
    suggestions: List[str] = field(default_factory=list)
    regenerate_instructions: Dict[str, Any] = field(default_factory=dict)


class QualityGate:
    """质量门自动评估"""

    def __init__(self, pass_threshold: float = 60.0,
                 regenerate_threshold: float = 40.0,
                 expect_audio: bool = True):
        self.pass_threshold = pass_threshold
        self.regenerate_threshold = regenerate_threshold
        self.expect_audio = expect_audio

    def evaluate(self, video_path: str,
                 script_requirements: Dict[str, Any] = None,
                 effect_plan: Dict[str, Any] = None) -> QualityReport:
        """
        评估视频质量

        Args:
            video_path: 视频文件路径
            script_requirements: 剧本要求（用于内容完整性检查）
            effect_plan: P3-2特效方案（用于特效质量检查）

        Returns:
            质量评估报告
        """
        report = QualityReport(file_path=video_path, total_score=0)

        # 1. 技术质量（25%）
        tech = self._evaluate_technical(video_path)
        report.dimensions.append(tech)

        # 2. 节奏质量（20%）
        rhythm = self._evaluate_rhythm(video_path)
        report.dimensions.append(rhythm)

        # 3. 特效质量（20%）
        effect = self._evaluate_effects(video_path, effect_plan)
        report.dimensions.append(effect)

        # 4. 音频质量（20%）
        audio = self._evaluate_audio(video_path)
        report.dimensions.append(audio)

        # 5. 内容完整性（15%）
        content = self._evaluate_content(video_path, script_requirements)
        report.dimensions.append(content)

        # 计算总分
        total_weight = sum(d.weight for d in report.dimensions)
        report.total_score = sum(d.score * d.weight for d in report.dimensions) / max(total_weight, 1)
        report.total_score = round(report.total_score, 1)

        # 判断是否通过
        report.passed = report.total_score >= self.pass_threshold
        report.auto_regenerate = report.total_score < self.regenerate_threshold

        # 收集建议
        for d in report.dimensions:
            report.suggestions.extend(d.issues)

        # 生成重生成指令
        if report.auto_regenerate:
            report.regenerate_instructions = self._generate_regenerate_instructions(report)

        return report

    def _evaluate_technical(self, video_path: str) -> DimensionScore:
        """评估技术质量"""
        score = 100.0
        issues = []

        try:
            result = subprocess.run(
                [FFPROBE, "-v", "quiet", "-print_format", "json",
                 "-show_format", "-show_streams", video_path],
                capture_output=True, text=True, timeout=15
            )
            info = json.loads(result.stdout)
            streams = info.get("streams", [])
            video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)

            if not video_stream:
                return DimensionScore("technical", 0, 0.25, ["未找到视频流"], False)

            # 分辨率检查
            width = int(video_stream.get("width", 0))
            height = int(video_stream.get("height", 0))
            if width < 720 or height < 720:
                score -= 20
                issues.append(f"分辨率过低: {width}x{height}（建议≥720p）")

            # 帧率检查
            fps_str = video_stream.get("r_frame_rate", "30/1")
            try:
                num, den = fps_str.split("/")
                fps = float(num) / float(den)
                if fps < 24:
                    score -= 15
                    issues.append(f"帧率过低: {fps}fps（建议≥24fps）")
            except Exception:
                pass

            # 码率检查
            bitrate = int(info.get("format", {}).get("bit_rate", 0))
            if bitrate > 0 and bitrate < 500000:
                score -= 10
                issues.append(f"码率过低: {bitrate/1000:.0f}kbps（可能影响画质）")

            # 编码检查
            codec = video_stream.get("codec_name", "")
            if codec not in ["h264", "h265", "hevc", "vp9", "av1"]:
                score -= 5
                issues.append(f"非标准编码: {codec}（可能兼容性差）")

            # 黑帧检测（采样前3帧和后3帧）
            black_frames = self._detect_black_frames(video_path)
            if black_frames > 0:
                score -= min(30, black_frames * 5)
                issues.append(f"检测到{black_frames}个黑帧（需移除或修复）")

        except Exception as e:
            score = 50
            issues.append(f"技术质量检测异常: {e}")

        return DimensionScore(
            "technical", max(0, score), 0.25,
            issues, score >= 60
        )

    def _detect_black_frames(self, video_path: str) -> int:
        """检测黑帧数量"""
        try:
            result = subprocess.run(
                [FFMPEG, "-i", video_path, "-vf", "blackdetect=d=0.1:pix_th=0.10",
                 "-an", "-f", "null", "-"],
                capture_output=True, text=True, timeout=30
            )
            # 解析blackdetect输出
            black_count = result.stderr.count("black_start")
            return black_count
        except Exception:
            return 0

    def _evaluate_rhythm(self, video_path: str) -> DimensionScore:
        """评估节奏质量"""
        score = 75.0  # 默认中等
        issues = []

        try:
            # 用ffmpeg检测场景切换
            result = subprocess.run(
                [FFMPEG, "-i", video_path, "-vf", "select='gt(scene,0.3)',showinfo",
                 "-an", "-f", "null", "-"],
                capture_output=True, text=True, timeout=30
            )
            scene_changes = result.stderr.count("showinfo")

            # 获取时长
            probe = subprocess.run(
                [FFPROBE, "-v", "quiet", "-print_format", "json",
                 "-show_format", video_path],
                capture_output=True, text=True, timeout=10
            )
            duration = float(json.loads(probe.stdout).get("format", {}).get("duration", 60))

            # 场景切换频率
            frequency = scene_changes / max(duration / 60, 0.1)

            if frequency < 3:
                score -= 15
                issues.append(f"镜头切换过少: {frequency:.1f}次/分钟（节奏可能拖沓）")
            elif frequency > 30:
                score -= 15
                issues.append(f"镜头切换过多: {frequency:.1f}次/分钟（节奏可能过快）")
            else:
                issues.append(f"镜头切换频率: {frequency:.1f}次/分钟（正常范围）")

        except Exception as e:
            issues.append(f"节奏检测异常: {e}")

        return DimensionScore(
            "rhythm", max(0, score), 0.20,
            issues, score >= 60
        )

    def _evaluate_effects(self, video_path: str,
                           effect_plan = None) -> DimensionScore:
        """评估特效质量"""
        score = 70.0
        issues = []

        if not effect_plan:
            issues.append("无特效方案对比，跳过特效匹配检查")
            return DimensionScore("effects", score, 0.20, issues, True)

        # 兼容EffectPlan对象和dict两种类型
        if hasattr(effect_plan, 'summary'):
            plan_dict = {'summary': effect_plan.summary, 'decisions': effect_plan.decisions}
        elif isinstance(effect_plan, dict):
            plan_dict = effect_plan
        else:
            plan_dict = {}

        # 检查特效方案是否被应用（通过P3-1分析结果对比）
        planned_effects = plan_dict.get("summary", {}).get("total_decisions", 0)
        if planned_effects == 0:
            issues.append("特效方案中无决策")
            score -= 10

        # 检查特效多样性
        by_type = plan_dict.get("summary", {}).get("by_type", {})
        if by_type:
            types_count = len(by_type)
            if types_count < 2:
                issues.append(f"特效类型单一: 仅{types_count}种（建议多样化）")
                score -= 10

        return DimensionScore(
            "effects", max(0, score), 0.20,
            issues, score >= 60
        )

    def _evaluate_audio(self, video_path: str) -> DimensionScore:
        """评估音频质量"""
        score = 80.0
        issues = []

        try:
            result = subprocess.run(
                [FFPROBE, "-v", "quiet", "-print_format", "json",
                 "-show_streams", video_path],
                capture_output=True, text=True, timeout=10
            )
            streams = json.loads(result.stdout).get("streams", [])
            audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

            if not audio_stream:
                if self.expect_audio:
                    return DimensionScore("audio", 50, 0.20, ["无音频轨道（预期有音频）"], False)
                else:
                    return DimensionScore("audio", 100, 0.20, ["无音频轨道（预期无音频，跳过）"], True)

            # 采样率检查
            sample_rate = int(audio_stream.get("sample_rate", 0))
            if sample_rate < 44100:
                score -= 10
                issues.append(f"采样率过低: {sample_rate}Hz（建议≥44.1kHz）")

            # 声道检查
            channels = int(audio_stream.get("channels", 0))
            if channels < 2:
                score -= 5
                issues.append(f"单声道音频（建议立体声）")

            # 音量检测（volumedetect）
            vol_result = subprocess.run(
                [FFMPEG, "-i", video_path, "-af", "volumedetect",
                 "-an", "-f", "null", "-"],
                capture_output=True, text=True, timeout=30
            )
            for line in vol_result.stderr.split("\n"):
                if "mean_volume" in line:
                    mean_vol = float(line.split(":")[1].strip().replace("dB", ""))
                    if mean_vol < -30:
                        score -= 15
                        issues.append(f"平均音量过低: {mean_vol:.1f}dB（建议-16到-20dB）")
                    elif mean_vol > -10:
                        score -= 10
                        issues.append(f"平均音量过高: {mean_vol:.1f}dB（可能爆音）")
                    break

        except Exception as e:
            issues.append(f"音频检测异常: {e}")

        return DimensionScore(
            "audio", max(0, score), 0.20,
            issues, score >= 60
        )

    def _evaluate_content(self, video_path: str,
                          script_requirements: Dict[str, Any] = None) -> DimensionScore:
        """评估内容完整性"""
        score = 80.0
        issues = []

        if not script_requirements:
            issues.append("无剧本要求，跳过内容完整性检查")
            return DimensionScore("content", score, 0.15, issues, True)

        # 检查时长是否符合要求
        required_duration = script_requirements.get("target_duration", 0)
        if required_duration > 0:
            try:
                probe = subprocess.run(
                    [FFPROBE, "-v", "quiet", "-print_format", "json",
                     "-show_format", video_path],
                    capture_output=True, text=True, timeout=10
                )
                actual_duration = float(json.loads(probe.stdout).get("format", {}).get("duration", 0))
                duration_diff = abs(actual_duration - required_duration)
                if duration_diff > required_duration * 0.2:
                    score -= 20
                    issues.append(f"时长偏差过大: 实际{actual_duration:.0f}s vs 要求{required_duration:.0f}s")
            except Exception:
                pass

        # 检查关键内容点
        key_points = script_requirements.get("key_points", [])
        if key_points:
            issues.append(f"需人工确认{len(key_points)}个关键内容点是否覆盖")

        return DimensionScore(
            "content", max(0, score), 0.15,
            issues, score >= 60
        )

    def _generate_regenerate_instructions(self, report: QualityReport) -> Dict[str, Any]:
        """生成自动重生成指令"""
        instructions = {
            "reason": f"总分{report.total_score}低于阈值{self.regenerate_threshold}",
            "fix_dimensions": [],
            "priority_fixes": [],
        }

        for d in report.dimensions:
            if d.score < 60:
                instructions["fix_dimensions"].append(d.name)
                instructions["priority_fixes"].extend(d.issues[:3])

        return instructions

    def export_report(self, report: QualityReport, output_path: str):
        """导出报告为JSON"""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        data = {
            "file_path": report.file_path,
            "total_score": report.total_score,
            "passed": report.passed,
            "auto_regenerate": report.auto_regenerate,
            "dimensions": [
                {
                    "name": d.name,
                    "score": d.score,
                    "weight": d.weight,
                    "issues": d.issues,
                    "passed": d.passed,
                }
                for d in report.dimensions
            ],
            "suggestions": report.suggestions,
            "regenerate_instructions": report.regenerate_instructions,
        }
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return output_path


def main():
    import argparse
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description="质量门自动评估系统")
    parser.add_argument("video", help="视频文件路径")
    parser.add_argument("-o", "--output", help="输出报告路径")
    args = parser.parse_args()

    if not os.path.exists(args.video):
        logger.error(f"错误: 文件不存在 - {args.video}")
        return

    gate = QualityGate()
    report = gate.evaluate(args.video)

    logger.info(f"=== 质量评估报告 ===")
    logger.info(f"文件: {report.file_path}")
    logger.info(f"总分: {report.total_score}/100")
    logger.info(f"通过: {'✅ 是' if report.passed else '❌ 否'}")
    logger.info(f"自动重生成: {'是' if report.auto_regenerate else '否'}")
    logger.info(f"\n=== 各维度评分 ===")
    for d in report.dimensions:
        status = "✅" if d.passed else "❌"
        logger.info(f"  {status} {d.name}: {d.score:.0f}/100 (权重{d.weight})")
        for issue in d.issues:
            logger.info(f"    - {issue}")

    if report.suggestions:
        logger.info(f"\n=== 修复建议 ===")
        for i, s in enumerate(report.suggestions[:10], 1):
            logger.info(f"  {i}. {s}")

    if args.output:
        path = gate.export_report(report, args.output)
        logger.info(f"\n报告已保存: {path}")


if __name__ == "__main__":
    main()
