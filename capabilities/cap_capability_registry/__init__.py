"""
cap_capability_registry - 四项目能力注册中心
统一管理 ai-video-editor / anysearch-skill / comfyui-controls / blender-controls 的能力
"""
from .registry import CapabilityRegistry, Capability, CapabilityType, ProjectRole

__all__ = ["CapabilityRegistry", "Capability", "CapabilityType", "ProjectRole"]
__version__ = "0.1.0"
