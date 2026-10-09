"""
方案决策器 v1.0 (P21-2)
根据原型卡自动选择技术路线，评估可行性，输出实施方案

核心能力：
1. 多方案评分（2D精灵/3D渲染/I2V/纯剪映/混合）
2. 资源约束评估（GPU/显存/时间/素材）
3. 风险识别（透明通道/坐标系统/音画同步）
4. 输出实施计划（分阶段任务清单）

使用方法：
    from solution_planner import SolutionPlanner
    planner = SolutionPlanner()
    plan = planner.plan(prototype_card)
    logger.info(plan["recommendation"])
    plan.save("方案.json")
"""

import logging
logger = logging.getLogger(__name__)


import os
import json
from typing import List, Dict, Any
from dataclasses import dataclass, field, asdict


@dataclass
class TechniqueOption:
    """技术方案选项"""
    name: str
    description: str
    score: float = 0.0  # 0-100
    pros: List[str] = field(default_factory=list)
    cons: List[str] = field(default_factory=list)
    required_resources: Dict[str, Any] = field(default_factory=dict)
    risks: List[str] = field(default_factory=list)


@dataclass
class ImplementationPlan:
    """实施计划"""
    prototype_source: str
    recommendation: str
    confidence: float
    options: List[TechniqueOption] = field(default_factory=list)
    phases: List[Dict[str, Any]] = field(default_factory=list)
    resource_requirements: Dict[str, Any] = field(default_factory=dict)
    risks: List[str] = field(default_factory=list)
    key_decisions: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    def save(self, path: str):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    def summary(self) -> str:
        lines = [
            "=" * 60,
            f"  实施方案: {self.recommendation}",
            f"  置信度: {self.confidence:.0f}%",
            "=" * 60,
            "",
            "  方案评分:",
        ]
        for opt in sorted(self.options, key=lambda x: x.score, reverse=True):
            marker = "★" if opt.name == self.recommendation else " "
            lines.append(f"  {marker} {opt.name}: {opt.score:.0f}分")
            for pro in opt.pros[:2]:
                lines.append(f"      + {pro}")
            for con in opt.cons[:2]:
                lines.append(f"      - {con}")
        lines.append("")
        lines.append("  实施阶段:")
        for i, phase in enumerate(self.phases, 1):
            lines.append(f"  {i}. {phase['name']} ({phase['duration']})")
            lines.append(f"     {phase['description']}")
        lines.append("")
        lines.append("  关键决策:")
        for d in self.key_decisions:
            lines.append(f"    - {d}")
        lines.append("")
        lines.append("  风险:")
        for r in self.risks[:5]:
            lines.append(f"    ⚠ {r}")
        lines.append("=" * 60)
        return "\n".join(lines)


class SolutionPlanner:
    """方案决策器"""

    def __init__(self, gpu_vram_gb: float = 12.0):
        self.gpu_vram_gb = gpu_vram_gb

    def _load_prototype(self, prototype) -> dict:
        """加载原型卡（支持dict或JSON路径）"""
        if isinstance(prototype, str):
            with open(prototype, "r", encoding="utf-8") as f:
                return json.load(f)
        elif isinstance(prototype, dict):
            return prototype
        else:
            return prototype.to_dict()

    def _evaluate_2d_sprite(self, proto: dict) -> TechniqueOption:
        """评估2D精灵方案"""
        score = 50.0
        pros = ["完全可控", "渲染快", "透明通道天然支持"]
        cons = ["需要角色素材", "动作有限", "美术工作量大"]
        risks = []

        # 2D动画适合角色少、场景固定的视频
        shot_density = proto.get("shot_density", "normal")
        if shot_density == "slow":
            score += 15  # 慢节奏适合2D
        if proto.get("total_shots", 0) <= 5:
            score += 10  # 镜头少适合2D

        # 检测是否有角色运动
        audio_events = proto.get("audio_events", [])
        sfx_count = sum(1 for e in audio_events if e.get("event_type") == "sfx")
        if sfx_count > 3:
            score -= 10  # 音效多意味着动作多，2D难做
            risks.append("多音效对应复杂动作，2D关键帧工作量大")

        # 竖屏适合2D
        if proto.get("visual_style", {}).get("orientation") == "portrait":
            score += 5

        return TechniqueOption(
            name="2D精灵+剪映关键帧",
            description="生成角色透明PNG，在剪映中用位置/缩放/旋转/透明度关键帧做动画",
            score=min(score, 95),
            pros=pros,
            cons=cons,
            required_resources={"角色PNG": "需要", "剪映": "必须", "GPU": "低"},
            risks=risks,
        )

    def _evaluate_3d_render(self, proto: dict) -> TechniqueOption:
        """评估3D渲染方案"""
        score = 40.0
        pros = ["动作自然", "镜头自由", "可复用模型"]
        cons = ["渲染慢", "学习成本高", "透明通道在剪映不生效"]
        risks = ["Blender MOV ProRes 4444的alpha在剪映5.9中不生效", "渲染时间长"]

        # 3D适合复杂镜头运动
        if proto.get("shot_density") == "fast":
            score += 10

        # 显存评估
        if self.gpu_vram_gb < 8:
            score -= 20
            risks.append("显存不足，3D渲染可能OOM")

        # 已知问题：剪映不支持透明视频
        score -= 15
        risks.append("剪映5.9不支持WebM/MOV透明通道，3D渲染需用绿幕抠像")

        return TechniqueOption(
            name="Blender 3D渲染",
            description="Blender建模+动画+渲染，输出视频后在剪映合成",
            score=max(score, 10),
            pros=pros,
            cons=cons,
            required_resources={"Blender": "必须", "GPU": "高", "时间": "长"},
            risks=risks,
        )

    def _evaluate_i2v(self, proto: dict) -> TechniqueOption:
        """评估I2V方案"""
        score = 55.0
        pros = ["动作自然", "真实感强", "无需建模"]
        cons = ["不可控", "一致性差", "生成慢", "显存需求高"]
        risks = ["角色一致性难以保证", "I2V生成可能不符合预期"]

        # I2V适合真实感、角色少的场景
        if proto.get("visual_style", {}).get("avg_brightness", 0.5) > 0.6:
            score += 5  # 亮场适合I2V

        # 显存评估
        if self.gpu_vram_gb >= 12:
            score += 10
        else:
            score -= 15
            risks.append("显存不足，I2V只能低分辨率")

        # 镜头多适合I2V（每个镜头一个生成）
        if proto.get("total_shots", 0) > 5:
            score += 5

        return TechniqueOption(
            name="ComfyUI I2V生成",
            description="混元/LTX I2V逐镜头生成，剪映合成",
            score=min(score, 90),
            pros=pros,
            cons=cons,
            required_resources={"ComfyUI": "必须", "GPU": "高", "参考图": "需要"},
            risks=risks,
        )

    def _evaluate_pure_jianying(self, proto: dict) -> TechniqueOption:
        """评估纯剪映方案"""
        score = 60.0
        pros = ["最快", "最稳定", "原生支持所有特效"]
        cons = ["效果有限", "依赖素材", "复杂动画难做"]
        risks = []

        # 纯剪映适合短视频、特效驱动
        if proto.get("shot_density") == "fast":
            score += 15  # 快节奏适合剪映卡点
        if proto.get("duration", 0) < 30:
            score += 10  # 短视频适合剪映

        # 音效多适合剪映（卡点）
        sfx_count = sum(1 for e in proto.get("audio_events", []) if e.get("event_type") == "sfx")
        if sfx_count > 3:
            score += 5

        return TechniqueOption(
            name="纯剪映特效合成",
            description="剪映原生特效+转场+文字+贴纸，无需外部生成",
            score=min(score, 95),
            pros=pros,
            cons=cons,
            required_resources={"剪映": "必须", "素材": "需要"},
            risks=risks,
        )

    def _evaluate_hybrid(self, proto: dict) -> TechniqueOption:
        """评估混合方案"""
        score = 70.0
        pros = ["各取所长", "质量可控", "效率平衡"]
        cons = ["流程复杂", "需要多工具协同", "质检点多"]
        risks = ["多工具间格式转换问题", "坐标系统不一致"]

        # 混合方案通常是最佳选择
        score += 10

        # 根据原型特点调整
        if proto.get("total_shots", 0) > 3:
            score += 5  # 多镜头适合混合

        return TechniqueOption(
            name="混合方案(2D+剪映+I2V)",
            description="角色用2D精灵，场景用I2V，合成用剪映关键帧",
            score=min(score, 95),
            pros=pros,
            cons=cons,
            required_resources={"角色PNG": "需要", "ComfyUI": "可选", "剪映": "必须"},
            risks=risks,
        )

    def _build_phases(self, recommendation: str, proto: dict) -> List[Dict[str, Any]]:
        """构建分阶段实施计划"""
        phases = []

        # 阶段1：原型验证
        phases.append({
            "name": "原型验证",
            "duration": "10-20分钟",
            "description": "用coord_verify确认坐标方向，用quick_qc建立质检基线",
            "tasks": ["坐标验证", "素材清单确认", "质检基线建立"],
            "exit_criteria": "坐标方向确认，素材齐全",
        })

        # 阶段2：素材准备
        if "2D" in recommendation or "混合" in recommendation:
            phases.append({
                "name": "素材准备",
                "duration": "20-40分钟",
                "description": "生成/收集角色透明PNG、背景图、音效文件",
                "tasks": ["角色去背景(remove_background)", "背景图生成", "音效准备"],
                "exit_criteria": "所有素材就位，去背景无白边",
            })

        if "I2V" in recommendation:
            phases.append({
                "name": "I2V生成",
                "duration": "30-60分钟",
                "description": "逐镜头生成视频片段，低分辨率先验证",
                "tasks": ["参考图生成", "I2V逐镜头生成", "片段质检"],
                "exit_criteria": "所有镜头生成完成，质量达标",
            })

        # 阶段3：单镜头验证
        phases.append({
            "name": "单镜头验证",
            "duration": "15-30分钟",
            "description": "先做1个关键镜头，验证位置/动画/音画同步",
            "tasks": ["关键镜头构建", "quick_qc质检", "坐标确认"],
            "exit_criteria": "关键镜头通过质检，位置正确",
        })

        # 阶段4：全片合成
        phases.append({
            "name": "全片合成",
            "duration": "20-40分钟",
            "description": "所有镜头按时间轴合成，添加转场/特效/音效",
            "tasks": ["多轨道合成", "转场添加", "音效对齐", "字幕添加"],
            "exit_criteria": "全片合成完成",
        })

        # 阶段5：质检交付
        phases.append({
            "name": "质检交付",
            "duration": "10-20分钟",
            "description": "quick_qc全片质检，修复问题，导出交付",
            "tasks": ["全片质检", "问题修复", "导出视频", "最终验收"],
            "exit_criteria": "质检0问题，用户验收通过",
        })

        return phases

    def plan(self, prototype, output_dir: str = None) -> ImplementationPlan:
        """
        根据原型卡生成实施方案

        Args:
            prototype: 原型卡（dict/JSON路径/PrototypeCard对象）
            output_dir: 输出目录

        Returns:
            ImplementationPlan: 实施方案
        """
        proto = self._load_prototype(prototype)

        logger.info(f"\n{'='*60}")
        logger.info(f"  方案决策器")
        logger.info(f"{'='*60}")
        logger.info(f"  原型: {os.path.basename(proto.get('source_file', 'unknown'))}")
        logger.info(f"  时长: {proto.get('duration', 0):.1f}s | 镜头: {proto.get('total_shots', 0)} | 密度: {proto.get('shot_density')}")

        # 评估各方案
        logger.info("\n[1/3] 评估技术方案...")
        options = [
            self._evaluate_2d_sprite(proto),
            self._evaluate_3d_render(proto),
            self._evaluate_i2v(proto),
            self._evaluate_pure_jianying(proto),
            self._evaluate_hybrid(proto),
        ]
        options.sort(key=lambda x: x.score, reverse=True)

        for opt in options:
            logger.info(f"  {opt.name}: {opt.score:.0f}分")

        # 选择最佳方案
        best = options[0]
        recommendation = best.name
        confidence = best.score

        logger.info(f"\n[2/3] 推荐方案: {recommendation} ({confidence:.0f}分)")

        # 关键决策
        key_decisions = []
        if "2D" in recommendation or "混合" in recommendation:
            key_decisions.append("角色使用透明PNG+剪映关键帧，不使用3D渲染（剪映不支持透明视频）")
            key_decisions.append("所有角色t=0必须设置完整初始状态（位置+alpha+scale+rotation）")
        if "I2V" in recommendation:
            key_decisions.append("I2V先低分辨率验证，再高分辨率生成")
            key_decisions.append("每个镜头独立生成，保证一致性")
        key_decisions.append("每阶段用quick_qc质检，不等全片完成才发现问题")
        key_decisions.append("坐标系统：x=-1左/1右，y=+1上/-1下（剪映y正=上）")

        # 风险汇总
        all_risks = []
        for opt in options:
            all_risks.extend(opt.risks)
        all_risks = list(set(all_risks))[:8]

        # 构建实施计划
        logger.info("[3/3] 构建实施计划...")
        phases = self._build_phases(recommendation, proto)

        plan = ImplementationPlan(
            prototype_source=proto.get("source_file", ""),
            recommendation=recommendation,
            confidence=confidence,
            options=options,
            phases=phases,
            resource_requirements={
                "gpu_vram_gb": self.gpu_vram_gb,
                "estimated_time": f"{len(phases) * 20}-{len(phases) * 40}分钟",
                "tools_needed": [opt.name for opt in options if opt.score > 40],
            },
            risks=all_risks,
            key_decisions=key_decisions,
        )

        # 保存
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            json_path = os.path.join(output_dir, "solution_plan.json")
            plan.save(json_path)
            md_path = os.path.join(output_dir, "solution_summary.md")
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(plan.summary())
            logger.info(f"\n✅ 方案已保存: {json_path}")

        logger.info(plan.summary())
        return plan


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="方案决策器 - 根据原型卡生成实施方案")
    parser.add_argument("prototype", help="原型卡JSON路径")
    parser.add_argument("-o", "--output", help="输出目录", default=None)
    args = parser.parse_args()

    planner = SolutionPlanner()
    planner.plan(args.prototype, args.output)
