"""
Pipeline剧本驱动层 v1.0
将P0三模块（剧本引擎+智能调度器+能力注册中心）深度集成到E2E Pipeline
实现"输入需求→自动出片"全链路

流程:
1. 用户需求 → 剧本引擎生成剧本（场景/镜头/旁白）
2. 剧本 → 智能调度器分配特效/素材/轨道
3. 调度计划 → E2E Pipeline合成剪映工程
4. 工程 → 质量门检查
5. 输出报告

使用方法:
    from pipeline_script_driver import ScriptDrivenPipeline
    driver = ScriptDrivenPipeline()
    result = driver.run(
        topic="探店美食",
        video_type="exploration",
        duration=60,
        output_name="探店视频_自动生成"
    )
"""
import os
import sys
import json
from typing import Dict, Any, Optional, List
from datetime import datetime

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SKILL_ROOT)

# P0三模块
try:
    from cap_script_engine import ScriptEngine, VideoGenre
    _SCRIPT_ENGINE_AVAILABLE = True
except ImportError:
    _SCRIPT_ENGINE_AVAILABLE = False

try:
    from cap_smart_director import SmartDirector
    _SMART_DIRECTOR_AVAILABLE = True
except ImportError:
    _SMART_DIRECTOR_AVAILABLE = False

try:
    from cap_capability_registry import CapabilityRegistry
    _REGISTRY_AVAILABLE = True
except ImportError:
    _REGISTRY_AVAILABLE = False

# E2E Pipeline
try:
    from cap_e2e_pipeline.pipeline import E2EPipeline
    _PIPELINE_AVAILABLE = True
except ImportError:
    _PIPELINE_AVAILABLE = False

# 质量门
try:
    from cap_creative.draft_quality_checker import DraftQualityChecker
    _QUALITY_GATE_AVAILABLE = True
except ImportError:
    _QUALITY_GATE_AVAILABLE = False

# 帧对齐工具
try:
    from scripts.draft_frame_aligner import align_draft_to_frames
    _FRAME_ALIGNER_AVAILABLE = True
except ImportError:
    _FRAME_ALIGNER_AVAILABLE = False


class ScriptDrivenPipeline:
    """剧本驱动的端到端视频生成Pipeline"""

    def __init__(self, project_dir: str = None, output_dir: str = None):
        """
        Args:
            project_dir: 项目工作目录（素材/中间文件）
            output_dir: 输出目录（剪映工程）
        """
        self.project_dir = project_dir or os.path.join(SKILL_ROOT, "script_outputs")
        self.output_dir = output_dir or os.path.join(SKILL_ROOT, "outputs")
        os.makedirs(self.project_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)

        self.script_engine = ScriptEngine() if _SCRIPT_ENGINE_AVAILABLE else None
        self.smart_director = SmartDirector() if _SMART_DIRECTOR_AVAILABLE else None
        self.registry = CapabilityRegistry() if _REGISTRY_AVAILABLE else None
        self.pipeline = E2EPipeline(project_dir=self.project_dir) if _PIPELINE_AVAILABLE else None

        self._check_dependencies()

    def _check_dependencies(self) -> Dict[str, bool]:
        """检查依赖可用性"""
        deps = {
            "剧本引擎": _SCRIPT_ENGINE_AVAILABLE,
            "智能调度器": _SMART_DIRECTOR_AVAILABLE,
            "能力注册中心": _REGISTRY_AVAILABLE,
            "E2E Pipeline": _PIPELINE_AVAILABLE,
            "质量门": _QUALITY_GATE_AVAILABLE,
            "帧对齐工具": _FRAME_ALIGNER_AVAILABLE,
        }
        print("=" * 60)
        print("📋 剧本驱动Pipeline - 依赖检查")
        print("=" * 60)
        for name, available in deps.items():
            status = "✅" if available else "❌"
            print(f"  {status} {name}")
        print()
        return deps

    def generate_script(self, topic: str, video_type: str = "exploration",
                        duration: int = 60, style: str = "default") -> Dict[str, Any]:
        """
        Step 1: 生成剧本

        Args:
            topic: 视频主题
            video_type: 视频类型 (exploration/vlog/tutorial/product/emotional/story)
            duration: 目标时长（秒）
            style: 风格预设

        Returns:
            剧本字典
        """
        if not self.script_engine:
            raise RuntimeError("剧本引擎不可用")

        print(f"\n{'='*60}")
        print(f"📝 Step 1: 生成剧本")
        print(f"{'='*60}")
        print(f"  主题: {topic}")
        print(f"  类型: {video_type}")
        print(f"  时长: {duration}秒")

        # video_type字符串映射到VideoGenre枚举
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
        genre = genre_map.get(video_type.lower(), VideoGenre.CUSTOM)
        script = self.script_engine.generate(
            idea=topic,
            genre=genre,
            duration=float(duration),
        )

        # 验证剧本
        validation = self.script_engine.validate(script)
        if not validation["valid"]:
            print(f"  ⚠️ 剧本验证警告: {validation['issues']}")

        # 保存剧本
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        script_path = os.path.join(self.project_dir, f"script_{timestamp}.json")
        self.script_engine.save(script, script_path)

        print(f"  ✅ 剧本生成完成: {len(script.scenes)}场景, {script.total_shots}镜头")
        print(f"  📄 剧本已保存: {script_path}")

        return script

    def direct(self, script: Dict[str, Any]) -> Dict[str, Any]:
        """
        Step 2: 智能调度（特效/素材/轨道分配）

        Args:
            script: 剧本字典

        Returns:
            调度计划字典
        """
        if not self.smart_director:
            raise RuntimeError("智能调度器不可用")

        print(f"\n{'='*60}")
        print(f"🎬 Step 2: 智能调度")
        print(f"{'='*60}")

        direction = self.smart_director.direct(script)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        direction_path = os.path.join(self.project_dir, f"direction_{timestamp}.json")
        self.smart_director.save(direction, direction_path)

        # 统计
        effect_counts = {}
        for shot in direction.shot_directions:
            for eff in shot.effects:
                effect_counts[eff.effect_name] = effect_counts.get(eff.effect_name, 0) + 1

        print(f"  ✅ 调度完成: {len(direction.shot_directions)}镜头")
        print(f"  🎨 特效分配: {effect_counts}")
        print(f"  📄 调度计划已保存: {direction_path}")

        return direction.to_dict()

    def synthesize(self, direction: Dict[str, Any], project_name: str,
                   hook_effect: str = "wipe", theme: str = "",
                   duration: float = 30.0) -> Dict[str, Any]:
        """
        Step 3: 剪映工程合成

        Args:
            direction: 调度计划（字典）
            project_name: 工程名
            hook_effect: 钩子特效（wipe/subtitle_bar/character_card等）
            theme: 视频主题
            duration: 目标时长

        Returns:
            合成结果
        """
        if not self.pipeline:
            raise RuntimeError("E2E Pipeline不可用")

        print(f"\n{'='*60}")
        print(f"🎞️ Step 3: 剪映工程合成")
        print(f"{'='*60}")
        print(f"  工程名: {project_name}")
        print(f"  钩子特效: {hook_effect}")

        # 从调度计划提取素材列表
        input_images = []
        for shot in direction.get("shots", []):
            for mat in shot.get("materials", []):
                mat_path = mat.get("source") or mat.get("path")
                if mat_path and os.path.exists(mat_path):
                    input_images.append(mat_path)

        # 从调度计划提取字幕文本
        custom_subtitles = []
        for shot in direction.get("shots", []):
            narration = shot.get("narration") or shot.get("text") or ""
            if narration:
                custom_subtitles.append(narration)

        shot_count = len(direction.get("shots", [])) or 5

        # 调用pipeline合成（匹配E2EPipeline.run实际接口）
        result = self.pipeline.run(
            theme=theme or "自动生成视频",
            duration=duration,
            shot_count=shot_count,
            project_name=project_name,
            custom_subtitles=custom_subtitles if custom_subtitles else None,
            input_images=input_images if input_images else None,
            hook_effect=hook_effect,
            use_ltx=False,
            add_bgm=False,
        )

        draft_path = result.get("draft_path", "")
        print(f"  ✅ 工程合成完成: {draft_path}")
        print(f"  📊 片段数: {result.get('segment_count', '?')}")
        print(f"  ⏱️ 时长: {result.get('duration', '?')}秒")

        return result

    def quality_check(self, draft_path: str) -> Optional[Dict[str, Any]]:
        """
        Step 4: 质量门检查

        Args:
            draft_path: 剪映工程路径

        Returns:
            质量门报告
        """
        if not _QUALITY_GATE_AVAILABLE:
            print("  ⚠️ 质量门不可用，跳过")
            return None

        print(f"\n{'='*60}")
        print(f"🔍 Step 4: 质量门检查")
        print(f"{'='*60}")

        # 先帧对齐
        if _FRAME_ALIGNER_AVAILABLE:
            print("  🔧 执行帧对齐...")
            align_draft_to_frames(draft_path, fps=30, backup=True)

        # 质量门检查
        checker = DraftQualityChecker(draft_path)
        report = checker.check()

        # 保存HTML报告
        report_path = os.path.join(self.project_dir, "quality_report.html")
        checker.save_html_report(report, report_path)

        print(f"  📄 报告已保存: {report_path}")
        return report

    def run(self, topic: str, video_type: str = "exploration",
            duration: int = 60, project_name: str = None,
            hook_effect: str = "wipe", style: str = "default") -> Dict[str, Any]:
        """
        全链路运行：输入需求 → 自动出片

        Args:
            topic: 视频主题
            video_type: 视频类型
            duration: 目标时长（秒）
            project_name: 工程名（默认自动生成）
            hook_effect: 钩子特效
            style: 风格预设

        Returns:
            完整结果字典（剧本/调度/合成/质量门）
        """
        if project_name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            project_name = f"ScriptDriven_{timestamp}"

        start_time = datetime.now()
        print(f"\n{'🚀'*20}")
        print(f"剧本驱动Pipeline - 全链路启动")
        print(f"主题: {topic} | 类型: {video_type} | 时长: {duration}秒")
        print(f"{'🚀'*20}")

        result = {
            "status": "running",
            "topic": topic,
            "video_type": video_type,
            "target_duration": duration,
            "project_name": project_name,
            "steps": {},
        }

        try:
            # Step 1: 生成剧本
            script = self.generate_script(topic, video_type, duration, style)
            result["steps"]["script"] = {"status": "success", "path": os.path.join(self.project_dir, "script_*.json")}

            # Step 2: 智能调度
            direction = self.direct(script)
            result["steps"]["direction"] = {"status": "success"}

            # Step 3: 剪映合成
            synth_result = self.synthesize(direction, project_name, hook_effect, theme=topic, duration=duration)
            result["steps"]["synthesize"] = synth_result
            draft_path = synth_result.get("draft_path", "")

            # Step 4: 质量门
            if draft_path and os.path.exists(draft_path):
                quality_report = self.quality_check(draft_path)
                result["steps"]["quality"] = {
                    "status": "success",
                    "passed": quality_report.all_passed if quality_report else None,
                }
            else:
                result["steps"]["quality"] = {"status": "skipped", "reason": "工程路径不存在"}

            result["status"] = "success"
            elapsed = (datetime.now() - start_time).total_seconds()
            result["elapsed_seconds"] = elapsed

            print(f"\n{'✅'*20}")
            print(f"全链路完成! 耗时: {elapsed:.1f}秒")
            print(f"工程: {draft_path}")
            print(f"{'✅'*20}")

        except Exception as e:
            result["status"] = "failed"
            result["error"] = str(e)
            print(f"\n❌ 全链路失败: {e}")
            import traceback
            traceback.print_exc()

        return result


if __name__ == "__main__":
    # 测试运行
    driver = ScriptDrivenPipeline()
    result = driver.run(
        topic="城市夜景探店",
        video_type="exploration",
        duration=30,
        project_name="ScriptDriven_Test",
        hook_effect="wipe",
    )
    print(f"\n最终状态: {result['status']}")
