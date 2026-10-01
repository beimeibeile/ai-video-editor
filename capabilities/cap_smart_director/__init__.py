"""
cap_smart_director - 智能调度器
输入剧本 → 输出调度计划（特效/素材/转场自动匹配）
"""
from .smart_director import SmartDirector, DirectionPlan, ShotDirection, EffectAssignment, MaterialAssignment

__all__ = ["SmartDirector", "DirectionPlan", "ShotDirection", "EffectAssignment", "MaterialAssignment"]
__version__ = "0.1.0"
