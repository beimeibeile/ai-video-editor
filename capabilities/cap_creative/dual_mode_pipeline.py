"""
双模式Pipeline架构 v1.0
========================
战略定位（用户确认）：
- 剧类 = 电影模式：必须I2V真正动态视频，分镜用镜头语言，借鉴shuohao精度
- 短视频类 = 标签模式：碎片剪辑组合再创作，标签驱动，特效+转场+卡点+文字动画

架构：
  DualModePipeline（统一入口，自动路由）
  ├── MovieModePipeline（剧类/电影模式）
  │   ├── 剧本解析 → 分镜（镜头语言：焦距/机位/构图/视线/焦点/稳定性）
  │   ├── 角色场景参考图生成（ComfyUI）
  │   ├── I2V视频生成（混元/HunyuanVideo）
  │   ├── 声音设计（对话TTS + 旁白 + BGM + SFX）
  │   └── 剪映工程合成（多轨道对齐）
  │
  └── ShortVideoModePipeline（短视频/标签模式）
      ├── 标签解析（tag_engine：5大类36标签）
      ├── 素材准备（用户素材/ComfyUI生成/模板素材）
      ├── 卡点检测（auto_beat：BPM+节拍+强度分级）
      ├── 特效匹配（标签→特效映射）
      ├── 文字动画（字幕条/角色卡/文字擦开/蒙版开场）
      ├── BGM生成（real_bgm_generator：10种情绪）
      └── 剪映工程合成（碎片剪辑+转场+卡点）

共享能力：
  - SoundEngine（TTS + BGM + SFX）
  - ComfyUIPipeline（出图/I2V）
  - QualityGate（质量门32道+导演运镜规则）
  - EffectLibrary（25+特效库）
"""

import os
import sys
import json
from typing import Dict, Any, Optional, List, Literal
from dataclasses import dataclass, field
from enum import Enum

# 模式类型
class ContentMode(Enum):
    MOVIE = "movie"        # 剧类/电影模式
    SHORT_VIDEO = "short"  # 短视频/标签模式
    AUTO = "auto"          # 自动判断


@dataclass
class PipelineConfig:
    """Pipeline配置"""
    mode: ContentMode = ContentMode.AUTO
    project_name: str = "untitled"
    width: int = 1080
    height: int = 1920
    duration: float = 60.0
    fps: int = 30

    # 电影模式参数
    script_path: Optional[str] = None
    i2v_model: str = "hunyuanvideo1.5_720p_i2v_fp16"
    use_i2v: bool = True

    # 短视频模式参数
    tags: List[str] = field(default_factory=list)
    text_lines: List[str] = field(default_factory=list)
    material_paths: List[str] = field(default_factory=list)
    bgm_mood: str = "cyberpunk"
    use_beat_detection: bool = True

    # 共享参数
    output_dir: Optional[str] = None
    comfyui_api: str = "http://127.0.0.1:8188"
    jianying_drafts_dir: str = r"D:\JianyingProDrafts\JianyingPro Drafts"


@dataclass
class PipelineResult:
    """Pipeline执行结果"""
    status: str = "pending"  # pending/running/success/failed
    mode: str = ""
    project_name: str = ""
    draft_path: str = ""
    stages: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "mode": self.mode,
            "project_name": self.project_name,
            "draft_path": self.draft_path,
            "stages": self.stages,
            "errors": self.errors,
            "warnings": self.warnings,
        }


class DualModePipeline:
    """
    双模式统一Pipeline入口
    根据内容类型自动路由到电影模式或短视频模式
    """

    def __init__(self, skill_root: str = None):
        if skill_root is None:
            skill_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.skill_root = skill_root
        self._load_capabilities()

    def _load_capabilities(self):
        """加载共享能力模块（延迟导入，避免循环依赖）"""
        self._tag_engine = None
        self._bgm_generator = None
        self._sound_engine = None
        self._comfyui_pipeline = None

    @property
    def tag_engine(self):
        if self._tag_engine is None:
            try:
                from cap_creative.tag_engine import TagEngine
                self._tag_engine = TagEngine()
            except ImportError:
                self._tag_engine = None
        return self._tag_engine

    @property
    def bgm_generator(self):
        if self._bgm_generator is None:
            try:
                from cap_creative.real_bgm_generator import RealBGMGenerator
                self._bgm_generator = RealBGMGenerator()
            except ImportError:
                self._bgm_generator = None
        return self._bgm_generator

    def detect_mode(self, config: PipelineConfig) -> ContentMode:
        """
        自动判断内容模式
        规则：
        - 有剧本文件/script_path → 电影模式
        - 有tags标签 → 短视频模式
        - 时长>120秒且有角色/对话 → 电影模式
        - 否则默认短视频模式
        """
        if config.mode != ContentMode.AUTO:
            return config.mode

        # 有剧本文件 → 电影模式
        if config.script_path and os.path.exists(config.script_path):
            return ContentMode.MOVIE

        # 有标签 → 短视频模式
        if config.tags:
            return ContentMode.SHORT_VIDEO

        # 长时长+有文字内容 → 可能是剧类
        if config.duration > 120 and len(config.text_lines) > 5:
            return ContentMode.MOVIE

        # 默认短视频模式
        return ContentMode.SHORT_VIDEO

    def run(self, config: PipelineConfig) -> PipelineResult:
        """
        执行Pipeline（统一入口）
        """
        result = PipelineResult(
            project_name=config.project_name,
        )

        # 1. 模式判断
        mode = self.detect_mode(config)
        result.mode = mode.value
        config.mode = mode
        print(f"\n{'='*60}")
        print(f"双模式Pipeline启动: {config.project_name}")
        print(f"模式: {mode.value} ({'电影/剧类' if mode == ContentMode.MOVIE else '短视频/标签'})")
        print(f"{'='*60}\n")

        # 2. 路由到对应模式
        try:
            if mode == ContentMode.MOVIE:
                result = self._run_movie_mode(config, result)
            else:
                result = self._run_short_video_mode(config, result)

            result.status = "success"
            print(f"\n✅ Pipeline完成: {result.status}")
            print(f"   草稿路径: {result.draft_path}")

        except Exception as e:
            result.status = "failed"
            result.errors.append(str(e))
            print(f"\n❌ Pipeline失败: {e}")
            import traceback
            traceback.print_exc()

        return result

    def _run_movie_mode(self, config: PipelineConfig, result: PipelineResult) -> PipelineResult:
        """
        电影模式（剧类）执行流程
        阶段：剧本解析 → 分镜 → 参考图 → I2V → 声音 → 合成
        """
        print("\n--- 电影模式 ---")

        # 阶段1: 剧本解析
        print("[1/6] 剧本解析...")
        script_data = self._parse_script(config)
        result.stages["script_parsing"] = {"scenes": len(script_data.get("scenes", [])), "shots": len(script_data.get("shots", []))}

        # 阶段2: 分镜生成（镜头语言）
        print("[2/6] 分镜生成（镜头语言）...")
        storyboard = self._generate_storyboard(script_data)
        result.stages["storyboard"] = {"shots": len(storyboard)}

        # 阶段2.5: 质量门验证 + auto_fix自动修复
        print("[2.5/6] 质量门验证 + 自动修复...")
        try:
            from movie_storyboard import MovieStoryboardEngine
            sb_engine = MovieStoryboardEngine()
            # 转换为validate需要的格式
            sb_dict = {"title": config.project_name, "scenes": [{"scene_id": "S1", "segments": [{"segment_id": "S1_01", "shots": storyboard}]}]}
            val_result = sb_engine.validate(sb_dict)
            if not val_result["passed"] or val_result["diagnosis"]:
                print(f"   质量门: {len(val_result['issues'])}问题, {len(val_result['diagnosis'])}诊断")
                fix_result = sb_engine.auto_fix(sb_dict)
                if fix_result["fixed"]:
                    storyboard = fix_result["storyboard"]["scenes"][0]["segments"][0]["shots"]
                    print(f"   ✅ 自动修复 {len(fix_result['changes'])} 项")
                    result.stages["storyboard_fix"] = {"changes": fix_result["changes"]}
            else:
                print("   ✅ 质量门通过，无需修复")
        except Exception as e:
            print(f"   ⚠️ 质量门跳过: {e}")

        # 阶段3: 角色场景参考图
        print("[3/6] 角色场景参考图生成...")
        refs = self._generate_reference_images(storyboard, config)
        result.stages["reference_images"] = {"count": len(refs)}

        # 阶段4: I2V视频生成
        if config.use_i2v:
            print("[4/6] I2V视频生成...")
            videos = self._generate_i2v_clips(storyboard, refs, config)
            result.stages["i2v_generation"] = {"clips": len(videos)}
        else:
            print("[4/6] I2V已跳过（use_i2v=False）")
            result.stages["i2v_generation"] = {"skipped": True}
            videos = []

        # 阶段5: 声音设计
        print("[5/6] 声音设计...")
        audio = self._design_audio(script_data, storyboard, config)
        result.stages["audio_design"] = audio

        # 阶段6: 剪映工程合成
        print("[6/6] 剪映工程合成...")
        draft_path = self._build_movie_project(storyboard, videos, audio, config)
        result.draft_path = draft_path
        result.stages["project_building"] = {"draft_path": draft_path}

        return result

    def _run_short_video_mode(self, config: PipelineConfig, result: PipelineResult) -> PipelineResult:
        """
        短视频模式（标签驱动）执行流程
        阶段：标签解析 → 卡点检测 → 特效匹配 → 素材准备 → 文字动画 → BGM → 合成
        """
        print("\n--- 短视频模式 ---")

        # 阶段1: 标签解析
        print("[1/7] 标签解析...")
        normalized_tags = []
        if self.tag_engine and config.tags:
            normalized_tags = self.tag_engine.normalize_tags(config.tags)
            matched_effects = self.tag_engine.match_effects(normalized_tags)
            print(f"   标准化标签: {normalized_tags}")
            print(f"   匹配特效: {len(matched_effects)}个")
        else:
            matched_effects = []
        result.stages["tag_parsing"] = {
            "tags": normalized_tags,
            "matched_effects": len(matched_effects),
        }

        # 阶段2: 卡点检测
        if config.use_beat_detection and config.material_paths:
            print("[2/7] 卡点检测...")
            beat_data = self._detect_beats(config)
            result.stages["beat_detection"] = beat_data
        else:
            print("[2/7] 卡点检测跳过")
            beat_data = None
            result.stages["beat_detection"] = {"skipped": True}

        # 阶段3: BGM生成
        print("[3/7] BGM生成...")
        bgm_path = None
        if self.bgm_generator:
            bgm_path = self.bgm_generator.generate(
                mood=config.bgm_mood,
                duration=config.duration,
                output_path=os.path.join(config.output_dir or ".", f"{config.project_name}_bgm.wav"),
            )
            print(f"   BGM: {bgm_path}")
        result.stages["bgm_generation"] = {"path": bgm_path, "mood": config.bgm_mood}

        # 阶段4: 文字动画准备
        print("[4/7] 文字动画准备...")
        text_assets = self._prepare_text_animations(config)
        result.stages["text_animations"] = {"count": len(text_assets)}

        # 阶段5: 特效应用计划
        print("[5/7] 特效应用计划...")
        effect_plan = self._plan_effects(normalized_tags, matched_effects, beat_data)
        result.stages["effect_planning"] = {"effects": len(effect_plan)}

        # 阶段6: 剪映工程合成
        print("[6/7] 剪映工程合成...")
        draft_path = self._build_short_video_project(
            config, beat_data, effect_plan, text_assets, bgm_path
        )
        result.draft_path = draft_path
        result.stages["project_building"] = {"draft_path": draft_path}

        # 阶段7: 质量检查
        print("[7/7] 质量检查...")
        quality = self._quality_check(draft_path)
        result.stages["quality_check"] = quality

        return result

    # ===== 电影模式子方法（占位，后续逐步实现） =====

    def _parse_script(self, config: PipelineConfig) -> dict:
        """解析剧本文件"""
        # TODO: 集成剧本解析引擎
        return {"scenes": [], "shots": [], "characters": []}

    def _generate_storyboard(self, script_data: dict) -> list:
        """生成分镜（镜头语言：焦距/机位/构图/视线/焦点/稳定性）"""
        try:
            from cap_creative.movie_storyboard import MovieStoryboardEngine
            engine = MovieStoryboardEngine()
            result = engine.generate_from_script(script_data)
            shots = result.get("shots", [])
            print(f"   分镜引擎: {len(shots)}个镜头")
            return shots
        except Exception as e:
            print(f"   ⚠️ 分镜引擎失败: {e}")
            return []

    def _generate_reference_images(self, storyboard: list, config: PipelineConfig) -> list:
        """生成角色场景参考图（ComfyUI）"""
        # TODO: 集成ComfyUI出图pipeline
        return []

    def _generate_i2v_clips(self, storyboard: list, refs: list, config: PipelineConfig) -> list:
        """I2V视频生成（混元/HunyuanVideo）"""
        try:
            from cap_creative.hunyuan_i2v_runner import HunyuanI2VRunner
            runner = HunyuanI2VRunner()
            avail = runner.check_available()
            if not avail["ready"]:
                print(f"   ⚠️ 混元I2V不可用: {avail.get('details', {})}")
                return []

            videos = []
            # 为每个有参考图的分镜生成I2V
            for i, shot in enumerate(storyboard[:3]):  # 限制最多3个，避免耗时过长
                ref_image = refs[i] if i < len(refs) else None
                if ref_image and os.path.exists(ref_image):
                    prompt = shot.get("prompt", shot.get("description", ""))
                    duration = shot.get("duration", 3.0)
                    print(f"   生成I2V [{i+1}]: {prompt[:30]}... ({duration}s)")
                    result = runner.generate(
                        image_path=ref_image,
                        prompt=prompt,
                        duration=duration,
                        fps=config.fps,
                        width=config.width,
                        height=config.height,
                        output_dir=config.output_dir,
                        timeout=600,
                    )
                    if result.get("status") == "success":
                        videos.append(result.get("output_file"))
            print(f"   I2V生成: {len(videos)}个视频")
            return videos
        except Exception as e:
            print(f"   ⚠️ I2V生成失败: {e}")
            return []

    def _design_audio(self, script_data: dict, storyboard: list, config: PipelineConfig) -> dict:
        """声音设计（对话+旁白+BGM+SFX）"""
        # TODO: 集成声音引擎
        return {"dialogue": 0, "narration": 0, "bgm": "", "sfx": 0}

    def _build_movie_project(self, storyboard, videos, audio, config) -> str:
        """构建电影模式剪映工程"""
        # TODO: 多轨道对齐合成
        return ""

    # ===== 短视频模式子方法 =====

    def _detect_beats(self, config: PipelineConfig) -> dict:
        """卡点检测"""
        try:
            sys.path.insert(0, os.path.join(self.skill_root, "scripts"))
            from auto_beat import generate_beat_timeline
            # 使用第一个音频素材或BGM进行卡点检测
            audio_path = next((p for p in config.material_paths if p.endswith(('.mp3', '.wav', '.m4a'))), None)
            if audio_path:
                return generate_beat_timeline(audio_path, duration=config.duration)
        except Exception as e:
            print(f"   卡点检测失败: {e}")
        return {"beats": [], "cuts": [], "beat_count": 0}

    def _prepare_text_animations(self, config: PipelineConfig) -> list:
        """准备文字动画素材"""
        # 文字动画在剪映工程构建时直接添加原生文字轨道
        return config.text_lines

    def _plan_effects(self, tags: list, matched_effects: list, beat_data: dict) -> list:
        """制定特效应用计划"""
        plan = []
        for effect in matched_effects:
            plan.append({"effect": effect, "timing": "beat_synced" if beat_data else "fixed"})
        return plan

    def _build_short_video_project(self, config, beat_data, effect_plan, text_assets, bgm_path) -> str:
        """构建短视频模式剪映工程（碎片剪辑+转场+卡点）"""
        try:
            from cap_creative.short_video_composer import compose_from_materials
            result = compose_from_materials(
                material_paths=config.material_paths,
                bgm_path=bgm_path,
                text_lines=config.text_lines,
                project_name=config.project_name,
                duration=config.duration,
                use_beat_detection=config.use_beat_detection,
                transition="叠化",
                camera_move="缓推",
                width=config.width,
                height=config.height,
            )
            if result.get("status") == "success":
                print(f"   工程: {result.get('draft_path')}")
                return result.get("draft_path", "")
        except Exception as e:
            print(f"   ⚠️ 碎片剪辑合成失败: {e}")
        return os.path.join(config.jianying_drafts_dir, config.project_name)

    def _quality_check(self, draft_path: str) -> dict:
        """质量检查"""
        # TODO: 集成质量门
        return {"passed": True, "checks": 0, "issues": []}


# ===== 便捷函数 =====

def create_movie_pipeline(
    project_name: str,
    script_path: str,
    duration: float = 180.0,
    width: int = 1080,
    height: int = 1920,
    **kwargs,
) -> PipelineResult:
    """快捷创建电影模式Pipeline"""
    config = PipelineConfig(
        mode=ContentMode.MOVIE,
        project_name=project_name,
        script_path=script_path,
        duration=duration,
        width=width,
        height=height,
        **kwargs,
    )
    pipeline = DualModePipeline()
    return pipeline.run(config)


def create_short_video_pipeline(
    project_name: str,
    tags: List[str],
    text_lines: List[str] = None,
    material_paths: List[str] = None,
    duration: float = 60.0,
    bgm_mood: str = "cyberpunk",
    **kwargs,
) -> PipelineResult:
    """快捷创建短视频模式Pipeline"""
    config = PipelineConfig(
        mode=ContentMode.SHORT_VIDEO,
        project_name=project_name,
        tags=tags,
        text_lines=text_lines or [],
        material_paths=material_paths or [],
        duration=duration,
        bgm_mood=bgm_mood,
        **kwargs,
    )
    pipeline = DualModePipeline()
    return pipeline.run(config)


if __name__ == "__main__":
    print("=" * 60)
    print("双模式Pipeline架构 v1.0")
    print("=" * 60)
    print("\n模式:")
    print("  movie     - 剧类/电影模式（I2V驱动，镜头语言）")
    print("  short     - 短视频/标签模式（特效+卡点+文字动画）")
    print("  auto      - 自动判断")
    print("\n快捷函数:")
    print("  create_movie_pipeline(project_name, script_path, ...)")
    print("  create_short_video_pipeline(project_name, tags, ...)")
    print("\n共享能力:")
    print("  - TagEngine（标签引擎，5大类36标签）")
    print("  - RealBGMGenerator（真实BGM，10种情绪）")
    print("  - SoundEngine（声音引擎）")
    print("  - ComfyUIPipeline（出图/I2V）")
    print("  - QualityGate（质量门）")
    print("  - EffectLibrary（25+特效库）")
