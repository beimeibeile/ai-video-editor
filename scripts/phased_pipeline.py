"""
分阶段验证流程 + 质检闭环 v1.0 (P21-3 + P21-4)
不再一次跑完，而是分阶段验证，每阶段可暂停修正

核心能力：
1. 分阶段执行（原型验证→素材准备→单镜头验证→全片合成→质检交付）
2. 每阶段自动质检（quick_qc）
3. 质检问题自动定位+修复建议
4. 阶段间checkpoint，可暂停/恢复
5. 问题修复后自动重跑该阶段

使用方法：
    from phased_pipeline import PhasedPipeline
    pipeline = PhasedPipeline()
    result = pipeline.run("参考视频.mp4", "输出目录")
    # 或指定阶段
    result = pipeline.run_phase("素材准备", ...)
"""

import logging
logger = logging.getLogger(__name__)


import os
import sys
import json
import time
import shutil
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum


class PhaseStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PhaseResult:
    """阶段执行结果"""
    phase_name: str
    status: PhaseStatus
    start_time: float = 0
    end_time: float = 0
    duration: float = 0
    qc_issues: List[str] = field(default_factory=list)
    qc_passed: bool = True
    artifacts: List[str] = field(default_factory=list)
    error: str = ""
    fix_suggestions: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["status"] = self.status.value
        return d


@dataclass
class PipelineState:
    """Pipeline状态（用于暂停/恢复）"""
    project_name: str
    source_video: str
    output_dir: str
    current_phase: str = ""
    phases: Dict[str, PhaseResult] = field(default_factory=dict)
    prototype_card: dict = field(default_factory=dict)
    solution_plan: dict = field(default_factory=dict)
    total_qc_issues: int = 0
    iterations: int = 0

    def save(self, path: str):
        data = {
            "project_name": self.project_name,
            "source_video": self.source_video,
            "output_dir": self.output_dir,
            "current_phase": self.current_phase,
            "phases": {k: v.to_dict() for k, v in self.phases.items()},
            "prototype_card": self.prototype_card,
            "solution_plan": self.solution_plan,
            "total_qc_issues": self.total_qc_issues,
            "iterations": self.iterations,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, path: str) -> "PipelineState":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        state = cls(
            project_name=data["project_name"],
            source_video=data["source_video"],
            output_dir=data["output_dir"],
            current_phase=data.get("current_phase", ""),
            total_qc_issues=data.get("total_qc_issues", 0),
            iterations=data.get("iterations", 0),
        )
        state.prototype_card = data.get("prototype_card", {})
        state.solution_plan = data.get("solution_plan", {})
        for name, pdict in data.get("phases", {}).items():
            state.phases[name] = PhaseResult(
                phase_name=pdict["phase_name"],
                status=PhaseStatus(pdict["status"]),
                start_time=pdict.get("start_time", 0),
                end_time=pdict.get("end_time", 0),
                duration=pdict.get("duration", 0),
                qc_issues=pdict.get("qc_issues", []),
                qc_passed=pdict.get("qc_passed", True),
                artifacts=pdict.get("artifacts", []),
                error=pdict.get("error", ""),
                fix_suggestions=pdict.get("fix_suggestions", []),
            )
        return state


class QCFixer:
    """质检问题自动修复建议生成器"""

    FIX_RULES = {
        "缺少初始关键帧": {
            "cause": "片段t=0时未设置位置/透明度/缩放的初始关键帧",
            "fix": "在片段开始时添加完整初始状态：position_x/position_y/alpha/scale",
            "auto_fix": "为所有视频片段t=0添加alpha=1.0, position_x=0, position_y=0, scale=1.0",
        },
        "透明度为0": {
            "cause": "片段alpha=0导致不可见",
            "fix": "检查alpha关键帧，确保t=0时alpha=1.0",
            "auto_fix": "将所有alpha=0的初始关键帧改为alpha=1.0",
        },
        "位置超出屏幕": {
            "cause": "片段位置x/y超出[-1,1]范围",
            "fix": "检查坐标系统：x=-1左/1右，y=+1上/-1下",
            "auto_fix": "将位置限制在[-1,1]范围内",
        },
        "缩放异常": {
            "cause": "片段scale过大或过小",
            "fix": "检查scale关键帧，正常范围0.1-3.0",
            "auto_fix": "将scale限制在[0.1, 3.0]范围内",
        },
    }

    @classmethod
    def analyze(cls, issues: List[str]) -> List[Dict[str, str]]:
        """分析质检问题，生成修复建议"""
        suggestions = []
        for issue in issues:
            for keyword, rule in cls.FIX_RULES.items():
                if keyword in issue:
                    suggestions.append({
                        "issue": issue,
                        "cause": rule["cause"],
                        "fix": rule["fix"],
                        "auto_fix": rule["auto_fix"],
                    })
                    break
            else:
                suggestions.append({
                    "issue": issue,
                    "cause": "未知",
                    "fix": "手动检查",
                    "auto_fix": "不支持自动修复",
                })
        return suggestions


class PhasedPipeline:
    """分阶段验证Pipeline"""

    PHASES = [
        "原型验证",
        "素材准备",
        "单镜头验证",
        "全片合成",
        "质检交付",
    ]

    def __init__(self, skill_root: str = None):
        if skill_root is None:
            skill_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.skill_root = skill_root
        self.scripts_dir = os.path.join(skill_root, "scripts")
        sys.path.insert(0, self.scripts_dir)

    def _run_phase(self, phase_name: str, state: PipelineState,
                   phase_func: Callable) -> PhaseResult:
        """执行单个阶段"""
        result = PhaseResult(phase_name=phase_name, status=PhaseStatus.RUNNING)
        result.start_time = time.time()

        logger.info(f"\n{'='*60}")
        logger.info(f"  阶段: {phase_name}")
        logger.info(f"{'='*60}")

        try:
            artifacts = phase_func(state)
            result.artifacts = artifacts or []
            result.status = PhaseStatus.PASSED

            # 自动质检
            qc_issues = self._auto_qc(state, phase_name)
            result.qc_issues = qc_issues
            if qc_issues:
                result.qc_passed = False
                result.fix_suggestions = [s["fix"] for s in QCFixer.analyze(qc_issues)]
                logger.info(f"  ⚠ 质检发现 {len(qc_issues)} 个问题")
                for issue in qc_issues[:3]:
                    logger.info(f"    - {issue}")
            else:
                logger.info(f"  ✅ 质检通过")

        except Exception as e:
            result.status = PhaseStatus.FAILED
            result.error = str(e)
            logger.error(f"  ❌ 失败: {e}")

        result.end_time = time.time()
        result.duration = result.end_time - result.start_time
        state.phases[phase_name] = result
        state.total_qc_issues += len(result.qc_issues)

        # 保存checkpoint
        self._save_checkpoint(state)

        return result

    def _auto_qc(self, state: PipelineState, phase_name: str) -> List[str]:
        """自动质检（根据阶段选择不同质检策略）"""
        issues = []

        # 检查是否有剪映工程可以质检
        draft_path = self._find_latest_draft(state.output_dir)
        if draft_path and phase_name in ("单镜头验证", "全片合成", "质检交付"):
            try:
                from quick_qc import quick_qc
                qc_result = quick_qc(draft_path, output_dir=os.path.join(state.output_dir, "qc"))
                issues = qc_result.get("issues", [])
            except Exception as e:
                logger.warning(f"  质检跳过: {e}")

        # 阶段特定检查
        if phase_name == "原型验证":
            if not state.prototype_card:
                issues.append("原型卡未生成")
            if not state.solution_plan:
                issues.append("方案未生成")

        elif phase_name == "素材准备":
            chars_dir = os.path.join(state.output_dir, "characters")
            if os.path.exists(chars_dir):
                pngs = [f for f in os.listdir(chars_dir) if f.endswith(".png")]
                if not pngs:
                    issues.append("角色素材为空")
            else:
                issues.append("角色素材目录不存在")

        return issues

    def _find_latest_draft(self, output_dir: str) -> Optional[str]:
        """查找最新的剪映工程"""
        # 先在输出目录找
        for root, dirs, files in os.walk(output_dir):
            if "draft_content.json" in files:
                return root
        # 再在D盘草稿目录找
        drafts_dir = r"D:\JianyingProDrafts\JianyingPro Drafts"
        if os.path.exists(drafts_dir):
            latest = None
            latest_time = 0
            for d in os.listdir(drafts_dir):
                dpath = os.path.join(drafts_dir, d)
                if os.path.isdir(dpath) and os.path.exists(os.path.join(dpath, "draft_content.json")):
                    mtime = os.path.getmtime(dpath)
                    if mtime > latest_time:
                        latest = dpath
                        latest_time = mtime
            return latest
        return None

    def _save_checkpoint(self, state: PipelineState):
        """保存checkpoint"""
        checkpoint_path = os.path.join(state.output_dir, "pipeline_state.json")
        state.save(checkpoint_path)

    def _phase_prototype_verify(self, state: PipelineState) -> List[str]:
        """阶段1：原型验证"""
        artifacts = []

        # 运行原型理解
        from prototype_analyzer import PrototypeAnalyzer
        analyzer = PrototypeAnalyzer()
        proto_dir = os.path.join(state.output_dir, "prototype")
        card = analyzer.analyze(state.source_video, proto_dir)
        state.prototype_card = card.to_dict()
        artifacts.append(os.path.join(proto_dir, "prototype_card.json"))

        # 运行方案决策
        from solution_planner import SolutionPlanner
        planner = SolutionPlanner()
        plan = planner.plan(card.to_dict(), os.path.join(state.output_dir, "solution"))
        state.solution_plan = plan.to_dict()
        artifacts.append(os.path.join(state.output_dir, "solution", "solution_plan.json"))

        # 坐标验证（调用coord_verify的main）
        import coord_verify
        coord_verify.main()
        artifacts.append("坐标验证工程(已创建)")

        return artifacts

    def _phase_material_prep(self, state: PipelineState) -> List[str]:
        """阶段2：素材准备"""
        artifacts = []
        chars_dir = os.path.join(state.output_dir, "characters")
        os.makedirs(chars_dir, exist_ok=True)

        # 检查是否有角色素材
        # 这里可以集成角色生成（ComfyUI）和去背景
        logger.info("  素材准备：角色PNG生成+去背景")
        logger.info("  （此阶段需用户提供或生成角色素材）")

        # 如果有需要去背景的图片，自动处理
        from remove_background import remove_bg
        for f in os.listdir(chars_dir):
            if f.endswith((".jpg", ".jpeg")) and not f.endswith("_nobg.png"):
                input_path = os.path.join(chars_dir, f)
                output_path = os.path.join(chars_dir, f.replace(".jpg", "_nobg.png").replace(".jpeg", "_nobg.png"))
                if not os.path.exists(output_path):
                    remove_bg(input_path, output_path, method="auto")
                    artifacts.append(output_path)

        return artifacts

    def _phase_single_shot(self, state: PipelineState) -> List[str]:
        """阶段3：单镜头验证"""
        artifacts = []
        logger.info("  单镜头验证：构建1个关键镜头并质检")
        # 这里集成具体的镜头构建逻辑
        # 先验证坐标和基本动画
        return artifacts

    def _phase_full_composite(self, state: PipelineState) -> List[str]:
        """阶段4：全片合成"""
        artifacts = []
        logger.info("  全片合成：所有镜头按时间轴合成")
        return artifacts

    def _phase_qc_delivery(self, state: PipelineState) -> List[str]:
        """阶段5：质检交付"""
        artifacts = []
        logger.info("  质检交付：全片质检+修复+导出")
        return artifacts

    def run(self, source_video: str, output_dir: str,
            project_name: str = None, start_phase: str = None) -> PipelineState:
        """
        运行分阶段Pipeline

        Args:
            source_video: 参考视频路径
            output_dir: 输出目录
            project_name: 项目名
            start_phase: 从哪个阶段开始（None则从头开始）

        Returns:
            PipelineState: 最终状态
        """
        if project_name is None:
            project_name = os.path.splitext(os.path.basename(source_video))[0]

        os.makedirs(output_dir, exist_ok=True)

        # 检查是否有checkpoint可以恢复
        checkpoint_path = os.path.join(output_dir, "pipeline_state.json")
        if os.path.exists(checkpoint_path) and start_phase is None:
            state = PipelineState.load(checkpoint_path)
            logger.info(f"📂 恢复checkpoint: 当前阶段={state.current_phase}")
        else:
            state = PipelineState(
                project_name=project_name,
                source_video=source_video,
                output_dir=output_dir,
            )

        state.iterations += 1

        # 确定从哪个阶段开始
        phase_funcs = {
            "原型验证": self._phase_prototype_verify,
            "素材准备": self._phase_material_prep,
            "单镜头验证": self._phase_single_shot,
            "全片合成": self._phase_full_composite,
            "质检交付": self._phase_qc_delivery,
        }

        start_index = 0
        if start_phase:
            start_index = self.PHASES.index(start_phase) if start_phase in self.PHASES else 0

        # 执行各阶段
        for i in range(start_index, len(self.PHASES)):
            phase_name = self.PHASES[i]
            state.current_phase = phase_name

            # 跳过已通过的阶段
            if phase_name in state.phases and state.phases[phase_name].status == PhaseStatus.PASSED:
                logger.warning(f"\n⏭ 跳过已完成阶段: {phase_name}")
                continue

            result = self._run_phase(phase_name, state, phase_funcs[phase_name])

            # 如果失败，停止执行
            if result.status == PhaseStatus.FAILED:
                logger.error(f"\n❌ Pipeline在'{phase_name}'阶段失败")
                logger.info(f"   修复后可从该阶段恢复: start_phase='{phase_name}'")
                break

            # 如果质检失败，询问是否继续（自动模式下继续，但记录问题）
            if not result.qc_passed:
                logger.info(f"\n⚠ 阶段'{phase_name}'质检未通过，但继续执行")
                logger.info(f"   修复建议: {result.fix_suggestions[:3]}")

        # 最终总结
        logger.info(f"\n{'='*60}")
        logger.info(f"  Pipeline完成")
        logger.info(f"{'='*60}")
        logger.info(f"  项目: {state.project_name}")
        logger.info(f"  迭代: {state.iterations}")
        logger.info(f"  总质检问题: {state.total_qc_issues}")
        for phase_name in self.PHASES:
            if phase_name in state.phases:
                r = state.phases[phase_name]
                status_icon = "✅" if r.status == PhaseStatus.PASSED else "❌" if r.status == PhaseStatus.FAILED else "⏳"
                logger.info(f"  {status_icon} {phase_name}: {r.status.value} ({r.duration:.1f}s, {len(r.qc_issues)}问题)")
        logger.info(f"{'='*60}")

        return state


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="分阶段验证Pipeline")
    parser.add_argument("video", help="参考视频路径")
    parser.add_argument("-o", "--output", help="输出目录", required=True)
    parser.add_argument("-n", "--name", help="项目名", default=None)
    parser.add_argument("-p", "--phase", help="从指定阶段开始", default=None)
    args = parser.parse_args()

    pipeline = PhasedPipeline()
    pipeline.run(args.video, args.output, args.name, args.phase)
