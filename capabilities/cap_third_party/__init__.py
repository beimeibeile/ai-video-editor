"""
第三方工具集成模块
统一适配器层，与OBS/PR/AE/Blender/ComfyUI等工具集成
"""
from .tool_base import ToolAdapterBase, ToolRegistry, ToolState, ToolInfo
from .blender_adapter import BlenderAdapter
from .comfyui_adapter import ComfyUIAdapter

__all__ = [
    "ToolAdapterBase",
    "ToolRegistry",
    "ToolState",
    "ToolInfo",
    "BlenderAdapter",
    "ComfyUIAdapter",
]
__version__ = "1.0.0"
