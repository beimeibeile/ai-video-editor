"""
AI自动选题和脚本引擎
基于热点趋势+用户偏好+历史数据，AI自动推荐选题并生成完整脚本
"""
from .ai_topic_engine import AITopicEngine, Topic

__all__ = ["AITopicEngine", "Topic"]
__version__ = "1.0.0"
