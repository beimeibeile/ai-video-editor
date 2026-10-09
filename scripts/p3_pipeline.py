#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P3端到端集成Pipeline
视频分析 → 特效编排 → 镜头决策 → 自动配乐 → 质量评估 → 剪映指令
"""
import sys
import os
import json
import argparse
import logging

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS_DIR)

logger = logging.getLogger(__name__)

from p3_common import (
    Segment, PipelineResult,
    video_analysis_to_segments,
    segments_to_effect_orchestrator_input,
    segments_to_camera_decision_input,
    merge_effect_plan_into_segments,
    merge_camera_plan_into_segments,
    generate_jianying_instructions,
)


class P3Pipeline:
    """P3端到端流水线"""

    def __init__(self, style: str = "vlog", bgm_dir: str = None):
        self.style = style
        self.bgm_dir = bgm_dir
        self._modules = {}

    def _load_module(self, name: str):
        """懒加载模块"""
        if name not in self._modules:
            if name == "analyzer":
                from p3_video_analyzer import VideoAnalyzer
                self._modules[name] = VideoAnalyzer(sample_interval=1.0)
            elif name == "orchestrator":
                from p3_effect_orchestrator import EffectOrchestrator
                self._modules[name] = EffectOrchestrator(style=self.style)
            elif name == "camera":
                from p3_camera_decision import CameraDecisionEngine
                self._modules[name] = CameraDecisionEngine()
            elif name == "music":
                from p3_auto_music import AutoMusicSystem
                self._modules[name] = AutoMusicSystem()
            elif name == "quality":
                from p3_quality_gate import QualityGate
                self._modules[name] = QualityGate(pass_threshold=60)
        return self._modules[name]

    def run_from_video(self, video_path: str, output_dir: str = None) -> PipelineResult:
        """从视频文件运行完整pipeline"""
        logger.info(f"[P3 Pipeline] 输入视频: {os.path.basename(video_path)}")
        result = PipelineResult()

        # Step 1: 视频分析
        logger.info("  [1/5] 视频内容分析...")
        analyzer = self._load_module("analyzer")
        analysis = analyzer.analyze(video_path)
        result.video_analysis = self._to_dict(analysis)
        segments = video_analysis_to_segments(analysis)
        logger.info(f"    检测到 {len(segments)} 个场景, 总时长 {analysis.duration:.1f}s")

        # Step 2: 特效编排
        logger.info("  [2/5] AI特效编排...")
        orchestrator = self._load_module("orchestrator")
        eff_input = segments_to_effect_orchestrator_input(segments)
        effect_plan = orchestrator.orchestrate(eff_input)
        result.effect_plan = self._to_dict(effect_plan)
        segments = merge_effect_plan_into_segments(segments, effect_plan)
        logger.info(f"    生成 {len(effect_plan.decisions)} 个特效决策, 平均置信度 {effect_plan.summary.get('avg_confidence', 0):.2f}")

        # Step 3: 镜头决策
        logger.info("  [3/5] 镜头语言决策...")
        camera = self._load_module("camera")
        cam_input = segments_to_camera_decision_input(segments)
        camera_plan = camera.decide(cam_input)
        result.camera_plan = self._to_dict(camera_plan)
        segments = merge_camera_plan_into_segments(segments, camera_plan)
        logger.info(f"    生成 {len(camera_plan.shots)} 个镜头决策, {sum(len(s.keyframes) for s in segments)} 个关键帧")

        # Step 4: 自动配乐
        logger.info("  [4/5] 自动配乐...")
        music = self._load_module("music")
        emotions = [
            {"start": s.start, "end": s.end, "emotion": s.emotion, "intensity": s.intensity}
            for s in segments
        ]
        music_plan = music.generate_music_plan(emotions, style=self.style)
        result.music_plan = music_plan
        logger.info(f"    生成 {len(music_plan.get('tracks', []))} 条音轨")

        # Step 5: 质量评估
        logger.info("  [5/5] 质量门评估...")
        quality = self._load_module("quality")
        quality_report = quality.evaluate(video_path, effect_plan=effect_plan)
        result.quality_report = self._quality_to_dict(quality_report)
        logger.info(f"    质量评分: {quality_report.total_score}/100 ({'通过' if quality_report.passed else '未通过'})")

        # 生成剪映指令
        result.segments = segments
        result.jianying_instructions = generate_jianying_instructions(segments)
        logger.info(f"  剪映指令: {len(result.jianying_instructions['tracks'])}轨道, "
              f"{len(result.jianying_instructions['animations'])}动画, "
              f"{len(result.jianying_instructions['keyframes'])}关键帧")

        # 保存
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            out_path = os.path.join(output_dir, "pipeline_result.json")
            result.export_json(out_path)
            logger.info(f"  结果已保存: {out_path}")

        return result

    def run_from_segments(self, segments: list, output_dir: str = None) -> PipelineResult:
        """从预设Segment列表运行pipeline（无需视频文件）"""
        logger.info(f"[P3 Pipeline] 输入: {len(segments)} 个预设镜头")
        result = PipelineResult()

        # Step 1: 特效编排
        logger.info("  [1/3] AI特效编排...")
        orchestrator = self._load_module("orchestrator")
        eff_input = segments_to_effect_orchestrator_input(segments)
        effect_plan = orchestrator.orchestrate(eff_input)
        result.effect_plan = self._to_dict(effect_plan)
        segments = merge_effect_plan_into_segments(segments, effect_plan)
        logger.info(f"    {len(effect_plan.decisions)} 决策, 置信度 {effect_plan.summary.get('avg_confidence', 0):.2f}")

        # Step 2: 镜头决策
        logger.info("  [2/3] 镜头语言决策...")
        camera = self._load_module("camera")
        cam_input = segments_to_camera_decision_input(segments)
        camera_plan = camera.decide(cam_input)
        result.camera_plan = self._to_dict(camera_plan)
        segments = merge_camera_plan_into_segments(segments, camera_plan)
        logger.info(f"    {len(camera_plan.shots)} 镜头决策")

        # Step 3: 自动配乐
        logger.info("  [3/3] 自动配乐...")
        music = self._load_module("music")
        emotions = [
            {"start": s.start, "end": s.end, "emotion": s.emotion, "intensity": s.intensity}
            for s in segments
        ]
        music_plan = music.generate_music_plan(emotions, style=self.style)
        result.music_plan = music_plan

        result.segments = segments
        result.jianying_instructions = generate_jianying_instructions(segments)

        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            result.export_json(os.path.join(output_dir, "pipeline_result.json"))

        return result

    def _to_dict(self, obj):
        """dataclass对象转dict"""
        from dataclasses import asdict, is_dataclass
        if is_dataclass(obj):
            return {k: self._to_dict(v) for k, v in asdict(obj).items()}
        elif isinstance(obj, list):
            return [self._to_dict(v) for v in obj]
        elif isinstance(obj, dict):
            return {k: self._to_dict(v) for k, v in obj.items()}
        return obj

    def _quality_to_dict(self, report):
        """质量报告转dict"""
        return {
            "file_path": report.file_path,
            "total_score": report.total_score,
            "passed": report.passed,
            "auto_regenerate": report.auto_regenerate,
            "dimensions": [
                {
                    "name": d.name,
                    "score": d.score,
                    "weight": d.weight,
                    "passed": d.passed,
                    "issues": d.issues,
                }
                for d in report.dimensions
            ],
            "suggestions": report.suggestions,
        }


def main():
    parser = argparse.ArgumentParser(description="P3端到端集成Pipeline")
    parser.add_argument("--video", help="输入视频文件路径")
    parser.add_argument("--style", default="vlog", choices=["cinematic", "douyin", "vlog", "product"])
    parser.add_argument("--output", default=None, help="输出目录")
    parser.add_argument("--test", action="store_true", help="运行预设测试用例")
    parser.add_argument("--build", action="store_true", help="构建剪映工程（端到端闭环）")
    parser.add_argument("--project-name", default=None, help="剪映工程名称")
    args = parser.parse_args()

    # 配置logging（命令行运行时输出到控制台）
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    output_dir = args.output or r"D:\DobaoWork_Project\Ai_Video_Editor\p3_pipeline_output"

    if args.test or not args.video:
        # 预设测试：4镜头情绪递进
        logger.info("=== P3 Pipeline 预设测试（4镜头情绪递进）===\n")
        test_segments = [
            Segment(index=0, start=0, end=4, duration=4, emotion="calm", scene_type="indoor",
                    pace="slow", intensity=0.3, content_type="establishing"),
            Segment(index=1, start=4, end=8, duration=4, emotion="happy", scene_type="outdoor_sunny",
                    pace="medium", intensity=0.7, content_type="portrait", dialogue="今天天气真好"),
            Segment(index=2, start=8, end=12, duration=4, emotion="excited", scene_type="action",
                    pace="fast", intensity=0.9, content_type="action", dialogue="冲啊！"),
            Segment(index=3, start=12, end=16, duration=4, emotion="warm", scene_type="indoor",
                    pace="slow", intensity=0.4, content_type="closeup", dialogue="明天见"),
        ]
        pipeline = P3Pipeline(style=args.style)
        result = pipeline.run_from_segments(test_segments, output_dir=output_dir)
        logger.info(f"\n=== Pipeline完成 ===")
        logger.info(f"输出目录: {output_dir}")
    else:
        if not os.path.exists(args.video):
            logger.error(f"错误: 视频文件不存在: {args.video}")
            sys.exit(1)
        pipeline = P3Pipeline(style=args.style)
        result = pipeline.run_from_video(args.video, output_dir=output_dir)

    # 构建剪映工程（端到端闭环）
    if args.build:
        logger.info(f"\n=== 构建剪映工程 ===")
        try:
            from p3_project_builder import build_full_project
            result_path = os.path.join(output_dir, "pipeline_result.json")
            proj_name = args.project_name or f"p3_{args.style}_build"
            draft_path = build_full_project(result_path, proj_name)
            logger.info(f"✅ 剪映工程已构建: {draft_path}")
        except Exception as e:
            logger.error(f"❌ 剪映工程构建失败: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
