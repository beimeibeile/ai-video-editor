"""
多模态交互接口
支持文字+语音+图片+参考视频多模态输入，统一交互接口
"""
from .multimodal import MultimodalInterface, MultimodalInput, ProcessedInput

__all__ = ["MultimodalInterface", "MultimodalInput", "ProcessedInput"]
__version__ = "1.0.0"
