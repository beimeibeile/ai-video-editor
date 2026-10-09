"""
TTS适配器（TTS Adapter）
统一多种TTS后端的调用接口。

支持的提供商：
- comfyui: ComfyUI Qwen3-TTS（当前主力）
- host: 宿主平台TTS
- edge: Edge TTS（降级）
- mock: 模拟
"""

import logging
logger = logging.getLogger(__name__)


import os
from typing import Dict, Any
from .base_adapter import BaseAdapter
from .internal_schema import (
    CapabilityType, AdapterConfig, TTSRequest, TTSResponse,
)


class TTSAdapter(BaseAdapter):
    """TTS适配器"""

    capability_type = CapabilityType.TTS

    def __init__(self, config: AdapterConfig = None):
        super().__init__(config)
        self._executor = None
        self._init_executor()

    def _init_executor(self):
        """初始化TTS执行器（复用现有tts_executor）"""
        try:
            import sys
            sys.path.insert(0, os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "scripts"
            ))
            from tts_executor import TTSExecutor
            self._executor = TTSExecutor()
            self._status.provider = "comfyui"
            self._status.available = True
        except Exception as e:
            self._status.error = f"TTS执行器初始化失败: {e}"
            self._status.available = False

    def _detect_availability(self) -> bool:
        return self._executor is not None

    def _translate_request(self, internal_request: TTSRequest) -> Dict[str, Any]:
        return {
            "text": internal_request.text,
            "voice": internal_request.voice,
            "emotion": internal_request.emotion,
            "speed": internal_request.speed,
        }

    def _call_external(self, external_request: Dict[str, Any]) -> Dict[str, Any]:
        if self._executor:
            result = self._executor.generate(
                text=external_request["text"],
                voice=external_request.get("voice", "default"),
                emotion=external_request.get("emotion", "neutral"),
            )
            return result or {}
        return {}

    def _translate_response(self, external_response: Dict[str, Any]) -> TTSResponse:
        if not external_response:
            return TTSResponse(success=False, error="TTS生成失败")

        return TTSResponse(
            success=True,
            audio_path=external_response.get("output_path", ""),
            duration_sec=external_response.get("duration", 0.0),
            provider=self._status.provider,
            voice_used=external_response.get("voice", ""),
        )

    def generate(self, text: str, voice: str = "default",
                 emotion: str = "neutral") -> TTSResponse:
        """便捷方法：生成语音"""
        request = TTSRequest(text=text, voice=voice, emotion=emotion)
        return self.execute(request)
