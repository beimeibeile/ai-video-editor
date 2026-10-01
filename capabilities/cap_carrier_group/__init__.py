"""
航空母舰战斗群 - 四姊妹项目能力联动中心

ai-video-editor = 航空母舰（指挥中枢）
anysearch-skill = 雷达（深度搜索）
comfyui-controls-skill = 舰载机（AI出图出视频）
blender-controls-skill = 导弹（3D特效）
"""
from .carrier_group import CarrierGroup, ProjectStatus, SISTER_PROJECTS

__all__ = ["CarrierGroup", "ProjectStatus", "SISTER_PROJECTS"]
__version__ = "1.0.0"
