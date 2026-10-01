"""
口语关键词标准化模块
将用户口语中的非标准表达转换为系统标准关键词
"""
from .keyword_normalizer import KeywordNormalizer, NormalizedResult, normalize_text, STANDARD_KEYWORDS

__all__ = ["KeywordNormalizer", "NormalizedResult", "normalize_text", "STANDARD_KEYWORDS"]
__version__ = "1.0.0"
