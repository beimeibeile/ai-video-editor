"""
用户偏好学习系统
记录用户使用习惯和偏好，自动调整生成参数，越用越懂用户
"""
from .user_preferences import UserPreferenceLearner, UserProfile, GenerationRecord

__all__ = ["UserPreferenceLearner", "UserProfile", "GenerationRecord"]
__version__ = "1.0.0"
