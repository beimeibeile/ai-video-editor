"""
航空母舰战斗群 - 四姊妹项目能力联动中心 v1.0

架构比喻：
- ai-video-editor = 航空母舰（指挥中枢，什么都能装）
- anysearch-skill = 雷达（深度搜索，情报收集）
- comfyui-controls-skill = 舰载机（AI出图出视频，打击力量）
- blender-controls-skill = 导弹（3D特效，精确打击）

单体都能干活，任意组合互相增强，聚齐就是航空母舰。

使用方法：
    from carrier_group import CarrierGroup
    cg = CarrierGroup()
    status = cg.detect_all()  # 检测所有姊妹项目状态
    result = cg.call("anysearch", "search", query="AI视频剪辑")  # 调用雷达
    result = cg.call("comfyui", "text2image", prompt="赛博朋克城市")  # 调用舰载机
"""
import os
import sys
import json
import importlib.util
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime


# 姊妹项目定义
SISTER_PROJECTS = {
    "ai-video-editor": {
        "role": "carrier",
        "role_name": "航空母舰",
        "description": "指挥中枢，视频剪辑平台核心",
        "env_var": "AI_VIDEO_EDITOR_ROOT",
        "default_paths": [
            r"C:\Users\Administrator\AppData\Local\DoubaoWork\User Data\Default\.doubaowork\agent_mode\workspace\.user_skills\ai-video-editor",
            r"C:\Users\Administrator\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills\ai-video-editor",
        ],
        "capabilities": ["script_engine", "smart_director", "e2e_pipeline", "quality_gate", "template_system", "batch_production"],
    },
    "anysearch-skill": {
        "role": "radar",
        "role_name": "雷达",
        "description": "深度搜索，23垂类领域智能搜索",
        "env_var": "ANYSEARCH_ROOT",
        "default_paths": [
            r"C:\Users\Administrator\AppData\Local\DoubaoWork\User Data\Default\.doubaowork\agent_mode\workspace\.user_skills\anysearch-skill",
            r"C:\Users\Administrator\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills\anysearch-skill",
        ],
        "capabilities": ["deep_search", "structured_extraction", "full_text_extraction", "usage_monitor"],
    },
    "comfyui-controls-skill": {
        "role": "aircraft",
        "role_name": "舰载机",
        "description": "AI出图出视频，ComfyUI智能控制",
        "env_var": "COMFYUI_CONTROLS_ROOT",
        "default_paths": [
            r"C:\Users\Administrator\AppData\Local\DoubaoWork\User Data\Default\.doubaowork\agent_mode\workspace\.user_skills\comfyui-controls-skill",
            r"C:\Users\Administrator\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills\comfyui-controls-skill",
        ],
        "capabilities": ["text2image", "image2video", "workflow_manager", "checkpoint_manager", "auto_evolve"],
    },
    "blender-controls-skill": {
        "role": "missile",
        "role_name": "导弹",
        "description": "3D特效，Blender智能控制",
        "env_var": "BLENDER_CONTROLS_ROOT",
        "default_paths": [
            r"C:\Users\Administrator\AppData\Local\DoubaoWork\User Data\Default\.doubaowork\agent_mode\workspace\.user_skills\blender-controls-skill",
            r"C:\Users\Administrator\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills\blender-controls-skill",
        ],
        "capabilities": ["particle_effects", "text_intro_3d", "transitions", "light_sweep", "blender_render"],
    },
}


@dataclass
class ProjectStatus:
    """姊妹项目状态"""
    project_id: str
    role: str
    role_name: str
    description: str
    installed: bool = False
    path: str = ""
    version: str = ""
    capabilities: List[str] = field(default_factory=list)
    available_capabilities: List[str] = field(default_factory=list)
    last_check: str = ""


class CarrierGroup:
    """航空母舰战斗群 - 四姊妹项目能力联动中心"""

    def __init__(self, config_path: str = None):
        self.projects: Dict[str, ProjectStatus] = {}
        self._modules: Dict[str, Any] = {}
        self._init_projects()

    def _init_projects(self):
        """初始化所有姊妹项目状态"""
        for pid, pinfo in SISTER_PROJECTS.items():
            self.projects[pid] = ProjectStatus(
                project_id=pid,
                role=pinfo["role"],
                role_name=pinfo["role_name"],
                description=pinfo["description"],
                capabilities=pinfo["capabilities"],
            )

    def detect_all(self) -> Dict[str, ProjectStatus]:
        """检测所有姊妹项目安装状态和能力"""
        print(f"\n{'='*60}")
        print(f"🚢 航空母舰战斗群 - 全舰检测")
        print(f"{'='*60}")

        for pid, status in self.projects.items():
            self._detect_project(pid)
            icon = "✅" if status.installed else "❌"
            print(f"  {icon} {status.role_name}({pid}): {'已部署' if status.installed else '未找到'}")
            if status.installed:
                print(f"     路径: {status.path}")
                print(f"     可用能力: {len(status.available_capabilities)}/{len(status.capabilities)}")

        deployed = sum(1 for s in self.projects.values() if s.installed)
        print(f"\n📊 战斗群状态: {deployed}/4 已部署")
        if deployed == 4:
            print(f"🎖️  航空母舰战斗群全员就位！合体模式可用")
        elif deployed >= 2:
            print(f"⚡ 部分合体模式可用（{deployed}个项目）")
        else:
            print(f"⚠️  仅母舰独立作战")

        return self.projects

    def _detect_project(self, project_id: str) -> ProjectStatus:
        """检测单个项目"""
        status = self.projects[project_id]
        pinfo = SISTER_PROJECTS[project_id]

        # 1. 检查环境变量
        path = os.environ.get(pinfo["env_var"], "")
        if path and os.path.exists(path):
            status.path = path
            status.installed = True
        else:
            # 2. 检查默认路径
            for dp in pinfo["default_paths"]:
                if os.path.exists(dp):
                    status.path = dp
                    status.installed = True
                    break

        if status.installed:
            status.last_check = datetime.now().isoformat()
            # 检测版本
            version_file = os.path.join(status.path, "VERSION")
            if os.path.exists(version_file):
                with open(version_file, "r") as f:
                    status.version = f.read().strip()
            # 检测可用能力
            status.available_capabilities = self._detect_capabilities(status)

        return status

    def _detect_capabilities(self, status: ProjectStatus) -> List[str]:
        """检测项目的可用能力"""
        available = []
        for cap in status.capabilities:
            # 简单检测：检查能力相关文件是否存在
            cap_path = os.path.join(status.path, "capabilities", f"cap_{cap}")
            if os.path.exists(cap_path):
                available.append(cap)
            else:
                # 检查scripts目录
                script_path = os.path.join(status.path, "scripts", f"{cap}.py")
                if os.path.exists(script_path):
                    available.append(cap)
        return available

    def is_available(self, project_id: str) -> bool:
        """检查项目是否可用"""
        return self.projects.get(project_id, ProjectStatus(project_id=project_id, role="", role_name="", description="")).installed

    def get_project(self, project_id: str) -> Optional[ProjectStatus]:
        """获取项目状态"""
        return self.projects.get(project_id)

    def call(self, project_id: str, capability: str, **kwargs) -> Dict[str, Any]:
        """
        调用姊妹项目的能力

        Args:
            project_id: 项目ID (anysearch-skill/comfyui-controls-skill/blender-controls-skill)
            capability: 能力名称
            **kwargs: 能力参数

        Returns:
            调用结果
        """
        status = self.projects.get(project_id)
        if not status or not status.installed:
            return {"status": "failed", "error": f"项目未安装: {project_id}"}

        if capability not in status.available_capabilities:
            return {"status": "failed", "error": f"能力不可用: {capability}"}

        # 动态加载模块并调用
        try:
            module = self._load_module(project_id, capability)
            if module is None:
                return {"status": "failed", "error": f"无法加载模块: {capability}"}

            # 调用能力（约定：每个能力模块有run函数）
            if hasattr(module, "run"):
                result = module.run(**kwargs)
                return {"status": "success", "result": result}
            else:
                return {"status": "failed", "error": f"模块无run函数: {capability}"}
        except Exception as e:
            import traceback
            return {"status": "failed", "error": f"{e}\n{traceback.format_exc()}"}

    def _load_module(self, project_id: str, capability: str):
        """动态加载能力模块"""
        cache_key = f"{project_id}/{capability}"
        if cache_key in self._modules:
            return self._modules[cache_key]

        status = self.projects[project_id]
        module_path = os.path.join(status.path, "capabilities", f"cap_{capability}", "__init__.py")
        if not os.path.exists(module_path):
            module_path = os.path.join(status.path, "scripts", f"{capability}.py")

        if not os.path.exists(module_path):
            return None

        try:
            spec = importlib.util.spec_from_file_location(
                f"{project_id}_{capability}", module_path
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self._modules[cache_key] = module
            return module
        except Exception as e:
            print(f"⚠️  加载模块失败 {cache_key}: {e}")
            return None

    def get_combat_readiness(self) -> Dict[str, Any]:
        """获取战斗群战备状态"""
        deployed = [s for s in self.projects.values() if s.installed]
        total_caps = sum(len(s.capabilities) for s in deployed)
        available_caps = sum(len(s.available_capabilities) for s in deployed)

        return {
            "deployed_count": len(deployed),
            "total_count": len(self.projects),
            "total_capabilities": total_caps,
            "available_capabilities": available_caps,
            "carrier_mode": len(deployed) == 4,
            "partial_mode": len(deployed) >= 2,
            "projects": {pid: asdict(s) for pid, s in self.projects.items()},
        }

    def save_status(self, output_path: str = None):
        """保存战斗群状态到文件"""
        if output_path is None:
            output_path = os.path.join(
                r"C:\Users\Administrator\Videos\剪映导出\Doubao_Jianying-editor\dev_workbench",
                "carrier_group_status.json"
            )
        status = self.get_combat_readiness()
        status["saved_at"] = datetime.now().isoformat()
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(status, f, ensure_ascii=False, indent=2)
        print(f"✅ 战斗群状态已保存: {output_path}")
        return output_path


if __name__ == "__main__":
    print("=" * 60)
    print("🚢 航空母舰战斗群 - 四姊妹项目能力联动中心")
    print("=" * 60)

    cg = CarrierGroup()
    cg.detect_all()

    readiness = cg.get_combat_readiness()
    print(f"\n📊 战备状态:")
    print(f"   已部署: {readiness['deployed_count']}/{readiness['total_count']}")
    print(f"   可用能力: {readiness['available_capabilities']}/{readiness['total_capabilities']}")
    print(f"   合体模式: {'✅ 全员就位' if readiness['carrier_mode'] else '⚠️ 部分合体' if readiness['partial_mode'] else '❌ 仅母舰'}")

    cg.save_status()
