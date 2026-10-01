"""
自然语言指令引擎
用户用自然语言描述需求，系统自动解析意图、提取参数、生成视频
"""
from .natural_language import NaturalLanguageEngine, ParsedCommand

__all__ = ["NaturalLanguageEngine", "ParsedCommand"]
__version__ = "1.0.0"
