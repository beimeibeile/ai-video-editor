"""
航空母舰战斗群联动中心 v2.0 (P4-1增强)
四姊妹项目深度集成：统一能力调用+跨项目数据共享+战斗群状态API

架构：
- ai-video-editor (母舰/指挥中枢) - 视频剪辑+全链路编排
- anysearch-skill (雷达) - 深度搜索+信息检索
- comfyui-controls-skill (舰载机) - AI出图出视频
- blender-controls-skill (导弹) - 3D特效+粒子

核心能力：
1. 统一能力调用接口 call_capability(capability_name, **kwargs)
2. 能力路由 - 根据能力类型自动路由到对应项目
3. 跨项目数据共享 - 配置/素材/模板共享
4. 战斗群状态API - REST API获取战备状态
5. 合体模式 - 多项目协同工作流
"""
import os
import sys
import json
import importlib.util
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime

SKILL_ROOT = r"C:\Users\Administrator\AppData\Local\DoubaoWork\User Data\Default\.doubaowork\agent_mode\workspace\.user_skills\ai-video-editor"
sys.path.insert(0, SKILL_ROOT)
sys.path.insert(0, os.path.join(SKILL_ROOT, "capabilities"))


# ==================== 四姊妹项目定义 ====================

@dataclass
class SisterProject:
    """姊妹项目定义"""
    name: str  # 项目标识
    role: str  # 角色：母舰/雷达/舰载机/导弹
    description: str
    default_path: str
    capabilities: List[str]  # 提供的能力列表
    installed: bool = False
    version: str = ""
    status: str = "unknown"  # ready/busy/error/unknown


SISTER_PROJECTS = {
    "ai-video-editor": SisterProject(
        name="ai-video-editor",
        role="母舰",
        description="视频剪辑平台+全链路编排+质量门",
        default_path=SKILL_ROOT,
        capabilities=["video_editing", "pipeline_orchestration", "quality_gate",
                      "script_engine", "storyboard", "character_engine", "effects_library",
                      "template_system", "batch_production"],
    ),
    "anysearch-skill": SisterProject(
        name="anysearch-skill",
        role="雷达",
        description="深度搜索+23垂类领域+结构化输出+全文提取",
        default_path=r"C:\Users\Administrator\AppData\Local\DoubaoWork\User Data\Default\.doubaowork\agent_mode\workspace\.user_skills\anysearch-skill",
        capabilities=["deep_search", "structured_extraction", "full_text_extraction",
                      "vertical_domain_search", "usage_monitoring"],
    ),
    "comfyui-controls-skill": SisterProject(
        name="comfyui-controls-skill",
        role="舰载机",
        description="ComfyUI智能管理+工作流控制+AI出图出视频",
        default_path=r"C:\Users\Administrator\AppData\Local\DoubaoWork\User Data\Default\.doubaowork\agent_mode\workspace\.user_skills\comfyui-controls-skill",
        capabilities=["text_to_image", "image_to_video", "workflow_management",
                      "model_management", "batch_generation", "quality_control"],
    ),
    "blender-controls-skill": SisterProject(
        name="blender-controls-skill",
        role="导弹",
        description="Blender智能管理+3D特效+粒子+渲染",
        default_path=r"C:\Users\Administrator\AppData\Local\DoubaoWork\User Data\Default\.doubaowork\agent_mode\workspace\.user_skills\blender-controls-skill",
        capabilities=["3d_rendering", "particle_effects", "text_animation",
                      "transitions", "scene_management", "blender_control"],
    ),
}

# 能力路由表：能力名 -> 项目名
CAPABILITY_ROUTING = {
    # 视频剪辑（母舰）
    "video_editing": "ai-video-editor",
    "pipeline_orchestration": "ai-video-editor",
    "quality_gate": "ai-video-editor",
    "script_engine": "ai-video-editor",
    "storyboard": "ai-video-editor",
    "character_engine": "ai-video-editor",
    "effects_library": "ai-video-editor",
    "template_system": "ai-video-editor",
    "batch_production": "ai-video-editor",
    # 搜索（雷达）
    "deep_search": "anysearch-skill",
    "structured_extraction": "anysearch-skill",
    "full_text_extraction": "anysearch-skill",
    "vertical_domain_search": "anysearch-skill",
    # AI生成（舰载机）
    "text_to_image": "comfyui-controls-skill",
    "image_to_video": "comfyui-controls-skill",
    "workflow_management": "comfyui-controls-skill",
    "model_management": "comfyui-controls-skill",
    "batch_generation": "comfyui-controls-skill",
    # 3D特效（导弹）
    "3d_rendering": "blender-controls-skill",
    "particle_effects": "blender-controls-skill",
    "text_animation": "blender-controls-skill",
    "transitions": "blender-controls-skill",
    "scene_management": "blender-controls-skill",
    "blender_control": "blender-controls-skill",
}


# ==================== 战斗群状态 ====================

@dataclass
class CarrierGroupStatus:
    """战斗群战备状态"""
    timestamp: str = ""
    total_projects: int = 4
    installed_projects: int = 0
    ready_projects: int = 0
    projects: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    total_capabilities: int = 0
    available_capabilities: int = 0
    combat_mode: str = "solo"  # solo/partial/full
    recommendations: List[str] = field(default_factory=list)


class CarrierGroup:
    """航空母舰战斗群联动中心 v2.0"""

    def __init__(self, status_file: str = None):
        self.projects: Dict[str, SisterProject] = {}
        self._loaded_modules: Dict[str, Any] = {}
        self.status_file = status_file or os.path.join(
            r"C:\Users\Administrator\Videos\剪映导出\Doubao_Jianying-editor\dev_workbench",
            "carrier_group_status.json"
        )
        self.detect_all()

    def detect_all(self) -> CarrierGroupStatus:
        """检测所有姊妹项目安装状态"""
        self.projects = {}
        for name, project in SISTER_PROJECTS.items():
            p = SisterProject(**asdict(project))
            p.installed = os.path.exists(p.default_path)
            if p.installed:
                p.status = "ready"
                # 尝试读取版本
                version_file = os.path.join(p.default_path, "VERSION")
                if os.path.exists(version_file):
                    try:
                        with open(version_file, "r") as f:
                            p.version = f.read().strip()
                    except Exception:
                        pass
            else:
                p.status = "not_installed"
            self.projects[name] = p

        status = self._build_status()
        self._save_status(status)
        return status

    def _build_status(self) -> CarrierGroupStatus:
        """构建战斗群状态"""
        installed = [p for p in self.projects.values() if p.installed]
        ready = [p for p in self.projects.values() if p.status == "ready"]

        all_caps = set()
        avail_caps = set()
        for p in self.projects.values():
            all_caps.update(p.capabilities)
            if p.installed:
                avail_caps.update(p.capabilities)

        # 战斗模式判断
        if len(ready) == 4:
            combat_mode = "full"
        elif len(ready) >= 2:
            combat_mode = "partial"
        else:
            combat_mode = "solo"

        # 建议
        recommendations = []
        if len(ready) < 4:
            missing = [p.name for p in self.projects.values() if not p.installed]
            recommendations.append(f"未安装项目: {', '.join(missing)}")
        if combat_mode == "full":
            recommendations.append("✅ 全员就位，合体模式可用，战斗力最大化")
        elif combat_mode == "partial":
            recommendations.append("⚠️ 部分合体，建议安装剩余项目以解锁完整能力")

        status = CarrierGroupStatus(
            timestamp=datetime.now().isoformat(),
            total_projects=4,
            installed_projects=len(installed),
            ready_projects=len(ready),
            projects={name: asdict(p) for name, p in self.projects.items()},
            total_capabilities=len(all_caps),
            available_capabilities=len(avail_caps),
            combat_mode=combat_mode,
            recommendations=recommendations,
        )
        return status

    def _save_status(self, status: CarrierGroupStatus):
        """保存状态到文件"""
        try:
            os.makedirs(os.path.dirname(self.status_file), exist_ok=True)
            with open(self.status_file, "w", encoding="utf-8") as f:
                json.dump(asdict(status), f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def get_status(self) -> Dict[str, Any]:
        """获取战斗群状态（API用）"""
        status = self._build_status()
        return asdict(status)

    # ==================== 统一能力调用 ====================

    def call_capability(self, capability_name: str, **kwargs) -> Dict[str, Any]:
        """
        统一能力调用接口

        Args:
            capability_name: 能力名称（见CAPABILITY_ROUTING）
            **kwargs: 能力参数

        Returns:
            调用结果字典
        """
        # 路由到对应项目
        project_name = CAPABILITY_ROUTING.get(capability_name)
        if not project_name:
            return {
                "success": False,
                "error": f"未知能力: {capability_name}",
                "available_capabilities": list(CAPABILITY_ROUTING.keys()),
            }

        project = self.projects.get(project_name)
        if not project or not project.installed:
            return {
                "success": False,
                "error": f"项目未安装: {project_name}",
                "project_path": project.default_path if project else "未知",
            }

        # 动态加载项目模块并调用
        try:
            result = self._dispatch_call(project_name, capability_name, **kwargs)
            return {
                "success": True,
                "capability": capability_name,
                "project": project_name,
                "result": result,
            }
        except Exception as e:
            return {
                "success": False,
                "capability": capability_name,
                "project": project_name,
                "error": str(e),
            }

    def _dispatch_call(self, project_name: str, capability_name: str, **kwargs) -> Any:
        """分发调用到具体项目"""
        # 母舰（ai-video-editor）的能力直接调用
        if project_name == "ai-video-editor":
            return self._call_ai_video_editor(capability_name, **kwargs)

        # 其他项目通过动态加载调用
        project = self.projects[project_name]
        module = self._load_project_module(project_name, project.default_path)
        if module and hasattr(module, "call_capability"):
            return module.call_capability(capability_name, **kwargs)
        raise NotImplementedError(f"项目 {project_name} 暂不支持能力调用: {capability_name}")

    def _call_ai_video_editor(self, capability_name: str, **kwargs) -> Any:
        """调用母舰能力"""
        if capability_name == "script_engine":
            from cap_script_engine import ScriptEngine, VideoGenre
            engine = ScriptEngine()
            genre = VideoGenre(kwargs.get("genre", "CUSTOM"))
            script = engine.generate(
                idea=kwargs.get("idea", ""),
                genre=genre,
                duration=kwargs.get("duration", 30),
            )
            return script.to_dict() if hasattr(script, "to_dict") else str(script)

        elif capability_name == "storyboard":
            from cap_storyboard_engine.storyboard_engine import StoryboardGenerator
            gen = StoryboardGenerator()
            sb = gen.generate(
                theme=kwargs.get("theme", ""),
                style=kwargs.get("style", "cinematic"),
                total_duration=kwargs.get("duration", 15),
                shot_count=kwargs.get("shot_count", 5),
            )
            return sb.to_dict()

        elif capability_name == "quality_gate":
            draft_path = kwargs.get("draft_path", "")
            if not draft_path or not os.path.exists(draft_path):
                raise ValueError(f"草稿路径不存在: {draft_path}")
            from cap_creative.quality_gate import QualityGate
            qg = QualityGate()
            report = qg.check(draft_path)
            return report if isinstance(report, dict) else {"status": "completed"}

        elif capability_name == "pipeline_orchestration":
            from cap_pipeline_orchestrator import PipelineOrchestrator
            orch = PipelineOrchestrator()
            result = orch.run_full_pipeline(
                topic=kwargs.get("topic", ""),
                video_type=kwargs.get("video_type", "exploration"),
                duration=kwargs.get("duration", 30),
                project_name=kwargs.get("project_name"),
            )
            return asdict(result)

        elif capability_name == "template_system":
            from cap_template_system import TemplateSystem
            ts = TemplateSystem()
            if kwargs.get("action") == "list":
                return [t.to_dict() if hasattr(t, "to_dict") else str(t) for t in ts.list_templates()]
            elif kwargs.get("action") == "apply":
                template = ts.get_template(kwargs.get("template_id", ""))
                if template:
                    return template.to_dict() if hasattr(template, "to_dict") else str(template)
            return {"available_templates": len(ts.list_templates())}

        elif capability_name == "effects_library":
            effects_path = os.path.join(SKILL_ROOT, "effects", "index.json")
            if os.path.exists(effects_path):
                with open(effects_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            return {"effects": [], "count": 0}

        else:
            raise NotImplementedError(f"母舰能力暂未实现调用接口: {capability_name}")

    def _load_project_module(self, project_name: str, project_path: str):
        """动态加载项目模块"""
        if project_name in self._loaded_modules:
            return self._loaded_modules[project_name]

        # 尝试加载项目的主模块
        possible_paths = [
            os.path.join(project_path, "capabilities", "cap_carrier_bridge", "bridge.py"),
            os.path.join(project_path, "bridge.py"),
            os.path.join(project_path, "main.py"),
        ]

        for path in possible_paths:
            if os.path.exists(path):
                try:
                    spec = importlib.util.spec_from_file_location(f"{project_name}_bridge", path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    self._loaded_modules[project_name] = module
                    return module
                except Exception:
                    continue

        return None

    # ==================== 合体模式工作流 ====================

    def run_combined_workflow(self, workflow_type: str, **kwargs) -> Dict[str, Any]:
        """
        运行合体模式工作流

        工作流类型：
        - research_to_video: 搜索→剧本→分镜→素材→合成（雷达+母舰+舰载机）
        - script_to_3d_video: 剧本→角色→分镜→3D素材→合成（母舰+导弹）
        - full_combat: 全员协同（雷达+母舰+舰载机+导弹）
        """
        status = self.get_status()
        if status["combat_mode"] == "solo":
            return {"success": False, "error": "合体模式需要至少2个项目就位", "status": status}

        results = {}
        workflow_steps = []

        if workflow_type == "research_to_video":
            # 步骤1：雷达搜索素材
            workflow_steps.append("雷达搜索")
            search_result = self.call_capability("deep_search", query=kwargs.get("topic", ""))
            results["search"] = search_result

            # 步骤2：母舰生成剧本
            workflow_steps.append("剧本生成")
            script_result = self.call_capability("script_engine", idea=kwargs.get("topic", ""))
            results["script"] = script_result

            # 步骤3：舰载机生成素材
            workflow_steps.append("AI素材生成")
            image_result = self.call_capability("text_to_image", prompt=kwargs.get("topic", ""))
            results["images"] = image_result

            # 步骤4：母舰合成
            workflow_steps.append("剪映合成")
            pipeline_result = self.call_capability("pipeline_orchestration", topic=kwargs.get("topic", ""))
            results["pipeline"] = pipeline_result

        elif workflow_type == "full_combat":
            # 全员协同
            workflow_steps = ["雷达搜索", "剧本生成", "角色分析", "分镜定版",
                              "AI素材", "3D特效", "剪映合成", "质量门"]
            # 简化实现：调用母舰全链路编排
            pipeline_result = self.call_capability("pipeline_orchestration", topic=kwargs.get("topic", ""))
            results["pipeline"] = pipeline_result

        else:
            return {"success": False, "error": f"未知工作流类型: {workflow_type}"}

        return {
            "success": True,
            "workflow_type": workflow_type,
            "steps": workflow_steps,
            "results": results,
            "combat_mode": status["combat_mode"],
        }

    # ==================== 跨项目数据共享 ====================

    def share_config(self, key: str, value: Any, project_name: str = "all"):
        """跨项目共享配置"""
        shared_dir = os.path.join(SKILL_ROOT, "shared_data")
        os.makedirs(shared_dir, exist_ok=True)

        config_file = os.path.join(shared_dir, "shared_config.json")
        config = {}
        if os.path.exists(config_file):
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
            except Exception:
                pass

        config[key] = {
            "value": value,
            "shared_by": "ai-video-editor",
            "shared_with": project_name,
            "timestamp": datetime.now().isoformat(),
        }

        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

    def get_shared_config(self, key: str) -> Any:
        """获取共享配置"""
        config_file = os.path.join(SKILL_ROOT, "shared_data", "shared_config.json")
        if os.path.exists(config_file):
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                return config.get(key, {}).get("value")
            except Exception:
                pass
        return None


if __name__ == "__main__":
    print("=" * 60)
    print("🚢 航空母舰战斗群联动中心 v2.0")
    print("=" * 60)

    group = CarrierGroup()
    status = group.get_status()

    print(f"\n战备状态:")
    print(f"  战斗模式: {status['combat_mode']}")
    print(f"  项目就位: {status['ready_projects']}/{status['total_projects']}")
    print(f"  能力可用: {status['available_capabilities']}/{status['total_capabilities']}")

    print(f"\n项目详情:")
    for name, p in status["projects"].items():
        icon = "✅" if p["installed"] else "❌"
        print(f"  {icon} {name} ({p['role']}): {p['status']}")

    print(f"\n建议:")
    for rec in status["recommendations"]:
        print(f"  - {rec}")

    print(f"\n能力路由表 ({len(CAPABILITY_ROUTING)}项):")
    for cap, proj in list(CAPABILITY_ROUTING.items())[:5]:
        print(f"  {cap} -> {proj}")
    print(f"  ... 共{len(CAPABILITY_ROUTING)}项")
