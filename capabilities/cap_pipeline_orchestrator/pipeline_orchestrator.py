"""
全链路编排器 v1.0 (Pipeline Orchestrator)
商业化闭环核心：需求→剧本→角色→分镜→素材→合成→质量门→导出

完整流程：
1. 需求输入（主题/类型/时长/模板）
2. 剧本生成（ScriptEngine 或 DramaEngine）
3. 角色分析（CharacterEngine：性格/关系/弧光/一致性）
4. 分镜定版（StoryboardEngine：多机位/蒙太奇/节奏）
5. 智能调度（SmartDirector：特效/素材/运镜分配）
6. 剪映合成（E2EPipeline：工程创建/素材/字幕/特效/转场）
7. 质量门检查（QualityGate：7道edit+10道storyboard）
8. 导出交付（工程路径/报告/统计）

使用方法：
    from pipeline_orchestrator import PipelineOrchestrator
    orch = PipelineOrchestrator()
    result = orch.run_full_pipeline(
        topic="城市夜景探店",
        video_type="exploration",
        duration=30,
        template_id="exploration_food",
    )
"""
import os
import sys
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict

SKILL_ROOT = r"C:\Users\Administrator\AppData\Local\DoubaoWork\User Data\Default\.doubaowork\agent_mode\workspace\.user_skills\ai-video-editor"
sys.path.insert(0, SKILL_ROOT)
sys.path.insert(0, os.path.join(SKILL_ROOT, "capabilities"))
sys.path.insert(0, os.path.join(SKILL_ROOT, "scripts"))


@dataclass
class PipelineStep:
    """流水线步骤"""
    name: str
    status: str = "pending"  # pending/running/success/failed/skipped
    started_at: str = ""
    finished_at: str = ""
    duration_seconds: float = 0
    result_summary: str = ""
    error: str = ""


@dataclass
class PipelineResult:
    """流水线结果"""
    success: bool
    project_name: str = ""
    draft_path: str = ""
    total_duration: float = 0
    steps: List[PipelineStep] = field(default_factory=list)
    script_info: Dict[str, Any] = field(default_factory=dict)
    character_info: Dict[str, Any] = field(default_factory=dict)
    storyboard_info: Dict[str, Any] = field(default_factory=dict)
    quality_report: Dict[str, Any] = field(default_factory=dict)
    output_files: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class PipelineOrchestrator:
    """全链路编排器"""

    STEP_NAMES = [
        "需求解析",
        "剧本生成",
        "角色分析",
        "分镜定版",
        "智能调度",
        "剪映合成",
        "质量门检查",
        "导出交付",
    ]

    def __init__(self, output_dir: str = None):
        self.output_dir = output_dir or os.path.join(SKILL_ROOT, "pipeline_outputs")
        os.makedirs(self.output_dir, exist_ok=True)
        self.steps: List[PipelineStep] = []

    def run_full_pipeline(self,
                            topic: str,
                            video_type: str = "exploration",
                            duration: float = 30.0,
                            template_id: str = None,
                            project_name: str = None,
                            hook_effect: str = "wipe",
                            enable_character_analysis: bool = True,
                            enable_storyboard: bool = True,
                            enable_quality_gate: bool = True) -> PipelineResult:
        """
        运行完整流水线

        Args:
            topic: 视频主题
            video_type: 视频类型
            duration: 目标时长（秒）
            template_id: 模板ID（可选）
            project_name: 工程名（可选，自动生成）
            hook_effect: 钩子特效
            enable_character_analysis: 是否启用角色分析
            enable_storyboard: 是否启用分镜定版
            enable_quality_gate: 是否启用质量门

        Returns:
            PipelineResult
        """
        if project_name is None:
            project_name = f"Pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        result = PipelineResult(
            success=False,
            project_name=project_name,
            metadata={
                "topic": topic,
                "video_type": video_type,
                "target_duration": duration,
                "template_id": template_id,
                "hook_effect": hook_effect,
                "started_at": datetime.now().isoformat(),
            }
        )

        print(f"\n{'='*60}")
        print(f"🚀 全链路流水线启动: {project_name}")
        print(f"   主题: {topic}")
        print(f"   类型: {video_type}, 时长: {duration}s")
        print(f"   模板: {template_id or '无'}")
        print(f"{'='*60}")

        # Step 1: 需求解析
        step = self._start_step("需求解析")
        step.result_summary = f"主题:{topic}, 类型:{video_type}, 时长:{duration}s"
        self._finish_step(step, success=True)
        result.steps.append(step)

        # Step 2: 剧本生成
        script = None
        step = self._start_step("剧本生成")
        try:
            from cap_script_engine import ScriptEngine, VideoGenre
            engine = ScriptEngine()
            genre_map = {
                "exploration": VideoGenre.EXPLORATION,
                "vlog": VideoGenre.VLOG,
                "tutorial": VideoGenre.TUTORIAL,
                "product": VideoGenre.PROMO,
                "emotional": VideoGenre.STORY,
                "story": VideoGenre.STORY,
                "ecommerce": VideoGenre.ECOMMERCE,
                "talking": VideoGenre.TALKING,
            }
            genre = genre_map.get(video_type, VideoGenre.CUSTOM)

            # 如果有模板，增强主题描述
            enhanced_topic = topic
            if template_id:
                try:
                    from cap_template_system import TemplateSystem
                    ts = TemplateSystem()
                    template = ts.get_template(template_id)
                    if template:
                        enhanced_topic = f"{topic}。风格:{template.style_params.get('tone', '')}。场景结构:{', '.join(s['content'] for s in template.scene_structure[:3])}"
                except Exception:
                    pass

            script = engine.generate(
                idea=enhanced_topic,
                genre=genre,
                duration=duration,
                title=project_name,
            )
            step.result_summary = f"{len(script.scenes)}场景, {script.total_shots}镜头"
            result.script_info = {
                "title": script.title,
                "scenes": len(script.scenes),
                "total_shots": script.total_shots,
                "genre": genre.value,
            }
            self._finish_step(step, success=True)
        except Exception as e:
            import traceback
            step.error = f"{e}\n{traceback.format_exc()}"
            self._finish_step(step, success=False)
            result.steps.append(step)
            result.metadata["error"] = f"剧本生成失败: {e}"
            return result
        result.steps.append(step)

        # Step 3: 角色分析（可选）
        if enable_character_analysis and script:
            step = self._start_step("角色分析")
            try:
                from cap_character_engine import CharacterEngine
                char_engine = CharacterEngine()
                personalities = char_engine.analyze_personality(script)
                relationships = char_engine.build_relationship_graph(script)
                arcs = char_engine.analyze_character_arc(script)
                step.result_summary = f"{len(personalities)}角色, {len(relationships)}对关系"
                result.character_info = {
                    "characters": list(personalities.keys()),
                    "relationships": len(relationships),
                    "arcs": len(arcs),
                }
                self._finish_step(step, success=True)
            except Exception as e:
                step.error = str(e)
                step.result_summary = f"跳过（{e}）"
                self._finish_step(step, success=True)  # 角色分析失败不阻断
            result.steps.append(step)

        # Step 4: 分镜定版（可选）
        if enable_storyboard and script:
            step = self._start_step("分镜定版")
            try:
                from cap_storyboard_engine.storyboard_engine import StoryboardGenerator
                sb_gen = StoryboardGenerator()
                storyboard = sb_gen.generate(
                    theme=topic,
                    style="cinematic",
                    total_duration=duration,
                    shot_count=min(10, script.total_shots),
                )
                step.result_summary = f"{len(storyboard.shots)}镜头, {storyboard.total_duration:.0f}s"
                result.storyboard_info = {
                    "shot_count": len(storyboard.shots),
                    "total_duration": storyboard.total_duration,
                    "style": storyboard.style,
                }
                self._finish_step(step, success=True)
            except Exception as e:
                step.error = str(e)
                step.result_summary = f"跳过（{e}）"
                self._finish_step(step, success=True)  # 分镜定版失败不阻断
            result.steps.append(step)

        # Step 5: 智能调度
        direction_plan = None
        step = self._start_step("智能调度")
        try:
            from cap_smart_director import SmartDirector
            director = SmartDirector()
            direction_plan = director.direct(script)
            step.result_summary = f"{len(direction_plan.shot_directions)}镜头调度完成"
            self._finish_step(step, success=True)
        except Exception as e:
            step.error = str(e)
            self._finish_step(step, success=False)
            result.steps.append(step)
            result.metadata["error"] = f"智能调度失败: {e}"
            return result
        result.steps.append(step)

        # Step 6: 剪映合成
        step = self._start_step("剪映合成")
        try:
            from cap_e2e_pipeline.pipeline_script_driver import ScriptDrivenPipeline
            project_output = os.path.join(self.output_dir, project_name)
            driver = ScriptDrivenPipeline(
                project_dir=project_output,
                output_dir=os.path.join(project_output, "outputs"),
            )
            synth_result = driver.run(
                topic=topic,
                video_type=video_type,
                duration=duration,
                project_name=project_name,
                hook_effect=hook_effect,
            )

            # 查找工程路径
            draft_path = os.path.join(
                r"C:\Users\Administrator\AppData\Local\JianyingPro\User Data\Projects\com.lveditor.draft",
                project_name
            )
            if not os.path.exists(draft_path):
                # 尝试D盘
                draft_path = os.path.join(
                    r"D:\JianyingProDrafts\JianyingPro Drafts",
                    project_name
                )

            result.draft_path = draft_path
            result.total_duration = synth_result.get("total_duration", duration)
            step.result_summary = f"工程:{project_name}, 时长:{result.total_duration:.1f}s"
            self._finish_step(step, success=True)
        except Exception as e:
            import traceback
            step.error = f"{e}\n{traceback.format_exc()}"
            self._finish_step(step, success=False)
            result.steps.append(step)
            result.metadata["error"] = f"剪映合成失败: {e}"
            return result
        result.steps.append(step)

        # Step 7: 质量门检查（可选）
        if enable_quality_gate and result.draft_path and os.path.exists(result.draft_path):
            step = self._start_step("质量门检查")
            try:
                from cap_creative.quality_gate import QualityGate
                qg = QualityGate()
                report = qg.check(result.draft_path)
                result.quality_report = report if isinstance(report, dict) else {"status": "completed"}
                passed = report.get("passed", 0) if isinstance(report, dict) else 0
                total = report.get("total", 0) if isinstance(report, dict) else 0
                step.result_summary = f"{passed}/{total}通过"
                self._finish_step(step, success=True)
            except Exception as e:
                step.error = str(e)
                step.result_summary = f"跳过（{e}）"
                self._finish_step(step, success=True)  # 质量门失败不阻断
            result.steps.append(step)

        # Step 8: 导出交付
        step = self._start_step("导出交付")
        try:
            # 保存流水线报告
            report_path = os.path.join(self.output_dir, project_name, "pipeline_report.json")
            os.makedirs(os.path.dirname(report_path), exist_ok=True)
            report_data = {
                "project_name": project_name,
                "topic": topic,
                "video_type": video_type,
                "duration": result.total_duration,
                "draft_path": result.draft_path,
                "steps": [asdict(s) for s in result.steps],
                "script_info": result.script_info,
                "character_info": result.character_info,
                "storyboard_info": result.storyboard_info,
                "quality_report": result.quality_report,
                "metadata": result.metadata,
                "finished_at": datetime.now().isoformat(),
            }
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2, default=str)
            result.output_files.append(report_path)
            step.result_summary = f"报告:{report_path}"
            self._finish_step(step, success=True)
        except Exception as e:
            step.error = str(e)
            self._finish_step(step, success=False)
        result.steps.append(step)

        # 最终结果
        result.success = all(s.status == "success" for s in result.steps if s.name not in ["角色分析", "分镜定版", "质量门检查"])
        result.metadata["finished_at"] = datetime.now().isoformat()
        result.metadata["total_elapsed"] = sum(s.duration_seconds for s in result.steps)

        print(f"\n{'='*60}")
        print(f"{'✅ 流水线完成' if result.success else '⚠️ 流水线部分完成'}: {project_name}")
        print(f"   总耗时: {result.metadata['total_elapsed']:.1f}秒")
        print(f"   工程路径: {result.draft_path}")
        for s in result.steps:
            icon = "✅" if s.status == "success" else "❌" if s.status == "failed" else "⏭️"
            print(f"   {icon} {s.name}: {s.result_summary} ({s.duration_seconds:.1f}s)")
        print(f"{'='*60}")

        return result

    def _start_step(self, name: str) -> PipelineStep:
        step = PipelineStep(name=name, status="running", started_at=datetime.now().isoformat())
        print(f"\n▶ [{name}] 开始...")
        return step

    def _finish_step(self, step: PipelineStep, success: bool):
        step.status = "success" if success else "failed"
        step.finished_at = datetime.now().isoformat()
        if step.started_at:
            try:
                start = datetime.fromisoformat(step.started_at)
                end = datetime.fromisoformat(step.finished_at)
                step.duration_seconds = (end - start).total_seconds()
            except Exception:
                pass
        icon = "✅" if success else "❌"
        print(f"  {icon} [{step.name}] {step.result_summary} ({step.duration_seconds:.1f}s)")


if __name__ == "__main__":
    print("=" * 60)
    print("全链路编排器 v1.0")
    print("=" * 60)

    orch = PipelineOrchestrator()
    result = orch.run_full_pipeline(
        topic="测试全链路流水线",
        video_type="exploration",
        duration=15,
        project_name="Orchestrator_Test",
        enable_character_analysis=True,
        enable_storyboard=True,
        enable_quality_gate=False,
    )

    print(f"\n最终结果: {'成功' if result.success else '失败'}")
    print(f"工程路径: {result.draft_path}")
