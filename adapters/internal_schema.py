"""
内部规范定义（Internal Schema）
所有外部能力的输入输出必须先转换为内部规范，再交给核心引擎使用。

核心原则：
- 内部系统只认识内部规范，不直接处理外部API格式
- 适配器负责双向翻译：外部格式 ↔ 内部规范
- 外部API变化只影响适配器，不影响核心引擎
"""

import logging
logger = logging.getLogger(__name__)


from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from enum import Enum


class CapabilityType(Enum):
    """能力类型枚举"""
    LLM = "llm"                    # 大语言模型
    TTS = "tts"                    # 语音合成
    SFX = "sfx"                    # 音效生成
    VIDEO_GEN = "video_gen"        # 视频生成
    IMAGE_GEN = "image_gen"        # 图像生成
    MUSIC = "music"                # 音乐生成
    SUBTITLE = "subtitle"          # 字幕生成
    HOST = "host"                  # 宿主综合能力


class ProviderPriority(Enum):
    """提供商优先级"""
    HOST = 0        # 宿主平台（最高）
    CLOUD = 1       # 云端API
    LOCAL = 2       # 本地部署
    MOCK = 3        # 模拟（最低）


@dataclass
class CapabilityStatus:
    """能力状态"""
    capability_type: CapabilityType
    available: bool
    provider: str = ""
    provider_priority: ProviderPriority = ProviderPriority.MOCK
    model: str = ""
    latency_ms: int = 0
    quality_score: float = 0.0
    error: str = ""


@dataclass
class LLMRequest:
    """LLM请求（内部规范）"""
    message: str
    system_prompt: str = ""
    temperature: float = 0.7
    max_tokens: int = 2000
    response_format: str = "text"  # text / json
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMResponse:
    """LLM响应（内部规范）"""
    success: bool
    content: str = ""
    parsed_json: Optional[Dict[str, Any]] = None
    provider: str = ""
    model: str = ""
    tokens_used: int = 0
    latency_ms: int = 0
    error: str = ""


@dataclass
class TTSRequest:
    """TTS请求（内部规范）"""
    text: str
    voice: str = "default"
    emotion: str = "neutral"
    speed: float = 1.0
    pitch: float = 1.0
    output_format: str = "wav"
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TTSResponse:
    """TTS响应（内部规范）"""
    success: bool
    audio_path: str = ""
    duration_sec: float = 0.0
    sample_rate: int = 24000
    provider: str = ""
    voice_used: str = ""
    error: str = ""


@dataclass
class SFXRequest:
    """音效请求（内部规范）"""
    description: str
    duration_sec: float = 3.0
    category: str = "general"  # general/impact/whoosh/ambient/voice_effect
    output_format: str = "wav"
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SFXResponse:
    """音效响应（内部规范）"""
    success: bool
    audio_path: str = ""
    duration_sec: float = 0.0
    category: str = ""
    quality_rating: str = ""  # A/B/C
    provider: str = ""
    error: str = ""


@dataclass
class AdapterConfig:
    """适配器配置"""
    capability_type: CapabilityType
    provider: str = "auto"
    api_key: str = ""
    base_url: str = ""
    model: str = ""
    timeout: int = 60
    fallback_enabled: bool = True
    custom_params: Dict[str, Any] = field(default_factory=dict)
