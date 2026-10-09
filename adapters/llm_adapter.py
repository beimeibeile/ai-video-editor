"""
LLM适配器（LLM Adapter）
统一多种LLM后端的调用接口，实现内部规范 ↔ 外部API格式的双向翻译。

支持的提供商：
- host: 宿主平台LLM（最高优先级）
- openai: OpenAI兼容API
- ark/doubao: 火山方舟/豆包
- ollama/local: 本地Ollama
- mock: 模拟（最低优先级）
"""

import logging
logger = logging.getLogger(__name__)


import os
import json
from typing import Dict, Any
from .base_adapter import BaseAdapter
from .internal_schema import (
    CapabilityType, ProviderPriority, CapabilityStatus,
    AdapterConfig, LLMRequest, LLMResponse,
)


class LLMAdapter(BaseAdapter):
    """LLM适配器"""

    capability_type = CapabilityType.LLM

    def __init__(self, config: AdapterConfig = None):
        super().__init__(config)
        self._client = None
        self._init_client()

    def _init_client(self):
        """初始化LLM客户端（复用现有llm_client）"""
        try:
            import sys
            sys.path.insert(0, os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "scripts"
            ))
            from llm_client import LLMClient

            provider = self.config.provider if self.config.provider != "auto" else None
            self._client = LLMClient(
                provider=provider or "auto",
                api_key=self.config.api_key or None,
                base_url=self.config.base_url or None,
                model=self.config.model or None,
                timeout=self.config.timeout,
            )
            self._status.provider = self._client.provider
            self._status.model = self._client.model
            self._status.available = self._client.is_available
        except Exception as e:
            self._status.error = f"LLM客户端初始化失败: {e}"
            self._status.available = False

    def _detect_availability(self) -> bool:
        """探测LLM可用性"""
        if self._client:
            return self._client.is_available
        return False

    def _translate_request(self, internal_request: LLMRequest) -> Dict[str, Any]:
        """将内部规范LLM请求翻译为外部调用参数"""
        return {
            "message": internal_request.message,
            "system_prompt": internal_request.system_prompt,
            "temperature": internal_request.temperature,
            "max_tokens": internal_request.max_tokens,
            "response_format": internal_request.response_format,
        }

    def _call_external(self, external_request: Dict[str, Any]) -> Dict[str, Any]:
        """调用LLM客户端"""
        if external_request["response_format"] == "json":
            result = self._client.chat_json(
                message=external_request["message"],
                system_prompt=external_request["system_prompt"],
                temperature=external_request["temperature"],
                max_tokens=external_request["max_tokens"],
            )
            return {"type": "json", "data": result}
        else:
            result = self._client.chat(
                message=external_request["message"],
                system_prompt=external_request["system_prompt"],
                temperature=external_request["temperature"],
                max_tokens=external_request["max_tokens"],
            )
            return {"type": "text", "data": result}

    def _translate_response(self, external_response: Dict[str, Any]) -> LLMResponse:
        """将外部响应翻译为内部规范LLMResponse"""
        data = external_response.get("data")
        resp_type = external_response.get("type", "text")

        if data is None:
            return LLMResponse(
                success=False,
                error="LLM返回空响应",
                provider=self._status.provider,
            )

        if resp_type == "json":
            return LLMResponse(
                success=True,
                content=json.dumps(data, ensure_ascii=False) if isinstance(data, dict) else str(data),
                parsed_json=data if isinstance(data, dict) else None,
                provider=self._status.provider,
                model=self._status.model,
            )
        else:
            return LLMResponse(
                success=True,
                content=str(data),
                provider=self._status.provider,
                model=self._status.model,
            )

    def chat(self, message: str, system_prompt: str = "",
             temperature: float = 0.7, max_tokens: int = 2000) -> LLMResponse:
        """便捷方法：文本聊天"""
        request = LLMRequest(
            message=message,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format="text",
        )
        return self.execute(request)

    def chat_json(self, message: str, system_prompt: str = "",
                  temperature: float = 0.3, max_tokens: int = 3000) -> LLMResponse:
        """便捷方法：JSON响应"""
        request = LLMRequest(
            message=message,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format="json",
        )
        return self.execute(request)


def create_llm_adapter(provider: str = "auto") -> LLMAdapter:
    """工厂方法：创建LLM适配器"""
    config = AdapterConfig(
        capability_type=CapabilityType.LLM,
        provider=provider,
    )
    return LLMAdapter(config)
