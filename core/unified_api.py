"""
四姊妹项目统一API接口 v1.0
ai-video-editor + anysearch-skill + Comfyui-controls-skill + Blender-controls-skill
提供统一的能力发现、调用、状态检测接口

架构：航空母舰战斗群
- ai-video-editor = 航空母舰（指挥中枢，视频合成）
- anysearch-skill = 雷达（信息检索，素材搜索）
- Comfyui-controls-skill = 导弹（AI生成，图像/视频）
- Blender-controls-skill = 舰载机（3D特效，动画渲染）
"""
import os
import sys
import json
import importlib
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum


class SisterProject(Enum):
    """四姊妹项目枚举"""
    AI_VIDEO_EDITOR = "ai-video-editor"
    ANYSEARCH = "anysearch-skill"
    COMFYUI_CONTROLS = "Comfyui-controls-skill"
    BLENDER_CONTROLS = "Blender-controls-skill"


class CapabilityStatus(Enum):
    """能力状态"""
    AVAILABLE = "available"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


@dataclass
class CapabilityInfo:
    """能力信息"""
    name: str
    project: str
    description: str = ""
    status: CapabilityStatus = CapabilityStatus.UNKNOWN
    dependencies: List[str] = field(default_factory=list)
    entry_point: str = ""
    tags: List[str] = field(default_factory=list)


@dataclass
class ProjectInfo:
    """项目信息"""
    name: str
    path: str
    status: CapabilityStatus = CapabilityStatus.UNKNOWN
    version: str = ""
    capabilities: List[CapabilityInfo] = field(default_factory=list)
    api_endpoint: str = ""


class UnifiedAPI:
    """
    四姊妹项目统一API接口
    
    使用方法：
        api = UnifiedAPI()
        api.discover()  # 发现所有项目和能力
        result = api.call("comfyui", "generate_image", prompt="...")  # 调用能力
        status = api.get_status()  # 获取所有项目状态
    """
    
    def __init__(self, skill_root: str = None):
        if skill_root is None:
            skill_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.skill_root = skill_root
        self.projects: Dict[str, ProjectInfo] = {}
        self._capability_cache: Dict[str, Any] = {}
        
        # 项目路径配置
        self._project_paths = {
            SisterProject.AI_VIDEO_EDITOR.value: skill_root,
            SisterProject.ANYSEARCH.value: self._find_sister_project("anysearch-skill"),
            SisterProject.COMFYUI_CONTROLS.value: self._find_sister_project("Comfyui-controls-skill"),
            SisterProject.BLENDER_CONTROLS.value: self._find_sister_project("Blender-controls-skill"),
        }
    
    def _find_sister_project(self, name: str) -> str:
        """查找姊妹项目路径"""
        # 尝试多个可能的位置
        candidates = [
            os.path.join(os.path.dirname(self.skill_root), name),
            os.path.join(os.path.expanduser("~"), ".doubao", "agent_mode", "workspace", ".user_skills", name),
            os.path.join(os.path.expanduser("~"), ".doubaowork", "agent_mode", "workspace", ".user_skills", name),
        ]
        for path in candidates:
            if os.path.exists(path):
                return path
        return ""
    
    def discover(self) -> Dict[str, ProjectInfo]:
        """
        发现所有四姊妹项目和能力
        Returns: 项目信息字典
        """
        print("=" * 60)
        print("四姊妹项目统一API - 能力发现")
        print("=" * 60)
        
        for project_enum in SisterProject:
            name = project_enum.value
            path = self._project_paths.get(name, "")
            
            if path and os.path.exists(path):
                status = CapabilityStatus.AVAILABLE
                version = self._read_version(path)
                capabilities = self._discover_capabilities(name, path)
                print(f"  ✅ {name}: {len(capabilities)}能力")
            else:
                status = CapabilityStatus.UNAVAILABLE
                version = ""
                capabilities = []
                print(f"  ❌ {name}: 未找到")
            
            self.projects[name] = ProjectInfo(
                name=name,
                path=path,
                status=status,
                version=version,
                capabilities=capabilities,
            )
        
        print(f"\n总计: {sum(len(p.capabilities) for p in self.projects.values())}能力")
        return self.projects
    
    def _read_version(self, path: str) -> str:
        """读取项目版本"""
        # 尝试从SKILL.md读取
        skill_md = os.path.join(path, "SKILL.md")
        if os.path.exists(skill_md):
            try:
                with open(skill_md, 'r', encoding='utf-8') as f:
                    for line in f:
                        if 'version:' in line.lower() or '版本' in line:
                            return line.strip()[:50]
            except:
                pass
        return "unknown"
    
    def _discover_capabilities(self, project_name: str, path: str) -> List[CapabilityInfo]:
        """发现项目中的能力模块"""
        capabilities = []
        
        # 扫描capabilities目录
        cap_dir = os.path.join(path, "capabilities")
        if os.path.exists(cap_dir):
            for name in os.listdir(cap_dir):
                cap_path = os.path.join(cap_dir, name)
                if os.path.isdir(cap_path) and name.startswith("cap_"):
                    capabilities.append(CapabilityInfo(
                        name=name,
                        project=project_name,
                        description=f"{project_name}的{name}能力",
                        status=CapabilityStatus.AVAILABLE,
                        entry_point=cap_path,
                    ))
        
        # 扫描scripts目录（ai-video-editor的脚本能力）
        scripts_dir = os.path.join(path, "scripts")
        if os.path.exists(scripts_dir):
            for name in os.listdir(scripts_dir):
                if name.endswith(".py") and not name.startswith("_"):
                    cap_name = name.replace(".py", "")
                    capabilities.append(CapabilityInfo(
                        name=cap_name,
                        project=project_name,
                        description=f"{project_name}的{cap_name}脚本",
                        status=CapabilityStatus.AVAILABLE,
                        entry_point=os.path.join(scripts_dir, name),
                        tags=["script"],
                    ))
        
        return capabilities
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取所有项目状态摘要
        Returns: 状态字典
        """
        status = {
            "projects": {},
            "total_capabilities": 0,
            "available_projects": 0,
        }
        
        for name, project in self.projects.items():
            status["projects"][name] = {
                "status": project.status.value,
                "version": project.version,
                "capabilities_count": len(project.capabilities),
                "path": project.path,
            }
            status["total_capabilities"] += len(project.capabilities)
            if project.status == CapabilityStatus.AVAILABLE:
                status["available_projects"] += 1
        
        return status
    
    def call(self, project: str, capability: str, method: str = None, **kwargs) -> Dict[str, Any]:
        """
        统一调用接口
        
        Args:
            project: 项目名（ai-video-editor/anysearch-skill/Comfyui-controls-skill/Blender-controls-skill）
            capability: 能力名
            method: 方法名（可选）
            **kwargs: 调用参数
        
        Returns: 调用结果
        """
        project_info = self.projects.get(project)
        if not project_info:
            return {"status": "error", "error": f"项目{project}未发现，请先调用discover()"}
        
        if project_info.status != CapabilityStatus.AVAILABLE:
            return {"status": "error", "error": f"项目{project}不可用"}
        
        # 查找能力
        cap_info = next((c for c in project_info.capabilities if c.name == capability), None)
        if not cap_info:
            return {"status": "error", "error": f"能力{capability}未找到"}
        
        # 动态导入并调用
        try:
            cap_path = cap_info.entry_point
            if os.path.isdir(cap_path):
                # 目录型能力，尝试导入__init__或主模块
                init_file = os.path.join(cap_path, "__init__.py")
                if os.path.exists(init_file):
                    module_path = init_file
                else:
                    # 查找主py文件
                    py_files = [f for f in os.listdir(cap_path) if f.endswith(".py") and not f.startswith("_")]
                    if py_files:
                        module_path = os.path.join(cap_path, py_files[0])
                    else:
                        return {"status": "error", "error": f"能力{capability}无入口模块"}
            else:
                module_path = cap_path
            
            # 动态导入
            spec = importlib.util.spec_from_file_location(capability, module_path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[capability] = module
            spec.loader.exec_module(module)
            
            # 调用方法
            if method and hasattr(module, method):
                func = getattr(module, method)
                result = func(**kwargs)
                return {"status": "success", "result": result}
            elif hasattr(module, 'main'):
                result = module.main(**kwargs)
                return {"status": "success", "result": result}
            else:
                return {"status": "success", "module_loaded": True, "available_methods": [m for m in dir(module) if not m.startswith('_')]}
        
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def list_capabilities(self, project: str = None) -> List[Dict[str, Any]]:
        """
        列出所有能力（可按项目筛选）
        """
        result = []
        for name, project_info in self.projects.items():
            if project and name != project:
                continue
            for cap in project_info.capabilities:
                result.append({
                    "project": name,
                    "name": cap.name,
                    "status": cap.status.value,
                    "description": cap.description,
                    "tags": cap.tags,
                })
        return result


# 全局单例
_api_instance: Optional[UnifiedAPI] = None


def get_api() -> UnifiedAPI:
    """获取统一API单例"""
    global _api_instance
    if _api_instance is None:
        _api_instance = UnifiedAPI()
        _api_instance.discover()
    return _api_instance


if __name__ == "__main__":
    print("四姊妹项目统一API接口 v1.0")
    print("=" * 60)
    
    api = UnifiedAPI()
    projects = api.discover()
    
    print("\n项目状态:")
    status = api.get_status()
    print(f"  可用项目: {status['available_projects']}/4")
    print(f"  总能力数: {status['total_capabilities']}")
    
    print("\n能力列表:")
    for cap in api.list_capabilities():
        print(f"  [{cap['project']}] {cap['name']}: {cap['status']}")
