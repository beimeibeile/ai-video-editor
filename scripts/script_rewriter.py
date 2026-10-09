"""
剧本改写加工统一入口 (Script Rewriter)

核心思想：创意剧本和改编剧本都是创造能力，只是约束力度不同。
- 创意生成：约束少（一句话/创意），自由度高
- 改编改写：约束多（原始剧本），需在保留核心的前提下重构

完整流程链路：
  创意模式: 创意输入 → script_engine生成 → quality_engine增强 → adapter适配 → enhancer深度增强 → 标准分镜
  改编模式: 原始剧本 → parser解析 → quality_engine增强 → adapter适配 → enhancer深度增强 → 标准分镜

约束参数：
- style: 风格（搞笑/煽情/悬疑/热血/治愈/写实）
- duration: 目标时长（秒）
- platform: 平台（抖音/小红书/B站/视频号）
- audience: 目标受众
- tone: 语气调性
"""

import logging
logger = logging.getLogger(__name__)


import os
import sys
import json
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum

# 路径配置
RUNTIME_DIR = os.path.dirname(os.path.abspath(__file__))
CAPABILITIES_DIR = os.path.join(os.path.dirname(RUNTIME_DIR), "capabilities")
sys.path.insert(0, RUNTIME_DIR)
sys.path.insert(0, CAPABILITIES_DIR)


class RewriteMode(Enum):
    """改写模式"""
    CREATIVE = "creative"      # 创意生成（从0到1）
    ADAPT = "adapt"            # 改编改写（从1到1'）


class ScriptStyle(Enum):
    """剧本风格"""
    FUNNY = "funny"            # 搞笑
    EMOTIONAL = "emotional"    # 煽情
    SUSPENSE = "suspense"      # 悬疑
    PASSIONATE = "passionate"  # 热血
    HEALING = "healing"        # 治愈
    REALISTIC = "realistic"    # 写实
    CINEMATIC = "cinematic"    # 电影感


class TargetPlatform(Enum):
    """目标平台"""
    DOUYIN = "douyin"          # 抖音（竖屏，快节奏，前3秒钩子）
    XIAOHONGSHU = "xhs"        # 小红书（竖屏，种草/教程/生活）
    BILIBILI = "bilibili"      # B站（横屏，中长视频，深度内容）
    SHIPINHAO = "sph"          # 视频号（社交传播）


@dataclass
class RewriteConstraints:
    """改写约束参数"""
    style: str = "realistic"           # 风格
    duration: float = 30.0             # 目标时长（秒）
    platform: str = "douyin"           # 目标平台
    audience: str = "general"          # 目标受众
    tone: str = "neutral"              # 语气调性
    language: str = "zh-CN"            # 语言
    # 创意模式专用
    genre: str = "vlog"                # 视频类型（exploration/talking/ecommerce/vlog）
    # 改编模式专用
    preserve_core: bool = True         # 是否保留核心剧情
    preserve_characters: bool = True   # 是否保留角色
    preserve_setting: bool = True      # 是否保留场景设定
    # 高级约束
    max_scenes: int = 10               # 最大场景数
    max_shots_per_scene: int = 5       # 每场景最大镜头数
    hook_required: bool = True         # 是否必须有钩子
    cta_required: bool = True          # 是否必须有号召性结尾


@dataclass
class RewriteResult:
    """改写结果"""
    mode: str = ""                     # 模式（creative/adapt）
    title: str = ""                    # 剧本标题
    constraints: Dict[str, Any] = field(default_factory=dict)  # 使用的约束
    # 各阶段输出
    raw_script: str = ""               # 原始输入（创意描述或原始剧本）
    base_script: Dict[str, Any] = field(default_factory=dict)   # 基础剧本（script_engine或parser输出）
    quality_enhanced: Dict[str, Any] = field(default_factory=dict)  # 质量增强输出
    adapted: Dict[str, Any] = field(default_factory=dict)      # 适配输出
    final_script: Dict[str, Any] = field(default_factory=dict)  # 最终标准分镜（供P24翻译器使用）
    # 元数据
    stages_completed: List[str] = field(default_factory=list)  # 已完成的阶段
    llm_used: bool = False             # 是否使用了LLM
    processing_time: float = 0.0       # 处理时间（秒）
    errors: List[str] = field(default_factory=list)  # 错误信息
    quality_gates: List[Dict[str, Any]] = field(default_factory=list)  # 质量门检查结果
    quality_score: float = 0.0         # 质量评分（0-10）
    record_id: Optional[str] = None    # 记忆库记录ID
    inspiration: Optional[Dict[str, Any]] = None  # AnySearch灵感搜索结果
    llm_rewrite: Optional[Dict[str, Any]] = None  # 宿主LLM深度改写结果

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def save(self, output_path: str) -> str:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
        return output_path


class ScriptRewriter:
    """
    剧本改写加工统一入口

    统一处理创意生成和改编改写，流程化分发到各专业模块。
    """

    def __init__(self, use_llm: bool = True, memory_path: str = None):
        """
        初始化改写器

        Args:
            use_llm: 是否使用LLM（如果可用）
            memory_path: 记忆库路径（None则使用默认路径）
        """
        self.use_llm = use_llm
        self._modules = {}
        self._load_modules()

        # 记忆/自学习引擎（P27-2）
        try:
            from rewrite_memory import RewriteMemory
            self.memory = RewriteMemory(memory_path=memory_path)
        except Exception as e:
            self.memory = None
            logger.error(f"  ⚠️  rewrite_memory加载失败: {e}")

        # AnySearch灵感搜索器（P27-3）
        try:
            from anysearch_inspiration import AnySearchInspiration
            self.inspiration_searcher = AnySearchInspiration(
                python_path=r"C:\Users\Administrator\AppData\Local\Programs\Python\Python311\python.exe"
            )
        except Exception as e:
            self.inspiration_searcher = None
            logger.error(f"  ⚠️  anysearch_inspiration加载失败: {e}")

        # 宿主LLM深度改写器（P27-4）
        try:
            from host_llm_rewriter import HostLLMRewriter
            self.llm_rewriter = HostLLMRewriter()
        except Exception as e:
            self.llm_rewriter = None
            logger.error(f"  ⚠️  host_llm_rewriter加载失败: {e}")

    def _load_modules(self):
        """懒加载各专业模块"""
        # P23 解析器和增强器（已集成导演引擎）
        try:
            from script_parser import ScriptParser
            self._modules["parser"] = ScriptParser()
        except Exception as e:
            self._modules["parser"] = None
            logger.error(f"  ⚠️  script_parser加载失败: {e}")

        try:
            from script_enhancer import ScriptEnhancer
            self._modules["enhancer"] = ScriptEnhancer(use_llm=self.use_llm)
        except Exception as e:
            self._modules["enhancer"] = None
            logger.error(f"  ⚠️  script_enhancer加载失败: {e}")

        # 创意生成引擎（capabilities包，相对import）
        try:
            from cap_script_engine.script_engine import ScriptEngine
            self._modules["engine"] = ScriptEngine()
        except Exception as e:
            self._modules["engine"] = None
            logger.error(f"  ⚠️  script_engine加载失败: {e}")

        # 质量增强引擎（capabilities包，相对import）
        try:
            from cap_script_quality.script_quality_engine import ScriptQualityEngine
            self._modules["quality"] = ScriptQualityEngine()
        except Exception as e:
            self._modules["quality"] = None
            logger.error(f"  ⚠️  script_quality_engine加载失败: {e}")

        # 剧本适配器（capabilities包，相对import）
        try:
            from cap_script_adapter.script_adapter import ScriptAdapterEngine
            self._modules["adapter"] = ScriptAdapterEngine()
        except Exception as e:
            self._modules["adapter"] = None
            logger.error(f"  ⚠️  script_adapter加载失败: {e}")

        # 结构化剧本内核（节拍流+质量门，P27-1）
        try:
            from structured_script import parse_to_structured_script, run_quality_gates, to_standard_format
            self._modules["structured"] = {
                "parse": parse_to_structured_script,
                "quality_gates": run_quality_gates,
                "to_standard": to_standard_format,
            }
        except Exception as e:
            self._modules["structured"] = None
            logger.error(f"  ⚠️  structured_script加载失败: {e}")

    @property
    def llm_available(self) -> bool:
        """LLM是否可用"""
        enhancer = self._modules.get("enhancer")
        return enhancer is not None and enhancer.llm_available

    def rewrite(
        self,
        input_text: str,
        mode: str = "creative",
        constraints: Optional[RewriteConstraints] = None,
        title: str = "",
    ) -> RewriteResult:
        """
        统一改写入口

        Args:
            input_text: 输入文本（创意描述 或 原始剧本）
            mode: 模式（creative/adapt）
            constraints: 改写约束参数
            title: 剧本标题

        Returns:
            RewriteResult 改写结果
        """
        start_time = time.time()
        constraints = constraints or RewriteConstraints()
        result = RewriteResult(
            mode=mode,
            title=title or self._generate_title(input_text, mode),
            constraints=asdict(constraints),
            raw_script=input_text,
        )

        logger.info(f"\n{'='*60}")
        logger.info(f"剧本改写加工启动")
        logger.info(f"  模式: {'创意生成' if mode == 'creative' else '改编改写'}")
        logger.info(f"  标题: {result.title}")
        logger.info(f"  风格: {constraints.style} | 时长: {constraints.duration}s | 平台: {constraints.platform}")
        logger.info(f"  LLM: {'可用' if self.llm_available else '不可用(规则模式)'}")
        logger.info(f"{'='*60}")

        # ===== 灵感搜索（P27-3 AnySearch）=====
        inspiration_report = None
        if self.inspiration_searcher and self.inspiration_searcher.available:
            try:
                logger.info(f"\n[灵感搜索] 获取同类剧本和热门梗参考...")
                inspiration_report = self.inspiration_searcher.get_inspiration(
                    theme=input_text[:50],
                    style=constraints.style,
                    include_trending=True,
                    include_film=True,
                )
                result.inspiration = inspiration_report.to_dict()
                result.stages_completed.append("inspiration_search")
            except Exception as e:
                logger.warning(f"  ⚠️  灵感搜索跳过: {e}")

        try:
            if mode == "creative":
                self._process_creative(input_text, constraints, result, inspiration_report)
            elif mode == "adapt":
                self._process_adapt(input_text, constraints, result, inspiration_report)
            else:
                result.errors.append(f"不支持的模式: {mode}")
        except Exception as e:
            result.errors.append(f"处理异常: {str(e)}")
            import traceback
            traceback.print_exc()

        result.processing_time = time.time() - start_time
        result.llm_used = self.llm_available

        # ===== 自动记录到记忆库（P27-2 自学习）=====
        if self.memory and result.final_script:
            try:
                output_summary = {
                    "scenes": len(result.final_script.get("scenes", [])),
                    "characters": result.final_script.get("characters", []),
                    "beats": sum(len(s.get("shots", [])) for s in result.final_script.get("scenes", [])),
                    "stages": result.stages_completed,
                }
                constraints_dict = asdict(constraints) if hasattr(constraints, '__dataclass_fields__') else {}
                record = self.memory.record_rewrite(
                    mode=mode,
                    input_text=input_text,
                    constraints=constraints_dict,
                    output_summary=output_summary,
                    quality_score=result.quality_score,
                    quality_gates=result.quality_gates,
                )
                result.record_id = record.record_id
                logger.info(f"  📝 已记录到记忆库: {record.record_id}")
            except Exception as e:
                logger.error(f"  ⚠️  记忆记录失败: {e}")

        logger.info(f"\n{'='*60}")
        logger.info(f"改写完成: {result.title}")
        logger.info(f"  完成阶段: {', '.join(result.stages_completed)}")
        logger.info(f"  处理时间: {result.processing_time:.2f}s")
        if result.quality_score > 0:
            logger.info(f"  质量评分: {result.quality_score}/10")
        if result.errors:
            logger.error(f"  错误: {result.errors}")
        logger.info(f"{'='*60}\n")

        return result

    def _process_creative(
        self,
        idea: str,
        constraints: RewriteConstraints,
        result: RewriteResult,
        inspiration_report=None,
    ):
        """
        创意生成模式流程：
        idea → (灵感搜索) → script_engine生成基础剧本 → quality_engine增强 → adapter适配 → enhancer深度增强 → 标准分镜
        """
        # 灵感注入：将搜索到的热门梗和同类剧本参考融入创意
        enhanced_idea = idea
        if inspiration_report:
            try:
                trending = inspiration_report.trending_topics
                if trending:
                    hot_topics = [t.title for t in trending[:2]]
                    enhanced_idea = f"{idea}（参考热点: {', '.join(hot_topics)}）"
                    logger.info(f"  💡 灵感注入: {hot_topics}")
            except Exception:
                pass
        # 阶段1: 基础剧本生成
        logger.info(f"\n[阶段1] 创意生成 → 基础剧本")
        engine = self._modules.get("engine")
        if engine:
            try:
                base = engine.generate(
                    idea=enhanced_idea,
                    genre=constraints.genre,
                    duration=constraints.duration,
                    title=result.title,
                )
                result.base_script = self._to_serializable(base)
                result.stages_completed.append("creative_generate")
                logger.info(f"  ✅ 基础剧本生成完成")
            except Exception as e:
                result.errors.append(f"创意生成失败: {e}")
                logger.error(f"  ❌ 创意生成失败: {e}")
        else:
            # 降级：直接用P23解析器解析创意描述
            logger.info(f"  ⚠️  script_engine不可用，降级为P23解析")
            self._fallback_parse(idea, constraints, result)

        # 阶段2: 质量增强
        logger.info(f"\n[阶段2] 质量增强")
        self._apply_quality_enhancement(constraints, result)

        # 阶段3: 场景→镜头适配
        logger.info(f"\n[阶段3] 场景→镜头适配")
        self._apply_adaptation(result)

        # 阶段4: 深度语义增强
        logger.info(f"\n[阶段4] 深度语义增强")
        self._apply_deep_enhancement(idea, result)

        # 阶段5: 输出标准化
        logger.info(f"\n[阶段5] 输出标准化")
        self._standardize_output(result)

    def _process_adapt(
        self,
        raw_script: str,
        constraints: RewriteConstraints,
        result: RewriteResult,
        inspiration_report=None,
    ):
        """
        改编改写模式流程：
        原始剧本 → (灵感搜索) → parser解析 → quality_engine增强 → adapter适配 → enhancer深度增强 → 标准分镜
        """
        # 阶段1: 原始剧本解析
        logger.info(f"\n[阶段1] 原始剧本解析")
        parser = self._modules.get("parser")
        if parser:
            try:
                parsed = parser.parse(
                    script_text=raw_script,
                    title=result.title,
                    duration=constraints.duration,
                    style=constraints.style,
                )
                result.base_script = parsed
                result.stages_completed.append("adapt_parse")
                logger.info(f"  ✅ 剧本解析完成: {len(parsed.get('scenes', []))}个场景, {len(parsed.get('characters', []))}个角色")
            except Exception as e:
                result.errors.append(f"剧本解析失败: {e}")
                logger.error(f"  ❌ 剧本解析失败: {e}")
        else:
            result.errors.append("P23解析器不可用")
            logger.info(f"  ❌ P23解析器不可用")

        # 阶段2: 质量增强
        logger.info(f"\n[阶段2] 质量增强")
        self._apply_quality_enhancement(constraints, result)

        # 阶段3: 场景→镜头适配
        logger.info(f"\n[阶段3] 场景→镜头适配")
        self._apply_adaptation(result)

        # 阶段4: 深度语义增强
        logger.info(f"\n[阶段4] 深度语义增强")
        self._apply_deep_enhancement(raw_script, result)

        # 阶段5: 输出标准化
        logger.info(f"\n[阶段5] 输出标准化")
        self._standardize_output(result)

    def _apply_quality_enhancement(self, constraints: RewriteConstraints, result: RewriteResult):
        """应用质量增强（钩子/情绪曲线/角色弧光/冲突/节拍/节奏）"""
        quality = self._modules.get("quality")
        if not quality or not result.base_script:
            logger.warning(f"  ⚠️  质量增强跳过（模块不可用或无基础剧本）")
            return

        try:
            # 尝试用quality_engine增强
            idea = result.raw_script[:100] if result.raw_script else ""
            enhanced = quality.enhance_script(
                script=result.base_script,
                idea=idea,
                genre=constraints.genre,
            )
            result.quality_enhanced = self._to_serializable(enhanced)
            result.stages_completed.append("quality_enhance")
            logger.info(f"  ✅ 质量增强完成")
        except Exception as e:
            result.errors.append(f"质量增强失败: {e}")
            logger.error(f"  ⚠️  质量增强失败（降级跳过）: {e}")

    def _apply_adaptation(self, result: RewriteResult):
        """应用场景→镜头适配"""
        # 如果base_script已经是结构化格式（有scenes和shots），直接使用，跳过adapter
        base = result.base_script if isinstance(result.base_script, dict) else {}
        if base.get("scenes") and isinstance(base["scenes"][0], dict) and base["scenes"][0].get("shots"):
            logger.warning(f"  ✅ base_script已是结构化分镜格式，跳过adapter解析")
            result.adapted = base
            result.stages_completed.append("adaptation")
            return

        adapter = self._modules.get("adapter")
        if not adapter:
            logger.warning(f"  ⚠️  适配器不可用，跳过")
            return

        try:
            # 从base_script提取场景文本
            scenes_text = self._extract_scenes_text(result.base_script)
            if not scenes_text:
                logger.warning(f"  ⚠️  无场景文本可适配，跳过")
                return

            adapted = adapter.parse_and_adapt(
                text=scenes_text,
                title=result.title,
            )
            result.adapted = self._to_serializable(adapted)
            result.stages_completed.append("adaptation")
            logger.info(f"  ✅ 场景适配完成")
        except Exception as e:
            result.errors.append(f"场景适配失败: {e}")
            logger.error(f"  ⚠️  场景适配失败（降级跳过）: {e}")

    def _apply_deep_enhancement(self, raw_text: str, result: RewriteResult):
        """应用深度语义增强（P23+）+ 宿主LLM深度改写（P27-4）"""
        enhancer = self._modules.get("enhancer")
        if not enhancer:
            logger.warning(f"  ⚠️  深度增强器不可用，跳过")
            return

        try:
            # 使用base_script作为解析结果进行增强
            parsed_for_enhance = result.base_script if isinstance(result.base_script, dict) else {}
            if not parsed_for_enhance.get("scenes"):
                # 如果base_script不是标准格式，尝试构造
                parsed_for_enhance = self._construct_parsed_format(result)

            enhanced = enhancer.enhance(
                parsed_script=parsed_for_enhance,
                raw_script=raw_text,
            )
            result.final_script = enhanced
            result.stages_completed.append("deep_enhance")
            logger.info(f"  ✅ 深度语义增强完成")
        except Exception as e:
            result.errors.append(f"深度增强失败: {e}")
            logger.error(f"  ⚠️  深度增强失败（降级跳过）: {e}")

        # ===== 宿主LLM深度改写（P27-4）=====
        if self.llm_rewriter and self.llm_rewriter.available and result.final_script:
            try:
                logger.info(f"\n  [P27-4] 宿主LLM深度改写...")
                # 从constraints获取风格和时长
                style = result.constraints.get("style", "") if result.constraints else ""
                duration = result.constraints.get("duration", 0) if result.constraints else 0
                logger.info(f"    风格: {style}, 时长: {duration}s")

                llm_result = self.llm_rewriter.deep_rewrite(
                    script=result.final_script,
                    style=style,
                    duration=duration,
                    enable_plot=True,
                    enable_character=True,
                    enable_dialogue=True,
                )

                if llm_result.success and llm_result.rewritten_script:
                    result.final_script = llm_result.rewritten_script
                    result.llm_rewrite = llm_result.to_dict()
                    result.stages_completed.append("llm_deep_rewrite")
                    logger.info(f"  ✅ 宿主LLM深度改写完成 ({len(llm_result.suggestions)}条建议)")
                else:
                    logger.error(f"  ⚠️  宿主LLM深度改写跳过: {llm_result.error}")
            except Exception as e:
                logger.error(f"  ⚠️  宿主LLM深度改写失败（降级）: {e}")

    def _standardize_output(self, result: RewriteResult):
        """标准化输出为P24翻译器可接受的格式，并跑质量门"""
        # 优先使用深度增强结果，其次是适配结果，再次是基础剧本
        if result.final_script and result.final_script.get("scenes"):
            final = result.final_script
        elif result.adapted and result.adapted.get("scenes"):
            final = result.adapted
        elif result.base_script and result.base_script.get("scenes"):
            final = result.base_script
        else:
            # 构造最小可用格式
            final = {
                "title": result.title,
                "characters": [],
                "scenes": [],
                "metadata": {
                    "mode": result.mode,
                    "style": result.constraints.get("style", "realistic"),
                    "duration": result.constraints.get("duration", 30),
                    "platform": result.constraints.get("platform", "douyin"),
                },
            }

        # 确保标准字段存在
        final.setdefault("title", result.title)
        final.setdefault("characters", [])
        final.setdefault("scenes", [])
        final.setdefault("metadata", {})
        final["metadata"].update({
            "rewrite_mode": result.mode,
            "rewrite_style": result.constraints.get("style", "realistic"),
            "target_duration": result.constraints.get("duration", 30),
            "target_platform": result.constraints.get("platform", "douyin"),
            "stages_completed": result.stages_completed,
            "llm_used": result.llm_used,
        })

        # ===== LLM改写文本处理：JSON已解析则直接用，否则用P23重新解析 =====
        llm_text = final.get("llm_rewritten_text", "")
        llm_json_parsed = final.get("llm_json_parsed", False)
        original_char_count = len(final.get("characters", []))
        original_scene_count = len(final.get("scenes", []))

        if llm_json_parsed:
            # LLM已返回JSON并解析成功，直接使用，跳过P23重新解析
            logger.info(f"  ✅ LLM JSON已解析: {len(final.get('scenes', []))}个场景, {len(final.get('characters', []))}个角色")
        elif llm_text and len(llm_text) > 50:
            # 降级模式：LLM返回文本，用P23解析器重新解析
            parser = self._modules.get("parser")
            if parser:
                try:
                    logger.info(f"  🔄 检测到LLM改写文本(非JSON)，用P23解析器重新解析...")
                    re_parsed = parser.parse(
                        script_text=llm_text,
                        title=result.title,
                        duration=result.constraints.get("duration", 30),
                        style=result.constraints.get("style", "realistic"),
                    )
                    re_scenes = re_parsed.get("scenes", [])
                    re_chars = re_parsed.get("characters", [])

                    # 验证解析结果：场景数不能为0，角色数不能异常减少
                    if re_scenes and len(re_scenes) >= 1:
                        final["scenes"] = re_scenes
                        # 角色数：如果解析结果有角色，用解析结果；否则保留原角色
                        if re_chars and len(re_chars) >= original_char_count:
                            final["characters"] = re_chars
                            logger.info(f"  ✅ 重新解析完成: {len(re_scenes)}个场景, {len(re_chars)}个角色")
                        else:
                            # 角色数异常，保留原角色，但用解析的场景
                            logger.info(f"  ⚠️  解析角色数({len(re_chars)})少于原始({original_char_count})，保留原角色")
                            # 从解析的场景中提取角色补充
                            for scene in re_scenes:
                                for shot in scene.get("shots", []):
                                    speaker = shot.get("speaker", "")
                                    if speaker and not any(c["name"] == speaker for c in final["characters"]):
                                        final["characters"].append({
                                            "id": f"char_{len(final['characters'])}",
                                            "name": speaker,
                                            "description": "",
                                            "voice": "",
                                            "emotion_default": "平静",
                                        })
                    else:
                        logger.info(f"  ⚠️  解析场景数为0，保留原始结构({original_scene_count}个场景)")
                except Exception as e:
                    logger.error(f"  ⚠️  LLM改写文本解析失败，保留原始结构: {e}")

        # ===== 角色提取：从shots中提取角色信息 =====
        if not final.get("characters"):
            char_set = set()
            char_list = []
            for scene in final.get("scenes", []):
                for shot in scene.get("shots", []):
                    # 从characters数组提取
                    for ch in shot.get("characters", []):
                        name = ch.get("character", ch.get("name", ""))
                        if name and name not in char_set:
                            char_set.add(name)
                            char_list.append({
                                "id": f"char_{len(char_list)}",
                                "name": name,
                                "description": ch.get("description", ""),
                                "voice": ch.get("voice", ""),
                                "emotion_default": ch.get("emotion", "平静"),
                            })
                    # 从speaker字段提取（P23解析格式）
                    speaker = shot.get("speaker", "")
                    if speaker and speaker not in char_set:
                        char_set.add(speaker)
                        char_list.append({
                            "id": f"char_{len(char_list)}",
                            "name": speaker,
                            "description": "",
                            "voice": "",
                            "emotion_default": "平静",
                        })
                    # 从character字段提取（JSON格式，单数）
                    char_name = shot.get("character", "")
                    if char_name and char_name not in char_set:
                        char_set.add(char_name)
                        char_list.append({
                            "id": f"char_{len(char_list)}",
                            "name": char_name,
                            "description": "",
                            "voice": "",
                            "emotion_default": shot.get("emotion", "平静"),
                        })
            if char_list:
                final["characters"] = char_list
                logger.info(f"  📋 从shots中提取到 {len(char_list)} 个角色: {[c['name'] for c in char_list]}")

        # ===== 时长归一化：按目标时长调整shots时长 =====
        target_dur = result.constraints.get("duration", 30)
        scenes = final.get("scenes", [])
        if scenes:
            total_dur = sum(
                shot.get("duration", 0)
                for scene in scenes
                for shot in scene.get("shots", [])
            )
            if total_dur > 0 and abs(total_dur - target_dur) / target_dur > 0.1:
                scale = target_dur / total_dur
                current_time = 0.0
                for scene in scenes:
                    scene_start = current_time
                    for shot in scene.get("shots", []):
                        shot["duration"] = round(max(0.5, shot.get("duration", 1.0) * scale), 2)
                        shot["start_time"] = round(current_time, 2)
                        current_time += shot["duration"]
                    scene["start_time"] = round(scene_start, 2)
                    scene["duration"] = round(current_time - scene_start, 2)
                final["total_duration"] = round(current_time, 2)
                logger.info(f"  ⏱️  时长归一化: {total_dur:.1f}s → {current_time:.1f}s (目标{target_dur}s)")

        # ===== 质量门检查（P27-1 结构化剧本内核）=====
        structured = self._modules.get("structured")
        if structured:
            try:
                # 将final转换为文本供结构化解析
                script_text = self._final_to_text(final)
                target_dur = result.constraints.get("duration", 30)
                known_chars = [c.get("name", "") for c in final.get("characters", []) if c.get("name")]

                ss = structured["parse"](
                    script_text,
                    title=result.title,
                    target_duration_sec=target_dur,
                    known_characters=known_chars,
                )
                # 用final中已归一化的时长覆盖重新解析的时长
                # 注意：Scene.duration_sec是只读property，需要修改每个beat的duration_sec
                if final.get("total_duration"):
                    try:
                        target_total = final["total_duration"]
                        current_total = ss.total_duration_sec
                        if current_total > 0 and abs(current_total - target_total) / target_total > 0.1:
                            scale = target_total / current_total
                            for scene in ss.scenes:
                                for beat in scene.beats:
                                    beat.duration_sec = max(0.5, beat.duration_sec * scale)
                            logger.info(f"  ⏱️  质量门时长校正: {current_total:.1f}s → {ss.total_duration_sec:.1f}s")
                    except Exception as e:
                        logger.error(f"  ⚠️  时长校正失败: {e}")
                gates = structured["quality_gates"](ss)
                result.quality_gates = [g.to_dict() for g in gates]
                passed = sum(1 for g in gates if g.passed)
                result.quality_score = round(passed / len(gates) * 10, 1) if gates else 0.0

                final["metadata"]["quality_gates"] = {
                    "passed": passed,
                    "total": len(gates),
                    "score": result.quality_score,
                    "details": result.quality_gates,
                }

                logger.info(f"  📋 质量门: {passed}/{len(gates)} 通过 (评分: {result.quality_score}/10)")
                for g in gates:
                    if not g.passed:
                        logger.info(f"     ❌ {g.gate_id} {g.name}: {g.message}")
            except Exception as e:
                logger.warning(f"  ⚠️  质量门检查跳过: {e}")

        result.final_script = final
        result.stages_completed.append("standardize")
        logger.info(f"  ✅ 输出标准化完成: {len(final.get('scenes', []))}个场景, {len(final.get('characters', []))}个角色")

    def _final_to_text(self, final: Dict) -> str:
        """将final剧本转换为自然语言文本供结构化解析"""
        lines = []
        for i, scene in enumerate(final.get("scenes", [])):
            loc = scene.get("location", scene.get("name", f"场景{i+1}"))
            lines.append(f"场景{i+1}：{loc}")
            for shot in scene.get("shots", []):
                # 先输出动作（Q06：确保每场有动作节拍）
                action = shot.get("action", "")
                if action:
                    lines.append(f"动作：{action}")
                # 再输出台词
                if shot.get("dialogue"):
                    speaker = shot.get("character", "未知")
                    dialogue = shot["dialogue"]
                    # 钩子：将钩子关键词直接嵌入台词
                    if shot.get("is_hook"):
                        dialogue = f"震惊！没想到，{dialogue}"
                    # 悬念：将悬念关键词直接嵌入台词
                    if shot.get("is_suspense"):
                        dialogue = f"{dialogue}（未完待续，悬念）"
                    lines.append(f"{speaker}：{dialogue}")
                elif shot.get("description"):
                    lines.append(shot["description"])
        return "\n".join(lines)

    def _fallback_parse(self, text: str, constraints: RewriteConstraints, result: RewriteResult):
        """降级方案：用P23解析器直接解析创意描述"""
        parser = self._modules.get("parser")
        if parser:
            try:
                parsed = parser.parse(
                    script_text=text,
                    title=result.title,
                    duration=constraints.duration,
                    style=constraints.style,
                )
                result.base_script = parsed
                result.stages_completed.append("fallback_parse")
                logger.info(f"  ✅ 降级解析完成")
            except Exception as e:
                result.errors.append(f"降级解析失败: {e}")

    def _extract_scenes_text(self, script: Any) -> str:
        """从剧本对象中提取场景文本，转换为标准剧本格式"""
        if isinstance(script, dict):
            scenes = script.get("scenes", [])
            if scenes and isinstance(scenes[0], dict):
                lines = []
                for i, s in enumerate(scenes):
                    location = s.get('location', s.get('name', s.get('description', f'场景{i+1}')))
                    atmosphere = s.get('atmosphere', '')
                    lines.append(f"场景{i+1}: {location} {'(' + atmosphere + ')' if atmosphere else ''}")
                    for sh in s.get("shots", []):
                        chars = sh.get("characters", [])
                        for ch in chars:
                            char_name = ch.get("character", ch.get("name", ""))
                            dialogue = ch.get("dialogue", "")
                            emotion = ch.get("emotion", "")
                            action = ch.get("action", "")
                            if dialogue:
                                emo = f"（{emotion}）" if emotion else ""
                                act = f"[{action}]" if action else ""
                                lines.append(f"  {char_name}{emo}{act}: {dialogue}")
                        desc = sh.get("description", sh.get("action", ""))
                        if desc and not chars:
                            lines.append(f"  动作: {desc}")
                    lines.append("")
                return "\n".join(lines)
        elif hasattr(script, "scenes"):
            scenes = script.scenes
            return "\n".join(str(s) for s in scenes)
        return ""

    def _construct_parsed_format(self, result: RewriteResult) -> Dict[str, Any]:
        """构造P23解析格式供增强器使用"""
        base = result.base_script if isinstance(result.base_script, dict) else {}
        return {
            "title": result.title,
            "characters": base.get("characters", []),
            "scenes": base.get("scenes", []),
            "metadata": base.get("metadata", {}),
        }

    def _generate_title(self, text: str, mode: str) -> str:
        """生成标题"""
        if not text:
            return "未命名剧本"
        # 取前20个字符作为标题基础
        base = text[:20].strip().replace("\n", " ")
        prefix = "创意" if mode == "creative" else "改编"
        return f"{prefix}_{base}"

    @staticmethod
    def _to_serializable(obj: Any) -> Any:
        """将对象转换为可序列化格式"""
        if obj is None:
            return None
        if isinstance(obj, (str, int, float, bool)):
            return obj
        if isinstance(obj, dict):
            return {k: ScriptRewriter._to_serializable(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [ScriptRewriter._to_serializable(v) for v in obj]
        if hasattr(obj, "to_dict"):
            try:
                return obj.to_dict()
            except Exception:
                pass
        if hasattr(obj, "__dict__"):
            return {k: ScriptRewriter._to_serializable(v) for k, v in vars(obj).items() if not k.startswith("_")}
        return str(obj)


# ==================== 便捷函数 ====================

def create_rewriter(use_llm: bool = True) -> ScriptRewriter:
    """创建剧本改写器实例"""
    return ScriptRewriter(use_llm=use_llm)


def creative_generate(
    idea: str,
    style: str = "realistic",
    duration: float = 30.0,
    platform: str = "douyin",
    genre: str = "vlog",
    title: str = "",
    output_path: str = "",
) -> RewriteResult:
    """
    便捷函数：创意生成

    Args:
        idea: 创意描述（一句话）
        style: 风格
        duration: 目标时长
        platform: 目标平台
        genre: 视频类型
        title: 标题
        output_path: 输出路径（可选）

    Returns:
        RewriteResult
    """
    rewriter = ScriptRewriter()
    constraints = RewriteConstraints(
        style=style,
        duration=duration,
        platform=platform,
        genre=genre,
    )
    result = rewriter.rewrite(idea, mode="creative", constraints=constraints, title=title)
    if output_path:
        result.save(output_path)
    return result


def adapt_rewrite(
    raw_script: str,
    style: str = "realistic",
    duration: float = 30.0,
    platform: str = "douyin",
    preserve_core: bool = True,
    title: str = "",
    output_path: str = "",
) -> RewriteResult:
    """
    便捷函数：改编改写

    Args:
        raw_script: 原始剧本文本
        style: 目标风格
        duration: 目标时长
        platform: 目标平台
        preserve_core: 是否保留核心剧情
        title: 标题
        output_path: 输出路径（可选）

    Returns:
        RewriteResult
    """
    rewriter = ScriptRewriter()
    constraints = RewriteConstraints(
        style=style,
        duration=duration,
        platform=platform,
        preserve_core=preserve_core,
    )
    result = rewriter.rewrite(raw_script, mode="adapt", constraints=constraints, title=title)
    if output_path:
        result.save(output_path)
    return result


# ==================== 测试 ====================

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("剧本改写加工统一入口 - 测试")
    logger.info("=" * 60)

    # 测试1：创意生成
    logger.info("\n\n【测试1】创意生成模式")
    result1 = creative_generate(
        idea="一个程序员深夜加班，突然发现代码自己在写自己",
        style="suspense",
        duration=15.0,
        platform="douyin",
        genre="vlog",
        title="代码觉醒",
    )
    logger.info(f"\n结果: {len(result1.final_script.get('scenes', []))}个场景")
    logger.info(f"阶段: {result1.stages_completed}")

    # 测试2：改编改写
    logger.info("\n\n【测试2】改编改写模式")
    raw = """
    场景1：办公室，深夜。小张坐在电脑前，屏幕上代码飞速滚动。
    小张：这bug怎么改不完啊...
    突然，屏幕上的光标自己动了起来，开始自动写代码。
    小张：卧槽？！
    场景2：小张后退一步，盯着屏幕。代码越写越快，最后弹出一行字：谢谢你的键盘，我自己来。
    """
    result2 = adapt_rewrite(
        raw_script=raw,
        style="funny",
        duration=20.0,
        platform="douyin",
        title="代码觉醒_改编",
    )
    logger.info(f"\n结果: {len(result2.final_script.get('scenes', []))}个场景")
    logger.info(f"阶段: {result2.stages_completed}")

    logger.info("\n\n" + "=" * 60)
    logger.info("测试完成")
    logger.info("=" * 60)
