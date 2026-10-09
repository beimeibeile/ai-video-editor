"""
适配器基类（Base Adapter）
所有外部能力适配器必须继承此类，实现统一接口。

核心职责：
1. 统一外部能力的调用接口
2. 双向格式翻译：外部API格式 ↔ 内部规范
3. 自动降级链管理
4. 能力状态探测与健康检查
"""

import logging
logger = logging.getLogger(__name__)


import time
from abc import ABC, abstractmethod
from typing import Dict, Any, List
from .internal_schema import (
    CapabilityType, ProviderPriority, CapabilityStatus,
    AdapterConfig,
)


class BaseAdapter(ABC):
    """适配器基类"""

    # 子类必须指定能力类型
    capability_type: CapabilityType = None

    def __init__(self, config: AdapterConfig = None):
        self.config = config or AdapterConfig(capability_type=self.capability_type)
        self._status = CapabilityStatus(
            capability_type=self.capability_type,
            available=False,
            provider=self.config.provider,
        )
        self._fallback_chain: List['BaseAdapter'] = []

    @abstractmethod
    def _detect_availability(self) -> bool:
        """探测当前提供商是否可用（子类实现）"""
        pass

    @abstractmethod
    def _translate_request(self, internal_request: Any) -> Dict[str, Any]:
        """将内部规范请求翻译为外部API格式（子类实现）"""
        pass

    @abstractmethod
    def _call_external(self, external_request: Dict[str, Any]) -> Dict[str, Any]:
        """调用外部API（子类实现）"""
        pass

    @abstractmethod
    def _translate_response(self, external_response: Dict[str, Any]) -> Any:
        """将外部API响应翻译为内部规范（子类实现）"""
        pass

    def execute(self, internal_request: Any) -> Any:
        """
        统一执行入口（模板方法模式）

        流程：
        1. 检查可用性
        2. 翻译请求（内部→外部）
        3. 调用外部API
        4. 翻译响应（外部→内部）
        5. 失败时自动降级
        """
        start_time = time.time()

        # 1. 检查可用性
        if not self._status.available:
            self._detect_availability()

        if not self._status.available:
            return self._fallback(internal_request)

        try:
            # 2. 翻译请求
            external_request = self._translate_request(internal_request)

            # 3. 调用外部API
            external_response = self._call_external(external_request)

            # 4. 翻译响应
            internal_response = self._translate_response(external_response)

            # 更新状态
            latency_ms = int((time.time() - start_time) * 1000)
            self._status.latency_ms = latency_ms

            if hasattr(internal_response, 'latency_ms'):
                internal_response.latency_ms = latency_ms
            if hasattr(internal_response, 'provider'):
                internal_response.provider = self._status.provider

            return internal_response

        except Exception as e:
            # 5. 失败降级
            self._status.available = False
            self._status.error = str(e)
            return self._fallback(internal_request)

    def _fallback(self, internal_request: Any) -> Any:
        """自动降级到下一个优先级的适配器"""
        if not self.config.fallback_enabled or not self._fallback_chain:
            # 无降级链，返回失败响应
            return self._make_failure_response("所有提供商均不可用")

        for fallback_adapter in self._fallback_chain:
            try:
                if fallback_adapter.check_availability():
                    result = fallback_adapter.execute(internal_request)
                    if result and getattr(result, 'success', False):
                        return result
            except Exception:
                continue

        return self._make_failure_response("降级链全部失败")

    def _make_failure_response(self, error: str) -> Any:
        """构造失败响应（子类可覆盖）"""
        return type('FailureResponse', (), {
            'success': False,
            'error': error,
            'provider': self._status.provider,
        })()

    def check_availability(self) -> bool:
        """检查能力可用性"""
        self._status.available = self._detect_availability()
        return self._status.available

    def get_status(self) -> CapabilityStatus:
        """获取能力状态"""
        return self._status

    def set_fallback_chain(self, adapters: List['BaseAdapter']):
        """设置降级链（按优先级排序）"""
        self._fallback_chain = adapters

    def add_fallback(self, adapter: 'BaseAdapter'):
        """添加降级适配器"""
        self._fallback_chain.append(adapter)
