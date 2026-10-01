"""
四项目能力注册中心 cap_capability_registry
统一管理 ai-video-editor / anysearch-skill / comfyui-controls / blender-controls 的能力
- 注册：各项目声明自己的能力
- 发现：ai-video-editor查询可用能力
- 调度：统一调用接口，不再硬编码路径
"""
import os
import sys
import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from enum import Enum


class CapabilityType(str, Enum):
    """能力类型"""
    SEARCH = "search"           # 搜索能力
    GENERATE_IMAGE = "gen_image"  # 图像生成
    GENERATE_VIDEO = "gen_video"  # 视频生成
    RENDER_3D = "render_3d"     # 3D渲染
    EDIT = "edit"               # 剪辑编辑
    EFFECT = "effect"           # 特效
    QUALITY_CHECK = "quality"   # 质量检测
    ANALYSIS = "analysis"       # 分析理解


class ProjectRole(str, Enum):
    """项目角色"""
    CORE = "航母·指挥中枢"
    RADAR = "雷达·情报搜索"
    MISSILE = "导弹·AI生成"
    FIGHTER = "舰载机·3D制作"


@dataclass
class Capability:
    """能力描述"""
    name: str                    # 能力名称
    type: CapabilityType         # 能力类型
    project: str                 # 所属项目
    description: str = ""        # 能力描述
    version: str = "1.0.0"       # 版本
    status: str = "available"    # available/unavailable/testing
    entry_point: str = ""        # 调用入口(模块路径或CLI)
    params: Dict[str, Any] = field(default_factory=dict)  # 参数说明
    requires: List[str] = field(default_factory=list)  # 依赖(如comfyui, blender)
    priority: int = 0            # 优先级(0默认，越大越优先)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type.value,
            "project": self.project,
            "description": self.description,
            "version": self.version,
            "status": self.status,
            "entry_point": self.entry_point,
            "params": self.params,
            "requires": self.requires,
            "priority": self.priority,
        }


class CapabilityRegistry:
    """能力注册中心（单例）"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.capabilities: List[Capability] = []
        self.project_paths: Dict[str, str] = {}
        self._register_defaults()

    def _register_defaults(self):
        """注册四个项目的默认能力"""
        # 项目路径
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        skills_root = os.path.dirname(base)  # .user_skills目录

        self.project_paths = {
            "ai-video-editor": os.path.join(skills_root, "ai-video-editor"),
            "anysearch-skill": os.path.join(skills_root, "anysearch-skill"),
            "comfyui-controls-skill": os.path.join(skills_root, "comfyui-controls-skill"),
            "blender-controls-skill": os.path.join(skills_root, "blender-controls-skill"),
        }

        # === ai-video-editor 能力 ===
        self.register(Capability(
            name="剪映工程创建", type=CapabilityType.EDIT, project="ai-video-editor",
            description="创建/编辑剪映草稿工程，支持多轨道/文字/图片/视频",
            entry_point="jy_wrapper.JyProject", requires=["jianying"],
        ))
        self.register(Capability(
            name="蒙版关键帧", type=CapabilityType.EFFECT, project="ai-video-editor",
            description="蒙版大小/位置/旋转/羽化关键帧动画（标记+注入模式）",
            entry_point="scripts.mask_keyframe",
        ))
        self.register(Capability(
            name="特效库(16+)", type=CapabilityType.EFFECT, project="ai-video-editor",
            description="蒙版快闪/发光轮廓/百叶窗/文字擦开/字幕条/人物卡等",
            entry_point="scripts.*",
        ))
        self.register(Capability(
            name="质量门(17道)", type=CapabilityType.QUALITY_CHECK, project="ai-video-editor",
            description="7 edit + 10 storyboard质量检测，输出HTML报告",
            entry_point="cap_creative.draft_quality_checker",
        ))
        self.register(Capability(
            name="端到端pipeline", type=CapabilityType.EDIT, project="ai-video-editor",
            description="分镜→素材→剪映合成，6种hook_effect",
            entry_point="cap_e2e_pipeline.pipeline",
        ))
        self.register(Capability(
            name="剧本引擎", type=CapabilityType.ANALYSIS, project="ai-video-editor",
            description="输入需求→输出有故事线的完整剧本(三幕结构)",
            entry_point="cap_script_engine.script_engine", version="0.1.0",
        ))
        self.register(Capability(
            name="智能调度器", type=CapabilityType.ANALYSIS, project="ai-video-editor",
            description="剧本→自动匹配特效/素材/转场调度计划",
            entry_point="cap_smart_director.smart_director", version="0.1.0",
        ))
        self.register(Capability(
            name="视频帧对齐", type=CapabilityType.EDIT, project="ai-video-editor",
            description="ffmpeg裁剪视频到精确帧边界",
            entry_point="scripts.video_frame_align", requires=["ffmpeg"],
        ))

        # === anysearch-skill 能力 ===
        self.register(Capability(
            name="23垂类深度搜索", type=CapabilityType.SEARCH, project="anysearch-skill",
            description="法律/医疗/金融/学术等23领域结构化搜索",
            entry_point="anysearch", requires=["anysearch"],
        ))
        self.register(Capability(
            name="4语言CLI", type=CapabilityType.SEARCH, project="anysearch-skill",
            description="中文/英文/日文/韩文搜索接口",
            entry_point="anysearch.cli",
        ))

        # === comfyui-controls-skill 能力 ===
        self.register(Capability(
            name="文生图", type=CapabilityType.GENERATE_IMAGE, project="comfyui-controls-skill",
            description="ComfyUI文生图，支持sd_xl_turbo等模型",
            entry_point="comfy_controls.text_to_image", requires=["comfyui"],
        ))
        self.register(Capability(
            name="图生视频(LTX/混元)", type=CapabilityType.GENERATE_VIDEO, project="comfyui-controls-skill",
            description="LTX-2.5/混元I2V图生视频",
            entry_point="comfy_controls.image_to_video", requires=["comfyui"],
        ))
        self.register(Capability(
            name="批量生成", type=CapabilityType.GENERATE_IMAGE, project="comfyui-controls-skill",
            description="批量出图/出视频，自动排队",
            entry_point="cap_batch_generator", requires=["comfyui"],
        ))
        self.register(Capability(
            name="模型管理", type=CapabilityType.GENERATE_IMAGE, project="comfyui-controls-skill",
            description="checkpoint探测/切换/统计",
            entry_point="cap_model_manager", requires=["comfyui"],
        ))
        self.register(Capability(
            name="自我进化", type=CapabilityType.ANALYSIS, project="comfyui-controls-skill",
            description="自动评估输出质量/分析失败/优化报告",
            entry_point="cap_self_evolution",
        ))

        # === blender-controls-skill 能力 ===
        self.register(Capability(
            name="3D场景管理", type=CapabilityType.RENDER_3D, project="blender-controls-skill",
            description="创建/编辑Blender场景，物体/灯光/相机",
            entry_point="cap_scene_manager", requires=["blender"],
        ))
        self.register(Capability(
            name="批量渲染", type=CapabilityType.RENDER_3D, project="blender-controls-skill",
            description="后台批量渲染动画/帧",
            entry_point="cap_batch_renderer", requires=["blender"],
        ))
        self.register(Capability(
            name="3D特效库", type=CapabilityType.EFFECT, project="blender-controls-skill",
            description="粒子背景/3D文字入场/转场遮罩/光线扫描",
            entry_point="cap_effects_library", requires=["blender"],
        ))
        self.register(Capability(
            name="渲染质量控制", type=CapabilityType.QUALITY_CHECK, project="blender-controls-skill",
            description="渲染结果质量检测",
            entry_point="cap_quality_control", requires=["blender"],
        ))

    def register(self, capability: Capability):
        """注册能力"""
        # 同名同项目则更新
        for i, c in enumerate(self.capabilities):
            if c.name == capability.name and c.project == capability.project:
                self.capabilities[i] = capability
                return
        self.capabilities.append(capability)

    def discover(self, capability_type: CapabilityType = None, project: str = None,
                 available_only: bool = True) -> List[Capability]:
        """发现能力"""
        results = self.capabilities
        if capability_type:
            results = [c for c in results if c.type == capability_type]
        if project:
            results = [c for c in results if c.project == project]
        if available_only:
            results = [c for c in results if c.status == "available"]
        # 按优先级排序
        results.sort(key=lambda c: -c.priority)
        return results

    def get(self, name: str, project: str = None) -> Optional[Capability]:
        """按名称获取能力"""
        for c in self.capabilities:
            if c.name == name and (project is None or c.project == project):
                return c
        return None

    def get_project_path(self, project: str) -> Optional[str]:
        """获取项目本地路径"""
        return self.project_paths.get(project)

    def check_dependencies(self, capability: Capability) -> Dict[str, bool]:
        """检查能力依赖是否满足"""
        result = {}
        for dep in capability.requires:
            if dep == "comfyui":
                result[dep] = self._check_comfyui()
            elif dep == "blender":
                result[dep] = self._check_blender()
            elif dep == "ffmpeg":
                result[dep] = self._check_ffmpeg()
            elif dep == "jianying":
                result[dep] = self._check_jianying()
            elif dep == "anysearch":
                result[dep] = self._check_anysearch()
            else:
                result[dep] = True  # 未知依赖默认通过
        return result

    def _check_comfyui(self) -> bool:
        try:
            import urllib.request
            urllib.request.urlopen("http://127.0.0.1:8188/system_stats", timeout=2)
            return True
        except:
            return False

    def _check_blender(self) -> bool:
        return os.path.exists(r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe")

    def _check_ffmpeg(self) -> bool:
        return os.path.exists(r"D:\Ai\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe")

    def _check_jianying(self) -> bool:
        return os.path.exists(r"C:\JianyingPro_5.9\JianyingPro.exe")

    def _check_anysearch(self) -> bool:
        path = self.project_paths.get("anysearch-skill", "")
        return os.path.exists(os.path.join(path, "SKILL.md"))

    def summary(self) -> str:
        """注册中心摘要"""
        by_project = {}
        by_type = {}
        for c in self.capabilities:
            by_project[c.project] = by_project.get(c.project, 0) + 1
            by_type[c.type.value] = by_type.get(c.type.value, 0) + 1

        lines = [
            "=" * 50,
            "能力注册中心",
            "=" * 50,
            f"总能力数: {len(self.capabilities)}",
            "",
            "按项目:",
        ]
        for p, n in sorted(by_project.items()):
            lines.append(f"  {p}: {n}项")
        lines.append("")
        lines.append("按类型:")
        for t, n in sorted(by_type.items()):
            lines.append(f"  {t}: {n}项")
        return "\n".join(lines)

    def save(self, path: str):
        """保存注册中心快照"""
        data = {
            "capabilities": [c.to_dict() for c in self.capabilities],
            "project_paths": self.project_paths,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    registry = CapabilityRegistry()
    print(registry.summary())

    print("\n=== 可用的图像生成能力 ===")
    for c in registry.discover(CapabilityType.GENERATE_IMAGE):
        deps = registry.check_dependencies(c)
        dep_status = " ".join(f"{k}:{'✓' if v else '✗'}" for k, v in deps.items())
        print(f"  [{c.project}] {c.name} - {c.description[:30]} | 依赖: {dep_status}")

    print("\n=== 可用的特效能力 ===")
    for c in registry.discover(CapabilityType.EFFECT):
        print(f"  [{c.project}] {c.name}")

    # 保存
    out = os.path.join(os.path.dirname(__file__), "registry_snapshot.json")
    registry.save(out)
    print(f"\n✅ 注册中心快照已保存: {out}")
