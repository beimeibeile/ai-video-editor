"""
SFX适配器（SFX Adapter）
统一多种音效生成后端的调用接口。

支持的提供商：
- comfyui: ComfyUI Stable Audio 3（当前主力）
- library: 本地音效库（降级）
- host: 宿主平台音效
- mock: 模拟
"""

import os
from typing import Dict, Any
from .base_adapter import BaseAdapter
from .internal_schema import (
    CapabilityType, AdapterConfig, SFXRequest, SFXResponse,
)


class SFXAdapter(BaseAdapter):
    """SFX适配器"""

    capability_type = CapabilityType.SFX

    def __init__(self, config: AdapterConfig = None):
        super().__init__(config)
        self._executor = None
        self._library = None
        self._init_executor()

    def _init_executor(self):
        """初始化音效执行器（复用现有sfx_executor和sound_library）"""
        try:
            import sys
            sys.path.insert(0, os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "scripts"
            ))
            from sfx_executor import SFXExecutor
            self._executor = SFXExecutor()
            self._status.provider = "comfyui"
            self._status.available = True
        except Exception as e:
            self._status.error = f"SFX执行器初始化失败: {e}"
            self._status.available = False

    def _detect_availability(self) -> bool:
        return self._executor is not None

    def _translate_request(self, internal_request: SFXRequest) -> Dict[str, Any]:
        return {
            "description": internal_request.description,
            "duration": internal_request.duration_sec,
            "category": internal_request.category,
        }

    def _call_external(self, external_request: Dict[str, Any]) -> Dict[str, Any]:
        if self._executor:
            result = self._executor.generate(
                description=external_request["description"],
                duration=external_request.get("duration", 3.0),
            )
            return result or {}
        return {}

    def _translate_response(self, external_response: Dict[str, Any]) -> SFXResponse:
        if not external_response:
            return SFXResponse(success=False, error="音效生成失败")

        return SFXResponse(
            success=True,
            audio_path=external_response.get("output_path", ""),
            duration_sec=external_response.get("duration", 0.0),
            category=external_response.get("category", "general"),
            quality_rating=external_response.get("rating", "B"),
            provider=self._status.provider,
        )

    def generate(self, description: str, duration_sec: float = 3.0,
                 category: str = "general") -> SFXResponse:
        """便捷方法：生成音效"""
        request = SFXRequest(
            description=description,
            duration_sec=duration_sec,
            category=category,
        )
        return self.execute(request)
